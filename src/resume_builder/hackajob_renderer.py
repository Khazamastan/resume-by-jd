from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from dateutil import parser as date_parser
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from .models import ResumeDocument, ResumeSection

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = PROJECT_ROOT / "assets" / "hackajob"
LOGO_DIR = ASSET_DIR / "logos"
FONT_DIR = ASSET_DIR / "fonts"
ICON_DIR = PROJECT_ROOT / "assets" / "icons"
SPACE_GROTESK_COMPLETE_DIR = PROJECT_ROOT / "SpaceGrotesk_Complete" / "Fonts"

DEFAULT_ACCENT_HEX = "#74dcc0"
PAGE_BG_HEX = "#ffffff"
CARD_BG_HEX = "#ffffff"
CARD_BORDER_HEX = "#f2f2f2"
TEXT_COLOR_HEX = "#4b4b4b"
TEXT_DARK_HEX = "#2f2f2f"
TEXT_MUTED_HEX = "#666666"
ICON_BORDER_HEX = "#e8e8e8"
_HEX_COLOR_PATTERN = re.compile(r"^#?(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")

OUTER_MARGIN = 17
TOP_MARGIN = 14
BOTTOM_MARGIN = 8
CARD_GAP = 18
CARD_RADIUS = 8
CARD_PAD_X = 12
CARD_PAD_TOP = 10
CARD_PAD_BOTTOM = 10
CARD_BORDER_WIDTH = 0.75
DIVIDER_LINE_WIDTH = 0.65

HACKAJOB_MEDIUM = "HackajobSpaceGroteskMedium"
HACKAJOB_BOLD = "HackajobSpaceGroteskBold"
HACKAJOB_BULLET = "HackajobUnicodeBullet"
EXPERIENCE_BULLET_CHAR = "-"
EXPERIENCE_BULLET_X_OFFSET = 44
METRIC_TOKEN_PATTERN = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?(?:\s?(?:%|percent|x|k|m|b|ms|s|mins?|hours?|days?|months?|years?))?\b",
    re.IGNORECASE,
)
FORCED_BULLET_HIGHLIGHTS: Tuple[str, ...] = (
    "MAUI",
    "MFA",
    "OCI",
    "OCI DevOps SCM",
    "One My Profile",
    "Objectives",
    "Incent",
    "Module Federation",
    "ML-driven",
    "SVG",
    "iStyle",
    "Fabric.js",
    "Canvas",
    "Angular",
)

MEDIUM_FONT_CANDIDATES = [
    SPACE_GROTESK_COMPLETE_DIR / "WEB" / "fonts" / "SpaceGrotesk-Medium.ttf",
    SPACE_GROTESK_COMPLETE_DIR / "OTF" / "SpaceGrotesk-Medium.otf",
    SPACE_GROTESK_COMPLETE_DIR / "WEB" / "fonts" / "SpaceGrotesk-Regular.ttf",
    FONT_DIR / "spacegrotesk-medium.ttf",
    FONT_DIR / "spacegrotesk-medium-subset.ttf",
]

BOLD_FONT_CANDIDATES = [
    SPACE_GROTESK_COMPLETE_DIR / "WEB" / "fonts" / "SpaceGrotesk-Bold.ttf",
    SPACE_GROTESK_COMPLETE_DIR / "OTF" / "SpaceGrotesk-Bold.otf",
    SPACE_GROTESK_COMPLETE_DIR / "WEB" / "fonts" / "SpaceGrotesk-SemiBold.ttf",
    FONT_DIR / "spacegrotesk-bold.ttf",
    FONT_DIR / "spacegrotesk-bold-subset.ttf",
]

BULLET_FONT_CANDIDATES = [
    FONT_DIR / "NotoSans-Regular.ttf",
    Path("/System/Library/Fonts/Supplemental/NotoSans-Regular.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
]


@dataclass
class _ExperienceEntry:
    company: str
    role: str
    location: str
    date_range: str
    chips: List[str]
    bullets: List[str]
    start_date: str = ""
    end_date: str = ""
    start_date_iso: str = ""
    end_date_iso: str = ""


@dataclass
class _EducationEntry:
    institution: str
    degree: str
    location_year: str


@dataclass
class _Segment:
    kind: str
    height: float
    payload: Dict[str, object]


@dataclass(frozen=True)
class _HackajobPalette:
    page_bg: colors.Color
    card_bg: colors.Color
    card_border: colors.Color
    header_gradient_left_top: colors.Color
    header_gradient_right_top: colors.Color
    header_gradient_left_bottom: colors.Color
    header_gradient_right_bottom: colors.Color
    text_color: colors.Color
    text_dark: colors.Color
    text_muted: colors.Color
    icon_border: colors.Color
    avatar_ring: colors.Color


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_hex_color(value: str | None, fallback: str = DEFAULT_ACCENT_HEX) -> str:
    candidate = (value or "").strip()
    if not candidate or not _HEX_COLOR_PATTERN.fullmatch(candidate):
        candidate = fallback
    if not candidate.startswith("#"):
        candidate = f"#{candidate}"
    if len(candidate) == 4:
        candidate = "#" + "".join(ch * 2 for ch in candidate[1:])
    return candidate.lower()


def _hex_to_rgb(hex_value: str) -> Tuple[float, float, float]:
    normalized = _normalize_hex_color(hex_value).lstrip("#")
    red = int(normalized[0:2], 16) / 255.0
    green = int(normalized[2:4], 16) / 255.0
    blue = int(normalized[4:6], 16) / 255.0
    return red, green, blue


def _mix_hex(base: str, mix_with: str, amount: float) -> str:
    ratio = max(0.0, min(1.0, amount))
    base_r, base_g, base_b = _hex_to_rgb(base)
    mix_r, mix_g, mix_b = _hex_to_rgb(mix_with)
    red = base_r + (mix_r - base_r) * ratio
    green = base_g + (mix_g - base_g) * ratio
    blue = base_b + (mix_b - base_b) * ratio
    return "#{:02x}{:02x}{:02x}".format(int(red * 255), int(green * 255), int(blue * 255))


def _build_palette(accent_color: str | None, primary_color: str | None) -> _HackajobPalette:
    accent_hex = _normalize_hex_color(accent_color or primary_color, DEFAULT_ACCENT_HEX)
    return _HackajobPalette(
        page_bg=colors.HexColor(PAGE_BG_HEX),
        card_bg=colors.HexColor(CARD_BG_HEX),
        card_border=colors.HexColor(CARD_BORDER_HEX),
        header_gradient_left_top=colors.HexColor(_mix_hex(accent_hex, "#ffffff", 0.72)),
        header_gradient_right_top=colors.HexColor(_mix_hex(accent_hex, "#ffffff", 0.94)),
        header_gradient_left_bottom=colors.HexColor(_mix_hex(accent_hex, "#ffffff", 0.77)),
        header_gradient_right_bottom=colors.HexColor(_mix_hex(accent_hex, "#ffffff", 0.97)),
        text_color=colors.HexColor(TEXT_COLOR_HEX),
        text_dark=colors.HexColor(TEXT_DARK_HEX),
        text_muted=colors.HexColor(TEXT_MUTED_HEX),
        icon_border=colors.HexColor(_mix_hex(ICON_BORDER_HEX, accent_hex, 0.22)),
        avatar_ring=colors.HexColor(_mix_hex(accent_hex, "#ffffff", 0.10)),
    )


def _register_fonts() -> Tuple[str, str]:
    medium_path = next((path for path in MEDIUM_FONT_CANDIDATES if path.exists()), None)
    bold_path = next((path for path in BOLD_FONT_CANDIDATES if path.exists()), None)
    try:
        if medium_path and HACKAJOB_MEDIUM not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(HACKAJOB_MEDIUM, str(medium_path)))
    except Exception:
        pass
    try:
        if bold_path and HACKAJOB_BOLD not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(HACKAJOB_BOLD, str(bold_path)))
    except Exception:
        pass

    medium_name = HACKAJOB_MEDIUM if HACKAJOB_MEDIUM in pdfmetrics.getRegisteredFontNames() else "Helvetica"
    bold_name = HACKAJOB_BOLD if HACKAJOB_BOLD in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
    return medium_name, bold_name


