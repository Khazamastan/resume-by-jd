from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime
from typing import Dict, Iterable, List, Sequence, Union

from dateutil import parser as date_parser

from .models import ReferenceStructure, ResumeDocument, ResumeProfile, ResumeSection, SkillInsights, Theme


def _stringify_sequence(value: Sequence[object]) -> str:
    return ", ".join(str(item).strip() for item in value if str(item).strip())


def _normalize_skill(skill: Union[str, Dict[str, object], Sequence[object]]) -> str:
    if isinstance(skill, dict):
        parts: List[str] = []
        for key, value in skill.items():
            if isinstance(value, (list, tuple, set)):
                value_str = _stringify_sequence(value)
            else:
                value_str = str(value).strip()
            if value_str:
                parts.append(f"{key}: {value_str}" if key else value_str)
        skill = " ".join(parts)
    elif isinstance(skill, (list, tuple, set)):
        skill = _stringify_sequence(skill)
    return str(skill).strip()


def _merge_skills(profile: ResumeProfile, insights: SkillInsights) -> List[str]:
    existing = {_normalize_skill(skill).lower(): skill for skill in profile.skills}
    ordered: List[str] = list(profile.skills)
    for skill in insights.mandatory:
        key = _normalize_skill(skill).lower()
        if key not in existing:
            ordered.append(skill)
            existing[key] = skill
    return ordered


def _fmt_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = date_parser.parse(str(value))
        return parsed.strftime("%b %Y")
    except (ValueError, TypeError):
        return str(value)


def _format_experience_entry(item: dict) -> Dict[str, object]:
    role = item.get("role") or item.get("title")
    company = item.get("company")
    start = item.get("start")
    end = item.get("end")
    location = item.get("location")

    start_text = _fmt_date(start)
    end_text = _fmt_date(end) or ("Present" if end in (None, "", "Present") else "")
    date_range = (
        f"{start_text} – {end_text}"
        if start_text or end_text
        else ""
    )

    return {
        "role": role,
        "company": company,
        "location": location,
        "date_range": date_range,
        "bullets": item.get("bullets", []) or [],
    }


def _group_skills(skills: List) -> Dict[str, List[str]]:
    grouped: Dict[str, List[str]] = OrderedDict()
    additional: List[str] = []
    for skill in skills:
        normalized = _normalize_skill(skill)
        if not normalized:
            continue
        if ":" in normalized:
            category, values = normalized.split(":", 1)
            category = category.strip().title() or "Other"
            items = [value.strip() for value in values.split(",") if value.strip()]
            if not items:
                continue
            grouped.setdefault(category, [])
            for item in items:
                if item not in grouped[category]:
                    grouped[category].append(item)
        else:
            additional.append(normalized)

    if additional:
        grouped.setdefault("Additional Skills", [])
        for item in additional:
            if item not in grouped["Additional Skills"]:
                grouped["Additional Skills"].append(item)

    return grouped


def _collect_highlight_terms(profile: ResumeProfile, insights: SkillInsights) -> List[str]:
    """Gather skill phrases to emphasize within experience bullets."""
    terms: List[str] = []
    seen: set[str] = set()

    def _add_term(raw: str | None) -> None:
        if not raw:
            return
        candidate = str(raw).strip()
        if not candidate:
            return
        if len(candidate.split()) > 4:
            return
        lowered = candidate.lower()
        if lowered in seen:
            return
        seen.add(lowered)
        terms.append(candidate)

    for skill in profile.skills:
        normalized = _normalize_skill(skill)
        if not normalized:
            continue
        for fragment in re.split(r"[,/•;]", normalized):
            _add_term(fragment)

    for bucket in (insights.mandatory, insights.preferred, insights.keywords):
        for item in bucket:
            normalized = _normalize_skill(item)
            _add_term(normalized)

    return terms


