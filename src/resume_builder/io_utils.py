from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .models import ResumeProfile, ResumeSection

_CITE_START_PATTERN = re.compile(r"\[cite_start\]")
_CITE_PATTERN = re.compile(r"\s*\[cite:\s*[0-9,\s]+\]")


def _ensure_path(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path


def _strip_citation_artifacts(raw_text: str) -> str:
    without_starts = _CITE_START_PATTERN.sub("", raw_text)
    return _CITE_PATTERN.sub("", without_starts)


def _normalize_profile_skills(raw_skills: Any) -> List[str]:
    """Accept both legacy list schema and categorized map schema for skills."""
    normalized: List[str] = []

    def _append_category(category: object, values: object) -> None:
        category_text = str(category).strip()
        if not category_text:
            return
        items: List[str] = []
        if isinstance(values, (list, tuple, set)):
            for item in values:
                item_text = str(item).strip()
                if item_text:
                    items.append(item_text)
        elif values is not None:
            value_text = str(values).strip()
            if value_text:
                items.append(value_text)
        if items:
            normalized.append(f"{category_text}: {', '.join(items)}")

    if raw_skills is None:
        return normalized
    if isinstance(raw_skills, dict):
        for category, values in raw_skills.items():
            _append_category(category, values)
        return normalized
    if isinstance(raw_skills, (list, tuple, set)):
        for entry in raw_skills:
            if isinstance(entry, dict):
                for category, values in entry.items():
                    _append_category(category, values)
                continue
            text = str(entry).strip()
            if text:
                normalized.append(text)
        return normalized
    text = str(raw_skills).strip()
    if text:
        normalized.append(text)
    return normalized


def load_profile(profile_path: str | Path) -> ResumeProfile:
    """Load structured resume profile data from YAML or JSON."""
    path = _ensure_path(Path(profile_path))
    data: Dict[str, Any]
    if path.suffix.lower() in {".yaml", ".yml"}:
        text = path.read_text()
        try:
            data = yaml.safe_load(text) or {}
        except yaml.YAMLError:
            cleaned_text = _strip_citation_artifacts(text)
            try:
                data = yaml.safe_load(cleaned_text) or {}
            except yaml.YAMLError as cleaned_error:
                raise ValueError(f"Invalid YAML profile file: {path}") from cleaned_error
    elif path.suffix.lower() == ".json":
        data = json.loads(path.read_text())
    else:
        raise ValueError("Profile file must be YAML or JSON.")

    name = data.get("name")
    if not name:
        raise ValueError("Profile data must include a 'name' field.")

    resume = ResumeProfile(
        name=name,
        headline=data.get("headline"),
        contact=data.get("contact", {}),
        summary=data.get("summary", []) or [],
        experience=data.get("experience", []) or [],
        education=data.get("education", []) or [],
        projects=data.get("projects", []) or [],
        certifications=data.get("certifications", []) or [],
        skills=_normalize_profile_skills(data.get("skills")),
    )

    for section in data.get("additional_sections", []) or []:
        resume.additional_sections.append(
            ResumeSection(
                title=section.get("title", "Additional"),
                bullets=section.get("bullets", []) or [],
                paragraphs=section.get("paragraphs", []) or [],
                meta=section.get("meta", {}) or {},
            )
        )

    return resume


def ensure_directory(path: str | Path) -> Path:
    """Create parent directory for the given output path."""
    output_path = Path(path)
    if output_path.is_dir():
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def dump_json(obj: Any, destination: str | Path) -> None:
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(obj, indent=2, ensure_ascii=False))


def _ordered_contact(contact: Dict[str, str]) -> OrderedDict[str, str]:
    ordered: OrderedDict[str, str] = OrderedDict()
    preferred_order = [
        "phone",
        "email",
        "location",
        "linkedin",
        "github",
        "website",
        "portfolio",
    ]
    for key in preferred_order:
        value = contact.get(key)
        if value:
            ordered[key] = value
    for key, value in contact.items():
        if key in ordered or not value:
            continue
        ordered[key] = value
    return ordered


def _non_empty(values: List[str]) -> List[str]:
    return [value for value in values if value]


