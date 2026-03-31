from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path
from typing import List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from .models import ResumeDocument, ResumeSection, Theme

BASE_FONTS = {
    "Helvetica",
    "Helvetica-Bold",
    "Helvetica-Oblique",
    "Times-Roman",
    "Times-Bold",
    "Times-Italic",
    "Courier",
    "Courier-Bold",
}


def _unique_terms(terms: List[str]) -> List[str]:
    seen: set[str] = set()
    cleaned: List[str] = []
    for term in terms:
        if not term:
            continue
        candidate = str(term).strip()
        if not candidate:
            continue
        lowered = candidate.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(candidate)
    cleaned.sort(key=len, reverse=True)
    return cleaned


def _apply_highlight_terms(text: str, terms: List[str]) -> str:
    if not text or not terms:
        return text
    result = text
    for term in _unique_terms(terms):
        pattern = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE)
        result = pattern.sub(lambda match: f"<b>{match.group(0)}</b>", result)
    return result


_METRIC_PATTERN = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\+?(?:\s?(?:%|percent|pts|x|k|m|b|million|billion))?",
    re.IGNORECASE,
)


def _highlight_metrics(text: str) -> str:
    if not text:
        return text

    def repl(match: re.Match[str]) -> str:
        start = match.start()
        end = match.end()
        before = match.string[max(0, start - 3) : start].lower()
        after = match.string[end : end + 4].lower()
        if before == "<b>" and after.startswith("</b"):
            return match.group(0)
        return f"<b>{match.group(0)}</b>"

    return _METRIC_PATTERN.sub(repl, text)


_UPPER_PATTERN = re.compile(r"\b[A-Z0-9]{2,}\b")
_UPPER_STOPWORDS = {"AND", "THE", "FOR", "WITH", "FROM", "THIS", "THAT"}


def _highlight_uppercase_terms(text: str) -> str:
    if not text:
        return text

    def repl(match: re.Match[str]) -> str:
        word = match.group(0)
        if word in _UPPER_STOPWORDS:
            return word
        start = match.start()
        end = match.end()
        before = match.string[max(0, start - 3) : start].lower()
        after = match.string[end : end + 4].lower()
        if before == "<b>" and after.startswith("</b"):
            return word
        return f"<b>{word}</b>"

    return _UPPER_PATTERN.sub(repl, text)


def _format_highlighted_text(text: str, terms: List[str]) -> str:
    highlighted = _apply_highlight_terms(text, terms)
    highlighted = _highlight_metrics(highlighted)
    highlighted = _highlight_uppercase_terms(highlighted)
    return highlighted


def _hex_to_rgb(value: str) -> Tuple[float, float, float]:
    hex_value = value.lstrip("#")
    length = len(hex_value)
    if length not in (3, 6):
        return 0.0, 0.0, 0.0
    if length == 3:
        hex_value = "".join(ch * 2 for ch in hex_value)
    r = int(hex_value[0:2], 16) / 255.0
    g = int(hex_value[2:4], 16) / 255.0
    b = int(hex_value[4:6], 16) / 255.0
    return r, g, b


def _is_dark_color(hex_value: str) -> bool:
    r, g, b = _hex_to_rgb(hex_value or "#000000")
    # Perceived luminance formula
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return luminance < 0.5


def _tint_color(hex_value: str, amount: float = 0.25) -> colors.Color:
    r, g, b = _hex_to_rgb(hex_value or "#000000")
    r = min(1.0, r + (1.0 - r) * amount)
    g = min(1.0, g + (1.0 - g) * amount)
    b = min(1.0, b + (1.0 - b) * amount)
    return colors.Color(r, g, b)


def _resolve_font(font_name: str) -> str:
    """Fall back to core fonts if the reference font is unavailable."""
    if not font_name:
        return "Helvetica"
    if font_name in BASE_FONTS:
        return font_name
    if font_name.endswith("-Bold"):
        return "Helvetica-Bold"
    return "Helvetica"


