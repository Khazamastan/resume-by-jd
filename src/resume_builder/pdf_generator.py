from __future__ import annotations

from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.platypus import (
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

    styles.add(
        ParagraphStyle(
            "ResumeBody",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=theme.body_size,
            leading=theme.body_size * theme.line_height,
            textColor=colors.HexColor(theme.primary_color),
        )
    )
    styles.add(
        ParagraphStyle(
            "ResumeHeading",
            parent=styles["Heading2"],
            fontName=heading_font,
            fontSize=theme.heading_size,
            leading=theme.heading_size * theme.line_height,
            textColor=colors.HexColor(theme.accent_color),
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
            textColor=colors.HexColor(theme.accent_color),
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
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=theme.body_size,
            leading=theme.body_size * theme.line_height,
            textColor=colors.HexColor(theme.primary_color),
            leftIndent=12,
        )
    )
    return styles


def _section_elements(section: ResumeSection, styles: StyleSheet1) -> List:
    elements: List = []
    if not (section.paragraphs or section.bullets):
        return elements

    elements.append(Paragraph(section.title, styles["ResumeHeading"]))
    if section.paragraphs:
        for paragraph in section.paragraphs:
            elements.append(Paragraph(paragraph, styles["ResumeBody"]))
            elements.append(Spacer(1, 4))
    if section.bullets:
        bullet_font = _resolve_font(styles["ResumeBody"].fontName)
        bullet_items = [
            ListItem(Paragraph(bullet, styles["ResumeBody"]))
            for bullet in section.bullets
        ]
        elements.append(
            ListFlowable(
                bullet_items,
                bulletType="bullet",
                start="•",
                leftIndent=12,
                bulletFontName=bullet_font,
                bulletFontSize=styles["ResumeBody"].fontSize,
            )
        )
        elements.append(Spacer(1, 6))
    return elements


def render_resume(document: ResumeDocument, output_path: str | Path) -> Path:
    """Render the resume document into a PDF."""
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    theme = document.theme
    pagesize = (theme.page_width, theme.page_height) if theme.page_width and theme.page_height else A4
    styles = _build_styles(theme)

    doc = SimpleDocTemplate(
        str(dest),
        pagesize=pagesize,
        leftMargin=theme.margin_left,
        rightMargin=theme.margin_right,
        topMargin=theme.margin_top,
        bottomMargin=theme.margin_bottom,
    )

    elements: List = []
    elements.append(Paragraph(document.profile.name, styles["ResumeName"]))
    if document.profile.headline:
        elements.append(Paragraph(document.profile.headline, styles["ResumeSubheading"]))
    if document.profile.contact:
        contact_line = " | ".join(f"{k.title()}: {v}" for k, v in document.profile.contact.items())
        elements.append(Paragraph(contact_line, styles["ResumeBody"]))
        elements.append(Spacer(1, 8))

    for section in document.sections:
        elements.extend(_section_elements(section, styles))

    doc.build(elements)
    return dest
