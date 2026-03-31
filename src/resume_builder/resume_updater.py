from __future__ import annotations

from datetime import datetime
from typing import List

from dateutil import parser as date_parser

from .models import ReferenceStructure, ResumeDocument, ResumeProfile, ResumeSection, SkillInsights, Theme


def _normalize_skill(skill: str) -> str:
    return skill.strip()


def _merge_skills(profile: ResumeProfile, insights: SkillInsights) -> List[str]:
    existing = {_normalize_skill(skill).lower(): skill for skill in profile.skills}
    ordered: List[str] = list(profile.skills)
    for skill in insights.mandatory:
        key = _normalize_skill(skill).lower()
        if key not in existing:
            ordered.append(skill)
            existing[key] = skill
    return ordered


def _format_experience_item(item: dict) -> List[str]:
    lines: List[str] = []
    role = item.get("role") or item.get("title")
    company = item.get("company")
    start = item.get("start")
    end = item.get("end") or "Present"
    location = item.get("location")

    def _fmt_date(value: str | None) -> str:
        if not value:
            return ""
        try:
            parsed = date_parser.parse(str(value))
            return parsed.strftime("%b %Y")
        except (ValueError, TypeError):
            return str(value)

    date_part = f"{_fmt_date(start)} – {_fmt_date(end)}" if start or end else ""
    header_parts = [part for part in [role, company, location, date_part] if part]
    if header_parts:
        lines.append(" | ".join(header_parts))
    for bullet in item.get("bullets", []) or []:
        lines.append(f"• {bullet}")
    return lines


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

    # Summary section
    summary_lines = list(profile.summary)
    if insights.mandatory:
        summary_lines.append(
            "Core strengths aligned with the role: " + ", ".join(insights.mandatory[:6])
        )
    summary_section = ResumeSection(title="Summary", paragraphs=summary_lines)

    # Skills section
    skills_section = ResumeSection(title="Skills", bullets=merged_skills)

    # Experience section
    experience_lines: List[str] = []
    for experience in profile.experience:
        experience_lines.extend(_format_experience_item(experience))
    experience_section = _build_section("Experience", experience_lines, bullets=False)

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
    sections.extend(additional_sections)

    theme: Theme = reference.theme
    return ResumeDocument(profile=profile, sections=sections, theme=theme)