def _ensure_sentence(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    if cleaned.endswith((".", "!", "?")):
        return cleaned
    return f"{cleaned}."


def _collect_job_summary_terms(insights: SkillInsights, limit: int = 4) -> List[str]:
    combined: List[str] = []
    for bucket in (insights.mandatory, insights.preferred, insights.keywords):
        for item in bucket:
            value = _normalize_skill(item)
            if not value:
                continue
            value = value.replace("•", "").strip()
            if len(value.split()) > 4:
                continue
            key = value.lower()
            if key in combined or not value:
                continue
            combined.append(value)
    ordered: List[str] = []
    seen: set[str] = set()
    for value in combined:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return ordered[:limit]


def _categorize_skill(skill: str) -> str | None:
    lowered = skill.lower()
    for category, keywords in SKILL_CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                return category
    return None


def _build_skill_categories(profile: ResumeProfile, insights: SkillInsights) -> "OrderedDict[str, List[str]]":
    categories: "OrderedDict[str, List[str]]" = OrderedDict((category, []) for category in SKILL_CATEGORY_KEYWORDS.keys())
    seen: set[str] = set()

    def _register(item: str) -> None:
        normalized = _normalize_skill(item)
        if not normalized:
            return
        key = normalized.lower()
        if key in seen:
            return
        category = _categorize_skill(normalized)
        if not category:
            return
        bucket = categories.setdefault(category, [])
        if len(bucket) >= MAX_SKILLS_PER_CATEGORY:
            return
        bucket.append(normalized)
        seen.add(key)

    for item in insights.mandatory:
        _register(item)
    for skill in profile.skills:
        _register(skill)
    for item in insights.preferred:
        _register(item)
    for item in insights.keywords:
        _register(item)

    ordered_categories: "OrderedDict[str, List[str]]" = OrderedDict()
    for category, items in categories.items():
        if items:
            ordered_categories[category] = items

    ai_tools = ordered_categories.setdefault("AI Tools", [])
    defaults = ["Codex", "Cline", "Copilot"]
    existing = {item.lower() for item in ai_tools}
    for tool in defaults:
        if tool.lower() not in existing and len(ai_tools) < MAX_SKILLS_PER_CATEGORY:
            ai_tools.append(tool)
            existing.add(tool.lower())

    return ordered_categories


def _build_section(title: str, items: List[str], bullets: bool = True) -> ResumeSection:
    section = ResumeSection(title=title)
    for item in items:
        if bullets and item.startswith("•"):
            section.bullets.append(item.lstrip("• ").strip())
        elif bullets:
            section.bullets.append(item)
        else:
            section.paragraphs.append(item)
    return section


def build_resume_document(
    reference: ReferenceStructure,
    profile: ResumeProfile,
    insights: SkillInsights,
) -> ResumeDocument:
    """Create the resume document using reference styling and updated content."""
    merged_skills = _merge_skills(profile, insights)
    grouped_skills = _group_skills(merged_skills)

    # Summary section
    summary_paragraph = SUMMARY_TEMPLATE
    summary_terms = _collect_job_summary_terms(insights)
    if summary_terms:
        summary_paragraph = (
            f"{_ensure_sentence(SUMMARY_TEMPLATE)} Key strengths aligned to this role: {', '.join(summary_terms)}."
        )
    summary_section = ResumeSection(title="Summary", paragraphs=[summary_paragraph])

    # Skills section
    skills_section = ResumeSection(title="Technical Skills")
    skill_categories = _build_skill_categories(profile, insights)
    if skill_categories:
        skills_section.meta["category_lines"] = [(category, values) for category, values in skill_categories.items()]
    skills_section.bullets = []

    # Experience section
    experience_entries = [_format_experience_entry(exp) for exp in profile.experience]
    experience_section = ResumeSection(title="Professional Experience")
    experience_section.meta["entries"] = experience_entries
    experience_section.meta["highlight_terms"] = _collect_highlight_terms(profile, insights)

    # Education section
    education_lines: List[str] = []
    for edu in profile.education:
        school = edu.get("institution") or edu.get("school")
        degree = edu.get("degree")
        end = edu.get("end")
        entry_parts = [part for part in [school, degree] if part]
        if entry_parts:
            line = " | ".join(entry_parts)
            if end:
                try:
                    date_value = date_parser.parse(str(end))
                    line += f" ({date_value.strftime('%Y')})"
                except (ValueError, TypeError):
                    line += f" ({end})"
            education_lines.append(line)
        for detail in edu.get("details", []) or []:
            education_lines.append(f"• {detail}")
    education_section = _build_section("Education", education_lines, bullets=False)

    project_sections: List[ResumeSection] = []
    if profile.projects:
        project_lines: List[str] = []
        for project in profile.projects:
            title = project.get("name")
            tagline = project.get("summary") or project.get("description", "")
            technologies = project.get("technologies", [])
            highlight = " • ".join(
                [part for part in [title, tagline, ", ".join(technologies)] if part]
            )
            if highlight:
                project_lines.append(highlight)
            for bullet in project.get("bullets", []) or []:
                project_lines.append(f"• {bullet}")
        project_sections.append(_build_section("Projects", project_lines, bullets=False))

    certification_section: ResumeSection | None = None
    if profile.certifications:
        cert_lines = [
            f"{cert.get('name')} ({cert.get('issuer')})"
            if cert.get("issuer")
            else cert.get("name")
            for cert in profile.certifications
            if cert.get("name")
        ]
        certification_section = _build_section("Certifications", cert_lines, bullets=False)

    additional_sections = list(profile.additional_sections)

    sections: List[ResumeSection] = [
        summary_section,
        skills_section,
        experience_section,
        education_section,
    ]
    sections.extend(project_sections)
    if certification_section:
        sections.append(certification_section)
    for section in additional_sections:
        if section.title and section.title.lower() == "awards":
            section.meta.setdefault("highlight_terms", _collect_highlight_terms(profile, insights))
    sections.extend(additional_sections)

    theme: Theme = reference.theme
    return ResumeDocument(profile=profile, sections=sections, theme=theme)
SUMMARY_TEMPLATE = (
    "Principal Front-End Engineer with 10+ years of experience building high-scale web applications for global product companies. "
    "Expert in React and micro front-ends, with a focus on architecting resilient CI/CD pipelines that slash deployment times and boost developer velocity. "
    "I specialize in bridging the gap between complex engineering and business impact, ensuring systems are as performant as they are scalable."
)

SKILL_CATEGORY_KEYWORDS: "OrderedDict[str, List[str]]" = OrderedDict(
    [
        ("Programming Languages", ["javascript", "typescript", "python", "java", "c#", "c++", "go", "ruby", "php", "swift", "kotlin"]),
        ("Frontend", ["react", "redux", "vue", "angular", "next", "nuxt", "svelte", "html", "css", "sass", "less", "micro front", "webpack", "vite", "storybook", "material", "mui", "tailwind"]),
        ("Backend", ["node", "nestjs", "express", "graphql", "rest", "api", "java", "spring", "python", "django", "flask", "fastapi", "php", "laravel", "ruby", "rails"]),
        ("Databases", ["mysql", "postgres", "postgresql", "mongodb", "dynamodb", "redis", "nosql", "sql", "aurora", "snowflake"]),
        ("DevOps & CI/CD", ["ci", "cd", "jenkins", "github actions", "gitlab", "bitbucket pipelines", "docker", "kubernetes", "helm", "terraform", "ansible", "pipeline"]),
        ("Cloud & Infrastructure", ["aws", "azure", "gcp", "lambda", "cloudfront", "cloudwatch", "ec2", "s3", "cloud"]),
        ("Testing & Quality", ["jest", "cypress", "selenium", "playwright", "testing", "unit testing", "integration testing", "tdd", "bdd"]),
        ("AI Tools", ["codex", "cline", "copilot"]),
        ("Data & Analytics", ["kafka", "spark", "hadoop", "analytics", "tableau", "power bi"]),
    ]
)

MAX_SKILLS_PER_CATEGORY = 6
