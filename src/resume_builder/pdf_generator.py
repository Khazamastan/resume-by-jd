from __future__ import annotations

import re
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir
from typing import Dict, List, Tuple

from PIL import Image, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
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

from .hackajob_renderer import render_hackajob_resume
from .models import ResumeDocument, ResumeSection, Theme

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ICON_DIR = PROJECT_ROOT / "assets" / "icons"
ICON_SIZE_CONTACT = 12
ICON_SIZE_SECTION = 16
ICON_SECTION_TINT_AMOUNT = 0
ICON_CONTACT_TINT_AMOUNT = 00
ICON_ALPHA_SCALE = 0.55
ICON_ALPHA_GAMMA = 1.35
ICON_COLOR_LIGHTEN = -1
ICON_TINT_ENABLED = True
_ICON_TINT_CACHE: Dict[Tuple[str, str], Path] = {}


def _resolve_icon_path(asset_name: str) -> Path | None:
    """Return a bitmap icon path that ReportLab can render (PNG/JPG only)."""
    candidates = [
        ICON_DIR / f"{asset_name}.png",
        ICON_DIR / f"{asset_name}.PNG",
        ICON_DIR / f"{asset_name}.svg",
        ICON_DIR / f"{asset_name}.SVG",
    ]
    allowed_suffixes = {".png", ".jpg", ".jpeg"}
    for candidate in candidates:
        if not candidate.exists():
            continue
        if candidate.suffix.lower() not in allowed_suffixes:
            continue
        return candidate
    return None


@lru_cache(maxsize=64)
def _icon_native_dimensions(path: Path) -> Tuple[int, int]:
    try:
        with Image.open(path) as img:
            width = img.width or 1
            height = img.height or 1
    except Exception:
        width, height = 1, 1
    return width, height


def _tinted_icon_path(asset_name: str, color_hex: str) -> Path | None:
    base_path = _resolve_icon_path(asset_name)
    if not base_path:
        return None
    if not ICON_TINT_ENABLED:
        return base_path
    sanitized = (color_hex or "").strip()
    if not sanitized:
        sanitized = "#000000"
    if not sanitized.startswith("#"):
        sanitized = f"#{sanitized}"
    if len(sanitized) == 4:
        sanitized = "#" + "".join(ch * 2 for ch in sanitized[1:])
    tinted_hex = sanitized
    if ICON_COLOR_LIGHTEN > 0:
        tinted_hex = _mix_hex(sanitized, "#ffffff", ICON_COLOR_LIGHTEN)
    cache_key = (base_path.as_posix(), tinted_hex.lower())
    cached = _ICON_TINT_CACHE.get(cache_key)
    if cached and cached.exists():
        return cached
    dest_dir = Path(gettempdir()) / "resume_by_jd" / "icons"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{base_path.stem}_{tinted_hex.lstrip('#')}.png"
    try:
        with Image.open(base_path).convert("RGBA") as img:
            alpha = img.split()[-1] if img.mode == "RGBA" else None
            r = int(tinted_hex[1:3], 16)
            g = int(tinted_hex[3:5], 16)
            b = int(tinted_hex[5:7], 16)
            color_layer = Image.new("RGBA", img.size, (r, g, b, 255))
            if alpha is None:
                alpha = ImageOps.grayscale(img)
            if ICON_ALPHA_SCALE < 1.0 or ICON_ALPHA_GAMMA != 1.0:
                def _attenuate(value: int) -> int:
                    normalized = max(0.0, min(1.0, value / 255.0))
                    adjusted = normalized ** ICON_ALPHA_GAMMA if ICON_ALPHA_GAMMA != 1.0 else normalized
                    scaled = adjusted * ICON_ALPHA_SCALE
                    return int(max(0.0, min(1.0, scaled)) * 255)

                alpha = alpha.point(_attenuate)
            color_layer.putalpha(alpha)
            color_layer.save(dest_path)
    except Exception:
        return base_path
    _ICON_TINT_CACHE[cache_key] = dest_path
    return dest_path