def _register_bullet_font(fallback: str) -> str:
    bullet_path = next((path for path in BULLET_FONT_CANDIDATES if path.exists()), None)
    try:
        if bullet_path and HACKAJOB_BULLET not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(HACKAJOB_BULLET, str(bullet_path)))
    except Exception:
        pass
    if HACKAJOB_BULLET in pdfmetrics.getRegisteredFontNames():
        return HACKAJOB_BULLET
    return fallback


def _section_by_title(sections: Sequence[ResumeSection], keyword: str) -> ResumeSection | None:
    lower = keyword.lower()
    for section in sections:
        if lower in (section.title or "").lower():
            return section
    return None


def _escape_paragraph_text(text: str) -> str:
    escaped = html.escape(text or "", quote=False)
    return escaped.replace("\n", "<br/>")


def _measure_paragraph(text: str, style: ParagraphStyle, width: float) -> Tuple[Paragraph, float]:
    paragraph = Paragraph(_escape_paragraph_text(text), style)
    _, height = paragraph.wrap(width, 10000)
    return paragraph, float(height)


def _normalize_company_key(company: str) -> str:
    lowered = _clean_text(company).lower()
    if "oracle" in lowered:
        return "oracle"
    if "xactly" in lowered:
        return "xactly"
    if "nineleap" in lowered:
        return "nineleaps"
    if "pwc" in lowered:
        return "pwc"
    if "minewhat" in lowered:
        return "minewhat"
    if "thrymr" in lowered:
        return "thrymr"
    return "generic"


def _display_company_name(company: str) -> str:
    key = _normalize_company_key(company)
    if key == "pwc":
        return "PwC"
    if key == "nineleaps":
        return "Nineleaps Technology"
    return _clean_text(company)


def _company_logo_path(company: str) -> Path:
    key = _normalize_company_key(company)
    if key == "generic":
        return Path()
    return LOGO_DIR / f"{key}.png"


def _company_logo_variant(company: str) -> str:
    key = _normalize_company_key(company)
    if key == "generic":
        return "briefcase_badge"
    if key in {"oracle", "minewhat"}:
        return "rounded_square"
    return "transparent_mark"


def _logo_size_for_company(company: str, base_size: float, context: str) -> float:
    size = float(base_size)
    return max(8.0, size)


def _logo_content_scale(company: str, context: str) -> float:
    return 1.0


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    if cleaned.lower() in {"present", "current"}:
        return date.today()
    try:
        return date_parser.parse(cleaned, default=datetime.today()).date()
    except (ValueError, TypeError):
        return None


def _month_year(value: date | None) -> str:
    if value is None:
        return ""
    return value.strftime("%b %Y")


def _format_duration(start: date | None, end: date | None, end_label: str) -> str:
    if not start or not end:
        return ""
    months = max(0, (end.year - start.year) * 12 + (end.month - start.month))
    years, rem = divmod(months, 12)
    if years and rem:
        return f"{years} yr {rem} mo{'s' if rem != 1 else ''}"
    if years:
        return f"{years} year{'s' if years != 1 else ''}"
    if rem:
        return f"{rem} month{'s' if rem != 1 else ''}"
    if end_label in {"Current", "Present"}:
        return "1 month"
    return ""


def _format_hackajob_date_parts(start: str | None, end: str | None) -> Tuple[str, str, str]:
    start_date = _parse_date(start)
    end_is_current = _clean_text(end).lower() in {"present", "current", ""}
    end_date = _parse_date(end if end and not end_is_current else "current")
    start_text = _month_year(start_date)
    end_text = "Present" if end_is_current else _month_year(end_date)
    if start_text and end_text:
        base = f"{start_text} - {end_text}"
    else:
        base = start_text or end_text
    duration = _format_duration(start_date, end_date, end_text)
    if duration and base:
        return start_text, end_text, f"{base} ({duration})"
    return start_text, end_text, base


def _format_hackajob_date_range(start: str | None, end: str | None) -> str:
    _, _, date_range = _format_hackajob_date_parts(start, end)
    return date_range


def _split_date_range_text(date_range: str) -> Tuple[str, str]:
    cleaned = _clean_text(date_range)
    if not cleaned:
        return "", ""
    base = cleaned.split("(", 1)[0].strip()
    if " - " in base:
        start_text, end_text = base.split(" - ", 1)
        return _clean_text(start_text), _clean_text(end_text)
    return cleaned, ""


def _flatten_skills(section: ResumeSection | None, fallback: Iterable[str]) -> List[str]:
    skills: List[str] = []
    seen: set[str] = set()

    def add(skill: str) -> None:
        cleaned = _clean_text(skill)
        if not cleaned:
            return
        key = cleaned.lower()
        if key in seen:
            return
        seen.add(key)
        skills.append(cleaned)

    if section:
        category_lines = section.meta.get("category_lines") or []
        for line in category_lines:
            if isinstance(line, (list, tuple)) and len(line) == 2:
                _, items = line
                for item in items or []:
                    add(str(item))
        for bullet in section.bullets:
            add(bullet)
    for item in fallback:
        add(str(item))
    return skills


def _skills_from_text(text: str, ordered_skills: Sequence[str], limit: int = 6) -> List[str]:
    haystack = _clean_text(text).lower()
    found: List[str] = []
    seen: set[str] = set()
    for skill in ordered_skills:
        key = skill.lower()
        if key in seen:
            continue
        if key and key in haystack:
            found.append(skill)
            seen.add(key)
            if len(found) >= limit:
                return found
    return found


def _derive_entry_chips(entry: Dict[str, object], skill_pool: Sequence[str]) -> List[str]:
    text_parts = [entry.get("company"), entry.get("role")]
    text_parts.extend(entry.get("bullets", []) or [])
    combined = " ".join(_clean_text(part) for part in text_parts if part)
    matched = _skills_from_text(combined, skill_pool, limit=6)
    if matched:
        return matched
    return list(skill_pool[:3])


def _experience_entries(document: ResumeDocument, skill_pool: Sequence[str]) -> List[_ExperienceEntry]:
    entries: List[_ExperienceEntry] = []
    for item in document.profile.experience:
        company = _display_company_name(_clean_text(item.get("company")))
        role = _clean_text(item.get("role") or item.get("title"))
        location = _clean_text(item.get("location"))
        start_text, end_text, date_range = _format_hackajob_date_parts(item.get("start"), item.get("end"))
        start_dt = _parse_date(item.get("start"))
        end_raw = _clean_text(item.get("end"))
        end_dt = _parse_date(item.get("end")) if end_raw and end_raw.lower() not in {"present", "current"} else None
        start_iso = start_dt.strftime("%Y-%m-%d") if start_dt else ""
        end_iso = "Present" if end_raw.lower() in {"present", "current", ""} else (end_dt.strftime("%Y-%m-%d") if end_dt else "")
        bullets = [_clean_text(b) for b in item.get("bullets", []) or [] if _clean_text(b)]
        chips = _derive_entry_chips(item, skill_pool)
        entries.append(
            _ExperienceEntry(
                company=company,
                role=role,
                location=location,
                date_range=date_range,
                chips=chips,
                bullets=bullets,
                start_date=start_text,
                end_date=end_text,
                start_date_iso=start_iso,
                end_date_iso=end_iso,
            )
        )

    if entries:
        return entries

    experience_section = _section_by_title(document.sections, "experience")
    if experience_section:
        meta_entries = experience_section.meta.get("entries", []) or []
        for item in meta_entries:
            if not isinstance(item, dict):
                continue
            if item.get("start") or item.get("end"):
                start_text, end_text, date_range = _format_hackajob_date_parts(item.get("start"), item.get("end"))
            else:
                date_range = _clean_text(item.get("date_range"))
                start_text, end_text = _split_date_range_text(date_range)
            start_dt = _parse_date(item.get("start"))
            end_raw = _clean_text(item.get("end"))
            end_dt = _parse_date(item.get("end")) if end_raw and end_raw.lower() not in {"present", "current"} else None
            start_iso = start_dt.strftime("%Y-%m-%d") if start_dt else ""
            end_iso = "Present" if end_raw.lower() in {"present", "current", ""} else (end_dt.strftime("%Y-%m-%d") if end_dt else "")
            entries.append(
                _ExperienceEntry(
                    company=_display_company_name(_clean_text(item.get("company"))),
                    role=_clean_text(item.get("role")),
                    location=_clean_text(item.get("location")),
                    date_range=date_range,
                    chips=_derive_entry_chips(item, skill_pool),
                    bullets=[_clean_text(b) for b in item.get("bullets", []) or [] if _clean_text(b)],
                    start_date=start_text,
                    end_date=end_text,
                    start_date_iso=start_iso,
                    end_date_iso=end_iso,
                )
            )
    return entries


