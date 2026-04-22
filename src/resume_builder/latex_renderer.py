from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, List, Sequence, Tuple

from .models import ResumeDocument, ResumeProfile, ResumeSection

_ISO_DATE_PATTERN = re.compile(r"^(\d{4})-(\d{2})(?:-(\d{2}))?$")
_LATEX_ESCAPE_MAP = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "_": r"\_",
    "%": r"\%",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
_SPACE_PATTERN = re.compile(r"\s+")
_BOLD_OPEN_TAG = "<b>"
_BOLD_CLOSE_TAG = "</b>"
_METRIC_PATTERN = re.compile(
    r"(?<!\w)\d[\d,]*(?:\.\d+)?\+?(?:\s?(?:%|percent|pts|x|k|m|b|million|billion))?(?!\w)",
    re.IGNORECASE,
)
_UPPER_PATTERN = re.compile(r"\b[A-Z0-9]+(?:[/-][A-Z0-9]+)+\b|\b[A-Z0-9]{2,}\b")
_UPPER_STOPWORDS = {"AND", "THE", "FOR", "WITH", "FROM", "THIS", "THAT"}
_MONTH_ABBR_PATTERN = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\b", re.IGNORECASE)
_DATE_RANGE_SEPARATOR_PATTERN = re.compile(r"\s+(?:--|-|–|—)\s+")
_PDFLATEX_FALLBACK_PATHS = (
    "/Library/TeX/texbin/pdflatex",
    "/usr/texbin/pdflatex",
    "/opt/homebrew/bin/pdflatex",
    "/usr/local/bin/pdflatex",
    "/usr/bin/pdflatex",
)


@dataclass
class _WorkEntry:
    role: str
    company: str
    location: str
    date_range: str
    bullets: List[str]


@dataclass
class _EducationEntry:
    institution: str
    degree: str
    detail_line: str


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u00a0", " ").strip()
    return _SPACE_PATTERN.sub(" ", text)


def _latex_escape(value: object) -> str:
    text = _clean_text(value)
    text = text.replace("–", "--").replace("—", "--")
    return "".join(_LATEX_ESCAPE_MAP.get(char, char) for char in text)


def _latex_escape_fragment(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u00a0", " ")
    text = text.replace("–", "--").replace("—", "--")
    return "".join(_LATEX_ESCAPE_MAP.get(char, char) for char in text)


def _normalize_url(value: str | None) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    lowered = text.lower()
    if lowered.startswith(("http://", "https://", "mailto:")):
        return text
    if "@" in text and "/" not in text and " " not in text:
        return f"mailto:{text}"
    return f"https://{text}"


def _profile_headline(profile: ResumeProfile) -> str:
    headline = _clean_text(profile.headline)
    if not headline:
        return ""
    lower = headline.lower()
    marker = " at "
    if marker not in lower:
        return _latex_escape(headline)
    split_index = lower.rfind(marker)
    role = headline[:split_index].strip()
    company = headline[split_index + len(marker) :].strip()
    if role and company:
        return f"{_latex_escape(role)} at \\textbf{{{_latex_escape(company)}}}"
    return _latex_escape(headline)


def _format_month_year(value: object) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    lowered = text.lower()
    if lowered in {"present", "current", "now"}:
        return "Present"
    match = _ISO_DATE_PATTERN.fullmatch(text)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3) or "1")
        try:
            parsed = datetime(year, month, day)
        except ValueError:
            return text
        return parsed.strftime("%b %Y")
    return text


def _format_year(value: object) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    if re.fullmatch(r"\d{4}", text):
        return text
    match = _ISO_DATE_PATTERN.fullmatch(text)
    if match:
        return match.group(1)
    return text


def _section_title(section: ResumeSection) -> str:
    return _clean_text(section.title).lower()