CONTACT_ICON_CONFIG: Dict[str, Tuple[str, str, bool]] = {
    "phone": ("phone", "", True),
    "email": ("email", "", True),
    "location": ("location", "", True),
    "linkedin": ("linkedin", "LinkedIn", False),
}
SECTION_ICON_CONFIG: Dict[str, Tuple[str, int]] = {
    "summary": ("summary", ICON_SIZE_SECTION),
    "experience": ("experience", ICON_SIZE_SECTION),
    "professional experience": ("experience", ICON_SIZE_SECTION),
    "education": ("education", ICON_SIZE_SECTION),
    "skills": ("skills", ICON_SIZE_SECTION),
    "technical skills": ("skills", ICON_SIZE_SECTION),
    "awards": ("awards", ICON_SIZE_SECTION),
}

BASE_FONTS = {
    "Helvetica",
    "Helvetica-Bold",
    "Helvetica-Oblique",
    "Times-Roman",
    "Times-Bold",
    "Times-Italic",
    "Courier",
    "Courier-Bold",
    "Symbol",
    "ZapfDingbats",
}

BULLET_GLYPH = "\u25A0"
DEFAULT_BRAND_COLOR = colors.Color(17 / 255.0, 85 / 255.0, 204 / 255.0)

_ALLOWED_INLINE_TAGS = {
    "<b>": "\uFFF0B\uFFF1",
    "</b>": "\uFFF0b\uFFF1",
}

_BOLD_MARKDOWN_PATTERN = re.compile(r"(\*\*|__)(.+?)\1", re.DOTALL)
_ITALIC_MARKDOWN_PATTERN = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.DOTALL)
_CODE_MARKDOWN_PATTERN = re.compile(r"`([^`]+)`")
_LINK_MARKDOWN_PATTERN = re.compile(r"\[([^\]]+)]\(([^)]+)\)")


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
        def repl(match: re.Match[str]) -> str:
            start, end = match.span()
            before = match.string[max(0, start - 3) : start].lower()
            after = match.string[end : end + 4].lower()
            if before == "<b>" and after.startswith("</b"):
                return match.group(0)
            return f"<b>{match.group(0)}</b>"

        result = pattern.sub(repl, result)
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
    highlighted = _convert_markdown_to_markup(highlighted)
    return highlighted


def _restore_allowed_tags(text: str) -> str:
    restored = text
    for tag, placeholder in _ALLOWED_INLINE_TAGS.items():
        restored = restored.replace(placeholder, tag)
    return restored


