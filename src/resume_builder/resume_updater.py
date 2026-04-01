from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime
from typing import Dict, Iterable, List, Sequence, Union

from dateutil import parser as date_parser

from .models import ReferenceStructure, ResumeDocument, ResumeProfile, ResumeSection, SkillInsights, Theme

_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
_CID_ESCAPE_PATTERN = re.compile(r"\(cid:\d+\)")


def _sanitize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    text = _CONTROL_CHAR_PATTERN.sub("", text)
    text = _CID_ESCAPE_PATTERN.sub("", text)
    return text.replace("\u00a0", " ")


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
    return _sanitize_text(str(skill).strip())


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
    role = _sanitize_text(item.get("role") or item.get("title"))
    company = _sanitize_text(item.get("company"))
    start = item.get("start")
    end = item.get("end")
    location = _sanitize_text(item.get("location"))

    start_text = _fmt_date(start)
    end_text = _fmt_date(end) or ("Present" if end in (None, "", "Present") else "")
    if start_text and end_text:
        date_range = f"{start_text} - {end_text}"
    elif start_text:
        date_range = start_text
    elif end_text:
        date_range = end_text
    else:
        date_range = ""

    bullets: List[str] = []
    for bullet in item.get("bullets", []) or []:
        cleaned = _sanitize_text(bullet)
        if cleaned:
            bullets.append(cleaned)

    return {
        "role": role,
        "company": company,
        "location": location,
        "date_range": _sanitize_text(date_range),
        "bullets": bullets,
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


def _collect_highlight_terms(
    profile: ResumeProfile,
    insights: SkillInsights,
    additional_terms: Iterable[str] | None = None,
) -> List[str]:
    """Gather skill phrases to emphasize within experience bullets."""
    terms: List[str] = []
    seen: set[str] = set()

    def _add_term(raw: str | None) -> None:
        if not raw:
            return
        candidate = _sanitize_text(raw).strip()
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
        for fragment in re.split(r"[,/■;]", normalized):
            _add_term(fragment)

    for bucket in (insights.mandatory, insights.preferred, insights.keywords):
        for item in bucket:
            normalized = _normalize_skill(item)
            _add_term(normalized)

    if additional_terms:
        for term in additional_terms:
            _add_term(term)

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
            value = _sanitize_text(_normalize_skill(item))
            if not value:
                continue
            value = value.replace("■", "").strip()
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
    clean_title = _sanitize_text(title).strip()
    section = ResumeSection(title=clean_title or (title or ""))
    for item in items:
        cleaned = _sanitize_text(item)
        if not cleaned:
            continue
        if bullets and cleaned.startswith("■"):
            section.bullets.append(cleaned.lstrip("■ ").strip())
        elif bullets:
            section.bullets.append(cleaned)
        else:
            section.paragraphs.append(cleaned)
    return section


def _sanitize_profile(profile: ResumeProfile) -> None:
    profile.name = _sanitize_text(profile.name).strip() or profile.name
    if profile.headline is not None:
        profile.headline = _sanitize_text(profile.headline).strip()
    if profile.summary:
        summary_lines: List[str] = []
        for line in profile.summary:
            cleaned = _sanitize_text(line).strip()
            if cleaned:
                summary_lines.append(cleaned)
        profile.summary = summary_lines
    if profile.skills:
        cleaned_skills: List[str] = []
        for skill in profile.skills:
            cleaned_skill = _sanitize_text(skill).strip()
            if cleaned_skill:
                cleaned_skills.append(cleaned_skill)
        profile.skills = cleaned_skills
    if profile.contact:
        cleaned_contact: Dict[str, str] = {}
        for key, value in profile.contact.items():
            cleaned_value = _sanitize_text(value).strip()
            if cleaned_value:
                cleaned_contact[key] = cleaned_value
        profile.contact = cleaned_contact
    if profile.experience:
        for entry in profile.experience:
            for field in ("role", "company", "location"):
                if field in entry:
                    entry[field] = _sanitize_text(entry.get(field)).strip()
            if "bullets" in entry and isinstance(entry["bullets"], list):
                cleaned_bullets: List[str] = []
                for bullet in entry["bullets"]:
                    cleaned_bullet = _sanitize_text(bullet).strip()
                    if cleaned_bullet:
                        cleaned_bullets.append(cleaned_bullet)
                entry["bullets"] = cleaned_bullets
    if profile.education:
        for record in profile.education:
            for field in ("institution", "school", "degree", "location"):
                if field in record:
                    record[field] = _sanitize_text(record.get(field)).strip()
            if "details" in record and isinstance(record["details"], list):
                cleaned_details: List[str] = []
                for detail in record["details"]:
                    cleaned_detail = _sanitize_text(detail).strip()
                    if cleaned_detail:
                        cleaned_details.append(cleaned_detail)
                record["details"] = cleaned_details
    if profile.projects:
        for project in profile.projects:
            for field in ("name", "summary", "description"):
                if field in project:
                    project[field] = _sanitize_text(project.get(field)).strip()
            if "technologies" in project and isinstance(project["technologies"], list):
                cleaned_technologies: List[str] = []
                for tech in project["technologies"]:
                    cleaned_tech = _sanitize_text(tech).strip()
                    if cleaned_tech:
                        cleaned_technologies.append(cleaned_tech)
                project["technologies"] = cleaned_technologies
            if "bullets" in project and isinstance(project["bullets"], list):
                cleaned_project_bullets: List[str] = []
                for bullet in project["bullets"]:
                    cleaned_bullet = _sanitize_text(bullet).strip()
                    if cleaned_bullet:
                        cleaned_project_bullets.append(cleaned_bullet)
                project["bullets"] = cleaned_project_bullets
    if profile.certifications:
        for cert in profile.certifications:
            for field in ("name", "issuer"):
                if field in cert:
                    cert[field] = _sanitize_text(cert.get(field)).strip()
    if profile.additional_sections:
        converted_sections: List[ResumeSection] = []
        for section in profile.additional_sections:
            resume_section = _ensure_resume_section(section)
            _sanitize_section_content(resume_section)
            converted_sections.append(resume_section)
        profile.additional_sections = converted_sections


def _sanitize_section_content(section: ResumeSection) -> None:
    clean_title = _sanitize_text(section.title).strip()
    section.title = clean_title or (section.title.strip() if isinstance(section.title, str) else "")
    section.paragraphs = [text for text in (_sanitize_text(p).strip() for p in section.paragraphs) if text]
    section.bullets = [text for text in (_sanitize_text(b).strip() for b in section.bullets) if text]

    if "entries" in section.meta and isinstance(section.meta["entries"], list):
        cleaned_entries: List[Dict[str, object]] = []
        for entry in section.meta["entries"]:
            if not isinstance(entry, dict):
                continue
            cleaned_entry: Dict[str, object] = {}
            for key, value in entry.items():
                if isinstance(value, str):
                    cleaned_value = _sanitize_text(value).strip()
                    cleaned_entry[key] = cleaned_value
                elif isinstance(value, list):
                    cleaned_items: List[str] = []
                    for item in value:
                        if not isinstance(item, str):
                            continue
                        cleaned_item = _sanitize_text(item).strip()
                        if cleaned_item:
                            cleaned_items.append(cleaned_item)
                    cleaned_entry[key] = cleaned_items
                else:
                    cleaned_entry[key] = value
            cleaned_entries.append(cleaned_entry)
        section.meta["entries"] = cleaned_entries

    if "highlight_terms" in section.meta and isinstance(section.meta["highlight_terms"], list):
        cleaned_terms: List[str] = []
        for term in section.meta["highlight_terms"]:
            if not isinstance(term, str):
                continue
            cleaned_term = _sanitize_text(term).strip()
            if cleaned_term:
                cleaned_terms.append(cleaned_term)
        section.meta["highlight_terms"] = cleaned_terms

    if "category_lines" in section.meta and isinstance(section.meta["category_lines"], list):
        cleaned_categories: List[tuple[str, List[str]]] = []
        for line in section.meta["category_lines"]:
            if not isinstance(line, (list, tuple)) or len(line) != 2:
                continue
            category, items = line
            clean_category = _sanitize_text(category).strip()
            clean_items: List[str] = []
            if isinstance(items, list):
                for item in items:
                    cleaned_item = _sanitize_text(item).strip()
                    if cleaned_item:
                        clean_items.append(cleaned_item)
            if clean_category and clean_items:
                cleaned_categories.append((clean_category, clean_items))
        section.meta["category_lines"] = cleaned_categories


def _pop_additional_section(additional: List[ResumeSection], keywords: Sequence[str]) -> ResumeSection | None:
    """Remove and return the first additional section whose title contains any keyword."""
    for index, section in enumerate(additional):
        title_lower = (section.title or "").strip().lower()
        if any(keyword in title_lower for keyword in keywords):
            return additional.pop(index)
    return None


def _build_fallback_experience_entries(section: ResumeSection) -> List[Dict[str, object]]:
    """Best-effort extraction when structured experience data is unavailable."""
    paragraphs: List[str] = []
    for raw in section.paragraphs:
        cleaned = _sanitize_text(raw).strip()
        if cleaned:
            paragraphs.append(cleaned)

    bullets: List[str] = []
    for raw in section.bullets:
        cleaned = _sanitize_text(raw).strip()
        if cleaned:
            bullets.append(cleaned)
    lines: List[str] = []
    for paragraph in paragraphs:
        normalized_title = (section.title or "").strip().lower()
        if paragraph.strip().lower() == normalized_title:
            continue
        lines.append(paragraph)

    entries: List[Dict[str, object]] = []
    current: Dict[str, object] | None = None
    header_pattern = re.compile(r"(@| at | – | — | - | \| |\d{4})", re.IGNORECASE)
    for line in lines:
        if current is None or header_pattern.search(line):
            if current:
                current["bullets"] = [bullet for bullet in current.get("bullets", []) if bullet]
                if current["role"] or current["bullets"]:
                    entries.append(current)
            current = {
                "role": line.strip(),
                "company": "",
                "location": "",
                "date_range": "",
                "bullets": [],
            }
        else:
            current.setdefault("bullets", []).append(line.strip())

    if current:
        current.setdefault("bullets", []).extend(bullets)
        current["bullets"] = [bullet for bullet in current.get("bullets", []) if bullet]
        if current["role"] or current["bullets"]:
            entries.append(current)
    elif bullets:
        entries.append(
            {
                "role": "",
                "company": "",
                "location": "",
                "date_range": "",
                "bullets": bullets,
            }
        )
    return entries


def build_resume_document(
    reference: ReferenceStructure,
    profile: ResumeProfile,
    insights: SkillInsights,
) -> ResumeDocument:
    """Create the resume document using reference styling and updated content."""
    _sanitize_profile(profile)
    merged_skills = _merge_skills(profile, insights)
    grouped_skills = _group_skills(merged_skills)

    # Summary section
    summary_paragraph = SUMMARY_TEMPLATE
    summary_terms = _collect_job_summary_terms(insights)
    if summary_terms:
        summary_paragraph = (
            f"{_ensure_sentence(SUMMARY_TEMPLATE)} Key strengths aligned to this role: {', '.join(summary_terms)}."
        )
    summary_section = ResumeSection(title="Summary", paragraphs=[_sanitize_text(summary_paragraph)])

    # Skills section
    skills_section = ResumeSection(title="Technical Skills")
    skill_categories = _build_skill_categories(profile, insights)
    technical_skill_terms: List[str] = []
    if skill_categories:
        skills_section.meta["category_lines"] = [(category, values) for category, values in skill_categories.items()]
        for values in skill_categories.values():
            technical_skill_terms.extend(values)
    skills_section.bullets = []

    highlight_seed_terms = list(technical_skill_terms) + EXPLICIT_HIGHLIGHT_SKILLS
    highlight_terms = _collect_highlight_terms(profile, insights, highlight_seed_terms)

    # Experience section
    additional_sections = list(profile.additional_sections)
    experience_entries = [_format_experience_entry(exp) for exp in profile.experience]
    ref_experience_section = next(
        (section for section in reference.sections if "experience" in section.title.lower()),
        None,
    )
    experience_section = ResumeSection(title=ref_experience_section.title if ref_experience_section else "Professional Experience")
    if experience_entries:
        experience_section.meta["entries"] = experience_entries
        experience_section.meta["highlight_terms"] = list(highlight_terms)
    else:
        fallback_experience_section = _pop_additional_section(additional_sections, ("experience", "employment", "work history"))
        fallback_source = fallback_experience_section or ref_experience_section
        if fallback_source:
            fallback_entries = _build_fallback_experience_entries(fallback_source)
            if fallback_entries:
                experience_section.meta["entries"] = fallback_entries
                experience_section.meta["highlight_terms"] = list(highlight_terms)
            else:
                experience_section.paragraphs = list(fallback_source.paragraphs)
                experience_section.bullets = list(fallback_source.bullets)
                experience_section.meta["highlight_terms"] = list(highlight_terms)
        else:
            experience_section.paragraphs = []
            experience_section.bullets = []
    if "highlight_terms" not in experience_section.meta:
        experience_section.meta["highlight_terms"] = list(highlight_terms)

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
            education_lines.append(f"■ {detail}")
    ref_education_section = next(
        (section for section in reference.sections if "education" in section.title.lower()),
        None,
    )
    if education_lines:
        education_section = _build_section("Education", education_lines, bullets=False)
    else:
        fallback_education_section = _pop_additional_section(additional_sections, ("education", "academic"))
        fallback_source = fallback_education_section or ref_education_section
        if fallback_source:
            education_section = ResumeSection(title=fallback_source.title or "Education")
            education_section.paragraphs = [line.strip() for line in fallback_source.paragraphs if line.strip()]
            education_section.bullets = [line.strip() for line in fallback_source.bullets if line.strip()]
        else:
            education_section = ResumeSection(title="Education")
            education_section.paragraphs = []
            education_section.bullets = []

    project_sections: List[ResumeSection] = []
    if profile.projects:
        project_lines: List[str] = []
        for project in profile.projects:
            title = project.get("name")
            tagline = project.get("summary") or project.get("description", "")
            technologies = project.get("technologies", [])
            highlight = " | ".join(
                [part for part in [title, tagline, ", ".join(technologies)] if part]
            )
            if highlight:
                project_lines.append(highlight)
            for bullet in project.get("bullets", []) or []:
                project_lines.append(f"■ {bullet}")
        project_section = _build_section("Projects", project_lines, bullets=False)
        project_section.meta["highlight_terms"] = list(highlight_terms)
        project_sections.append(project_section)

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

    if not any(section.title.lower() == "awards" for section in additional_sections):
        ref_awards_section = next(
            (section for section in reference.sections if section.title.lower() == "awards"),
            None,
        )
        if ref_awards_section:
            awards_section = ResumeSection(title=ref_awards_section.title)
            awards_section.paragraphs = list(ref_awards_section.paragraphs)
            awards_section.bullets = list(ref_awards_section.bullets)
            additional_sections.append(awards_section)

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
        title_lower = (section.title or "").strip().lower()
        if title_lower == "awards":
            section.meta.setdefault("highlight_terms", list(highlight_terms))
        elif section.bullets and "highlight_terms" not in section.meta:
            section.meta["highlight_terms"] = list(highlight_terms)
    sections.extend(additional_sections)

    for section in sections:
        _sanitize_section_content(section)

    theme: Theme = reference.theme
    return ResumeDocument(profile=profile, sections=sections, theme=theme)
SUMMARY_TEMPLATE = (
    "Principal Front-End Engineer with 10+ years of experience building high-scale web applications for global product companies. "
    "Expert in React and micro front-ends, with a focus on architecting resilient CI/CD pipelines that slash deployment times and boost developer velocity. "
    "I specialize in bridging the gap between complex engineering and business impact, ensuring systems are as performant as they are scalable."
)

SKILL_CATEGORY_KEYWORDS: "OrderedDict[str, List[str]]" = OrderedDict(
    [
        (
            "Frontend",
            [
                "react",
                "redux",
                "mobx",
                "angular",
                "next",
                "nuxt",
                "svelte",
                "html",
                "css",
                "sass",
                "less",
                "micro front",
                "module federation",
                "storybook",
                "webpack",
                "vite",
                "tailwind",
                "styled components",
                "material",
                "mui",
            ],
        ),
        (
            "Backend",
            [
                "node",
                "nestjs",
                "express",
                "fastify",
                "graphql",
                "rest",
                "api",
                "python",
                "django",
                "flask",
                "fastapi",
                "java",
                "spring",
                "kotlin",
                "go",
                "php",
                "laravel",
                "ruby",
                "rails",
            ],
        ),
        (
            "Testing & DevOps",
            [
                "jest",
                "rtl",
                "react testing library",
                "cypress",
                "playwright",
                "selenium",
                "unit testing",
                "integration testing",
                "tdd",
                "bdd",
                "ci",
                "cd",
                "pipeline",
                "github actions",
                "gitlab",
                "teamcity",
                "jenkins",
                "docker",
                "kubernetes",
                "helm",
                "terraform",
                "ansible",
                "devops",
            ],
        ),
        ("AI Tools", ["codex", "cline", "copilot", "chatgpt", "cursor", "autopilot"]),
    ]
)

MAX_SKILLS_PER_CATEGORY = 6

EXPLICIT_HIGHLIGHT_SKILLS: List[str] = [
    "React.js",
    "Next.js",
    "TypeScript",
    "Micro-frontends (Module Federation)",
    "Server-Side Rendering (SSR)",
    "Webpack",
    "Vite",
    "Tailwind CSS",
    "State Management (Redux, MobX)",
    "Node.js",
    "Express",
    "Java/Spring Boot",
    "RESTful API Design",
    "Microservices",
    "NoSQL (MongoDB)",
    "AWS (Lambda, S3, SQS)",
    "CI/CD Pipelines",
    "Jest",
    "Playwright",
    "Cypress",
    "Performance Optimization (Lighthouse)",
    "GitHub Copilot",
    "Cline",
    "Codex",
]
def _ensure_resume_section(obj: object) -> ResumeSection:
    if isinstance(obj, ResumeSection):
        return obj
    if isinstance(obj, dict):
        title = obj.get("title", "")
        paragraphs = obj.get("paragraphs") or []
        bullets = obj.get("bullets") or []
        meta = obj.get("meta") or {}
        section = ResumeSection(
            title=_sanitize_text(title).strip(),
            paragraphs=[_sanitize_text(p).strip() for p in paragraphs if _sanitize_text(p).strip()],
            bullets=[_sanitize_text(b).strip() for b in bullets if _sanitize_text(b).strip()],
            meta=dict(meta),
        )
        return section
    return ResumeSection(title=_sanitize_text(str(obj)).strip() or "Untitled Section")