def _find_section(sections: Sequence[ResumeSection], keywords: Iterable[str]) -> ResumeSection | None:
    options = tuple(_clean_text(keyword).lower() for keyword in keywords if _clean_text(keyword))
    for section in sections:
        title = _section_title(section)
        if any(keyword in title for keyword in options):
            return section
    return None


def _non_empty(values: Iterable[object]) -> List[str]:
    cleaned: List[str] = []
    for value in values:
        text = _clean_text(value)
        if text:
            cleaned.append(text)
    return cleaned


def _summary_text(document: ResumeDocument) -> str:
    if document.profile.summary:
        return " ".join(_non_empty(document.profile.summary))
    summary_section = _find_section(document.sections, ("summary", "objective", "profile"))
    if not summary_section:
        return ""
    content = _non_empty(list(summary_section.paragraphs) + list(summary_section.bullets))
    return " ".join(content)


def _section_heading(section: ResumeSection | None, fallback: str) -> str:
    if section and _clean_text(section.title):
        return _clean_text(section.title)
    return fallback


def _append_section_heading(
    lines: List[str],
    title: str,
) -> None:
    lines.append(f"\\section*{{\\fontsize{{13pt}}{{15pt}}\\selectfont {_latex_escape(title)}}}")
    lines.append(r"\vspace{-16pt}")
    lines.append(r"\noindent\rule{\textwidth}{0.5pt}")


def _unique_terms(terms: Iterable[object]) -> List[str]:
    seen: set[str] = set()
    cleaned: List[str] = []
    for term in terms:
        candidate = _clean_text(term)
        if not candidate:
            continue
        lowered = candidate.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(candidate)
    cleaned.sort(key=len, reverse=True)
    return cleaned


def _apply_highlight_terms(text: str, terms: Sequence[str]) -> str:
    if not text or not terms:
        return text
    result = text
    for term in _unique_terms(terms):
        pattern = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE)

        def repl(match: re.Match[str]) -> str:
            start, end = match.span()
            if _is_inside_bold_span(match.string, start, end):
                return match.group(0)
            return f"{_BOLD_OPEN_TAG}{match.group(0)}{_BOLD_CLOSE_TAG}"

        result = pattern.sub(repl, result)
    return result


def _is_inside_bold_span(source: str, start: int, end: int) -> bool:
    open_index = source.rfind(_BOLD_OPEN_TAG, 0, start)
    if open_index == -1:
        return False
    close_index = source.rfind(_BOLD_CLOSE_TAG, 0, start)
    if close_index > open_index:
        return False
    return source.find(_BOLD_CLOSE_TAG, end) != -1


def _highlight_metrics(text: str) -> str:
    if not text:
        return text

    def repl(match: re.Match[str]) -> str:
        start, end = match.span()
        if _is_inside_bold_span(match.string, start, end):
            return match.group(0)
        return f"{_BOLD_OPEN_TAG}{match.group(0)}{_BOLD_CLOSE_TAG}"

    return _METRIC_PATTERN.sub(repl, text)


def _highlight_uppercase_terms(text: str) -> str:
    if not text:
        return text

    def repl(match: re.Match[str]) -> str:
        word = match.group(0)
        if word in _UPPER_STOPWORDS:
            return word
        if not any(char.isalpha() for char in word):
            return word
        start, end = match.span()
        if _is_inside_bold_span(match.string, start, end):
            return word
        return f"{_BOLD_OPEN_TAG}{word}{_BOLD_CLOSE_TAG}"

    return _UPPER_PATTERN.sub(repl, text)


def _highlight_markup(text: str, terms: Sequence[str]) -> str:
    highlighted = _apply_highlight_terms(text, terms)
    highlighted = _highlight_metrics(highlighted)
    highlighted = _highlight_uppercase_terms(highlighted)
    return highlighted