def _build_styles(theme: Theme) -> StyleSheet1:
    styles = getSampleStyleSheet()
    body_font = _resolve_font(theme.body_font)
    heading_font = _resolve_font(theme.heading_font)
    accent = theme.accent_color or "#1a1a1a"
    primary = theme.primary_color or "#333333"
    accent_text = colors.white if _is_dark_color(accent) else colors.black
    accent_tint = _tint_color(accent, 0.6)
    primary_color = colors.HexColor(primary)
    accent_line = _tint_color(accent, 0.7)

    styles.add(
        ParagraphStyle(
            "ResumeBody",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=theme.body_size,
            leading=theme.body_size * theme.line_height,
            textColor=primary_color,
        )
    )
    styles.add(
        ParagraphStyle(
            "ResumeMuted",
            parent=styles["ResumeBody"],
            textColor=colors.HexColor("#5f6b7a"),
        )
    )
    styles.add(
        ParagraphStyle(
            "ResumeHeading",
            parent=styles["Heading2"],
            fontName=heading_font,
            fontSize=theme.heading_size,
            leading=theme.heading_size * theme.line_height,
            textColor=accent_tint,
            spaceBefore=theme.body_size,
            spaceAfter=theme.body_size * 0.5,
            uppercase=False,
        )
    )
    styles.add(
        ParagraphStyle(
            "ResumeName",
            parent=styles["Heading1"],
            fontName=heading_font,
            fontSize=theme.heading_size + 4,
            leading=(theme.heading_size + 4) * theme.line_height,
            textColor=accent_text,
            spaceAfter=theme.body_size * 0.5,
        )
    )
    styles.add(
        ParagraphStyle(
            "ResumeSubheading",
            parent=styles["Normal"],
            fontName=heading_font,
            fontSize=theme.body_size + 1,
            leading=(theme.body_size + 1) * theme.line_height,
            textColor=colors.HexColor(theme.primary_color),
            spaceAfter=theme.body_size * 0.5,
        )
    )
    styles.add(
        ParagraphStyle(
            "ResumeBullet",
            parent=styles["ResumeBody"],
            bulletIndent=12,
            leftIndent=18,
        )
    )
    styles.add(
        ParagraphStyle(
            "SectionTitle",
            parent=styles["ResumeBody"],
            fontName=heading_font,
            fontSize=theme.body_size + 3,
            textColor=colors.HexColor(accent),
            spaceBefore=theme.body_size * 0.9,
            spaceAfter=theme.body_size * 0.6,
            uppercase=False,
        )
    )
    styles.add(
        ParagraphStyle(
            "ExperienceHeader",
            parent=styles["ResumeBody"],
            fontName=body_font,
            fontSize=min(theme.body_size + 1.0, theme.heading_size),
            leading=(theme.body_size + 1.0) * theme.line_height,
            textColor=colors.HexColor("#192a3d"),
            spaceAfter=theme.body_size * 0.1,
        )
    )
    styles.add(
        ParagraphStyle(
            "ExperienceMeta",
            parent=styles["ResumeMuted"],
            fontSize=max(theme.body_size - 0.5, 8),
            spaceAfter=theme.body_size * 0.05,
        )
    )
    styles.add(
        ParagraphStyle(
            "HeaderHeadline",
            parent=styles["ResumeBody"],
            fontName=heading_font,
            fontSize=theme.heading_size - 2,
            textColor=accent_text,
        )
    )
    styles.add(
        ParagraphStyle(
            "HeaderContact",
            parent=styles["ResumeBody"],
            fontName=body_font,
            fontSize=theme.body_size,
            textColor=accent_text,
        )
    )
    styles.add(
        ParagraphStyle(
            "Chip",
            parent=styles["ResumeBody"],
            fontSize=theme.body_size - 0.5,
            leading=(theme.body_size - 0.5) * theme.line_height,
            alignment=1,
        )
    )
    styles.add(
        ParagraphStyle(
            "SectionRule",
            parent=styles["ResumeBody"],
            textColor=accent_line,
        )
    )
    return styles