def _escape_preserving_tags(text: str) -> str:
    if not text:
        return ""
    protected = text
    for tag, placeholder in _ALLOWED_INLINE_TAGS.items():
        protected = protected.replace(tag, placeholder)
    escaped = (
        protected.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return _restore_allowed_tags(escaped)


def _wrap_with_tag(content: str, tag: str) -> str:
    open_tag = f"<{tag}>"
    close_tag = f"</{tag}>"
    stripped = content.strip()
    if stripped.startswith(open_tag) and stripped.endswith(close_tag):
        return content
    return f"{open_tag}{content}{close_tag}"


def _sanitize_url(value: str) -> str:
    safe = value.strip()
    if not safe:
        return ""
    return safe.replace('"', "%22").replace("'", "%27")


def _convert_markdown_to_markup(text: str) -> str:
    if not text:
        return ""

    escaped = _escape_preserving_tags(text)

    def bold_repl(match: re.Match[str]) -> str:
        content = match.group(2)
        return _wrap_with_tag(content, "b")

    def italic_repl(match: re.Match[str]) -> str:
        content = match.group(1)
        return _wrap_with_tag(content, "i")

    def code_repl(match: re.Match[str]) -> str:
        content = match.group(1)
        return f"<font face=\"Courier\">{content}</font>"

    def link_repl(match: re.Match[str]) -> str:
        label = match.group(1)
        href = _sanitize_url(match.group(2))
        if not href:
            return label
        return f"<link href=\"{href}\">{label}</link>"

    converted = _BOLD_MARKDOWN_PATTERN.sub(bold_repl, escaped)
    converted = _ITALIC_MARKDOWN_PATTERN.sub(italic_repl, converted)
    converted = _CODE_MARKDOWN_PATTERN.sub(code_repl, converted)
    converted = _LINK_MARKDOWN_PATTERN.sub(link_repl, converted)
    converted = converted.replace("\r\n", "\n").replace("\r", "\n")
    converted = converted.replace("\n", "<br/>")

    return converted


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


def _color_from_hex(value: str | None, fallback: colors.Color | None = None) -> colors.Color:
    if not value:
        return fallback or DEFAULT_BRAND_COLOR
    candidate = value.strip()
    if not candidate:
        return fallback or DEFAULT_BRAND_COLOR
    if not candidate.startswith("#"):
        candidate = f"#{candidate}"
    if len(candidate) not in (4, 7):
        return fallback or DEFAULT_BRAND_COLOR
    r, g, b = _hex_to_rgb(candidate)
    return colors.Color(r, g, b)


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


def _mix_hex(base: str, mix_with: str, amount: float) -> str:
    base_rgb = _hex_to_rgb(base)
    mix_rgb = _hex_to_rgb(mix_with)
    r = min(1.0, max(0.0, base_rgb[0] + (mix_rgb[0] - base_rgb[0]) * amount))
    g = min(1.0, max(0.0, base_rgb[1] + (mix_rgb[1] - base_rgb[1]) * amount))
    b = min(1.0, max(0.0, base_rgb[2] + (mix_rgb[2] - base_rgb[2]) * amount))
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def _resolve_font(font_name: str) -> str:
    """Fall back to core fonts if the reference font is unavailable."""
    if not font_name:
        return "Helvetica"
    if font_name in BASE_FONTS:
        return font_name
    if font_name.endswith("-Bold"):
        return "Helvetica-Bold"
    return "Helvetica"


def _resolve_bold_font(font_name: str) -> str:
    base = _resolve_font(font_name)
    if base.endswith("-Bold"):
        return base
    if base.startswith("Times"):
        return "Times-Bold"
    if base.startswith("Courier"):
        return "Courier-Bold"
    if base.startswith("Helvetica"):
        return "Helvetica-Bold"
    return "Helvetica-Bold"


def _resolve_bold_font(font_name: str) -> str:
    base = _resolve_font(font_name)
    if base.endswith("-Bold"):
        return base
    if base.startswith("Times"):
        return "Times-Bold"
    if base.startswith("Courier"):
        return "Courier-Bold"
    return "Helvetica-Bold"


def _bullet_character() -> str:
    return BULLET_GLYPH


def _bullet_font(styles: StyleSheet1) -> str:
    resume_body_style = styles.get("ResumeBody") if hasattr(styles, "get") else None
    if resume_body_style is None:
        resume_body_style = styles["ResumeBody"]
    font_name = getattr(resume_body_style, "fontName", "Helvetica")
    return _resolve_font(font_name)


def _bullet_font_size(styles: StyleSheet1) -> float:
    resume_body_style = styles.get("ResumeBody") if hasattr(styles, "get") else None
    if resume_body_style is None:
        resume_body_style = styles["ResumeBody"]
    base_size = float(getattr(resume_body_style, "fontSize", 10))
    return round(max(base_size * 1.2, base_size + 1.5), 1)


def _clean_bullet_text(text: str) -> str:
    stripped = text.lstrip("•■-• ").strip()
    return stripped


def _make_bullet_item(paragraph: Paragraph, styles: StyleSheet1) -> ListItem:
    bullet_color = getattr(styles, "_brand_color", DEFAULT_BRAND_COLOR)
    return ListItem(
        paragraph,
        bulletText=_bullet_character(),
        bulletFontName=_bullet_font(styles),
        bulletFontSize=_bullet_font_size(styles),
        bulletColor=bullet_color,
    )


def _listflowable_kwargs(styles: StyleSheet1) -> Dict[str, object]:
    return {
        "bulletType": "bullet",
        "bulletChar": _bullet_character(),
        "bulletFontName": _bullet_font(styles),
        "bulletFontSize": _bullet_font_size(styles),
        "bulletColor": getattr(styles, "_brand_color", DEFAULT_BRAND_COLOR),
    }


def _style_or(styles: StyleSheet1, name: str, fallback: ParagraphStyle) -> ParagraphStyle:
    try:
        return styles[name]
    except KeyError:
        return fallback


def _build_styles(theme: Theme) -> StyleSheet1:
    styles = getSampleStyleSheet()
    body_font = _resolve_font(theme.body_font)
    heading_font = _resolve_font(theme.heading_font)
    accent_hex = (theme.accent_color or theme.primary_color or "#1155cc").strip() or "#1155cc"
    accent_line = _tint_color(accent_hex, 0.7)
    brand_color = _color_from_hex(accent_hex, DEFAULT_BRAND_COLOR)
    styles._brand_color = brand_color
    styles._accent_hex = accent_hex

    styles.add(
        ParagraphStyle(
            "ResumeBody",
            parent=styles["Normal"],
            fontName=body_font,
            fontSize=theme.body_size,
            leading=theme.body_size * theme.line_height,
            textColor=colors.black,
        )
    )
    styles.add(
        ParagraphStyle(
            "ResumeMuted",
            parent=styles["ResumeBody"],
            textColor=colors.black,
        )
    )
    styles.add(
        ParagraphStyle(
            "ResumeHeading",
            parent=styles["Heading2"],
            fontName=heading_font,
            fontSize=theme.heading_size,
            leading=theme.heading_size * theme.line_height,
            textColor=brand_color,
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
            textColor=brand_color,
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
            textColor=colors.black,
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
    bullet_leading = styles["ResumeBody"].leading + theme.body_size * 0.1
    styles.add(
        ParagraphStyle(
            "ResumeBulletText",
            parent=styles["ResumeBody"],
            leading=bullet_leading,
            spaceAfter=theme.body_size * 0.3,
        )
    )
    summary_leading = styles["ResumeBody"].leading + theme.body_size * 0.1
    styles.add(
        ParagraphStyle(
            "SummaryBody",
            parent=styles["ResumeBody"],
            leading=summary_leading,
            spaceAfter=theme.body_size * 0.5,
        )
    )
    styles.add(
        ParagraphStyle(
            "SectionTitle",
            parent=styles["ResumeBody"],
            fontName=heading_font,
            fontSize=theme.body_size + 3,
            textColor=brand_color,
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
            textColor=colors.black,
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
            "ExperienceMetaRight",
            parent=styles["ExperienceMeta"],
            alignment=TA_RIGHT,
        )
    )
    styles.add(
        ParagraphStyle(
            "HeaderHeadline",
            parent=styles["ResumeBody"],
            fontName=heading_font,
            fontSize=theme.heading_size - 2,
            textColor=colors.black,
        )
    )
    styles.add(
        ParagraphStyle(
            "HeaderContact",
            parent=styles["ResumeBody"],
            fontName=body_font,
            fontSize=theme.body_size,
            textColor=colors.black,
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
    styles._section_rule_color = accent_line
    return styles


def _section_elements(section: ResumeSection, styles: StyleSheet1) -> List:
    elements: List = []
    title_lower = (section.title or "").strip().lower()
    must_render_titles = {"professional experience", "education", "awards"}
    is_experience_section = _is_experience_section_title(title_lower)
    if not (section.paragraphs or section.bullets or section.meta):
        if title_lower not in must_render_titles and not is_experience_section:
            return elements

    body_style = _style_or(styles, "ResumeBody", styles["Normal"])
    base_title_style = _style_or(styles, "SectionTitle", body_style)
    body_font_size = getattr(body_style, "fontSize", 10)
    heading_font_size = getattr(base_title_style, "fontSize", body_font_size + 4)
    default_icon_size = max(
        int(round(heading_font_size * 0.55)),
        int(round(body_font_size * 0.85)),
        int(round(ICON_SIZE_SECTION * 0.65)),
    )
    max_icon_size = int(round(max(heading_font_size, body_font_size) * 0.95))
    title_style = base_title_style
    icon_key, size_override = SECTION_ICON_CONFIG.get(title_lower, ("", 0))
    requested_size = size_override or default_icon_size
    icon_size = max(ICON_SIZE_SECTION, min(requested_size, max_icon_size))
    icon_markup = ""
    if icon_key:
        accent_hex = getattr(styles, "_accent_hex", "#1155cc")
        tint_hex = _mix_hex(accent_hex, "#ffffff", ICON_SECTION_TINT_AMOUNT)
        icon_path = _tinted_icon_path(icon_key, tint_hex) or _resolve_icon_path(icon_key)
        if icon_path:
            native_w, native_h = _icon_native_dimensions(icon_path)
            aspect = native_h / max(native_w, 1)
            scaled_height = max(1, int(round(icon_size * aspect)))
            icon_markup = (
                f'<img src="{icon_path.as_posix()}" width="{icon_size}" height="{scaled_height}" valign="middle"/>&#160;'
            )
    if is_experience_section:
        base_title_style = styles["SectionTitle"]
        title_style = ParagraphStyle(
            "SectionTitleExperience",
            parent=base_title_style,
            spaceBefore=max(getattr(base_title_style, "spaceBefore", 0) * 0.75, 0),
            spaceAfter=getattr(base_title_style, "spaceAfter", 0),
        )
    title_text = (section.title or "").strip()
    title_markup = f"{icon_markup}<b>{_escape_preserving_tags(title_text)}</b>" if title_text else ""
    elements.append(Paragraph(title_markup, title_style))
    rule_color = getattr(styles, "_section_rule_color", getattr(styles["SectionRule"], "textColor", colors.HexColor("#b5c4d6")))
    elements.append(HRFlowable(width="100%", thickness=0.6, color=rule_color))
    spacer_height = 6 if is_experience_section else 4
    elements.append(Spacer(1, spacer_height))
    if title_lower in {"skills", "technical skills"}:
        elements.extend(_skills_layout(section, styles))
        return elements

    if is_experience_section:
        elements.extend(_experience_layout(section, styles))
        return elements

    resume_body = styles["ResumeBody"]
    highlight_terms = section.meta.get("highlight_terms", [])
    is_awards = title_lower == "awards"

    summary_style = _style_or(styles, "SummaryBody", resume_body) if title_lower == "summary" else resume_body
    spacer_height_default = 5 if title_lower == "summary" else 4
    bullet_paragraph_style = _style_or(styles, "ResumeBulletText", resume_body)
    if section.paragraphs:
        for paragraph in section.paragraphs:
            text = paragraph.strip()
            if not text:
                continue
            if text.startswith(("■", "•", "-")):
                bullet_text = _format_highlighted_text(_clean_bullet_text(text), highlight_terms)
                bullet_item = _make_bullet_item(Paragraph(bullet_text, bullet_paragraph_style), styles)
                elements.append(
                    ListFlowable(
                        [bullet_item],
                        leftIndent=12,
                        spaceBefore=0,
                        spaceAfter=0,
                        **_listflowable_kwargs(styles),
                    )
                )
            else:
                if is_awards:
                    text = _format_highlighted_text(text, highlight_terms)
                elements.append(Paragraph(text, summary_style))
            elements.append(Spacer(1, spacer_height_default))

    if section.bullets and title_lower not in {"skills", "technical skills"}:
        bullet_items = [
            _make_bullet_item(
                Paragraph(
                    _format_highlighted_text(_clean_bullet_text(bullet), highlight_terms),
                    bullet_paragraph_style,
                ),
                styles,
            )
            for bullet in section.bullets
            if _clean_bullet_text(bullet)
        ]
        if bullet_items:
            elements.append(
                ListFlowable(
                    bullet_items,
                    leftIndent=12,
                    spaceBefore=0,
                    spaceAfter=0,
                    **_listflowable_kwargs(styles),
                )
            )
            elements.append(Spacer(1, spacer_height_default + 1))
    if title_lower not in {"skills", "technical skills"} and not is_experience_section and elements:
        elements.append(Spacer(1, 6))
    return elements


def _is_experience_section_title(title: str) -> bool:
    normalized = (title or "").strip().lower()
    if not normalized:
        return False
    base = re.sub(r"\s*\([^)]*\)\s*$", "", normalized).strip()
    if base in {"experience", "professional experience", "work experience", "employment history"}:
        return True
    return base.startswith("professional experience")


def _skills_layout(section: ResumeSection, styles: StyleSheet1) -> List:
    category_lines = section.meta.get("category_lines")
    resume_body = styles["ResumeBody"]
    skills_style = _style_or(styles, "SkillsBody", resume_body)
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
            flowables.append(Paragraph(line, skills_style))
            flowables.append(Spacer(1, 4))
        flowables.append(Spacer(1, 4))
        return flowables

    grouped = section.meta.get("grouped_skills")
    if grouped:
        flowables = [Spacer(1, 4)]
        for category, items in grouped.items():
            if not items:
                continue
            line = f"<b>{category}:</b> {', '.join(items)}"
            flowables.append(Paragraph(line, skills_style))
            flowables.append(Spacer(1, 4))
        flowables.append(Spacer(1, 4))
        return flowables

    chips = [skill.strip() for skill in section.bullets if skill.strip()]
    if not chips:
        return []

    return [Spacer(1, 4), Paragraph(", ".join(chips), skills_style), Spacer(1, 4)]


def _experience_layout(section: ResumeSection, styles: StyleSheet1) -> List:
    resume_body = styles["ResumeBody"]
    bullet_style = _style_or(styles, "ResumeBulletText", resume_body)
    entries = section.meta.get("entries", [])
    if not entries:
        fallback: List = []
        if section.paragraphs:
            for paragraph in section.paragraphs:
                text = paragraph.strip()
                if not text:
                    continue
                fallback.append(Paragraph(text, resume_body))
                fallback.append(Spacer(1, 4))
        if section.bullets:
            bullet_items = [
                _make_bullet_item(
                    Paragraph(
                        _format_highlighted_text(_clean_bullet_text(bullet), section.meta.get("highlight_terms", [])),
                        bullet_style,
                    ),
                    styles,
                )
                for bullet in section.bullets
                if _clean_bullet_text(bullet)
            ]
            if bullet_items:
                fallback.append(
                    ListFlowable(
                        bullet_items,
                        leftIndent=12,
                        spaceBefore=0,
                        spaceAfter=0,
                        **_listflowable_kwargs(styles),
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
            header_parts.append(f"<b>{_escape_preserving_tags(role)}</b>")
        if company:
            if role:
                header_parts.append(f"at {_escape_preserving_tags(company)}")
            else:
                header_parts.append(_escape_preserving_tags(company))

        meta_segments: List[str] = []
        if location:
            meta_segments.append(_escape_preserving_tags(location))
        if date_range:
            meta_segments.append(_escape_preserving_tags(date_range))

        header_text = " ".join(header_parts)
        meta_text = " | ".join(meta_segments)
        header_line = ""
        if header_text and meta_text:
            header_line = f"{header_text} | {meta_text}"
        elif header_text:
            header_line = header_text
        elif meta_text:
            header_line = meta_text

        header_flow: List = []
        if header_line:
            header_flow.append(Paragraph(header_line, styles["ExperienceHeader"]))
            if role and role.strip().lower() == "Principal Member Technical Staff":
                header_flow.append(Spacer(1, 2))
            header_flow.append(Spacer(1, 3))
        if bullets:
            bullet_items = []
            for bullet in bullets:
                clean_bullet = _clean_bullet_text(bullet)
                if not clean_bullet:
                    continue
                formatted_bullet = _format_highlighted_text(clean_bullet, highlight_terms)
                bullet_items.append(
                    _make_bullet_item(
                        Paragraph(formatted_bullet, bullet_style),
                        styles,
                    )
                )
        else:
            bullet_items = []

        bullet_flowables: List = []
        if bullet_items:
            bullet_flowables.append(
                ListFlowable(
                    bullet_items,
                    leftIndent=12,
                    spaceBefore=0,
                    spaceAfter=0,
                    **_listflowable_kwargs(styles),
                )
            )

        entry_spacing = Spacer(1, 6 if bullet_flowables else 3)
        combined_flow = header_flow + bullet_flowables + [entry_spacing]
        should_keep_together = bool(bullet_flowables) and len(bullet_items) <= 3

        if should_keep_together:
            flowables.append(KeepTogether(combined_flow))
        else:
            if header_flow:
                flowables.append(KeepTogether(header_flow))
            if bullet_flowables:
                flowables.extend(bullet_flowables)
            flowables.append(entry_spacing)

        if index < total_entries - 1:
            flowables.append(Spacer(1, 8))
    return flowables


def _build_header(document: ResumeDocument, styles: StyleSheet1) -> KeepTogether | None:
    profile = document.profile
    accent_hex = getattr(styles, "_accent_hex", document.theme.accent_color or document.theme.primary_color or "#1a1a1a")
    accent = accent_hex if accent_hex.startswith("#") else f"#{accent_hex}"
    name = profile.name.strip()
    headline = (profile.headline or "").strip()
    resume_body_style = _style_or(styles, "ResumeBody", styles["Normal"])
    body_font_size = getattr(resume_body_style, "fontSize", document.theme.body_size)
    base_contact_icon_size = max(
        int(round(body_font_size * 1.3)),
        int(round(ICON_SIZE_CONTACT * 0.8))
    )
    contact_icon_size = min(base_contact_icon_size, int(round(body_font_size * 1.8)))
    contact_parts: List[str] = []
    for key, value in profile.contact.items():
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned:
            continue
        lowered = key.lower()
        icon_markup = ""
        config = CONTACT_ICON_CONFIG.get(lowered)
        if config:
            icon_key, label_text, include_label = config
            accent_hex = getattr(styles, "_accent_hex", "#1155cc")
            normalized_accent = accent_hex if str(accent_hex).startswith("#") else f"#{accent_hex}"
            tinted_accent = _mix_hex(normalized_accent, "#ffffff", ICON_CONTACT_TINT_AMOUNT)
            icon_path = _tinted_icon_path(icon_key, tinted_accent) or _resolve_icon_path(icon_key)
            if icon_path:
                native_w, native_h = _icon_native_dimensions(icon_path)
                icon_width = contact_icon_size
                if lowered in {"phone", "location"}:
                    icon_width = max(10, int(round(contact_icon_size * 0.85)))
                aspect = native_h / max(native_w, 1)
                scaled_height = max(1, int(round(icon_width * aspect)))
                icon_markup = (
                    f'<img src="{icon_path.as_posix()}" width="{icon_width}" height="{scaled_height}" valign="middle"/>'
                )
        else:
            label_text = key.title()
            include_label = True
        escaped_value = _escape_preserving_tags(cleaned)
        if lowered == "linkedin":
            value_markup = "LinkedIn"
        else:
            value_markup = escaped_value
        if icon_markup:
            entry_text = f"{icon_markup}&#160;"
        else:
            entry_text = ""
        label = label_text
        if include_label and label:
            entry_text += f"{label}: {value_markup}"
        else:
            entry_text += value_markup
        contact_parts.append(entry_text)
    if not (name or headline or contact_parts):
        return None

    heading_font_raw = document.theme.heading_font or ""
    heading_font = _resolve_font(heading_font_raw)

    def _regularize_font(font_name: str) -> str:
        if not font_name:
            return "Helvetica"
        if font_name.endswith("-Bold"):
            candidate = font_name[: -len("-Bold")]
            if candidate.lower() == "times":
                return "Times-Roman"
            resolved = _resolve_font(candidate)
            if resolved != font_name:
                return resolved
        if font_name.endswith("Bold"):
            candidate = font_name.replace("Bold", "")
            resolved = _resolve_font(candidate)
            if resolved != font_name:
                return resolved
        normalized = _resolve_font(font_name)
        if normalized.startswith("Times") and not normalized.endswith("-Roman"):
            return "Times-Roman"
        return normalized
    name_font_family = _regularize_font(heading_font_raw)
    name_font = _resolve_bold_font(name_font_family)
    brand_color = getattr(styles, "_brand_color", DEFAULT_BRAND_COLOR)

    name_style = ParagraphStyle(
        "HeaderName",
        parent=styles["ResumeName"],
        textColor=brand_color,
        fontName=name_font,
        leading=styles["ResumeName"].leading + 2,
        spaceAfter=0,
        fontSize=max(styles["ResumeName"].fontSize - 4, styles["ResumeBody"].fontSize + 1),
        alignment=1,
    )
    base_headline_font = styles["ResumeBody"].fontSize
    role_font_size = max(base_headline_font - 0.5, 8)
    headline_style = ParagraphStyle(
        "HeaderHeadlineAccent",
        parent=styles["HeaderHeadline"],
        textColor=colors.black,
        fontSize=role_font_size,
        leading=(styles["HeaderHeadline"].leading / styles["HeaderHeadline"].fontSize) * role_font_size,
        spaceAfter=5,
        alignment=1,
    )
    contact_style = ParagraphStyle(
        "HeaderContactAccent",
        parent=styles["ResumeBody"],
        textColor=colors.black,
        leading=styles["ResumeBody"].leading,
        spaceBefore=0,
        spaceAfter=6,
        alignment=1,
    )

    flowables: List = []
    if name:
        flowables.append(Paragraph(_escape_preserving_tags(name), name_style))
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
    if (document.theme.template or "").lower() == "hackajob":
        return render_hackajob_resume(document, output_path)

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

    rendered_experience = False
    for section in document.sections:
        title_lower = (section.title or "").strip().lower()
        if _is_experience_section_title(title_lower):
            if rendered_experience:
                continue
            rendered_experience = True
        elements.extend(_section_elements(section, styles))

    doc.build(elements)
    return dest