def _latex_from_bold_markup(value: str) -> str:
    if not value:
        return ""
    if _BOLD_OPEN_TAG not in value:
        return _latex_escape_fragment(value)

    chunks = re.split(r"(<b>|</b>)", value)
    bold = False
    parts: List[str] = []
    for chunk in chunks:
        if chunk == _BOLD_OPEN_TAG:
            bold = True
            continue
        if chunk == _BOLD_CLOSE_TAG:
            bold = False
            continue
        escaped = _latex_escape_fragment(chunk)
        if not escaped:
            continue
        if bold:
            parts.append(f"\\textbf{{{escaped}}}")
        else:
            parts.append(escaped)
    return "".join(parts)


def _highlighted_latex_text(value: object, terms: Sequence[str]) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        return ""
    marked = _highlight_markup(cleaned, terms)
    return _latex_from_bold_markup(marked)


def _split_skill_line(line: str) -> Tuple[str, str] | None:
    cleaned = _clean_text(line)
    if ":" not in cleaned:
        return None
    category, values = cleaned.split(":", 1)
    clean_category = _clean_text(category).rstrip(":")
    clean_values = _clean_text(values)
    if not clean_category or not clean_values:
        return None
    return clean_category, clean_values


def _skills_content(document: ResumeDocument) -> Tuple[List[Tuple[str, str]], List[str], ResumeSection | None]:
    section = _find_section(document.sections, ("technical skills", "skills"))
    category_lines: List[Tuple[str, str]] = []
    freeform_lines: List[str] = []
    seen_category_lines: set[str] = set()
    seen_freeform: set[str] = set()

    def add_category_line(category: object, values: Iterable[object] | object) -> None:
        category_text = _clean_text(category).rstrip(":")
        raw_values = values if isinstance(values, (list, tuple, set)) else [values]
        value_text = ", ".join(_non_empty(raw_values))
        if not category_text or not value_text:
            return
        key = f"{category_text.lower()}::{value_text.lower()}"
        if key in seen_category_lines:
            return
        seen_category_lines.add(key)
        category_lines.append((category_text, value_text))

    def add_freeform_line(line: object) -> None:
        text = _clean_text(line)
        if not text:
            return
        parsed = _split_skill_line(text)
        if parsed:
            add_category_line(parsed[0], [parsed[1]])
            return
        key = text.lower()
        if key in seen_freeform:
            return
        seen_freeform.add(key)
        freeform_lines.append(text)

    if section and isinstance(section.meta, dict):
        raw_category_lines = section.meta.get("category_lines")
        if isinstance(raw_category_lines, list):
            for item in raw_category_lines:
                if isinstance(item, dict):
                    add_category_line(item.get("category"), item.get("items", []))
                elif isinstance(item, (list, tuple)) and len(item) == 2:
                    raw_items = item[1] if isinstance(item[1], (list, tuple, set)) else [item[1]]
                    add_category_line(item[0], raw_items)
    if section:
        for bullet in _non_empty(section.bullets):
            add_freeform_line(bullet)
    if not category_lines and not freeform_lines:
        for skill in _non_empty(document.profile.skills):
            add_freeform_line(skill)

    return category_lines, freeform_lines, section


def _collect_highlight_terms(document: ResumeDocument) -> List[str]:
    terms: List[str] = []
    seen: set[str] = set()

    def add(raw: object) -> None:
        candidate = _clean_text(raw)
        if not candidate:
            return
        if len(candidate.split()) > 4:
            return
        lowered = candidate.lower()
        if lowered in seen:
            return
        seen.add(lowered)
        terms.append(candidate)

    for section in document.sections:
        if not isinstance(section.meta, dict):
            continue
        highlight_terms = section.meta.get("highlight_terms")
        if not isinstance(highlight_terms, list):
            continue
        for term in highlight_terms:
            add(term)

    if terms:
        return terms

    for skill in _non_empty(document.profile.skills):
        if ":" in skill:
            _, values = skill.split(":", 1)
            for fragment in values.split(","):
                add(fragment)
        else:
            for fragment in skill.split(","):
                add(fragment)

    return terms