def _section_elements(section: ResumeSection, styles: StyleSheet1) -> List:
    elements: List = []
    if not (section.paragraphs or section.bullets or section.meta):
        return elements

    elements.append(Paragraph(f"<b>{section.title}</b>", styles["SectionTitle"]))
    rule_color = getattr(styles["SectionRule"], "textColor", colors.HexColor("#b5c4d6"))
    elements.append(HRFlowable(width="100%", thickness=0.6, color=rule_color))
    elements.append(Spacer(1, 4))
    title_lower = section.title.lower()
    if title_lower in {"skills", "technical skills"}:
        elements.extend(_skills_layout(section, styles))
        return elements

    if title_lower in {"experience", "professional experience"}:
        elements.extend(_experience_layout(section, styles))
        return elements

    highlight_terms = section.meta.get("highlight_terms", [])
    is_awards = title_lower == "awards"

    if section.paragraphs:
        for paragraph in section.paragraphs:
            text = paragraph.strip()
            if not text:
                continue
            if text.startswith("•"):
                bullet_text = text.lstrip("• ").strip()
                if is_awards:
                    bullet_text = _format_highlighted_text(bullet_text, highlight_terms)
                bullet_item = ListItem(Paragraph(bullet_text, styles["ResumeBody"]))
                elements.append(
                    ListFlowable(
                        [bullet_item],
                        bulletType="bullet",
                        start="•",
                        leftIndent=12,
                        bulletFontName=_resolve_font(styles["ResumeBody"].fontName),
                        bulletFontSize=styles["ResumeBody"].fontSize,
                    )
                )
            else:
                if is_awards:
                    text = _format_highlighted_text(text, highlight_terms)
                elements.append(Paragraph(text, styles["ResumeBody"]))
            elements.append(Spacer(1, 4))

    if section.bullets and title_lower not in {"skills", "technical skills"}:
        bullet_items = [
            ListItem(
                Paragraph(
                    _format_highlighted_text(bullet.strip(), highlight_terms) if is_awards else bullet.strip(),
                    styles["ResumeBody"],
                )
            )
            for bullet in section.bullets
            if bullet.strip()
        ]
        if bullet_items:
            elements.append(
                ListFlowable(
                    bullet_items,
                    bulletType="bullet",
                    start="•",
                    leftIndent=12,
                    bulletFontName=_resolve_font(styles["ResumeBody"].fontName),
                    bulletFontSize=styles["ResumeBody"].fontSize,
                )
            )
            elements.append(Spacer(1, 6))
    if title_lower not in {"skills", "technical skills", "experience", "professional experience"} and elements:
        elements.append(Spacer(1, 6))
    return elements


def _skills_layout(section: ResumeSection, styles: StyleSheet1) -> List:
    category_lines = section.meta.get("category_lines")
    if category_lines:
        flowables: List = [Spacer(1, 4)]
        for category, items in category_lines:
            if not items:
                continue
            unique_items: List[str] = []
            seen: set[str] = set()
            for item in items:
                value = item.strip()
                if not value:
                    continue
                key = value.lower()
                if key in seen:
                    continue
                seen.add(key)
                unique_items.append(value)
            if not unique_items:
                continue
            line = f"<b>{category}:</b> {', '.join(unique_items)}"
            flowables.append(Paragraph(line, styles["ResumeBody"]))
            flowables.append(Spacer(1, 3))
        flowables.append(Spacer(1, 4))
        return flowables

    grouped = section.meta.get("grouped_skills")
    if grouped:
        flowables = [Spacer(1, 4)]
        for category, items in grouped.items():
            if not items:
                continue
            line = f"<b>{category}:</b> {', '.join(items)}"
            flowables.append(Paragraph(line, styles["ResumeBody"]))
            flowables.append(Spacer(1, 3))
        flowables.append(Spacer(1, 4))
        return flowables

    chips = [skill.strip() for skill in section.bullets if skill.strip()]
    if not chips:
        return []

    return [Spacer(1, 4), Paragraph(", ".join(chips), styles["ResumeBody"]), Spacer(1, 4)]


