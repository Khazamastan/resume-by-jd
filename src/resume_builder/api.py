from __future__ import annotations

import os
import base64
from contextlib import asynccontextmanager
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import (
    analyze_job_description,
    build_resume_document,
    extract_reference_structure,
    render_resume,
)
from .io_utils import load_profile, profile_to_canonical, save_profile
from .latex_renderer import render_latex_resume
from .models import ResumeDocument, ResumeProfile, ResumeSection, Theme
from .profile_generator import build_profile_from_reference
from .resume_text_parser import parse_resume_text
import yaml
import re


class SectionUpdate(BaseModel):
    title: str
    paragraphs: List[str] = Field(default_factory=list)
    bullets: List[str] = Field(default_factory=list)
    meta: Optional[Dict[str, object]] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    headline: Optional[str] = None
    contact: Optional[Dict[str, str]] = None


class UpdatePayload(BaseModel):
    sections: List[SectionUpdate] = Field(default_factory=list)
    profile: Optional[ProfileUpdate] = None
    theme: Optional[Dict[str, object]] = None
    resume_text: Optional[str] = None


RESUME_SESSIONS: Dict[str, ResumeDocument] = {}

_HEX_COLOR_PATTERN = re.compile(r"^#?(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")
MIN_FONT_SIZE = 6.0
MAX_FONT_SIZE = 24.0
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REFERENCE_PATH = PROJECT_ROOT / "resume.pdf"
DEFAULT_PROFILE_PATH = PROJECT_ROOT / "profile.yaml"
SAMPLES_ROOT = PROJECT_ROOT / "samples"
DEFAULT_SAMPLE_PROFILE = "Khaja"
PROFILE_FILE_CANDIDATES = ("profile.yaml", "profile.yml", "profile.json")
ATS_FONT_CHOICES = (
    "Calibri",
    "Arial",
    "Georgia",
    "Helvetica",
    "SpaceGrotesk",
    "Garamond",
    "Tahoma",
    "Times New Roman",
    "Cambria",
    "Montserrat",
    "Lato",
    "Aptos",
)
_ATS_FONT_LOOKUP = {name.lower(): name for name in ATS_FONT_CHOICES}
_ATS_FONT_LOOKUP["space grotesk"] = "SpaceGrotesk"
_CONTACT_FIELD_ALIASES: Dict[str, tuple[str, ...]] = {
    "phone": ("phone", "mobile"),
    "email": ("email",),
    "location": ("location",),
    "linkedin": ("linkedin",),
    "notice_note": ("notice_note", "noticeNote", "notice"),
}
_HEADLINE_SPLIT_PATTERN = re.compile(r"\s+at\s+", re.IGNORECASE)
_HEADLINE_ROLE_HINT_PATTERN = re.compile(
    r"\b(engineer|developer|architect|manager|lead|staff|intern|consultant|analyst|"
    r"director|principal|designer|specialist|frontend|front-end|full[ -]?stack|devops|qa|sde)\b",
    re.IGNORECASE,
)
_HEADLINE_COMPANY_HINT_PATTERN = re.compile(
    r"\b(inc|corp|corporation|llc|ltd|limited|plc|technologies|technology|solutions|systems|"
    r"group|labs|university|college|school|consulting)\b",
    re.IGNORECASE,
)
_HEADLINE_COMMON_COMPANIES = {
    "oracle",
    "pwc",
    "google",
    "microsoft",
    "amazon",
    "meta",
    "apple",
    "infosys",
    "wipro",
    "tcs",
    "ibm",
    "accenture",
    "deloitte",
    "xactly",
    "nineleaps",
    "minewhat",
    "thrymr",
}
_ISO_DATE_PATTERN = re.compile(r"^(\d{4})-(\d{2})(?:-(\d{2}))?$")
_MONTH_ABBR = (
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _normalize_ats_font_family(value: str | None) -> str:
    if not value:
        return "Calibri"
    normalized = value.strip().lower()
    return _ATS_FONT_LOOKUP.get(normalized, "Calibri")


def _find_profile_file(profile_dir: Path) -> Optional[Path]:
    for filename in PROFILE_FILE_CANDIDATES:
        candidate = profile_dir / filename
        if candidate.exists():
            return candidate
    return None


def _discover_sample_profiles() -> List[Dict[str, str]]:
    if not SAMPLES_ROOT.exists():
        return []

    profiles: List[Dict[str, str]] = []
    for entry in sorted(SAMPLES_ROOT.iterdir(), key=lambda item: item.name.lower()):
        if not entry.is_dir():
            continue
        reference_path = entry / "resume.pdf"
        profile_path = _find_profile_file(entry)
        if not reference_path.exists() or profile_path is None:
            continue
        profiles.append(
            {
                "id": entry.name,
                "label": entry.name,
                "reference_path": str(reference_path),
                "profile_path": str(profile_path),
            }
        )
    return profiles


def _resolve_sample_profile_paths(sample_profile: Optional[str]) -> tuple[Path | None, Path | None]:
    discovered_profiles = _discover_sample_profiles()
    if not discovered_profiles:
        return None, None

    requested_profile = (sample_profile or DEFAULT_SAMPLE_PROFILE).strip()
    if not requested_profile:
        requested_profile = DEFAULT_SAMPLE_PROFILE

    for profile in discovered_profiles:
        if profile["id"].lower() == requested_profile.lower():
            return Path(profile["reference_path"]), Path(profile["profile_path"])

    available_profiles = ", ".join(profile["id"] for profile in discovered_profiles)
    raise HTTPException(
        status_code=400,
        detail=f"Unknown sample_profile '{requested_profile}'. Available options: {available_profiles}.",
    )


def _normalize_hex_color(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        raise ValueError("Color value is empty.")
    if not _HEX_COLOR_PATTERN.fullmatch(candidate):
        raise ValueError(f"Invalid color value: {value!r}")
    if not candidate.startswith("#"):
        candidate = f"#{candidate}"
    if len(candidate) == 4:
        candidate = "#" + "".join(ch * 2 for ch in candidate[1:])
    return candidate.lower()


def _normalize_font_size(value: float, field_name: str) -> float:
    if value < MIN_FONT_SIZE or value > MAX_FONT_SIZE:
        raise ValueError(
            f"{field_name} must be between {MIN_FONT_SIZE:.0f} and {MAX_FONT_SIZE:.0f}."
        )
    return value


def _theme_from_payload(payload: Optional[Dict[str, object]], base_theme: Optional[Theme] = None) -> Theme:
    theme = Theme(**asdict(base_theme)) if isinstance(base_theme, Theme) else Theme()
    if not isinstance(payload, dict):
        theme.ats_font_family = _normalize_ats_font_family(getattr(theme, "ats_font_family", None))
        return theme

    text_fields = ("body_font", "heading_font", "template", "ats_font_family")
    for field_name in text_fields:
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            setattr(theme, field_name, value.strip())

    color_fields = ("primary_color", "accent_color")
    for field_name in color_fields:
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            setattr(theme, field_name, _normalize_hex_color(value.strip()))

    numeric_fields = (
        "body_size",
        "heading_size",
        "line_height",
        "margin_left",
        "margin_right",
        "margin_top",
        "margin_bottom",
        "page_width",
        "page_height",
    )
    for field_name in numeric_fields:
        value = payload.get(field_name)
        if value is None:
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue
        if field_name in {"body_size", "heading_size"}:
            numeric_value = _normalize_font_size(numeric_value, field_name)
        setattr(theme, field_name, numeric_value)

    theme.ats_font_family = _normalize_ats_font_family(getattr(theme, "ats_font_family", None))

    return theme


def _encode_pdf(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("utf-8")


def _build_ats_theme(base_theme: Theme) -> Theme:
    page_width = base_theme.page_width or 595.0
    page_height = base_theme.page_height or 842.0
    ats_font_family = _normalize_ats_font_family(getattr(base_theme, "ats_font_family", None))
    primary_color = (base_theme.primary_color or "#111111").strip() or "#111111"
    accent_color = (base_theme.accent_color or primary_color).strip() or primary_color
    body_size = float(base_theme.body_size or 10.0)
    if body_size <= 0:
        body_size = 10.0
    heading_size = float(base_theme.heading_size or max(body_size + 2.0, 12.0))
    if heading_size <= 0:
        heading_size = max(body_size + 2.0, 12.0)
    heading_size = max(heading_size, body_size + 0.5)
    return Theme(
        body_font=ats_font_family,
        body_size=body_size,
        heading_font=f"{ats_font_family}-Bold",
        heading_size=heading_size,
        primary_color=primary_color,
        accent_color=accent_color,
        line_height=1.2,
        margin_left=42.0,
        margin_right=42.0,
        margin_top=36.0,
        margin_bottom=36.0,
        page_width=page_width,
        page_height=page_height,
        template="ats",
        ats_font_family=ats_font_family,
    )


def _build_ats_document(document: ResumeDocument) -> ResumeDocument:
    return ResumeDocument(
        profile=document.profile,
        sections=document.sections,
        theme=_build_ats_theme(document.theme),
    )


def _profile_payload(profile: ResumeProfile) -> Dict[str, object]:
    return {
        "name": profile.name,
        "headline": profile.headline,
        "contact": profile.contact,
    }


def _first_non_empty_contact_value(contact: Dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = str(contact.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _fill_missing_contact_from_profile(
    parsed_profile: ResumeProfile,
    fallback_profile: ResumeProfile | None,
) -> None:
    if fallback_profile is None:
        return

    merged_contact = dict(parsed_profile.contact or {})
    fallback_contact = dict(fallback_profile.contact or {})

    for field, aliases in _CONTACT_FIELD_ALIASES.items():
        existing = str(merged_contact.get(field, "") or "").strip()
        if existing:
            merged_contact[field] = existing
            continue
        fallback_value = _first_non_empty_contact_value(fallback_contact, aliases)
        if fallback_value:
            merged_contact[field] = fallback_value

    parsed_profile.contact = merged_contact


def _headline_from_experience(profile: ResumeProfile) -> str:
    for item in profile.experience or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "") or "").strip()
        company = str(item.get("company", "") or "").strip()
        if role and company:
            return f"{role} at {company}"
        if role:
            return role
        if company:
            return company
    return ""


def _normalized_phrase(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def _compact_phrase(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalized_phrase(value))


def _split_headline_at(value: str) -> tuple[str, str] | None:
    text = str(value or "").strip()
    if not text:
        return None
    matches = list(_HEADLINE_SPLIT_PATTERN.finditer(text))
    if not matches:
        return None
    marker = matches[-1]
    left = text[:marker.start()].strip()
    right = text[marker.end():].strip()
    if not left or not right:
        return None
    return left, right


def _looks_like_company_headline_fragment(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    lowered = _normalized_phrase(text)
    if lowered in _HEADLINE_COMMON_COMPANIES:
        return True
    if _HEADLINE_COMPANY_HINT_PATTERN.search(text):
        return True
    if text.isupper() and len(text) <= 8:
        return True
    return False


def _looks_like_role_headline_fragment(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    return bool(_HEADLINE_ROLE_HINT_PATTERN.search(text))


def _normalize_headline_order(headline: str | None, profile: ResumeProfile | None = None) -> str:
    text = str(headline or "").strip()
    if not text:
        return ""

    pair = _split_headline_at(text)
    if not pair:
        return text
    left, right = pair
    left_compact = _compact_phrase(left)
    right_compact = _compact_phrase(right)

    if profile is not None:
        for item in profile.experience or []:
            if not isinstance(item, dict):
                continue
            company = str(item.get("company", "") or "").strip()
            role = str(item.get("role", "") or item.get("title", "") or "").strip()
            if not company or not role:
                continue
            company_compact = _compact_phrase(company)
            role_compact = _compact_phrase(role)
            if left_compact == company_compact and right_compact == role_compact:
                return f"{role} at {company}"
            if left_compact == role_compact and right_compact == company_compact:
                return f"{role} at {company}"

    left_company_like = _looks_like_company_headline_fragment(left)
    right_company_like = _looks_like_company_headline_fragment(right)
    left_role_like = _looks_like_role_headline_fragment(left)
    right_role_like = _looks_like_role_headline_fragment(right)

    if right_role_like and not left_role_like and not right_company_like:
        return f"{right} at {left}"

    if left_company_like and not right_company_like and right_role_like:
        return f"{right} at {left}"
    if left_company_like and right_role_like and not left_role_like:
        return f"{right} at {left}"

    return f"{left} at {right}"


def _normalize_profile_headline(profile: ResumeProfile) -> None:
    normalized = _normalize_headline_order(profile.headline, profile)
    profile.headline = normalized or None


def _fill_missing_headline_from_profile(
    parsed_profile: ResumeProfile,
    fallback_profile: ResumeProfile | None,
) -> None:
    if fallback_profile is None:
        return
    existing_headline = str(parsed_profile.headline or "").strip()
    if existing_headline:
        return

    fallback_headline = str(fallback_profile.headline or "").strip()
    if not fallback_headline:
        fallback_headline = _headline_from_experience(fallback_profile)
    if fallback_headline:
        parsed_profile.headline = _normalize_headline_order(fallback_headline, fallback_profile)


def _non_empty_text_lines(values: List[str]) -> List[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def _is_awards_section(section: ResumeSection) -> bool:
    title = str(section.title or "").strip().lower()
    return "award" in title


def _has_awards_content(sections: List[ResumeSection]) -> bool:
    for section in sections:
        if not _is_awards_section(section):
            continue
        if _non_empty_text_lines(section.bullets) or _non_empty_text_lines(section.paragraphs):
            return True
    return False


def _backfill_missing_awards_from_profile(
    parsed_profile: ResumeProfile,
    parsed_sections: List[ResumeSection],
    fallback_profile: ResumeProfile | None,
) -> None:
    if fallback_profile is None:
        return
    if _has_awards_content(parsed_sections):
        return

    fallback_awards_sections = [
        section
        for section in (fallback_profile.additional_sections or [])
        if _is_awards_section(section)
    ]
    if not fallback_awards_sections:
        return

    merged_bullets: List[str] = []
    merged_paragraphs: List[str] = []
    for section in fallback_awards_sections:
        merged_bullets.extend(_non_empty_text_lines(section.bullets))
        merged_paragraphs.extend(_non_empty_text_lines(section.paragraphs))
    if not merged_bullets and not merged_paragraphs:
        return

    title = next(
        (str(section.title).strip() for section in fallback_awards_sections if str(section.title).strip()),
        "Awards",
    )
    awards_section = ResumeSection(
        title=title,
        bullets=list(merged_bullets),
        paragraphs=list(merged_paragraphs),
    )
    parsed_sections.append(awards_section)

    if not _has_awards_content(parsed_profile.additional_sections):
        parsed_profile.additional_sections.append(
            ResumeSection(
                title=title,
                bullets=list(merged_bullets),
                paragraphs=list(merged_paragraphs),
            )
        )


def _section_title_lower(section: ResumeSection) -> str:
    return str(section.title or "").strip().lower()


def _is_summary_section(section: ResumeSection) -> bool:
    title = _section_title_lower(section)
    return "summary" in title or "objective" in title or title == "profile"


def _is_skills_section(section: ResumeSection) -> bool:
    return "skill" in _section_title_lower(section)


def _is_experience_section(section: ResumeSection) -> bool:
    title = _section_title_lower(section)
    return "experience" in title or "employment" in title or "work history" in title


def _is_education_section(section: ResumeSection) -> bool:
    title = _section_title_lower(section)
    return "education" in title or "qualification" in title or "academic" in title


def _find_section(
    sections: List[ResumeSection],
    predicate,
) -> ResumeSection | None:
    for section in sections:
        if predicate(section):
            return section
    return None


def _section_has_content(section: ResumeSection) -> bool:
    if _non_empty_text_lines(section.paragraphs) or _non_empty_text_lines(section.bullets):
        return True
    if isinstance(section.meta, dict) and section.meta.get("entries"):
        return True
    if isinstance(section.meta, dict) and section.meta.get("category_lines"):
        return True
    return False


def _section_rank(title: str) -> int:
    lowered = str(title or "").strip().lower()
    if "summary" in lowered or "objective" in lowered:
        return 10
    if "skill" in lowered:
        return 20
    if "experience" in lowered or "employment" in lowered:
        return 30
    if "education" in lowered or "qualification" in lowered or "academic" in lowered:
        return 40
    if "award" in lowered or "honor" in lowered or "honour" in lowered:
        return 50
    return 100


def _insert_section_ordered(sections: List[ResumeSection], new_section: ResumeSection) -> None:
    new_rank = _section_rank(new_section.title)
    for index, section in enumerate(sections):
        if _section_rank(section.title) > new_rank:
            sections.insert(index, new_section)
            return
    sections.append(new_section)


def _iso_to_month_year(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered in {"present", "current"}:
        return "Present"
    match = _ISO_DATE_PATTERN.fullmatch(text)
    if not match:
        return text
    year = match.group(1)
    month = int(match.group(2))
    if 1 <= month < len(_MONTH_ABBR):
        return f"{_MONTH_ABBR[month]} {year}"
    return year


def _date_range_from_experience_item(item: Dict[str, object]) -> str:
    start = _iso_to_month_year(str(item.get("start", "") or ""))
    end = _iso_to_month_year(str(item.get("end", "") or ""))
    if start and end:
        return f"{start} - {end}"
    return start or end


def _normalized_experience_item(item: Dict[str, object]) -> Dict[str, object]:
    role = str(item.get("role", "") or item.get("title", "") or "").strip()
    company = str(item.get("company", "") or "").strip()
    location = str(item.get("location", "") or "").strip()
    start = str(item.get("start", "") or "").strip()
    end = str(item.get("end", "") or "").strip()
    raw_bullets = item.get("bullets", [])
    if isinstance(raw_bullets, str):
        bullets = [line.strip() for line in raw_bullets.splitlines() if line.strip()]
    else:
        bullets = _non_empty_text_lines([str(value) for value in (raw_bullets or [])])
    return {
        "role": role,
        "company": company,
        "location": location,
        "start": start,
        "end": end,
        "bullets": bullets,
    }


def _experience_section_entries_from_profile(profile: ResumeProfile) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    for raw_item in profile.experience or []:
        if not isinstance(raw_item, dict):
            continue
        item = _normalized_experience_item(raw_item)
        role = str(item.get("role", "")).strip()
        company = str(item.get("company", "")).strip()
        location = str(item.get("location", "")).strip()
        date_range = _date_range_from_experience_item(item)
        bullets = [str(value).strip() for value in (item.get("bullets", []) or []) if str(value).strip()]
        if not any([role, company, location, date_range, bullets]):
            continue
        entries.append(
            {
                "role": role,
                "company": company,
                "location": location,
                "date_range": date_range,
                "bullets": bullets,
            }
        )
    return entries


def _normalized_education_item(item: Dict[str, object]) -> Dict[str, object]:
    record: Dict[str, object] = {}
    degree = str(item.get("degree", "") or "").strip()
    institution = str(item.get("institution", "") or item.get("school", "") or "").strip()
    location = str(item.get("location", "") or "").strip()
    if degree:
        record["degree"] = degree
    if institution:
        record["institution"] = institution
    if location:
        record["location"] = location
    start = str(item.get("start", "") or "").strip()
    end = str(item.get("end", "") or "").strip()
    if start or end:
        year_bits = [bit for bit in [_iso_to_month_year(start), _iso_to_month_year(end)] if bit]
        if year_bits:
            record["year"] = " - ".join(year_bits)
    grade = str(item.get("grade", "") or "").strip()
    if grade:
        record["grade"] = grade
    return record


def _education_lines_from_records(records: List[Dict[str, object]]) -> List[str]:
    lines: List[str] = []
    for raw_item in records:
        item = _normalized_education_item(raw_item)
        institution = str(item.get("institution", "") or "").strip()
        degree = str(item.get("degree", "") or "").strip()
        location = str(item.get("location", "") or "").strip()
        year = str(item.get("year", "") or "").strip()
        grade = str(item.get("grade", "") or "").strip()
        parts = [part for part in [institution, degree, location, year, grade] if part]
        if not parts:
            continue
        lines.append(" | ".join(parts))
    return lines


def _has_profile_experience(profile: ResumeProfile) -> bool:
    for item in profile.experience or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "") or item.get("title", "") or "").strip()
        company = str(item.get("company", "") or "").strip()
        location = str(item.get("location", "") or "").strip()
        bullets = _non_empty_text_lines([str(value) for value in (item.get("bullets", []) or [])])
        if role or company or location or bullets:
            return True
    return False


def _has_profile_education(profile: ResumeProfile) -> bool:
    for item in profile.education or []:
        if not isinstance(item, dict):
            continue
        degree = str(item.get("degree", "") or "").strip()
        institution = str(item.get("institution", "") or item.get("school", "") or "").strip()
        if degree or institution:
            return True
    return False


def _backfill_missing_summary_from_profile(
    parsed_profile: ResumeProfile,
    parsed_sections: List[ResumeSection],
    fallback_profile: ResumeProfile | None,
) -> None:
    if fallback_profile is None:
        return

    summary_section = _find_section(parsed_sections, _is_summary_section)
    has_summary = bool(_non_empty_text_lines(parsed_profile.summary))
    if summary_section and _section_has_content(summary_section):
        has_summary = True
    if has_summary:
        return

    fallback_summary = _non_empty_text_lines(list(fallback_profile.summary or []))
    if not fallback_summary:
        return

    parsed_profile.summary = list(fallback_summary)
    if summary_section is not None:
        summary_section.paragraphs = list(fallback_summary)
        return

    _insert_section_ordered(
        parsed_sections,
        ResumeSection(title="Professional Summary", paragraphs=list(fallback_summary)),
    )


def _backfill_missing_skills_from_profile(
    parsed_profile: ResumeProfile,
    parsed_sections: List[ResumeSection],
    fallback_profile: ResumeProfile | None,
) -> None:
    if fallback_profile is None:
        return

    skills_section = _find_section(parsed_sections, _is_skills_section)
    has_skills = bool(_non_empty_text_lines(list(parsed_profile.skills or [])))
    if skills_section and _section_has_content(skills_section):
        has_skills = True
    if has_skills:
        return

    fallback_skills = _non_empty_text_lines(list(fallback_profile.skills or []))
    if not fallback_skills:
        return

    parsed_profile.skills = list(fallback_skills)
    if skills_section is not None:
        skills_section.bullets = list(fallback_skills)
        skills_section.meta.pop("category_lines", None)
        return

    _insert_section_ordered(
        parsed_sections,
        ResumeSection(title="Technical Skills", bullets=list(fallback_skills)),
    )


def _backfill_missing_experience_from_profile(
    parsed_profile: ResumeProfile,
    parsed_sections: List[ResumeSection],
    fallback_profile: ResumeProfile | None,
) -> None:
    if fallback_profile is None:
        return

    experience_section = _find_section(parsed_sections, _is_experience_section)
    has_experience = _has_profile_experience(parsed_profile)
    if experience_section and _section_has_content(experience_section):
        has_experience = True
    if has_experience:
        return

    normalized_profile_experience = [
        _normalized_experience_item(item)
        for item in (fallback_profile.experience or [])
        if isinstance(item, dict)
    ]
    normalized_profile_experience = [
        item
        for item in normalized_profile_experience
        if any(
            [
                str(item.get("role", "")).strip(),
                str(item.get("company", "")).strip(),
                str(item.get("location", "")).strip(),
                str(item.get("start", "")).strip(),
                str(item.get("end", "")).strip(),
                item.get("bullets", []),
            ]
        )
    ]
    section_entries = _experience_section_entries_from_profile(fallback_profile)
    if not normalized_profile_experience and not section_entries:
        return

    parsed_profile.experience = list(normalized_profile_experience)
    if not str(parsed_profile.headline or "").strip():
        parsed_profile.headline = _headline_from_experience(parsed_profile) or None

    if experience_section is None:
        experience_section = ResumeSection(title="Professional Experience")
        _insert_section_ordered(parsed_sections, experience_section)
    experience_section.meta["entries"] = list(section_entries)
    if not experience_section.paragraphs and not experience_section.bullets:
        for entry in section_entries:
            role = str(entry.get("role", "")).strip()
            company = str(entry.get("company", "")).strip()
            location = str(entry.get("location", "")).strip()
            date_range = str(entry.get("date_range", "")).strip()
            header_parts = [part for part in [role, f"@ {company}" if company else "", location, date_range] if part]
            if header_parts:
                experience_section.paragraphs.append(" | ".join(header_parts))
            experience_section.bullets.extend(
                [str(line).strip() for line in (entry.get("bullets", []) or []) if str(line).strip()]
            )


def _backfill_missing_education_from_profile(
    parsed_profile: ResumeProfile,
    parsed_sections: List[ResumeSection],
    fallback_profile: ResumeProfile | None,
) -> None:
    if fallback_profile is None:
        return

    education_section = _find_section(parsed_sections, _is_education_section)
    has_education = _has_profile_education(parsed_profile)
    if education_section and _section_has_content(education_section):
        has_education = True
    if has_education:
        return

    normalized_education = [
        _normalized_education_item(item)
        for item in (fallback_profile.education or [])
        if isinstance(item, dict)
    ]
    normalized_education = [item for item in normalized_education if item]
    if not normalized_education:
        return

    parsed_profile.education = list(normalized_education)
    education_lines = _education_lines_from_records(normalized_education)
    if not education_lines:
        return

    if education_section is None:
        education_section = ResumeSection(title="Education")
        _insert_section_ordered(parsed_sections, education_section)
    if not _section_has_content(education_section):
        education_section.paragraphs = list(education_lines)


def _backfill_missing_core_sections_from_profile(
    parsed_profile: ResumeProfile,
    parsed_sections: List[ResumeSection],
    fallback_profile: ResumeProfile | None,
) -> None:
    _backfill_missing_summary_from_profile(parsed_profile, parsed_sections, fallback_profile)
    _backfill_missing_skills_from_profile(parsed_profile, parsed_sections, fallback_profile)
    _backfill_missing_experience_from_profile(parsed_profile, parsed_sections, fallback_profile)
    _backfill_missing_education_from_profile(parsed_profile, parsed_sections, fallback_profile)
    _backfill_missing_awards_from_profile(parsed_profile, parsed_sections, fallback_profile)


def _section_payload(section: ResumeSection) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "title": section.title,
        "paragraphs": list(section.paragraphs),
        "bullets": list(section.bullets),
    }
    section_meta = section.meta or {}
    if (
        section.title.lower() in {"professional experience", "experience"}
        and "entries" in section_meta
        and not payload["paragraphs"]
        and not payload["bullets"]
    ):
        derived_paragraphs: List[str] = []
        derived_bullets: List[str] = []
        for entry in section_meta.get("entries", []):
            role = str(entry.get("role") or "").strip()
            company = str(entry.get("company") or "").strip()
            location = str(entry.get("location") or "").strip()
            date_range = str(entry.get("date_range") or "").strip()
            header_parts = [part for part in [role, f"@ {company}" if company else "", location, date_range] if part]
            if header_parts:
                derived_paragraphs.append(" | ".join(header_parts))
            for bullet in entry.get("bullets", []) or []:
                clean = str(bullet).strip()
                if clean:
                    derived_bullets.append(clean)
        if derived_paragraphs:
            payload["paragraphs"] = derived_paragraphs
        if derived_bullets:
            payload["bullets"] = derived_bullets
        section.paragraphs = list(payload["paragraphs"])
        section.bullets = list(payload["bullets"])
    if section_meta:
        payload["meta"] = section_meta
    return payload


def _document_payload(
    resume_id: str,
    document: ResumeDocument,
    pdf_bytes: bytes,
    ats_pdf_bytes: bytes | None = None,
    latex_pdf_bytes: bytes | None = None,
) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "resume_id": resume_id,
        "profile": _profile_payload(document.profile),
        "sections": [_section_payload(section) for section in document.sections],
        "theme": asdict(document.theme),
        "pdf": _encode_pdf(pdf_bytes),
    }
    if ats_pdf_bytes:
        payload["ats_pdf"] = _encode_pdf(ats_pdf_bytes)
    if latex_pdf_bytes:
        payload["latex_pdf"] = _encode_pdf(latex_pdf_bytes)
    return payload


def _apply_section_update(section: ResumeSection, update: SectionUpdate) -> None:
    new_title = update.title.strip()
    if new_title:
        section.title = new_title
    section.paragraphs = [paragraph.strip() for paragraph in update.paragraphs if paragraph.strip()]
    section.bullets = [bullet.strip() for bullet in update.bullets if bullet.strip()]
    if (section.paragraphs or section.bullets) and "entries" in section.meta:
        section.meta.pop("entries", None)

    if update.meta and isinstance(update.meta, dict):
        if "category_lines" in update.meta:
            normalized: List[tuple[str, List[str]]] = []
            raw_lines = update.meta.get("category_lines") or []
            for entry in raw_lines:
                if isinstance(entry, dict):
                    category = str(entry.get("category", "")).strip()
                    items = entry.get("items", [])
                elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                    category = str(entry[0]).strip()
                    items = entry[1]
                else:
                    continue
                if not category:
                    continue
                item_values = [
                    str(item).strip()
                    for item in (items or [])
                    if str(item).strip()
                ]
                normalized.append((category, item_values))
            if normalized:
                section.meta["category_lines"] = normalized
            elif "category_lines" in section.meta:
                section.meta.pop("category_lines")

        if "entries" in update.meta:
            normalized_entries: List[Dict[str, object]] = []
            raw_entries = update.meta.get("entries") or []
            for raw_entry in raw_entries:
                if not isinstance(raw_entry, dict):
                    continue
                role = str(raw_entry.get("role", "") or "").strip()
                company = str(raw_entry.get("company", "") or "").strip()
                location = str(raw_entry.get("location", "") or "").strip()
                date_range = str(raw_entry.get("date_range", "") or "").strip()
                raw_bullets = raw_entry.get("bullets", [])
                if isinstance(raw_bullets, str):
                    bullets = [line.strip() for line in raw_bullets.splitlines() if line.strip()]
                else:
                    bullets = [
                        str(item).strip()
                        for item in (raw_bullets or [])
                        if str(item).strip()
                    ]
                if not any([role, company, location, date_range, bullets]):
                    continue
                normalized_entries.append(
                    {
                        "role": role,
                        "company": company,
                        "location": location,
                        "date_range": date_range,
                        "bullets": bullets,
                    }
                )

            if normalized_entries:
                section.meta["entries"] = normalized_entries
                derived_paragraphs: List[str] = []
                derived_bullets: List[str] = []
                for entry in normalized_entries:
                    header_parts = [
                        entry["role"],
                        f"@ {entry['company']}" if entry["company"] else "",
                        entry["location"],
                        entry["date_range"],
                    ]
                    header = " | ".join([part for part in header_parts if part])
                    if header:
                        derived_paragraphs.append(header)
                    derived_bullets.extend(entry["bullets"])
                section.paragraphs = derived_paragraphs
                section.bullets = derived_bullets
            elif "entries" in section.meta:
                section.meta.pop("entries")


def _apply_profile_update(profile: ResumeProfile, update: Optional[ProfileUpdate]) -> None:
    if update is None:
        return

    if update.name is not None:
        cleaned_name = update.name.strip()
        if cleaned_name:
            profile.name = cleaned_name

    if update.headline is not None:
        profile.headline = update.headline.strip() or None

    if update.contact is not None:
        existing_contact = dict(profile.contact or {})
        normalized_contact: Dict[str, str] = {}
        for key in ("phone", "email", "location", "linkedin", "notice_note"):
            raw_value = update.contact.get(key, existing_contact.get(key, ""))
            clean_value = str(raw_value or "").strip()
            if clean_value:
                normalized_contact[key] = clean_value
        profile.contact = normalized_contact

    _normalize_profile_headline(profile)


def _maybe_mount_frontend(app: FastAPI) -> None:
    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    index_file = frontend_dir / "index.html"
    if not index_file.exists():
        return

    static_dir = frontend_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:  # pragma: no cover - FastAPI handles response
        return FileResponse(index_file)


@asynccontextmanager
async def _temporary_workspace() -> TemporaryDirectory:
    with TemporaryDirectory() as tmpdir:
        yield TemporaryDirectoryWrapper(Path(tmpdir))


class TemporaryDirectoryWrapper:
    """Wrapper adding helpers for FastAPI request handling."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, relative: str) -> Path:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        return target


def _sanitize_filename(original: Optional[str], default: str) -> str:
    if not original:
        return default
    candidate = Path(original).name.strip()
    return candidate or default


async def _persist_upload(upload: UploadFile, destination: Path) -> Path:
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"{upload.filename} is empty.")
    destination.write_bytes(data)
    await upload.close()
    return destination


async def _render_document_pdfs(document: ResumeDocument) -> tuple[bytes, bytes, bytes | None]:
    async with _temporary_workspace() as workspace:
        output_path = workspace.path("resume.pdf")
        render_resume(document, output_path)

        ats_output_path = workspace.path("resume_ats.pdf")
        ats_document = _build_ats_document(document)
        render_resume(ats_document, ats_output_path)

        latex_bytes: bytes | None = None
        latex_output_path = workspace.path("resume_latex.pdf")
        try:
            render_latex_resume(document, latex_output_path)
            latex_bytes = latex_output_path.read_bytes()
        except (FileNotFoundError, RuntimeError) as exc:
            # Keep API backward-compatible when LaTeX is unavailable.
            print(f"[latex-renderer] {exc}")

        return output_path.read_bytes(), ats_output_path.read_bytes(), latex_bytes


def _build_app() -> FastAPI:
    app = FastAPI(
        title="Resume by Job Description API",
        description="Expose resume generation as an HTTP service.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _maybe_mount_frontend(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/sample-profiles")
    async def list_sample_profiles() -> Dict[str, object]:
        profiles = _discover_sample_profiles()
        return {
            "default_profile": DEFAULT_SAMPLE_PROFILE,
            "profiles": [{"id": profile["id"], "label": profile["label"]} for profile in profiles],
        }

    @app.post("/api/generate")
    async def generate_resume(
        reference: UploadFile | None = File(default=None),
        profile: UploadFile | None = File(default=None),
        job_description: UploadFile | None = File(default=None),
        job_text: str | None = Form(default=None),
        resume_text: str | None = Form(default=None),
        sample_profile: str | None = Form(default=None),
        accent_color: str | None = Form(default=None),
        primary_color: str | None = Form(default=None),
        ats_font_family: str | None = Form(default=None),
        body_size: float | None = Form(default=None),
        heading_size: float | None = Form(default=None),
    ) -> Dict[str, object]:
        async with _temporary_workspace() as workspace:
            sample_reference_path: Path | None = None
            sample_profile_path: Path | None = None
            if reference is None or profile is None:
                sample_reference_path, sample_profile_path = _resolve_sample_profile_paths(sample_profile)

            if reference is not None:
                reference_path = workspace.path(_sanitize_filename(reference.filename, "reference.pdf"))
                await _persist_upload(reference, reference_path)
            elif sample_reference_path is not None:
                reference_path = workspace.path("reference.pdf")
                reference_path.write_bytes(sample_reference_path.read_bytes())
            else:
                if not DEFAULT_REFERENCE_PATH.exists():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Default reference resume not found at {DEFAULT_REFERENCE_PATH}. Upload a reference PDF.",
                    )
                reference_path = workspace.path("reference.pdf")
                reference_path.write_bytes(DEFAULT_REFERENCE_PATH.read_bytes())

            profile_path: Path | None = None
            if profile is not None:
                profile_path = workspace.path(_sanitize_filename(profile.filename, "profile.yml"))
                await _persist_upload(profile, profile_path)
            elif sample_profile_path is not None:
                profile_path = workspace.path("profile.yaml")
                profile_path.write_bytes(sample_profile_path.read_bytes())
            elif DEFAULT_PROFILE_PATH.exists():
                profile_path = workspace.path("profile.yaml")
                profile_path.write_bytes(DEFAULT_PROFILE_PATH.read_bytes())

            has_resume_text = bool(resume_text and resume_text.strip())

            if job_description and not has_resume_text:
                jd_path = workspace.path(_sanitize_filename(job_description.filename, "job.txt"))
                await _persist_upload(job_description, jd_path)
                job_contents = jd_path.read_text()
            elif (job_text and job_text.strip()) and not has_resume_text:
                job_contents = job_text.strip()
            else:
                job_contents = "N/A"

            try:
                reference_structure = extract_reference_structure(reference_path)
                if has_resume_text:
                    profile_data, parsed_sections = parse_resume_text(resume_text or "")
                    fallback_profile: ResumeProfile | None = None
                    if profile_path is not None and profile_path.exists():
                        fallback_profile = load_profile(profile_path)
                    _fill_missing_headline_from_profile(profile_data, fallback_profile)
                    _fill_missing_contact_from_profile(profile_data, fallback_profile)
                    _backfill_missing_core_sections_from_profile(profile_data, parsed_sections, fallback_profile)
                    _normalize_profile_headline(profile_data)
                    document = ResumeDocument(
                        profile=profile_data,
                        sections=parsed_sections,
                        theme=reference_structure.theme,
                    )
                else:
                    if profile_path:
                        profile_data = load_profile(profile_path)
                    else:
                        profile_data = build_profile_from_reference(reference_structure)
                        generated_profile_path = workspace.path("generated_profile.yml")
                        save_profile(profile_data, generated_profile_path)
                        print("--- Auto-generated profile ---")
                        canonical_profile = profile_to_canonical(profile_data)
                        print(yaml.safe_dump(canonical_profile, sort_keys=False, allow_unicode=True))
                        print(f"Profile saved to: {generated_profile_path}")
                    _normalize_profile_headline(profile_data)
                    insights = analyze_job_description(job_contents)
                    document = build_resume_document(reference_structure, profile_data, insights)
                theme_payload: Dict[str, object] = {}
                if accent_color and accent_color.strip():
                    theme_payload["accent_color"] = accent_color.strip()
                if primary_color and primary_color.strip():
                    theme_payload["primary_color"] = primary_color.strip()
                if ats_font_family and ats_font_family.strip():
                    theme_payload["ats_font_family"] = ats_font_family.strip()
                if body_size is not None:
                    theme_payload["body_size"] = body_size
                if heading_size is not None:
                    theme_payload["heading_size"] = heading_size
                document.theme = _theme_from_payload(theme_payload, document.theme)
            except (ValueError, FileNotFoundError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=500, detail="Failed to build resume.") from exc

        pdf_bytes, ats_pdf_bytes, latex_pdf_bytes = await _render_document_pdfs(document)

        resume_id = uuid4().hex
        RESUME_SESSIONS[resume_id] = document
        return _document_payload(resume_id, document, pdf_bytes, ats_pdf_bytes, latex_pdf_bytes)

    @app.get("/api/resume/{resume_id}")
    async def get_resume(resume_id: str) -> Dict[str, object]:
        document = RESUME_SESSIONS.get(resume_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Resume session not found.")

        pdf_bytes, ats_pdf_bytes, latex_pdf_bytes = await _render_document_pdfs(document)
        return _document_payload(resume_id, document, pdf_bytes, ats_pdf_bytes, latex_pdf_bytes)

    @app.post("/api/resume/import")
    async def import_resume(payload: UpdatePayload) -> Dict[str, object]:
        try:
            theme = _theme_from_payload(payload.theme)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        seed_name = "Candidate"
        if payload.profile and payload.profile.name and payload.profile.name.strip():
            seed_name = payload.profile.name.strip()

        document = ResumeDocument(
            profile=ResumeProfile(name=seed_name),
            sections=[],
            theme=theme,
        )
        _apply_profile_update(document.profile, payload.profile)
        _normalize_profile_headline(document.profile)

        imported_sections: List[ResumeSection] = []
        for update in payload.sections:
            section = ResumeSection(title=update.title.strip() or "Untitled Section")
            _apply_section_update(section, update)
            imported_sections.append(section)
        document.sections = imported_sections

        pdf_bytes, ats_pdf_bytes, latex_pdf_bytes = await _render_document_pdfs(document)

        resume_id = uuid4().hex
        RESUME_SESSIONS[resume_id] = document
        return _document_payload(resume_id, document, pdf_bytes, ats_pdf_bytes, latex_pdf_bytes)

    @app.put("/api/resume/{resume_id}")
    async def update_resume(resume_id: str, payload: UpdatePayload) -> Dict[str, object]:
        document = RESUME_SESSIONS.get(resume_id)
        has_resume_text = bool(payload.resume_text and payload.resume_text.strip())

        if document is None:
            # Serverless/cold starts can evict in-memory sessions. Rebuild from client payload.
            base_name = "Candidate"
            if payload.profile and payload.profile.name:
                candidate_name = payload.profile.name.strip()
                if candidate_name:
                    base_name = candidate_name
            document = ResumeDocument(
                profile=ResumeProfile(name=base_name),
                sections=[],
                theme=Theme(),
            )

        if payload.theme is not None:
            try:
                document.theme = _theme_from_payload(payload.theme, document.theme)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        if has_resume_text:
            try:
                parsed_profile, parsed_sections = parse_resume_text(payload.resume_text or "")
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            _fill_missing_headline_from_profile(parsed_profile, document.profile)
            _fill_missing_contact_from_profile(parsed_profile, document.profile)
            _backfill_missing_core_sections_from_profile(parsed_profile, parsed_sections, document.profile)
            if DEFAULT_PROFILE_PATH.exists():
                default_profile = load_profile(DEFAULT_PROFILE_PATH)
                _fill_missing_headline_from_profile(parsed_profile, default_profile)
                _fill_missing_contact_from_profile(parsed_profile, default_profile)
                _backfill_missing_core_sections_from_profile(parsed_profile, parsed_sections, default_profile)
            document.profile = parsed_profile
            document.sections = parsed_sections
            _apply_profile_update(document.profile, payload.profile)
        else:
            _apply_profile_update(document.profile, payload.profile)

            if payload.sections:
                existing_sections = list(document.sections)
                updated_sections: List[ResumeSection] = []

                for index, update in enumerate(payload.sections):
                    if index < len(existing_sections):
                        section = existing_sections[index]
                    else:
                        section = ResumeSection(title=update.title.strip() or "Untitled Section")
                    _apply_section_update(section, update)
                    updated_sections.append(section)

                document.sections = updated_sections

        _normalize_profile_headline(document.profile)

        pdf_bytes, ats_pdf_bytes, latex_pdf_bytes = await _render_document_pdfs(document)

        RESUME_SESSIONS[resume_id] = document
        return _document_payload(resume_id, document, pdf_bytes, ats_pdf_bytes, latex_pdf_bytes)

    @app.get("/api/resume/{resume_id}/pdf")
    async def download_resume(resume_id: str) -> StreamingResponse:
        document = RESUME_SESSIONS.get(resume_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Resume session not found.")

        pdf_bytes, _, _ = await _render_document_pdfs(document)

        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename=\"resume.pdf\"'},
        )

    @app.get("/api/resume/{resume_id}/latex-pdf")
    async def download_latex_resume(resume_id: str) -> StreamingResponse:
        document = RESUME_SESSIONS.get(resume_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Resume session not found.")

        async with _temporary_workspace() as workspace:
            latex_output_path = workspace.path("resume_latex.pdf")
            try:
                render_latex_resume(document, latex_output_path)
            except FileNotFoundError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            except RuntimeError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc
            latex_bytes = latex_output_path.read_bytes()

        return StreamingResponse(
            BytesIO(latex_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename=\"resume-latex.pdf\"'},
        )

    return app


app = _build_app()


def run() -> None:
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    reload_env = os.environ.get("RESUME_BY_JD_RELOAD", os.environ.get("UVICORN_RELOAD", "true")).lower()
    reload_enabled = reload_env not in {"0", "false", "no"}
    project_root = Path(__file__).resolve().parents[2]
    reload_targets = [
        project_root / "src",
        project_root / "frontend",
    ]
    reload_dirs = [str(path) for path in reload_targets if path.exists()]
    uvicorn.run(
        "resume_builder.api:app",
        host=host,
        port=port,
        reload=reload_enabled,
        reload_dirs=reload_dirs,
    )