def _work_entries_from_section(section: ResumeSection) -> List[_WorkEntry]:
    entries: List[_WorkEntry] = []
    if not isinstance(section.meta, dict):
        return entries
    raw_entries = section.meta.get("entries")
    if not isinstance(raw_entries, list):
        return entries
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        role = _clean_text(item.get("role") or item.get("title"))
        company = _clean_text(item.get("company"))
        location = _clean_text(item.get("location"))
        date_range = _clean_text(item.get("date_range"))
        if not date_range:
            start = _format_month_year(item.get("start"))
            end = _format_month_year(item.get("end"))
            if start and end:
                date_range = f"{start} -- {end}"
            else:
                date_range = start or end
        bullets = _non_empty(item.get("bullets", []))
        if not any([role, company, location, date_range, bullets]):
            continue
        entries.append(
            _WorkEntry(
                role=role,
                company=company,
                location=location,
                date_range=date_range,
                bullets=bullets,
            )
        )
    return entries


def _work_entries_from_profile(profile: ResumeProfile) -> List[_WorkEntry]:
    entries: List[_WorkEntry] = []
    for item in profile.experience or []:
        if not isinstance(item, dict):
            continue
        role = _clean_text(item.get("role") or item.get("title"))
        company = _clean_text(item.get("company"))
        location = _clean_text(item.get("location"))
        start = _format_month_year(item.get("start"))
        end = _format_month_year(item.get("end"))
        if start and end:
            date_range = f"{start} -- {end}"
        else:
            date_range = start or end
        bullets = _non_empty(item.get("bullets", []))
        if not any([role, company, location, date_range, bullets]):
            continue
        entries.append(
            _WorkEntry(
                role=role,
                company=company,
                location=location,
                date_range=date_range,
                bullets=bullets,
            )
        )
    return entries


def _match_profile_entry(
    entry: _WorkEntry,
    profile_entries: Sequence[_WorkEntry],
    index: int,
) -> _WorkEntry | None:
    role_key = _clean_text(entry.role).lower()
    company_key = _clean_text(entry.company).lower()

    if role_key and company_key:
        for candidate in profile_entries:
            if _clean_text(candidate.role).lower() == role_key and _clean_text(candidate.company).lower() == company_key:
                return candidate

    if role_key:
        for candidate in profile_entries:
            if _clean_text(candidate.role).lower() == role_key:
                return candidate

    if company_key:
        for candidate in profile_entries:
            if _clean_text(candidate.company).lower() == company_key:
                return candidate

    if 0 <= index < len(profile_entries):
        return profile_entries[index]
    return None


def _merge_work_entries_with_profile(
    section_entries: Sequence[_WorkEntry],
    profile_entries: Sequence[_WorkEntry],
) -> List[_WorkEntry]:
    merged: List[_WorkEntry] = []
    for index, entry in enumerate(section_entries):
        fallback = _match_profile_entry(entry, profile_entries, index)
        if not fallback:
            merged.append(entry)
            continue
        merged.append(
            _WorkEntry(
                role=entry.role or fallback.role,
                company=entry.company or fallback.company,
                location=entry.location or fallback.location,
                date_range=entry.date_range or fallback.date_range,
                bullets=entry.bullets if entry.bullets else list(fallback.bullets),
            )
        )
    return merged


def _work_entries(document: ResumeDocument) -> List[_WorkEntry]:
    profile_entries = _work_entries_from_profile(document.profile)
    section = _find_section(document.sections, ("professional experience", "work experience", "experience"))
    if section:
        from_section = _work_entries_from_section(section)
        if from_section:
            if profile_entries:
                return _merge_work_entries_with_profile(from_section, profile_entries)
            return from_section
    return profile_entries