def _experience_layout(section: ResumeSection, styles: StyleSheet1) -> List:
    entries = section.meta.get("entries", [])
    if not entries:
        fallback: List = []
        if section.paragraphs:
            for paragraph in section.paragraphs:
                text = paragraph.strip()
                if not text:
                    continue
                fallback.append(Paragraph(text, styles["ResumeBody"]))
                fallback.append(Spacer(1, 4))
        if section.bullets:
            bullet_items = [
                ListItem(Paragraph(_format_highlighted_text(bullet.strip(), section.meta.get("highlight_terms", [])), styles["ResumeBody"]))
                for bullet in section.bullets
                if bullet.strip()
            ]
            if bullet_items:
                fallback.append(
                    ListFlowable(
                        bullet_items,
                        bulletType="bullet",
                        start="•",
                        leftIndent=12,
                        bulletFontName=_resolve_font(styles["ResumeBody"].fontName),
                        bulletFontSize=styles["ResumeBody"].fontSize,
                    )
                )
                fallback.append(Spacer(1, 6))
        return fallback

    highlight_terms = section.meta.get("highlight_terms", [])

    flowables: List = []
    total_entries = len(entries)
    for index, entry in enumerate(entries):
        role = entry.get("role") or ""
        company = entry.get("company") or ""
        location = entry.get("location") or ""
        date_range = entry.get("date_range") or ""
        bullets = entry.get("bullets", []) or []

        header_parts: List[str] = []
        if role:
            header_parts.append(f"<b>{role}</b>")
        if company:
            header_parts.append(f"@ {company}")
        header_text = " ".join(header_parts)

        meta_segments = [segment for segment in [location, date_range] if segment]
        meta_line = " • ".join(meta_segments)

        entry_flow: List = []
        if header_text:
            entry_flow.append(Paragraph(header_text, styles["ExperienceHeader"]))
            if role and role.strip().lower() == "principal member technical staff":
                entry_flow.append(Spacer(1, 2))
        if meta_line:
            entry_flow.append(Paragraph(meta_line, styles["ExperienceMeta"]))
            entry_flow.append(Spacer(1, 4))
        if bullets:
            bullet_items = []
            for bullet in bullets:
                clean_bullet = bullet.lstrip("• ").strip()
                if not clean_bullet:
                    continue
                formatted_bullet = _format_highlighted_text(clean_bullet, highlight_terms)
                bullet_items.append(ListItem(Paragraph(formatted_bullet, styles["ResumeBody"])))
            if bullet_items:
                entry_flow.append(
                    ListFlowable(
                        bullet_items,
                        bulletType="bullet",
                        start="•",
                        leftIndent=12,
                        bulletFontName=_resolve_font(styles["ResumeBody"].fontName),
                        bulletFontSize=styles["ResumeBody"].fontSize,
                    )
                )
        entry_flow.append(Spacer(1, 6))
        flowables.append(KeepTogether(entry_flow))
        if index < total_entries - 1:
            flowables.append(Spacer(1, 12))
    return flowables


def _build_header(document: ResumeDocument, styles: StyleSheet1) -> KeepTogether | None:
    profile = document.profile
    accent = document.theme.accent_color or "#1a1a1a"
    name = profile.name.strip()
    headline = (profile.headline or "").strip()
    contact_parts = [value for key, value in profile.contact.items() if value]
    if not (name or headline or contact_parts):
        return None

    name_style = ParagraphStyle(
        "HeaderName",
        parent=styles["ResumeName"],
        textColor=colors.HexColor(accent),
        leading=styles["ResumeName"].leading + 2,
        spaceAfter=0,
        fontSize=max(styles["ResumeName"].fontSize - 2, styles["ResumeBody"].fontSize + 1.5),
        alignment=1,
    )
    role_font_size = max(styles["HeaderHeadline"].fontSize - 7, styles["ResumeBody"].fontSize + 0.8)
    headline_style = ParagraphStyle(
        "HeaderHeadlineAccent",
        parent=styles["HeaderHeadline"],
        textColor=colors.HexColor("#2b3a55"),
        fontSize=role_font_size,
        leading=(styles["HeaderHeadline"].leading / styles["HeaderHeadline"].fontSize) * role_font_size,
        spaceAfter=5,
        alignment=1,
    )
    contact_style = ParagraphStyle(
        "HeaderContactAccent",
        parent=styles["ResumeBody"],
        textColor=colors.HexColor("#3f4b63"),
        leading=styles["ResumeBody"].leading,
        spaceBefore=0,
        spaceAfter=6,
        alignment=1,
    )

    flowables: List = []
    if name:
        flowables.append(Paragraph(name, name_style))
    if headline:
        flowables.append(Paragraph(headline, headline_style))
        flowables.append(Spacer(1, 10))
    if contact_parts:
        flowables.append(Paragraph(" | ".join(contact_parts), contact_style))

    flowables.append(Spacer(1, 6))
    flowables.append(HRFlowable(width="100%", thickness=0.8, color=_tint_color(accent, 0.8)))
    flowables.append(Spacer(1, 12))

    return KeepTogether(flowables)


def render_resume(document: ResumeDocument, output_path: str | Path) -> Path:
    """Render the resume document into a PDF."""
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    theme = document.theme
    pagesize = (theme.page_width, theme.page_height) if theme.page_width and theme.page_height else A4
    styles = _build_styles(theme)

    top_margin = min(theme.margin_top, 36)
    bottom_margin = min(theme.margin_bottom, 36)
    left_margin = min(theme.margin_left, 42)
    right_margin = min(theme.margin_right, 42)

    doc = SimpleDocTemplate(
        str(dest),
        pagesize=pagesize,
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
    )

    elements: List = []
    header = _build_header(document, styles)
    if header:
        elements.append(header)

    for section in document.sections:
        elements.extend(_section_elements(section, styles))

    doc.build(elements)
    return dest