def _education_entries(document: ResumeDocument) -> List[_EducationEntry]:
    records: List[_EducationEntry] = []
    for item in document.profile.education:
        institution = _clean_text(item.get("institution") or item.get("school"))
        degree = _clean_text(item.get("degree"))
        location = _clean_text(item.get("location"))
        end_value = _parse_date(item.get("end"))
        year_text = str(end_value.year) if end_value else _clean_text(item.get("end"))
        location_year = ", ".join(part for part in [location, year_text] if part)
        records.append(_EducationEntry(institution=institution, degree=degree, location_year=location_year))
    if records:
        return records

    education_section = _section_by_title(document.sections, "education")
    if education_section:
        paragraphs = [line for line in education_section.paragraphs if _clean_text(line)]
        if paragraphs:
            institution = _clean_text(paragraphs[0])
            degree = _clean_text(paragraphs[1]) if len(paragraphs) > 1 else ""
            location_year = _clean_text(paragraphs[2]) if len(paragraphs) > 2 else ""
            records.append(_EducationEntry(institution=institution, degree=degree, location_year=location_year))
    return records


def _awards_bullets(document: ResumeDocument) -> List[str]:
    bullets: List[str] = []
    seen: set[str] = set()

    def add(value: object) -> None:
        text = _clean_text(value)
        if not text:
            return
        key = text.lower()
        if key in seen:
            return
        seen.add(key)
        bullets.append(text)

    for section in document.profile.additional_sections:
        if "award" not in _clean_text(section.title).lower():
            continue
        for line in section.bullets:
            add(line)
        for line in section.paragraphs:
            add(line)

    if bullets:
        return bullets

    awards_section = _section_by_title(document.sections, "award")
    if awards_section:
        for line in awards_section.bullets:
            add(line)
        for line in awards_section.paragraphs:
            add(line)
    return bullets


def _about_title(document: ResumeDocument) -> str:
    _ = document
    return "Professional Summary"


def _about_paragraphs(document: ResumeDocument) -> List[str]:
    summary_section = _section_by_title(document.sections, "summary")
    if summary_section and summary_section.paragraphs:
        return [_clean_text(paragraph) for paragraph in summary_section.paragraphs if _clean_text(paragraph)]
    if document.profile.summary:
        return [_clean_text(paragraph) for paragraph in document.profile.summary if _clean_text(paragraph)]
    return []


def _headline_text(document: ResumeDocument) -> str:
    headline = _clean_text(document.profile.headline)
    if " at " in headline.lower():
        return headline
    if document.profile.experience:
        first_company = _clean_text(document.profile.experience[0].get("company"))
        if headline and first_company:
            return f"{headline} at {first_company}"
    return headline


def _header_contact_items(document: ResumeDocument) -> List[Tuple[str, str, str]]:
    contact = document.profile.contact or {}
    items: List[Tuple[str, str, str]] = []
    phone = _clean_text(contact.get("phone"))
    email = _clean_text(contact.get("email"))
    location = _clean_text(contact.get("location"))
    linkedin = _clean_text(contact.get("linkedin"))
    if phone:
        items.append(("phone", phone, ""))
    if email:
        items.append(("email", email, ""))
    if location:
        items.append(("location", location, ""))
    if linkedin:
        items.append(("linkedin", "LinkedIn", ""))
    return items


def _skill_category_lines(section: ResumeSection | None, fallback: Iterable[str]) -> List[Tuple[str, List[str]]]:
    category_lines: List[Tuple[str, List[str]]] = []
    if section:
        raw_lines = section.meta.get("category_lines") or []
        for line in raw_lines:
            if not isinstance(line, (list, tuple)) or len(line) != 2:
                continue
            category = _clean_text(line[0])
            items_raw = line[1] if isinstance(line[1], (list, tuple)) else []
            items = [_clean_text(item) for item in items_raw if _clean_text(item)]
            if category and items:
                category_lines.append((category, items))
    if category_lines:
        return category_lines

    fallback_skills = [_clean_text(item) for item in fallback if _clean_text(item)]
    if fallback_skills:
        return [("Additional Skills", fallback_skills)]
    return []