def _canonical_experience(items: List[Dict[str, Any]]) -> List[OrderedDict[str, Any]]:
    entries: List[OrderedDict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        entry: OrderedDict[str, Any] = OrderedDict()
        for key in ("company", "role", "location", "start", "end"):
            value = item.get(key)
            if value:
                entry[key] = value
        bullets = _non_empty(list(item.get("bullets", []) or []))
        if bullets:
            entry["bullets"] = bullets
        if entry:
            entries.append(entry)
    return entries


def _canonical_education(records: List[Dict[str, Any]]) -> List[OrderedDict[str, Any]]:
    result: List[OrderedDict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        entry: OrderedDict[str, Any] = OrderedDict()
        for key in ("institution", "degree", "location", "start", "end"):
            value = record.get(key)
            if value:
                entry[key] = value
        details = _non_empty(list(record.get("details", []) or []))
        if details:
            entry["details"] = details
        if entry:
            result.append(entry)
    return result


def _canonical_projects(projects: List[Dict[str, Any]]) -> List[OrderedDict[str, Any]]:
    result: List[OrderedDict[str, Any]] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        entry: OrderedDict[str, Any] = OrderedDict()
        for key in ("name", "summary", "description"):
            value = project.get(key)
            if value:
                entry[key] = value
        technologies = _non_empty(list(project.get("technologies", []) or []))
        if technologies:
            entry["technologies"] = technologies
        bullets = _non_empty(list(project.get("bullets", []) or []))
        if bullets:
            entry["bullets"] = bullets
        if entry:
            result.append(entry)
    return result


def _canonical_certifications(certifications: List[Dict[str, Any]]) -> List[OrderedDict[str, Any]]:
    result: List[OrderedDict[str, Any]] = []
    for cert in certifications:
        if not isinstance(cert, dict):
            continue
        entry: OrderedDict[str, Any] = OrderedDict()
        for key in ("name", "issuer", "date"):
            value = cert.get(key)
            if value:
                entry[key] = value
        if entry:
            result.append(entry)
    return result


def _canonical_additional(sections: List[ResumeSection]) -> List[OrderedDict[str, Any]]:
    result: List[OrderedDict[str, Any]] = []
    for section in sections:
        entry: OrderedDict[str, Any] = OrderedDict()
        if section.title:
            entry["title"] = section.title
        bullets = _non_empty(list(section.bullets))
        if bullets:
            entry["bullets"] = bullets
        paragraphs = _non_empty(list(section.paragraphs))
        if paragraphs:
            entry["paragraphs"] = paragraphs
        if section.meta:
            entry["meta"] = section.meta
        if entry:
            result.append(entry)
    return result


def _canonical_skills(skills: List[str]) -> List[str] | OrderedDict[str, List[str]]:
    grouped: OrderedDict[str, List[str]] = OrderedDict()
    uncategorized: List[str] = []
    has_grouped = False

    for skill in skills:
        text = str(skill).strip()
        if not text:
            continue
        if ":" not in text:
            uncategorized.append(text)
            continue
        category, values = text.split(":", 1)
        category_key = re.sub(r"[^a-z0-9]+", "_", category.lower()).strip("_")
        items = [value.strip() for value in values.split(",") if value.strip()]
        if not category_key or not items:
            uncategorized.append(text)
            continue
        has_grouped = True
        bucket = grouped.setdefault(category_key, [])
        for item in items:
            if item not in bucket:
                bucket.append(item)

    if has_grouped:
        if uncategorized:
            grouped.setdefault("additional", [])
            for item in uncategorized:
                if item not in grouped["additional"]:
                    grouped["additional"].append(item)
        return grouped
    return uncategorized


def profile_to_canonical(profile: ResumeProfile) -> OrderedDict[str, Any]:
    data: OrderedDict[str, Any] = OrderedDict()
    data["name"] = profile.name
    if profile.headline:
        data["headline"] = profile.headline
    if profile.contact:
        data["contact"] = _ordered_contact(profile.contact)
    summary_lines = _non_empty(list(profile.summary))
    if summary_lines:
        data["summary"] = summary_lines
    experience_entries = _canonical_experience(profile.experience)
    if experience_entries:
        data["experience"] = experience_entries
    education_entries = _canonical_education(profile.education)
    if education_entries:
        data["education"] = education_entries
    skills = _non_empty(list(profile.skills))
    if skills:
        data["skills"] = _canonical_skills(skills)
    project_entries = _canonical_projects(profile.projects)
    if project_entries:
        data["projects"] = project_entries
    certification_entries = _canonical_certifications(profile.certifications)
    if certification_entries:
        data["certifications"] = certification_entries
    additional_entries = _canonical_additional(profile.additional_sections)
    if additional_entries:
        data["additional_sections"] = additional_entries
    return data


def save_profile(profile: ResumeProfile, destination: str | Path) -> Path:
    """Persist a resume profile to YAML in the canonical schema."""
    data = profile_to_canonical(profile)
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return dest