def _stylize_date_range(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return ""

    text = _DATE_RANGE_SEPARATOR_PATTERN.sub(" – ", text)

    def _month_repl(match: re.Match[str]) -> str:
        token = match.group(1)
        canonical = token[:1].upper() + token[1:].lower()
        if canonical.lower() == "sept":
            canonical = "Sep"
        if canonical == "May":
            return canonical
        return f"{canonical}."

    text = _MONTH_ABBR_PATTERN.sub(_month_repl, text)
    return text


def _stylize_location(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    lowered = text.lower()
    if lowered in {"bangalore", "bengaluru", "bangalore india", "bangalore, india", "bengaluru, india"}:
        return "Bangalore, KA"
    return text


def _education_entries(document: ResumeDocument) -> List[_EducationEntry]:
    entries: List[_EducationEntry] = []
    for item in document.profile.education or []:
        if not isinstance(item, dict):
            continue
        institution = _clean_text(item.get("institution") or item.get("school"))
        degree = _clean_text(item.get("degree"))
        location = _clean_text(item.get("location"))
        year = _clean_text(item.get("year"))
        if not year:
            start_year = _format_year(item.get("start"))
            end_year = _format_year(item.get("end"))
            if start_year and end_year:
                year = f"{start_year} -- {end_year}"
            else:
                year = start_year or end_year
        if not any([institution, degree, location, year]):
            continue
        detail_parts = [part for part in [location, year] if part]
        detail_line = ", ".join(detail_parts)
        entries.append(
            _EducationEntry(
                institution=institution,
                degree=degree,
                detail_line=detail_line,
            )
        )
    if entries:
        return entries

    section = _find_section(document.sections, ("education", "academic", "qualification"))
    if not section:
        return entries
    for paragraph in _non_empty(section.paragraphs):
        entries.append(_EducationEntry(institution=paragraph, degree="", detail_line=""))
    return entries


def _awards(document: ResumeDocument) -> List[str]:
    collected: List[str] = []
    for section in document.sections:
        if "award" not in _section_title(section):
            continue
        collected.extend(_non_empty(section.bullets))
        collected.extend(_non_empty(section.paragraphs))
    if collected:
        return collected
    for section in document.profile.additional_sections:
        if "award" not in _section_title(section):
            continue
        collected.extend(_non_empty(section.bullets))
        collected.extend(_non_empty(section.paragraphs))
    return collected


def build_latex_resume_source(document: ResumeDocument) -> str:
    profile = document.profile
    summary_text = _summary_text(document)
    skill_category_lines, skill_freeform_lines, skill_section = _skills_content(document)
    work_entries = _work_entries(document)
    education_entries = _education_entries(document)
    awards = _awards(document)
    highlight_terms = _collect_highlight_terms(document)
    summary_section = _find_section(document.sections, ("summary", "objective", "profile"))
    experience_section = _find_section(document.sections, ("professional experience", "work experience", "experience"))
    education_section = _find_section(document.sections, ("education", "academic", "qualification"))
    awards_section = _find_section(document.sections, ("awards", "achievements", "honors"))
    summary_heading = _section_heading(summary_section, "Professional Summary")
    skills_heading = _section_heading(skill_section, "Technical Skills")
    experience_heading = _section_heading(experience_section, "Work Experience")
    education_heading = _section_heading(education_section, "Education")
    awards_heading = _section_heading(awards_section, "Awards")
    contact = profile.contact or {}

    phone = _clean_text(contact.get("phone") or contact.get("mobile"))
    email = _clean_text(contact.get("email"))
    location = _clean_text(contact.get("location"))
    linkedin_url = _normalize_url(contact.get("linkedin"))
    github_url = _normalize_url(contact.get("github"))
    notice_note = _clean_text(contact.get("notice_note") or contact.get("noticeNote") or contact.get("notice"))

    headline = _profile_headline(profile)
    if not headline and work_entries:
        primary = work_entries[0]
        if primary.role and primary.company:
            headline = f"{_latex_escape(primary.role)} at \\textbf{{{_latex_escape(primary.company)}}}"
        elif primary.role:
            headline = _latex_escape(primary.role)

    contact_parts: List[str] = []
    if phone:
        contact_parts.append(_latex_escape(phone))
    if email:
        escaped_email = _latex_escape(email)
        contact_parts.append(f"\\href{{mailto:{_latex_escape(email)}}}{{{escaped_email}}}")
    if location:
        contact_parts.append(_latex_escape(location))
    if linkedin_url:
        contact_parts.append(f"\\href{{{_latex_escape(linkedin_url)}}}{{LinkedIn}}")
    if github_url:
        contact_parts.append(f"\\href{{{_latex_escape(github_url)}}}{{Github}}")

    lines: List[str] = [
        r"\documentclass[a4paper,10pt]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[margin=0.75in]{geometry}",
        r"\usepackage{enumitem}",
        r"\usepackage{hyperref}",
        r"\usepackage{setspace}",
        r"\usepackage{amssymb}",
        r"\setstretch{1.25}",
        r"\renewcommand{\labelitemi}{\raisebox{0.15ex}{\rule{0.6ex}{0.6ex}}}",
        r"\begin{document}",
        "",
        "% --- CONTACT INFORMATION ---",
        r"\begin{center}",
        f"    {{\\LARGE \\textbf{{{_latex_escape(profile.name)}}}}} \\\\",
    ]

    if headline:
        lines.extend(
            [
                r"    \vspace{5pt}",
                f"    {headline} \\\\",
            ]
        )
    if contact_parts:
        lines.extend(
            [
                r"    \vspace{5pt}",
                f"    {' --- '.join(contact_parts)}",
            ]
        )
    summary_line = _highlighted_latex_text(summary_text, highlight_terms)
    if not summary_line:
        summary_line = "Experienced software engineer focused on scalable web applications."

    rendered_skills: List[str] = []
    for category, values in skill_category_lines:
        rendered_skills.append(f"\\textbf{{{_latex_escape(category)}:}} {_latex_escape(values)}")
    for line in skill_freeform_lines:
        highlighted_line = _highlighted_latex_text(line, highlight_terms)
        if highlighted_line:
            rendered_skills.append(highlighted_line)

    lines.extend(
        [
            r"\end{center}",
            "% --- PROFESSIONAL SUMMARY ---",
        ]
    )
    _append_section_heading(lines, summary_heading)
    lines.append(summary_line)
    lines.extend(
        [
            "% --- TECHNICAL SKILLS ---",
        ]
    )
    _append_section_heading(lines, skills_heading)

    if rendered_skills:
        for index, line in enumerate(rendered_skills):
            suffix = r" \\" if index < len(rendered_skills) - 1 else ""
            lines.append(f"{line}{suffix}")
    else:
        lines.append("Not specified.")
    lines.extend(
        [
            "% --- WORK EXPERIENCE ---",
        ]
    )
    _append_section_heading(lines, experience_heading)

    for index, entry in enumerate(work_entries):
        role = _latex_escape(entry.role or "Role")
        date_range = _latex_escape(_stylize_date_range(entry.date_range))
        company = _latex_escape(entry.company)
        location_text = _latex_escape(_stylize_location(entry.location))
        lines.append(r"\begin{tabular*}{\textwidth}{@{}l@{\extracolsep{\fill}}r@{}}")
        lines.append(f"\\textbf{{{role}}} & {date_range} \\\\")
        if company or location_text:
            left_company = f"\\textit{{{company}}}" if company else ""
            right_location = f"\\textit{{{location_text}}}" if location_text else ""
            lines.append(f"{left_company} & {right_location} \\\\")
        lines.append(r"\end{tabular*}")
        if entry.bullets:
            lines.append(r"\begin{itemize}[noitemsep, topsep=2pt]")
            for bullet in entry.bullets:
                lines.append(f"    \\item {_highlighted_latex_text(bullet, highlight_terms)}")
            lines.append(r"\end{itemize}")
        if index < len(work_entries) - 1:
            lines.append(r"\vspace{5pt}")

    lines.extend(
        [
            "% --- EDUCATION ---",
        ]
    )
    _append_section_heading(lines, education_heading)
    for entry in education_entries:
        institution = _latex_escape(entry.institution)
        degree = _latex_escape(entry.degree)
        detail_line = _latex_escape(entry.detail_line)
        if institution and detail_line:
            lines.append(f"\\textbf{{{institution}}} \\hfill {detail_line} \\\\")
        elif institution:
            lines.append(f"\\textbf{{{institution}}} \\\\")
        if degree:
            lines.append(degree)

    if awards:
        lines.extend(
            [
                "% --- AWARDS ---",
            ]
        )
        _append_section_heading(lines, awards_heading)
        lines.append(r"\begin{itemize}[noitemsep, topsep=2pt]")
        for award in awards:
            lines.append(f"    \\item {_latex_escape(award)}")
        lines.append(r"\end{itemize}")

    if notice_note:
        lines.extend(
            [
                "",
                r"\vspace{10pt}",
                r"\begin{center}",
                f"    \\textit{{Note: {_latex_escape(notice_note)}}}",
                r"\end{center}",
            ]
        )

    lines.extend(["", r"\end{document}", ""])
    return "\n".join(lines)


def write_latex_resume(document: ResumeDocument, output_path: str | Path) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(build_latex_resume_source(document), encoding="utf-8")
    return destination


def _tail_log(stdout: str, stderr: str, limit: int = 25) -> str:
    lines: List[str] = []
    for chunk in (stdout, stderr):
        if not chunk:
            continue
        lines.extend(line for line in chunk.splitlines() if line.strip())
    if not lines:
        return "Unknown LaTeX compilation error."
    tail = lines[-limit:]
    return "\n".join(tail)


def _is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _resolve_pdflatex() -> str | None:
    discovered = shutil.which("pdflatex")
    if discovered:
        candidate = Path(discovered)
        if _is_executable_file(candidate):
            return str(candidate)

    texbin_env = os.environ.get("TEXBIN", "").strip()
    if texbin_env:
        texbin_candidate = Path(texbin_env) / "pdflatex"
        if _is_executable_file(texbin_candidate):
            return str(texbin_candidate)

    for raw_path in _PDFLATEX_FALLBACK_PATHS:
        candidate = Path(raw_path)
        if _is_executable_file(candidate):
            return str(candidate)

    texlive_root = Path("/usr/local/texlive")
    if texlive_root.exists():
        candidates = sorted(texlive_root.glob("*/bin/*/pdflatex"), reverse=True)
        for candidate in candidates:
            if _is_executable_file(candidate):
                return str(candidate)
    return None


def render_latex_resume(
    document: ResumeDocument,
    output_path: str | Path,
    *,
    tex_output_path: str | Path | None = None,
) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    source = build_latex_resume_source(document)
    if tex_output_path is not None:
        tex_destination = Path(tex_output_path)
        tex_destination.parent.mkdir(parents=True, exist_ok=True)
        tex_destination.write_text(source, encoding="utf-8")

    compiler = _resolve_pdflatex()
    if not compiler:
        process_path = os.environ.get("PATH", "")
        raise FileNotFoundError(
            "pdflatex is not installed or not discoverable by this process. "
            "Install MacTeX/TeX Live, then restart the API process. "
            f"Current PATH: {process_path}"
        )

    with TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        tex_path = workspace / "resume.tex"
        tex_path.write_text(source, encoding="utf-8")

        command = [
            compiler,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            "-output-directory",
            str(workspace),
            str(tex_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            message = _tail_log(result.stdout, result.stderr)
            raise RuntimeError(f"LaTeX compilation failed with exit code {result.returncode}.\n{message}")

        compiled_pdf = workspace / "resume.pdf"
        if not compiled_pdf.exists():
            raise RuntimeError("LaTeX compilation completed, but no PDF was produced.")

        shutil.copyfile(compiled_pdf, destination)

    return destination