def _merge_spans(spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not spans:
        return []
    ordered = sorted(spans, key=lambda item: (item[0], item[1]))
    merged: List[List[int]] = []
    for start, end in ordered:
        if start >= end:
            continue
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def _normalized_highlight_terms(terms: Sequence[str]) -> List[str]:
    cleaned: List[str] = []
    seen: set[str] = set()
    for term in terms:
        candidate = _clean_text(term)
        if len(candidate) < 2:
            continue
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(candidate)
    cleaned.sort(key=len, reverse=True)
    return cleaned


def _highlight_bullet_markup(text: str, highlight_terms: Sequence[str], bold_font: str) -> str:
    raw = _clean_text(text)
    if not raw:
        return ""

    spans: List[Tuple[int, int]] = []
    for match in METRIC_TOKEN_PATTERN.finditer(raw):
        spans.append((match.start(), match.end()))

    for term in _normalized_highlight_terms(highlight_terms):
        pattern = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(raw):
            spans.append((match.start(), match.end()))

    merged = _merge_spans(spans)
    if not merged:
        return html.escape(raw, quote=False)

    parts: List[str] = []
    cursor = 0
    for start, end in merged:
        if start > cursor:
            parts.append(html.escape(raw[cursor:start], quote=False))
        highlighted = html.escape(raw[start:end], quote=False)
        parts.append(f'<font face="{bold_font}">{highlighted}</font>')
        cursor = end
    if cursor < len(raw):
        parts.append(html.escape(raw[cursor:], quote=False))
    return "".join(parts)


def _ats_contact_line(document: ResumeDocument) -> str:
    contact = document.profile.contact or {}
    values = [
        _clean_text(contact.get("phone")),
        _clean_text(contact.get("email")),
        _clean_text(contact.get("location")),
    ]
    linkedin = _clean_text(contact.get("linkedin"))
    if linkedin:
        values.append(linkedin)
    parts = [value for value in values if value]
    return " | ".join(parts)


def _contact_value(contact: Dict[str, object], keys: Sequence[str]) -> str:
    for key in keys:
        value = _clean_text(contact.get(key))
        if value:
            return value
    return ""


def _location_components(location: str) -> Tuple[str, str, str, str, str]:
    cleaned = _clean_text(location)
    if not cleaned:
        return "", "", "", "", ""

    address = cleaned
    city = ""
    state = ""
    postal_code = ""
    country = ""
    parts = [_clean_text(part) for part in cleaned.split(",") if _clean_text(part)]
    if parts:
        city = parts[0]
    if len(parts) >= 2:
        second = parts[1]
        if re.fullmatch(r"[A-Z]{2,3}", second):
            state = second
        elif re.search(r"\d{4,6}", second):
            postal_match = re.search(r"\d{4,6}", second)
            if postal_match:
                postal_code = postal_match.group(0)
        else:
            country = second
    if len(parts) >= 3:
        third = parts[2]
        if not state and re.fullmatch(r"[A-Z]{2,3}", third):
            state = third
        elif not country:
            country = third
        if not postal_code:
            postal_match = re.search(r"\d{4,6}", third)
            if postal_match:
                postal_code = postal_match.group(0)
    if not postal_code:
        postal_match = re.search(r"\b\d{4,6}\b", cleaned)
        if postal_match:
            postal_code = postal_match.group(0)
    return address, city, state, postal_code, country


def _state_from_experience(document: ResumeDocument) -> str:
    for item in document.profile.experience:
        location = _clean_text(item.get("location"))
        if not location:
            continue
        parts = [_clean_text(part) for part in location.split(",") if _clean_text(part)]
        if len(parts) >= 2 and re.fullmatch(r"[A-Z]{2,3}", parts[1]):
            return parts[1]
    return ""


def _phone_parts(phone_value: str) -> Tuple[str, str]:
    phone = _clean_text(phone_value)
    if not phone:
        return "", ""
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return "", ""

    has_plus = phone.strip().startswith("+")
    if len(digits) <= 10 and not has_plus:
        return "", digits

    cc_len = min(3, max(1, len(digits) - 10))
    if has_plus and len(digits) > 10:
        return f"+{digits[:cc_len]}", digits[cc_len:]
    if len(digits) > 10:
        return f"+{digits[:cc_len]}", digits[cc_len:]
    return "", digits


def _ats_date_value(value: str) -> str:
    cleaned = _clean_text(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cleaned):
        year, month, _ = cleaned.split("-")
        return f"{month}/{year}"
    if re.fullmatch(r"\d{4}/\d{2}/\d{2}", cleaned):
        year, month, _ = cleaned.split("/")
        return f"{month}/{year}"
    return cleaned


def _ats_contact_fields(document: ResumeDocument) -> List[Tuple[str, str]]:
    contact = document.profile.contact or {}
    phone_raw = _contact_value(contact, ("phone", "mobile", "contact_number"))
    location_raw = _contact_value(contact, ("location", "address", "city"))
    address = _contact_value(contact, ("address", "street_address", "address_line_1", "line1", "street"))
    city = _contact_value(contact, ("city",))
    state = _contact_value(contact, ("state", "province", "region"))
    postal_code = _contact_value(contact, ("postal_code", "zipcode", "zip", "pincode", "postal"))

    loc_address, loc_city, loc_state, loc_postal, _loc_country = _location_components(location_raw)
    if not address:
        address = loc_address
    if not city:
        city = loc_city
    if not state:
        state = loc_state or _state_from_experience(document)
    if not postal_code:
        postal_code = loc_postal

    phone_device_type = _contact_value(contact, ("phone_device_type", "phone_type", "device_type"))
    if not phone_device_type and phone_raw:
        phone_device_type = "Mobile"

    country_phone_code = _contact_value(contact, ("country_phone_code", "phone_country_code", "country_code"))
    phone_number = _contact_value(contact, ("phone_number", "mobile_number", "number"))
    parsed_code, parsed_number = _phone_parts(phone_raw)
    if not country_phone_code:
        country_phone_code = parsed_code
    if country_phone_code and not country_phone_code.startswith("+"):
        country_phone_code = f"+{country_phone_code.lstrip('+')}"
    if not phone_number:
        phone_number = parsed_number

    postal_code = postal_code or "Not Available"
    state = state or "Not Available"
    address = address or "Not Available"
    city = city or "Not Available"
    phone_device_type = phone_device_type or "Not Available"
    country_phone_code = country_phone_code or "Not Available"
    phone_number = phone_number or "Not Available"

    return [
        ("Address", address),
        ("City", city),
        ("Postal Code", postal_code),
        ("State", state),
        ("Phone Device Type", phone_device_type),
        ("Country Phone Code", country_phone_code),
        ("Phone Number", phone_number),
    ]


def _layout_chips(skills: Sequence[str], width: float, font_name: str, font_size: float) -> List[List[Tuple[str, float]]]:
    rows: List[List[Tuple[str, float]]] = []
    current: List[Tuple[str, float]] = []
    current_width = 0.0
    chip_gap = 8.0
    for skill in skills:
        text = _clean_text(skill)
        if not text:
            continue
        chip_width = pdfmetrics.stringWidth(text, font_name, font_size) + 22
        if current and current_width + chip_gap + chip_width > width:
            rows.append(current)
            current = []
            current_width = 0.0
        if current:
            current_width += chip_gap
        current.append((text, chip_width))
        current_width += chip_width
    if current:
        rows.append(current)
    return rows


class _HackajobRenderer:
    def __init__(self, document: ResumeDocument, dest: Path) -> None:
        self.document = document
        self.dest = dest
        self.font_medium, self.font_bold = _register_fonts()
        self.font_bullet = _register_bullet_font(self.font_medium)

        theme = document.theme
        self.page_width, self.page_height = (
            (theme.page_width, theme.page_height) if theme.page_width and theme.page_height else A4
        )
        self.palette = _build_palette(theme.accent_color, theme.primary_color)
        self.canvas = Canvas(str(dest), pagesize=(self.page_width, self.page_height))
        self.page_number = 0
        self.cursor_top = TOP_MARGIN

        self.name_style = ParagraphStyle(
            "HackajobName",
            fontName=self.font_bold,
            fontSize=15,
            leading=18,
            textColor=self.palette.text_dark,
        )
        self.headline_style = ParagraphStyle(
            "HackajobHeadline",
            fontName=self.font_medium,
            fontSize=10.5,
            leading=14,
            textColor=self.palette.text_color,
        )
        self.contact_style = ParagraphStyle(
            "HackajobContact",
            fontName=self.font_medium,
            fontSize=9.0,
            leading=11,
            textColor=self.palette.text_color,
        )
        self.section_title_style = ParagraphStyle(
            "HackajobSectionTitle",
            fontName=self.font_bold,
            fontSize=10.5,
            leading=13,
            textColor=self.palette.text_dark,
        )
        self.body_style = ParagraphStyle(
            "HackajobBody",
            fontName=self.font_medium,
            fontSize=10.5,
            leading=16,
            textColor=self.palette.text_color,
        )
        self.meta_style = ParagraphStyle(
            "HackajobMeta",
            fontName=self.font_medium,
            fontSize=10.5,
            leading=15,
            textColor=self.palette.text_muted,
        )
        self.company_style = ParagraphStyle(
            "HackajobCompany",
            fontName=self.font_bold,
            fontSize=10.5,
            leading=14,
            textColor=self.palette.text_dark,
        )
        self.experience_bullet_style = ParagraphStyle(
            "HackajobExperienceBullet",
            parent=self.body_style,
            fontSize=10.5,
            leading=16,
            textColor=self.palette.text_color,
            leftIndent=0,
        )
        self.footer_width = 90
        self.footer_height = 12.75
        self.card_width = self.page_width - (OUTER_MARGIN * 2)

    def _draw_contact_row(
        self,
        top: float,
        x_start: float,
        max_width: float,
        items: Sequence[Tuple[str, str, str]],
    ) -> float:
        if not items:
            return 0.0
        chunks: List[str] = []
        for key, label, href in items:
            label_text = _clean_text(label)
            if not label_text:
                continue
            icon_markup = ""
            icon_path = ICON_DIR / f"{key}.png"
            if icon_path.exists():
                icon_markup = f'<img src="{icon_path.as_posix()}" width="8" height="8" valign="middle"/>&#160;'
            escaped_label = html.escape(label_text, quote=False)
            if href:
                safe_href = html.escape(href, quote=True)
                label_markup = f'<link href="{safe_href}">{escaped_label}</link>'
            else:
                label_markup = escaped_label
            chunks.append(f"{icon_markup}{label_markup}")
        if not chunks:
            return 0.0

        row_markup = " | ".join(chunks)
        row_style = ParagraphStyle(
            "HackajobContactRow",
            parent=self.contact_style,
            fontSize=9.0,
            leading=11.2,
            textColor=self.palette.text_color,
        )
        row_para = Paragraph(row_markup, row_style)
        _, row_height = row_para.wrap(max_width, 10000)
        row_para.drawOn(self.canvas, x_start, self._to_canvas_y(top, row_height))
        return float(row_height)

    def _measure_card_title(self, title: str, content_width: float, with_icon: bool = True) -> float:
        para, para_h = _measure_paragraph(title, self.section_title_style, max(content_width, 40))
        _ = para
        return max(para_h, 14.0)

    def _draw_card_title(
        self,
        title: str,
        icon_key: str,
        top: float,
        x: float,
        content_width: float,
    ) -> float:
        text_x = x
        para, para_h = _measure_paragraph(
            title,
            self.section_title_style,
            max(content_width, 40),
        )
        para.drawOn(self.canvas, text_x, self._to_canvas_y(top, para_h))
        return max(para_h, 14.0)

    def _draw_logo_image(
        self,
        logo_path: Path,
        x: float,
        y: float,
        width: float,
        height: float,
        radius: float,
    ) -> None:
        if not logo_path.exists():
            return
        self.canvas.saveState()
        clip = self.canvas.beginPath()
        clip.roundRect(x, y, width, height, radius)
        self.canvas.clipPath(clip, stroke=0, fill=0)
        self.canvas.drawImage(
            str(logo_path),
            x,
            y,
            width=width,
            height=height,
            preserveAspectRatio=True,
            mask="auto",
        )
        self.canvas.restoreState()

    def _draw_logo_tile(self, x: float, y: float, size: float, fill_hex: str, stroke_hex: str) -> None:
        self.canvas.saveState()
        self.canvas.setStrokeColor(colors.HexColor(stroke_hex))
        self.canvas.setFillColor(colors.HexColor(fill_hex))
        self.canvas.setLineWidth(0.5 if size <= 20 else 0.65)
        self.canvas.roundRect(x, y, size, size, max(1.8, size * 0.18), stroke=1, fill=1)
        self.canvas.restoreState()

    def _draw_briefcase_badge(
        self,
        x: float,
        y: float,
        size: float,
        fill_hex: str = "#eeeeee",
        stroke_hex: str = "#dbdbdb",
    ) -> None:
        self.canvas.saveState()
        self.canvas.setStrokeColor(colors.HexColor(stroke_hex))
        self.canvas.setFillColor(colors.HexColor(fill_hex))
        self.canvas.setLineWidth(0.55 if size <= 20 else 0.7)
        self.canvas.roundRect(x, y, size, size, max(2.0, size * 0.2), stroke=1, fill=1)

        body_w = size * 0.48
        body_h = size * 0.28
        body_x = x + (size - body_w) / 2
        body_y = y + (size * 0.33)
        self.canvas.setStrokeColor(colors.HexColor("#2f2f2f"))
        self.canvas.setLineWidth(max(0.65, size * 0.055))
        self.canvas.roundRect(body_x, body_y, body_w, body_h, max(0.9, size * 0.06), stroke=1, fill=0)

        handle_w = size * 0.23
        handle_h = size * 0.10
        handle_x = x + (size - handle_w) / 2
        handle_y = body_y + body_h
        self.canvas.roundRect(handle_x, handle_y, handle_w, handle_h, max(0.6, size * 0.04), stroke=1, fill=0)
        self.canvas.restoreState()

    def _draw_company_logo(self, company: str, x: float, y: float, size: float, context: str) -> None:
        variant = _company_logo_variant(company)
        draw_size = _logo_size_for_company(company, size, context)
        draw_x = x + (size - draw_size) / 2
        draw_y = y + (size - draw_size) / 2

        if variant == "briefcase_badge":
            if context == "header":
                self._draw_briefcase_badge(x, y, size, fill_hex="#ffffff", stroke_hex="#e7e7e7")
            else:
                self._draw_briefcase_badge(draw_x, draw_y, draw_size)
            return

        logo_path = _company_logo_path(company)
        if not logo_path.exists():
            self._draw_briefcase_badge(draw_x, draw_y, min(draw_size, size))
            return

        if variant == "rounded_square":
            self._draw_logo_image(
                logo_path=logo_path,
                x=draw_x,
                y=draw_y,
                width=draw_size,
                height=draw_size,
                radius=max(2.0, draw_size * (0.22 if context == "experience" else 0.2)),
            )
            return

        if context == "header":
            self._draw_logo_tile(x, y, size, fill_hex="#ffffff", stroke_hex="#e7e7e7")
            tile_x, tile_y, tile_size = x, y, size
        else:
            self._draw_logo_tile(draw_x, draw_y, draw_size, fill_hex="#ffffff", stroke_hex="#e3e3e3")
            tile_x, tile_y, tile_size = draw_x, draw_y, draw_size

        inner_pad = 1.2 if context == "header" else 1.5
        icon_scale = _logo_content_scale(company, context)
        icon_size = max(8.0, (tile_size - (inner_pad * 2)) * icon_scale)
        icon_x = tile_x + (tile_size - icon_size) / 2
        icon_y = tile_y + (tile_size - icon_size) / 2
        clip_radius = max(1.8, tile_size * 0.18)

        self.canvas.saveState()
        clip = self.canvas.beginPath()
        clip.roundRect(tile_x, tile_y, tile_size, tile_size, clip_radius)
        self.canvas.clipPath(clip, stroke=0, fill=0)
        self.canvas.drawImage(
            str(logo_path),
            icon_x,
            icon_y,
            width=icon_size,
            height=icon_size,
            preserveAspectRatio=True,
            mask="auto",
        )
        self.canvas.restoreState()

    def _to_canvas_y(self, top: float, height: float = 0) -> float:
        return self.page_height - top - height

    def _start_page(self, first_page: bool) -> None:
        if self.page_number > 0:
            self.canvas.showPage()
        self.page_number += 1
        self.canvas.setFillColor(self.palette.page_bg)
        self.canvas.rect(0, 0, self.page_width, self.page_height, stroke=0, fill=1)

        footer_path = LOGO_DIR / "footer_hackajob.png"
        if footer_path.exists():
            x = (self.page_width - self.footer_width) / 2
            self.canvas.drawImage(
                str(footer_path),
                x,
                12,
                width=self.footer_width,
                height=self.footer_height,
                preserveAspectRatio=True,
                mask="auto",
            )
        self.cursor_top = TOP_MARGIN
        if first_page:
            self._draw_header()
            self.cursor_top = 108

    def _draw_header(self) -> None:
        header_height = 96
        left_top = (
            self.palette.header_gradient_left_top.red,
            self.palette.header_gradient_left_top.green,
            self.palette.header_gradient_left_top.blue,
        )
        right_top = (
            self.palette.header_gradient_right_top.red,
            self.palette.header_gradient_right_top.green,
            self.palette.header_gradient_right_top.blue,
        )
        left_bottom = (
            self.palette.header_gradient_left_bottom.red,
            self.palette.header_gradient_left_bottom.green,
            self.palette.header_gradient_left_bottom.blue,
        )
        right_bottom = (
            self.palette.header_gradient_right_bottom.red,
            self.palette.header_gradient_right_bottom.green,
            self.palette.header_gradient_right_bottom.blue,
        )
        width = int(self.page_width)
        height = int(header_height)
        strip_w = 3
        for y in range(height):
            ty = y / max(height - 1, 1)
            left_r = left_top[0] + (left_bottom[0] - left_top[0]) * ty
            left_g = left_top[1] + (left_bottom[1] - left_top[1]) * ty
            left_b = left_top[2] + (left_bottom[2] - left_top[2]) * ty
            right_r = right_top[0] + (right_bottom[0] - right_top[0]) * ty
            right_g = right_top[1] + (right_bottom[1] - right_top[1]) * ty
            right_b = right_top[2] + (right_bottom[2] - right_top[2]) * ty
            canvas_y = self.page_height - y - 1
            for x in range(0, width, strip_w):
                tx = x / max(width - 1, 1)
                r = left_r + (right_r - left_r) * tx
                g = left_g + (right_g - left_g) * tx
                b = left_b + (right_b - left_b) * tx
                self.canvas.setFillColor(colors.Color(r, g, b))
                self.canvas.rect(x, canvas_y, strip_w + 0.2, 1.2, stroke=0, fill=1)
        self.canvas.setStrokeColor(self.palette.card_border)
        self.canvas.setLineWidth(CARD_BORDER_WIDTH)
        self.canvas.line(0, self.page_height - header_height, self.page_width, self.page_height - header_height)

        avatar_cx = 32
        avatar_top = 12
        avatar_radius = 21
        avatar_cy = self.page_height - avatar_top - avatar_radius
        self.canvas.setStrokeColor(self.palette.avatar_ring)
        self.canvas.setLineWidth(1.2)
        self.canvas.circle(avatar_cx, avatar_cy, avatar_radius, stroke=1, fill=0)
        self.canvas.setStrokeColor(colors.HexColor("#2f2f2f"))
        self.canvas.setLineWidth(1.9)
        self.canvas.circle(avatar_cx, avatar_cy + 8.0, 5.4, stroke=1, fill=0)
        self.canvas.roundRect(avatar_cx - 11.5, avatar_cy - 12.5, 23.0, 11.8, 5.6, stroke=1, fill=0)

        text_x = 67
        name = _clean_text(self.document.profile.name)
        headline = _headline_text(self.document)
        contact_items = _header_contact_items(self.document)
        previous_label = "Previous companies:"
        content_width = self.page_width - text_x - 30

        current_top = 14
        name_para, name_height = _measure_paragraph(name, self.name_style, content_width)
        name_para.drawOn(self.canvas, text_x, self._to_canvas_y(current_top, name_height))
        current_top += name_height + 2

        if headline:
            if " at " in headline:
                role_text, company_text = headline.rsplit(" at ", 1)
                headline_markup = (
                    f"{html.escape(role_text, quote=False)} at "
                    f'<font face="{self.font_bold}">{html.escape(company_text, quote=False)}</font>'
                )
                headline_para = Paragraph(headline_markup, self.headline_style)
                _, headline_height = headline_para.wrap(content_width, 10000)
                headline_height = float(headline_height)
            else:
                headline_para, headline_height = _measure_paragraph(headline, self.headline_style, content_width)
            headline_para.drawOn(self.canvas, text_x, self._to_canvas_y(current_top, headline_height))
            current_top += headline_height + 2

        if contact_items:
            contact_h = self._draw_contact_row(current_top, text_x, content_width, contact_items)
            current_top += contact_h + 2

        current_top += 8
        label_para, label_height = _measure_paragraph(
            previous_label,
            ParagraphStyle(
                "HackajobHeaderSmall",
                parent=self.headline_style,
                fontName=self.font_bold,
                fontSize=9,
                leading=11,
            ),
            90,
        )
        label_para.drawOn(self.canvas, text_x, self._to_canvas_y(current_top, label_height))

        companies = [
            "Oracle",
            "Xactly",
            "Nineleaps",
            "PwC",
            "Minewhat",
            "Thrymr",
        ]
        logo_x = 165
        logo_size = 18.5
        logo_y = self._to_canvas_y(current_top - 2, logo_size)
        for company in companies:
            self._draw_company_logo(company, logo_x, logo_y, logo_size, context="header")
            logo_x += 22

    def _available_height(self) -> float:
        return self.page_height - BOTTOM_MARGIN - self.cursor_top

    def _ensure_space(self, height: float) -> None:
        if height <= self._available_height():
            return
        self._start_page(first_page=False)

    def _draw_card_background(self, top: float, height: float) -> None:
        y = self._to_canvas_y(top, height)
        self.canvas.setFillColor(self.palette.card_bg)
        self.canvas.setStrokeColor(self.palette.card_border)
        self.canvas.setLineWidth(CARD_BORDER_WIDTH)
        self.canvas.roundRect(OUTER_MARGIN, y, self.card_width, height, CARD_RADIUS, stroke=1, fill=1)

    def _draw_about_card(self) -> None:
        title = _about_title(self.document)
        paragraphs = _about_paragraphs(self.document)
        if not paragraphs:
            return

        content_width = self.card_width - (CARD_PAD_X * 2)
        title_h = self._measure_card_title(title, content_width, with_icon=True)
        para_blocks = [_measure_paragraph(paragraph, self.body_style, content_width) for paragraph in paragraphs]

        content_h = CARD_PAD_TOP + title_h + 8
        for index, (_, para_h) in enumerate(para_blocks):
            content_h += para_h
            if index < len(para_blocks) - 1:
                content_h += 14
        content_h += CARD_PAD_BOTTOM

        self._ensure_space(content_h)
        top = self.cursor_top
        self._draw_card_background(top, content_h)

        content_top = top + CARD_PAD_TOP
        title_h_drawn = self._draw_card_title(
            title=title,
            icon_key="summary",
            top=content_top,
            x=OUTER_MARGIN + CARD_PAD_X,
            content_width=content_width,
        )
        _ = title_h_drawn
        content_top += title_h + 8
        for index, (para, para_h) in enumerate(para_blocks):
            para.drawOn(self.canvas, OUTER_MARGIN + CARD_PAD_X, self._to_canvas_y(content_top, para_h))
            content_top += para_h
            if index < len(para_blocks) - 1:
                content_top += 14

        self.cursor_top += content_h + CARD_GAP

    def _draw_skills_card(self) -> List[str]:
        skill_section = _section_by_title(self.document.sections, "skill")
        skills = _flatten_skills(skill_section, self.document.profile.skills)
        category_lines = _skill_category_lines(skill_section, self.document.profile.skills)
        if not category_lines:
            return []

        content_width = self.card_width - (CARD_PAD_X * 2)
        title_h = self._measure_card_title("Technical Skills", content_width, with_icon=True)
        skills_style = ParagraphStyle(
            "HackajobSkillLine",
            parent=self.body_style,
            fontSize=10.5,
            leading=16,
            textColor=self.palette.text_color,
        )
        rendered_lines: List[Tuple[Paragraph, float]] = []
        lines_h = 0.0
        for category, items in category_lines:
            category_markup = html.escape(category, quote=False)
            values_markup = html.escape(", ".join(items), quote=False)
            markup = f'<font face="{self.font_bold}">{category_markup}:</font> {values_markup}'
            paragraph = Paragraph(markup, skills_style)
            _, line_h = paragraph.wrap(content_width, 10000)
            rendered_lines.append((paragraph, float(line_h)))
            lines_h += float(line_h) + 4
        card_h = CARD_PAD_TOP + title_h + 10 + lines_h + CARD_PAD_BOTTOM

        self._ensure_space(card_h)
        top = self.cursor_top
        self._draw_card_background(top, card_h)

        content_top = top + CARD_PAD_TOP
        self._draw_card_title(
            title="Technical Skills",
            icon_key="skills",
            top=content_top,
            x=OUTER_MARGIN + CARD_PAD_X,
            content_width=content_width,
        )
        content_top += title_h + 10
        for paragraph, line_h in rendered_lines:
            paragraph.drawOn(self.canvas, OUTER_MARGIN + CARD_PAD_X, self._to_canvas_y(content_top, line_h))
            content_top += line_h + 4

        self.cursor_top += card_h + CARD_GAP
        return skills

    def _entry_header_segment(self, entry: _ExperienceEntry, content_width: float) -> _Segment:
        text_x_offset = 54
        text_width = content_width - text_x_offset
        role_text = _clean_text(entry.role)
        company_text = _clean_text(entry.company)
        role_line = role_text or company_text
        role_para, role_h = _measure_paragraph(role_line, self.company_style, text_width)

        location_text = _clean_text(entry.location)
        if location_text and "," in location_text:
            location_text = _clean_text(location_text.split(",", 1)[0])

        start_text = _clean_text(entry.start_date)
        end_text = _clean_text(entry.end_date)

        def _to_month_year(value: str) -> str:
            lowered = value.lower()
            if lowered in {"present", "current"}:
                return "Present"
            parsed = _parse_date(value)
            if not parsed:
                return value
            return parsed.strftime("%B %Y")

        start_compact = _to_month_year(start_text) if start_text else ""
        end_compact = _to_month_year(end_text) if end_text else ""
        date_compact = ""
        if start_compact and end_compact:
            date_compact = f"{start_compact} - {end_compact}"
        else:
            date_compact = start_compact or end_compact

        meta_lines: List[str] = []
        if company_text:
            meta_lines.append(company_text)
        line_two_parts: List[str] = []
        if location_text:
            line_two_parts.append(location_text)
        if date_compact:
            line_two_parts.append(date_compact)
        if line_two_parts:
            meta_lines.append(" . ".join(line_two_parts))
        meta_line = "\n".join(meta_lines)
        if meta_line:
            meta_para, meta_h = _measure_paragraph(meta_line, self.meta_style, text_width)
        else:
            meta_para, meta_h = _measure_paragraph("", self.meta_style, text_width)
            meta_h = 0.0

        text_block_h = role_h + meta_h
        header_h = max(34.0, text_block_h) + 6
        return _Segment(
            kind="entry_header",
            height=header_h,
            payload={
                "entry": entry,
                "role_para": role_para,
                "role_h": role_h,
                "meta_para": meta_para,
                "meta_h": meta_h,
                "text_x_offset": text_x_offset,
            },
        )

    def _entry_bullet_segments(
        self,
        entry: _ExperienceEntry,
        content_width: float,
        highlight_terms: Sequence[str],
    ) -> List[_Segment]:
        segments: List[_Segment] = []
        bullet_style = ParagraphStyle(
            "HackajobBulletLine",
            parent=self.experience_bullet_style,
            leftIndent=12,
            bulletIndent=0,
            bulletFontName=self.font_bullet,
            bulletFontSize=7.0,
            leading=13,
        )
        for bullet in entry.bullets:
            bullet_para = Paragraph(
                _highlight_bullet_markup(bullet, highlight_terms, self.font_bold),
                bullet_style,
                bulletText=EXPERIENCE_BULLET_CHAR,
            )
            _, bullet_h = bullet_para.wrap(content_width - EXPERIENCE_BULLET_X_OFFSET, 10000)
            segments.append(
                _Segment(
                    kind="entry_bullet",
                    height=float(bullet_h) + 6,
                    payload={"paragraph": bullet_para, "height": float(bullet_h)},
                )
            )
        return segments

    def _draw_entry_header(self, top: float, segment: _Segment, content_x: float, content_width: float) -> float:
        entry = segment.payload["entry"]
        text_x = content_x + float(segment.payload["text_x_offset"])
        logo_box_x = content_x
        logo_box_size = 38
        logo_box_y = self._to_canvas_y(top, logo_box_size)

        icon_size = 34
        icon_x = logo_box_x + (logo_box_size - icon_size) / 2
        icon_y = logo_box_y + (logo_box_size - icon_size) / 2
        self._draw_company_logo(entry.company, icon_x, icon_y, icon_size, context="experience")

        current_top = top
        role_para = segment.payload["role_para"]
        role_h = float(segment.payload["role_h"])
        role_para.drawOn(self.canvas, text_x, self._to_canvas_y(current_top, role_h))
        current_top += role_h

        meta_h = float(segment.payload["meta_h"])
        if meta_h > 0:
            meta_para = segment.payload["meta_para"]
            meta_para.drawOn(self.canvas, text_x, self._to_canvas_y(current_top, meta_h))
            current_top += meta_h

        current_top += 0

        return top + segment.height

    def _draw_experience_card(self, skills_pool: Sequence[str]) -> None:
        entries = _experience_entries(self.document, skills_pool)
        if not entries:
            return
        highlight_terms = list(skills_pool) if skills_pool else [str(skill) for skill in self.document.profile.skills]
        highlight_terms.extend(FORCED_BULLET_HIGHLIGHTS)

        content_width = self.card_width - (CARD_PAD_X * 2)
        title_h = self._measure_card_title("Work Experience", content_width, with_icon=True)

        segments: List[_Segment] = []
        for idx, entry in enumerate(entries):
            if idx > 0:
                segments.append(_Segment(kind="separator", height=20, payload={}))
            segments.append(self._entry_header_segment(entry, content_width))
            segments.extend(self._entry_bullet_segments(entry, content_width, highlight_terms))
            segments.append(_Segment(kind="entry_gap", height=0, payload={}))

        index = 0
        first_chunk = True
        while index < len(segments):
            available = self._available_height()
            min_card = 120
            if available < min_card:
                self._start_page(first_page=False)
                available = self._available_height()

            title_space = (title_h + 10) if first_chunk else 0
            base = CARD_PAD_TOP + CARD_PAD_BOTTOM + title_space
            used = base
            chunk_start = index
            while index < len(segments) and used + segments[index].height <= available:
                used += segments[index].height
                index += 1
            if index == chunk_start:
                used += segments[index].height
                index += 1

            card_height = used
            top = self.cursor_top
            self._draw_card_background(top, card_height)
            content_top = top + CARD_PAD_TOP
            content_x = OUTER_MARGIN + CARD_PAD_X

            if first_chunk:
                self._draw_card_title(
                    title="Work Experience",
                    icon_key="experience",
                    top=content_top,
                    x=content_x,
                    content_width=content_width,
                )
                content_top += title_h + 10

            for segment in segments[chunk_start:index]:
                if segment.kind == "separator":
                    line_y = self._to_canvas_y(content_top + 6)
                    self.canvas.setStrokeColor(self.palette.card_border)
                    self.canvas.setLineWidth(DIVIDER_LINE_WIDTH)
                    self.canvas.line(content_x, line_y, content_x + content_width, line_y)
                    content_top += segment.height
                    continue
                if segment.kind == "entry_header":
                    content_top = self._draw_entry_header(content_top, segment, content_x, content_width)
                    continue
                if segment.kind == "entry_bullet":
                    paragraph = segment.payload["paragraph"]
                    bullet_h = float(segment.payload["height"])
                    paragraph.drawOn(
                        self.canvas,
                        content_x + EXPERIENCE_BULLET_X_OFFSET,
                        self._to_canvas_y(content_top, bullet_h),
                    )
                    content_top += segment.height
                    continue
                content_top += segment.height

            self.cursor_top += card_height + CARD_GAP
            first_chunk = False
            if index < len(segments):
                self._start_page(first_page=False)

    def _draw_education_card(self) -> None:
        records = _education_entries(self.document)
        if not records:
            return

        content_width = self.card_width - (CARD_PAD_X * 2)
        title_h = self._measure_card_title("Education", content_width, with_icon=True)
        row_segments: List[_Segment] = []
        for idx, record in enumerate(records):
            if idx > 0:
                row_segments.append(_Segment(kind="separator", height=8, payload={}))

            text_width = content_width - 54
            inst_para, inst_h = _measure_paragraph(record.institution, self.company_style, text_width)
            degree_para, degree_h = _measure_paragraph(record.degree, self.meta_style, text_width)
            loc_para, loc_h = _measure_paragraph(record.location_year, self.meta_style, text_width)
            row_height = max(34.0, inst_h + degree_h + loc_h) + 2
            row_segments.append(
                _Segment(
                    kind="education_row",
                    height=row_height,
                    payload={
                        "record": record,
                        "institution": inst_para,
                        "inst_h": inst_h,
                        "degree": degree_para,
                        "degree_h": degree_h,
                        "location": loc_para,
                        "loc_h": loc_h,
                    },
                )
            )
        row_segments.append(_Segment(kind="entry_gap", height=2, payload={}))

        index = 0
        first_chunk = True
        while index < len(row_segments):
            available = self._available_height()
            if available < 100:
                self._start_page(first_page=False)
                available = self._available_height()

            title_space = (title_h + 10) if first_chunk else 0
            base = CARD_PAD_TOP + CARD_PAD_BOTTOM + title_space
            used = base
            chunk_start = index
            while index < len(row_segments) and used + row_segments[index].height <= available:
                used += row_segments[index].height
                index += 1
            if index == chunk_start:
                used += row_segments[index].height
                index += 1

            card_h = used
            top = self.cursor_top
            self._draw_card_background(top, card_h)
            content_top = top + CARD_PAD_TOP
            content_x = OUTER_MARGIN + CARD_PAD_X
            if first_chunk:
                self._draw_card_title(
                    title="Education",
                    icon_key="education",
                    top=content_top,
                    x=content_x,
                    content_width=content_width,
                )
                content_top += title_h + 10

            for segment in row_segments[chunk_start:index]:
                if segment.kind == "separator":
                    line_y = self._to_canvas_y(content_top + 6)
                    self.canvas.setStrokeColor(self.palette.card_border)
                    self.canvas.setLineWidth(DIVIDER_LINE_WIDTH)
                    self.canvas.line(content_x, line_y, content_x + content_width, line_y)
                    content_top += segment.height
                    continue
                if segment.kind == "education_row":
                    icon_box_size = 32
                    box_y = self._to_canvas_y(content_top, icon_box_size)
                    self.canvas.setStrokeColor(colors.HexColor("#e8e8e8"))
                    self.canvas.setLineWidth(CARD_BORDER_WIDTH)
                    self.canvas.roundRect(content_x, box_y, icon_box_size, icon_box_size, 6, stroke=1, fill=0)
                    icon_candidates = [LOGO_DIR / "Logonew.png", ICON_DIR / "education.png"]
                    icon_path = next((path for path in icon_candidates if path.exists()), None)
                    if icon_path:
                        icon_size = 22
                        icon_x = content_x + (icon_box_size - icon_size) / 2
                        icon_y = box_y + (icon_box_size - icon_size) / 2
                        self.canvas.drawImage(
                            str(icon_path),
                            icon_x,
                            icon_y,
                            width=icon_size,
                            height=icon_size,
                            preserveAspectRatio=True,
                            mask="auto",
                        )
                    text_x = content_x + 54
                    inst_para = segment.payload["institution"]
                    inst_h = float(segment.payload["inst_h"])
                    inst_para.drawOn(self.canvas, text_x, self._to_canvas_y(content_top, inst_h))
                    row_top = content_top + inst_h
                    degree_para = segment.payload["degree"]
                    degree_h = float(segment.payload["degree_h"])
                    degree_para.drawOn(self.canvas, text_x, self._to_canvas_y(row_top, degree_h))
                    row_top += degree_h
                    loc_para = segment.payload["location"]
                    loc_h = float(segment.payload["loc_h"])
                    loc_para.drawOn(self.canvas, text_x, self._to_canvas_y(row_top, loc_h))
                    content_top += segment.height
                    continue
                content_top += segment.height

            self.cursor_top += card_h + CARD_GAP
            first_chunk = False
            if index < len(row_segments):
                self._start_page(first_page=False)

    def _draw_awards_card(self) -> None:
        awards = _awards_bullets(self.document)
        if not awards:
            return

        content_width = self.card_width - (CARD_PAD_X * 2)
        title_h = self._measure_card_title("Awards", content_width, with_icon=True)
        bullet_style = ParagraphStyle(
            "HackajobAwardsBullet",
            parent=self.body_style,
            leftIndent=12,
            bulletIndent=0,
            bulletFontName=self.font_bullet,
            bulletFontSize=7.0,
            leading=12,
        )

        bullet_rows: List[Tuple[Paragraph, float]] = []
        rows_h = 0.0
        for line in awards:
            para = Paragraph(
                html.escape(line, quote=False),
                bullet_style,
                bulletText=EXPERIENCE_BULLET_CHAR,
            )
            _, row_h = para.wrap(content_width, 10000)
            row_h = float(row_h)
            bullet_rows.append((para, row_h))
            rows_h += row_h + 4

        card_h = CARD_PAD_TOP + title_h + 4 + rows_h + CARD_PAD_BOTTOM
        self._ensure_space(card_h)

        top = self.cursor_top
        self._draw_card_background(top, card_h)
        content_top = top + CARD_PAD_TOP
        content_x = OUTER_MARGIN + CARD_PAD_X

        self._draw_card_title(
            title="Awards",
            icon_key="awards",
            top=content_top,
            x=content_x,
            content_width=content_width,
        )
        content_top += title_h + 6

        for para, row_h in bullet_rows:
            para.drawOn(self.canvas, content_x, self._to_canvas_y(content_top, row_h))
            content_top += row_h + 4

        self.cursor_top += card_h + CARD_GAP

    def _build_ats_text(self, skills_pool: Sequence[str]) -> str:
        lines: List[str] = []
        name = _clean_text(self.document.profile.name)
        lines.append("Contact Information")
        if name:
            lines.append(f"Name: {name}")
        headline = _headline_text(self.document)
        if headline:
            lines.append(f"Headline: {headline}")
        contact_line = _ats_contact_line(self.document)
        if contact_line:
            lines.append(f"Contact: {contact_line}")
        for label, value in _ats_contact_fields(self.document):
            lines.append(f"{label}: {value}")

        return "\n".join(lines)

    def _draw_ats_text_layer(self, skills_pool: Sequence[str]) -> None:
        ats_text = self._build_ats_text(skills_pool)
        if not ats_text:
            return
        self.canvas.saveState()
        self.canvas.setFillColor(colors.HexColor("#ffffff"))
        self.canvas.setFont("Helvetica", 4.0)
        leading = 4.2
        text_obj = self.canvas.beginText()
        text_obj.setTextOrigin(2, 80)
        text_obj.setLeading(leading)
        for line in ats_text.splitlines():
            text_obj.textLine(line)
        self.canvas.drawText(text_obj)
        self.canvas.restoreState()

    def render(self) -> Path:
        self._start_page(first_page=True)
        self._draw_about_card()
        skills = self._draw_skills_card()
        self._draw_experience_card(skills)
        self._draw_education_card()
        self._draw_awards_card()
        self.canvas.save()
        return self.dest


def render_hackajob_resume(document: ResumeDocument, output_path: str | Path) -> Path:
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    renderer = _HackajobRenderer(document, dest)
    return renderer.render()
