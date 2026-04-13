from __future__ import annotations

import html
import re
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir
from typing import Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from PIL import Image, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
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
ICON_SECTION_ALPHA_SCALE = 0.82
ICON_SECTION_ALPHA_GAMMA = 1.0
ICON_COLOR_LIGHTEN = -1
ICON_TINT_ENABLED = True
_ICON_TINT_CACHE: Dict[Tuple[str, str, float, float], Path] = {}


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


def _tinted_icon_path(
    asset_name: str,
    color_hex: str,
    *,
    alpha_scale: float = ICON_ALPHA_SCALE,
    alpha_gamma: float = ICON_ALPHA_GAMMA,
) -> Path | None:
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
    normalized_scale = max(0.0, float(alpha_scale))
    normalized_gamma = max(0.01, float(alpha_gamma))
    cache_key = (
        base_path.as_posix(),
        tinted_hex.lower(),
        round(normalized_scale, 4),
        round(normalized_gamma, 4),
    )
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
            if normalized_scale < 1.0 or normalized_gamma != 1.0:
                def _attenuate(value: int) -> int:
                    normalized = max(0.0, min(1.0, value / 255.0))
                    adjusted = normalized ** normalized_gamma if normalized_gamma != 1.0 else normalized
                    scaled = adjusted * normalized_scale
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
ATS_TEMPLATE_NAMES = {"ats", "ats_plain", "ats_standard"}
ATS_SECTION_PRIORITY: Dict[str, int] = {
    "summary": 10,
    "professional summary": 10,
    "skills": 15,
    "technical skills": 15,
    "experience": 20,
    "professional experience": 20,
    "work experience": 20,
    "employment history": 20,
    "education": 30,
    "projects": 50,
    "certifications": 60,
    "awards": 70,
}
ATS_SKILL_LABEL_HIGHLIGHT = {
    "frontend",
    "backend",
    "testing & devops",
    "ai tools",
}
ATS_SANS_FONT_STACK = [
    "Calibri",
    "Arial",
    "Helvetica",
    "Verdana",
    "Tahoma",
    "Montserrat",
    "Lato",
    "Roboto",
    "Avenir",
    "Open Sans",
    "Aptos",
]
ATS_SERIF_FONT_STACK = [
    "Garamond",
    "Georgia",
    "Times New Roman",
    "Cambria",
]
ATS_FONT_FALLBACK_MAP: Dict[str, str] = {
    "calibri": "Helvetica",
    "arial": "Helvetica",
    "helvetica": "Helvetica",
    "verdana": "Helvetica",
    "tahoma": "Helvetica",
    "montserrat": "Helvetica",
    "lato": "Helvetica",
    "roboto": "Helvetica",
    "avenir": "Helvetica",
    "open sans": "Helvetica",
    "aptos": "Helvetica",
    "garamond": "Times-Roman",
    "georgia": "Times-Roman",
    "times new roman": "Times-Roman",
    "cambria": "Times-Roman",
}
ATS_FONT_DOWNLOAD_DIR = PROJECT_ROOT / "assets" / "ats_fonts"
ATS_SPACE_GROTESK_REGULAR = "ATSSpaceGroteskRegular"
ATS_SPACE_GROTESK_MEDIUM = "ATSSpaceGroteskMedium"
ATS_SPACE_GROTESK_BOLD = "ATSSpaceGroteskBold"
ATS_SPACE_GROTESK_LIGHT = "ATSSpaceGroteskLight"
ATS_SPACE_GROTESK_REGULAR_CANDIDATES = [
    ATS_FONT_DOWNLOAD_DIR / "SpaceGrotesk-Regular.ttf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "Fonts" / "WEB" / "fonts" / "SpaceGrotesk-Regular.ttf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "Fonts" / "OTF" / "SpaceGrotesk-Regular.otf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "WEB" / "fonts" / "SpaceGrotesk-Regular.ttf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "OTF" / "SpaceGrotesk-Regular.otf",
]
ATS_SPACE_GROTESK_MEDIUM_CANDIDATES = [
    ATS_FONT_DOWNLOAD_DIR / "SpaceGrotesk-Medium.ttf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "Fonts" / "WEB" / "fonts" / "SpaceGrotesk-Medium.ttf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "Fonts" / "OTF" / "SpaceGrotesk-Medium.otf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "WEB" / "fonts" / "SpaceGrotesk-Medium.ttf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "OTF" / "SpaceGrotesk-Medium.otf",
    PROJECT_ROOT / "assets" / "hackajob" / "fonts" / "spacegrotesk-medium.ttf",
    PROJECT_ROOT / "assets" / "hackajob" / "fonts" / "spacegrotesk-medium-subset.ttf",
]
ATS_SPACE_GROTESK_BOLD_CANDIDATES = [
    ATS_FONT_DOWNLOAD_DIR / "SpaceGrotesk-Bold.ttf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "Fonts" / "WEB" / "fonts" / "SpaceGrotesk-Bold.ttf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "Fonts" / "OTF" / "SpaceGrotesk-Bold.otf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "WEB" / "fonts" / "SpaceGrotesk-Bold.ttf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "OTF" / "SpaceGrotesk-Bold.otf",
    PROJECT_ROOT / "assets" / "hackajob" / "fonts" / "spacegrotesk-bold.ttf",
    PROJECT_ROOT / "assets" / "hackajob" / "fonts" / "spacegrotesk-bold-subset.ttf",
]
ATS_SPACE_GROTESK_LIGHT_CANDIDATES = [
    ATS_FONT_DOWNLOAD_DIR / "SpaceGrotesk-Light.ttf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "Fonts" / "WEB" / "fonts" / "SpaceGrotesk-Light.ttf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "Fonts" / "OTF" / "SpaceGrotesk-Light.otf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "WEB" / "fonts" / "SpaceGrotesk-Light.ttf",
    PROJECT_ROOT / "SpaceGrotesk_Complete" / "OTF" / "SpaceGrotesk-Light.otf",
]
ATS_SYSTEM_FONT_DIRS = [
    Path("/System/Library/Fonts/Supplemental"),
    Path("/Library/Fonts"),
]
ATS_ONLINE_FONT_SOURCES: Dict[str, List[str]] = {
    "Carlito-Regular.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/carlito/Carlito-Regular.ttf",
    ],
    "Carlito-Bold.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/carlito/Carlito-Bold.ttf",
    ],
    "Caladea-Regular.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/caladea/Caladea-Regular.ttf",
    ],
    "Caladea-Bold.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/caladea/Caladea-Bold.ttf",
    ],
    "Lato-Light.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/lato/Lato-Light.ttf",
    ],
    "Lato-Regular.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/lato/Lato-Regular.ttf",
    ],
    "Lato-Medium.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/lato/Lato-Medium.ttf",
    ],
    "Lato-Bold.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/lato/Lato-Bold.ttf",
    ],
    "SpaceGrotesk-Light.ttf": [
        "https://raw.githubusercontent.com/floriankarsten/space-grotesk/master/fonts/ttf/static/SpaceGrotesk-Light.ttf",
    ],
    "SpaceGrotesk-Regular.ttf": [
        "https://raw.githubusercontent.com/floriankarsten/space-grotesk/master/fonts/ttf/static/SpaceGrotesk-Regular.ttf",
    ],
    "SpaceGrotesk-Medium.ttf": [
        "https://raw.githubusercontent.com/floriankarsten/space-grotesk/master/fonts/ttf/static/SpaceGrotesk-Medium.ttf",
    ],
    "SpaceGrotesk-Bold.ttf": [
        "https://raw.githubusercontent.com/floriankarsten/space-grotesk/master/fonts/ttf/static/SpaceGrotesk-Bold.ttf",
    ],
    "Montserrat-Light.ttf": [
        "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Light.ttf",
    ],
    "Montserrat-Regular.ttf": [
        "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Regular.ttf",
    ],
    "Montserrat-Medium.ttf": [
        "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Medium.ttf",
    ],
    "Montserrat-Bold.ttf": [
        "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Bold.ttf",
    ],
    "Montserrat-Variable.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",
    ],
    "EBGaramond-Variable.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/ebgaramond/EBGaramond%5Bwght%5D.ttf",
    ],
    "Arimo-Variable.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/apache/arimo/Arimo%5Bwght%5D.ttf",
    ],
    "Tinos-Regular.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/apache/tinos/Tinos-Regular.ttf",
    ],
    "Tinos-Bold.ttf": [
        "https://raw.githubusercontent.com/google/fonts/main/apache/tinos/Tinos-Bold.ttf",
    ],
}
ATS_FONT_FAMILY_CANDIDATES: Dict[str, Dict[str, List[Path]]] = {
    "calibri": {
        "regular": [ATS_FONT_DOWNLOAD_DIR / "Carlito-Regular.ttf"],
        "medium": [ATS_FONT_DOWNLOAD_DIR / "Carlito-Regular.ttf"],
        "bold": [ATS_FONT_DOWNLOAD_DIR / "Carlito-Bold.ttf"],
        "light": [ATS_FONT_DOWNLOAD_DIR / "Carlito-Regular.ttf"],
    },
    "arial": {
        "regular": [ATS_SYSTEM_FONT_DIRS[0] / "Arial.ttf", ATS_FONT_DOWNLOAD_DIR / "Arimo-Variable.ttf"],
        "medium": [ATS_SYSTEM_FONT_DIRS[0] / "Arial.ttf", ATS_FONT_DOWNLOAD_DIR / "Arimo-Variable.ttf"],
        "bold": [ATS_SYSTEM_FONT_DIRS[0] / "Arial Bold.ttf", ATS_FONT_DOWNLOAD_DIR / "Arimo-Variable.ttf"],
        "light": [ATS_SYSTEM_FONT_DIRS[0] / "Arial.ttf", ATS_FONT_DOWNLOAD_DIR / "Arimo-Variable.ttf"],
    },
    "georgia": {
        "regular": [ATS_SYSTEM_FONT_DIRS[0] / "Georgia.ttf", ATS_FONT_DOWNLOAD_DIR / "Tinos-Regular.ttf"],
        "medium": [ATS_SYSTEM_FONT_DIRS[0] / "Georgia.ttf", ATS_FONT_DOWNLOAD_DIR / "Tinos-Regular.ttf"],
        "bold": [ATS_SYSTEM_FONT_DIRS[0] / "Georgia Bold.ttf", ATS_FONT_DOWNLOAD_DIR / "Tinos-Bold.ttf"],
        "light": [ATS_SYSTEM_FONT_DIRS[0] / "Georgia.ttf", ATS_FONT_DOWNLOAD_DIR / "Tinos-Regular.ttf"],
    },
    "helvetica": {},
    "spacegrotesk": {},
    "garamond": {
        "regular": [ATS_FONT_DOWNLOAD_DIR / "EBGaramond-Variable.ttf"],
        "medium": [ATS_FONT_DOWNLOAD_DIR / "EBGaramond-Variable.ttf"],
        "bold": [ATS_FONT_DOWNLOAD_DIR / "EBGaramond-Variable.ttf"],
        "light": [ATS_FONT_DOWNLOAD_DIR / "EBGaramond-Variable.ttf"],
    },
    "tahoma": {
        "regular": [ATS_SYSTEM_FONT_DIRS[0] / "Tahoma.ttf", ATS_FONT_DOWNLOAD_DIR / "Arimo-Variable.ttf"],
        "medium": [ATS_SYSTEM_FONT_DIRS[0] / "Tahoma.ttf", ATS_FONT_DOWNLOAD_DIR / "Arimo-Variable.ttf"],
        "bold": [ATS_SYSTEM_FONT_DIRS[0] / "Tahoma Bold.ttf", ATS_FONT_DOWNLOAD_DIR / "Arimo-Variable.ttf"],
        "light": [ATS_SYSTEM_FONT_DIRS[0] / "Tahoma.ttf", ATS_FONT_DOWNLOAD_DIR / "Arimo-Variable.ttf"],
    },
    "times new roman": {
        "regular": [ATS_SYSTEM_FONT_DIRS[0] / "Times New Roman.ttf", ATS_FONT_DOWNLOAD_DIR / "Tinos-Regular.ttf"],
        "medium": [ATS_SYSTEM_FONT_DIRS[0] / "Times New Roman.ttf", ATS_FONT_DOWNLOAD_DIR / "Tinos-Regular.ttf"],
        "bold": [ATS_SYSTEM_FONT_DIRS[0] / "Times New Roman Bold.ttf", ATS_FONT_DOWNLOAD_DIR / "Tinos-Bold.ttf"],
        "light": [ATS_SYSTEM_FONT_DIRS[0] / "Times New Roman.ttf", ATS_FONT_DOWNLOAD_DIR / "Tinos-Regular.ttf"],
    },
    "cambria": {
        "regular": [ATS_SYSTEM_FONT_DIRS[0] / "Cambria.ttf", ATS_FONT_DOWNLOAD_DIR / "Caladea-Regular.ttf"],
        "medium": [ATS_SYSTEM_FONT_DIRS[0] / "Cambria.ttf", ATS_FONT_DOWNLOAD_DIR / "Caladea-Regular.ttf"],
        "bold": [ATS_SYSTEM_FONT_DIRS[0] / "Cambria Bold.ttf", ATS_FONT_DOWNLOAD_DIR / "Caladea-Bold.ttf"],
        "light": [ATS_SYSTEM_FONT_DIRS[0] / "Cambria.ttf", ATS_FONT_DOWNLOAD_DIR / "Caladea-Regular.ttf"],
    },
    "montserrat": {
        "regular": [ATS_FONT_DOWNLOAD_DIR / "Montserrat-Regular.ttf", ATS_FONT_DOWNLOAD_DIR / "Montserrat-Variable.ttf"],
        "medium": [ATS_FONT_DOWNLOAD_DIR / "Montserrat-Medium.ttf", ATS_FONT_DOWNLOAD_DIR / "Montserrat-Variable.ttf"],
        "bold": [ATS_FONT_DOWNLOAD_DIR / "Montserrat-Bold.ttf", ATS_FONT_DOWNLOAD_DIR / "Montserrat-Variable.ttf"],
        "light": [ATS_FONT_DOWNLOAD_DIR / "Montserrat-Light.ttf", ATS_FONT_DOWNLOAD_DIR / "Montserrat-Variable.ttf"],
    },
    "lato": {
        "regular": [ATS_FONT_DOWNLOAD_DIR / "Lato-Regular.ttf"],
        "medium": [ATS_FONT_DOWNLOAD_DIR / "Lato-Medium.ttf"],
        "bold": [ATS_FONT_DOWNLOAD_DIR / "Lato-Bold.ttf"],
        "light": [ATS_FONT_DOWNLOAD_DIR / "Lato-Light.ttf"],
    },
    "aptos": {
        "regular": [ATS_FONT_DOWNLOAD_DIR / "Carlito-Regular.ttf"],
        "medium": [ATS_FONT_DOWNLOAD_DIR / "Carlito-Regular.ttf"],
        "bold": [ATS_FONT_DOWNLOAD_DIR / "Carlito-Bold.ttf"],
        "light": [ATS_FONT_DOWNLOAD_DIR / "Carlito-Regular.ttf"],
    },
}

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


def _normalize_font_token(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", (value or "").strip().lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _is_serif_hint(value: str) -> bool:
    token = _normalize_font_token(value)
    if not token:
        return False
    return any(keyword in token for keyword in ("garamond", "georgia", "times", "cambria", "serif"))


def _download_font_if_missing(path: Path) -> Path | None:
    if path.exists():
        return path
    urls = ATS_ONLINE_FONT_SOURCES.get(path.name)
    if not urls:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    for url in urls:
        try:
            with urlopen(url, timeout=12) as response:
                data = response.read()
            if not data:
                continue
            path.write_bytes(data)
            if path.exists():
                return path
        except (URLError, HTTPError, TimeoutError, OSError):
            continue
    return path if path.exists() else None


def _first_available_font_path(candidates: List[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
        downloaded = _download_font_if_missing(candidate)
        if downloaded and downloaded.exists():
            return downloaded
    return None


def _register_ttf_font(internal_name: str, path: Path) -> str | None:
    try:
        if internal_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(internal_name, str(path)))
        return internal_name if internal_name in pdfmetrics.getRegisteredFontNames() else None
    except Exception:
        return None


def _register_ats_space_grotesk_fonts() -> Tuple[str, str, str, str]:
    regular_path = _first_available_font_path(ATS_SPACE_GROTESK_REGULAR_CANDIDATES)
    medium_path = _first_available_font_path(ATS_SPACE_GROTESK_MEDIUM_CANDIDATES)
    bold_path = _first_available_font_path(ATS_SPACE_GROTESK_BOLD_CANDIDATES)
    light_path = _first_available_font_path(ATS_SPACE_GROTESK_LIGHT_CANDIDATES)

    try:
        if regular_path and ATS_SPACE_GROTESK_REGULAR not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(ATS_SPACE_GROTESK_REGULAR, str(regular_path)))
    except Exception:
        pass
    try:
        if medium_path and ATS_SPACE_GROTESK_MEDIUM not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(ATS_SPACE_GROTESK_MEDIUM, str(medium_path)))
    except Exception:
        pass
    try:
        if bold_path and ATS_SPACE_GROTESK_BOLD not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(ATS_SPACE_GROTESK_BOLD, str(bold_path)))
    except Exception:
        pass
    try:
        if light_path and ATS_SPACE_GROTESK_LIGHT not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(ATS_SPACE_GROTESK_LIGHT, str(light_path)))
    except Exception:
        pass

    available = set(pdfmetrics.getRegisteredFontNames())
    if ATS_SPACE_GROTESK_REGULAR in available:
        regular = ATS_SPACE_GROTESK_REGULAR
    elif ATS_SPACE_GROTESK_MEDIUM in available:
        regular = ATS_SPACE_GROTESK_MEDIUM
    else:
        regular = "Helvetica"
    medium = ATS_SPACE_GROTESK_MEDIUM if ATS_SPACE_GROTESK_MEDIUM in available else regular
    if ATS_SPACE_GROTESK_BOLD in available:
        bold = ATS_SPACE_GROTESK_BOLD
    elif medium.startswith("ATSSpaceGrotesk"):
        bold = medium
    else:
        bold = _resolve_bold_font(medium)
    if ATS_SPACE_GROTESK_LIGHT in available:
        light = ATS_SPACE_GROTESK_LIGHT
    elif regular.startswith("ATSSpaceGrotesk"):
        light = regular
    else:
        light = "Helvetica"
    return regular, medium, bold, light


def _resolve_ats_custom_font_set(token: str) -> Tuple[str, str, str, str] | None:
    config = ATS_FONT_FAMILY_CANDIDATES.get(token)
    if config is None:
        return None
    if token == "helvetica":
        return "Helvetica", "Helvetica", "Helvetica-Bold", "Helvetica"
    if token == "spacegrotesk":
        return _register_ats_space_grotesk_fonts()

    default_regular = _resolve_font(ATS_FONT_FALLBACK_MAP.get(token, "Helvetica"))
    default_bold = _resolve_bold_font(default_regular)
    name_seed = re.sub(r"[^A-Za-z0-9]+", "", token.title()) or "ATS"

    regular_path = _first_available_font_path(list(config.get("regular", [])))
    medium_path = _first_available_font_path(list(config.get("medium", [])))
    bold_path = _first_available_font_path(list(config.get("bold", [])))
    light_path = _first_available_font_path(list(config.get("light", [])))

    regular = _register_ttf_font(f"ATS{name_seed}Regular", regular_path) if regular_path else None
    medium = _register_ttf_font(f"ATS{name_seed}Medium", medium_path) if medium_path else None
    bold = _register_ttf_font(f"ATS{name_seed}Bold", bold_path) if bold_path else None
    light = _register_ttf_font(f"ATS{name_seed}Light", light_path) if light_path else None

    resolved_regular = regular or default_regular
    resolved_medium = medium or resolved_regular
    resolved_bold = bold or _resolve_bold_font(resolved_medium)
    resolved_light = light or resolved_regular
    return resolved_regular, resolved_medium, resolved_bold, resolved_light


def _resolve_ats_font_set(theme: Theme) -> Tuple[str, str, str, str]:
    """Use ATS-friendly font stacks with safe PDF-core fallbacks."""
    body_token = _normalize_font_token(theme.body_font or "")
    heading_token = _normalize_font_token(theme.heading_font or "")

    normalized_token = body_token or heading_token
    custom = _resolve_ats_custom_font_set(normalized_token)
    if custom:
        return custom

    preferred_regular = ATS_FONT_FALLBACK_MAP.get(body_token)
    if preferred_regular:
        regular = _resolve_font(preferred_regular)
        bold = _resolve_bold_font(regular)
        return regular, regular, bold, regular

    serif_hint = _is_serif_hint(theme.body_font or "") or _is_serif_hint(theme.heading_font or "")
    stack = ATS_SERIF_FONT_STACK if serif_hint else ATS_SANS_FONT_STACK
    for candidate in stack:
        mapped = ATS_FONT_FALLBACK_MAP.get(_normalize_font_token(candidate))
        if not mapped:
            continue
        regular = _resolve_font(mapped)
        bold = _resolve_bold_font(regular)
        return regular, regular, bold, regular
    return "Helvetica", "Helvetica", "Helvetica-Bold", "Helvetica"


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
        icon_path = _tinted_icon_path(
            icon_key,
            tint_hex,
            alpha_scale=ICON_SECTION_ALPHA_SCALE,
            alpha_gamma=ICON_SECTION_ALPHA_GAMMA,
        ) or _resolve_icon_path(icon_key)
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


def _plain_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _escape_text(value: object) -> str:
    return html.escape(_plain_text(value), quote=False)


def _build_ats_styles(theme: Theme) -> StyleSheet1:
    styles = getSampleStyleSheet()
    ats_body_font, ats_medium_font, ats_bold_font, ats_light_font = _resolve_ats_font_set(theme)
    selected_ats_font = _normalize_font_token(theme.ats_font_family or theme.body_font or "")
    ats_content_font = ats_medium_font if ats_medium_font and ats_medium_font != ats_body_font else ats_body_font
    if selected_ats_font == "spacegrotesk":
        # Keep SpaceGrotesk content at regular weight for better readability.
        ats_content_font = ats_body_font
    body_size = max(9.0, min(float(theme.body_size or 10.0) + 1.0, 12.0))
    heading_size = max(body_size + 2.2, 12.5)
    name_size = max(19.0, heading_size + 5.0)
    accent_hex = _plain_text(theme.accent_color or theme.primary_color or "#111827")
    if accent_hex and not accent_hex.startswith("#"):
        accent_hex = f"#{accent_hex}"
    if not accent_hex or len(accent_hex) not in (4, 7):
        accent_hex = "#111827"
    if not _is_dark_color(accent_hex):
        accent_hex = _mix_hex(accent_hex, "#111827", 0.58)
    section_color = _color_from_hex(accent_hex, colors.HexColor("#1f2937"))
    muted_color = _color_from_hex(_mix_hex(accent_hex, "#ffffff", 0.36), colors.HexColor("#4a596b"))
    contact_color = _color_from_hex(_mix_hex(accent_hex, "#ffffff", 0.38), colors.HexColor("#5f6f81"))
    rule_color = _color_from_hex(_mix_hex(accent_hex, "#ffffff", 0.76), colors.HexColor("#d1d5db"))
    body_color = colors.HexColor("#374b60")

    styles.add(
        ParagraphStyle(
            "ATSBody",
            parent=styles["Normal"],
            fontName=ats_content_font,
            fontSize=body_size,
            leading=body_size * 1.28,
            textColor=body_color,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            "ATSSectionBody",
            parent=styles["ATSBody"],
            leftIndent=0,
            spaceAfter=2.2,
        )
    )
    styles.add(
        ParagraphStyle(
            "ATSBullet",
            parent=styles["ATSBody"],
            fontName=ats_content_font,
            fontSize=body_size,
            leftIndent=max(body_size * 1.1, 11.0),
            firstLineIndent=0,
            leading=body_size * 1.28,
            textColor=body_color,
            spaceAfter=4.0,
            bulletIndent=0,
        )
    )
    styles.add(
        ParagraphStyle(
            "ATSName",
            parent=styles["ATSBody"],
            fontName=ats_bold_font,
            fontSize=name_size,
            leading=name_size * 1.2,
            textColor=section_color,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            "ATSHeadline",
            parent=styles["ATSBody"],
            fontName=ats_medium_font,
            fontSize=max(10.5, heading_size - 0.2),
            leading=max(10.5, heading_size - 0.2) * 1.2,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            "ATSContact",
            parent=styles["ATSBody"],
            fontSize=max(body_size - 0.2, 9.0),
            leading=max(body_size - 0.2, 9.0) * 1.2,
            textColor=contact_color,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            "ATSSection",
            parent=styles["ATSBody"],
            fontName=ats_bold_font,
            fontSize=max(11.0, heading_size - 0.3),
            leading=max(11.0, heading_size - 0.3) * 1.15,
            textColor=section_color,
            spaceBefore=9,
            spaceAfter=3.2,
        )
    )
    styles.add(
        ParagraphStyle(
            "ATSExperienceHeader",
            parent=styles["ATSBody"],
            fontName=ats_bold_font,
            fontSize=max(body_size + 0.25, 10.0),
            leading=max(body_size + 0.25, 10.0) * 1.2,
            textColor=section_color,
            spaceAfter=1.4,
        )
    )
    styles.add(
        ParagraphStyle(
            "ATSMeta",
            parent=styles["ATSBody"],
            fontSize=max(body_size - 0.3, 8.8),
            leading=max(body_size - 0.3, 8.8) * 1.2,
            textColor=muted_color,
            spaceAfter=3,
        )
    )
    styles._ats_font_variants = {
        "regular": ats_content_font,
        "medium": ats_medium_font or ats_content_font,
        "bold": ats_bold_font or ats_content_font,
        "light": ats_light_font or ats_content_font,
    }
    styles._ats_rule_color = rule_color
    styles._ats_emphasis_hex = accent_hex
    return styles


_ATS_HEX_COLOR_PATTERN = re.compile(r"^#?(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def _normalize_hex_for_ats(value: object) -> str | None:
    candidate = _plain_text(value)
    if not candidate:
        return None
    if not _ATS_HEX_COLOR_PATTERN.fullmatch(candidate):
        return None
    if not candidate.startswith("#"):
        candidate = f"#{candidate}"
    if len(candidate) == 4:
        candidate = "#" + "".join(ch * 2 for ch in candidate[1:])
    return candidate.lower()


def _ats_weight_to_font(weight: object, styles: StyleSheet1, fallback_font: str) -> str:
    variants = getattr(styles, "_ats_font_variants", {})
    token = _normalize_font_token(_plain_text(weight))
    if "bold" in token:
        return str(variants.get("bold") or fallback_font)
    if "medium" in token:
        return str(variants.get("medium") or fallback_font)
    if "light" in token:
        return str(variants.get("light") or fallback_font)
    return str(variants.get("regular") or fallback_font)


def _ats_section_style_overrides(
    section: ResumeSection,
    styles: StyleSheet1,
) -> Tuple[ParagraphStyle, ParagraphStyle, ParagraphStyle, ParagraphStyle, ParagraphStyle]:
    default_body = _style_or(styles, "ATSSectionBody", styles["ATSBody"])
    default_title = styles["ATSSection"]
    default_experience_header = styles["ATSExperienceHeader"]
    default_meta = styles["ATSMeta"]
    default_bullet = styles["ATSBullet"]

    if not isinstance(section.meta, dict):
        return default_title, default_body, default_experience_header, default_meta, default_bullet

    raw_style = section.meta.get("_reference_style")
    if not isinstance(raw_style, dict):
        return default_title, default_body, default_experience_header, default_meta, default_bullet

    heading_hex = _normalize_hex_for_ats(raw_style.get("heading_color"))
    body_hex = _normalize_hex_for_ats(raw_style.get("body_color"))

    heading_color = _color_from_hex(heading_hex or "", default_title.textColor)
    adjusted_body_hex = _mix_hex(body_hex, "#ffffff", 0.08) if body_hex else ""
    body_color = _color_from_hex(adjusted_body_hex, default_body.textColor)

    title_font = _ats_weight_to_font(raw_style.get("heading_weight"), styles, default_title.fontName)
    body_font = _ats_weight_to_font(raw_style.get("body_weight"), styles, default_body.fontName)

    title_style = ParagraphStyle(
        "ATSSectionOverrideTitle",
        parent=default_title,
        fontName=title_font,
        textColor=heading_color,
    )
    body_style = ParagraphStyle(
        "ATSSectionOverrideBody",
        parent=default_body,
        fontName=body_font,
        textColor=body_color,
    )
    experience_header_style = ParagraphStyle(
        "ATSSectionOverrideExperienceHeader",
        parent=default_experience_header,
        fontName=title_font,
        textColor=heading_color,
    )
    meta_style = ParagraphStyle(
        "ATSSectionOverrideMeta",
        parent=default_meta,
        fontName=body_font,
        textColor=body_color,
    )
    bullet_style = ParagraphStyle(
        "ATSSectionOverrideBullet",
        parent=default_bullet,
        fontName=body_font,
        textColor=body_color,
    )
    return title_style, body_style, experience_header_style, meta_style, bullet_style


def _ordered_sections_for_ats(document: ResumeDocument) -> List[ResumeSection]:
    sections = [section for section in document.sections if section and _plain_text(section.title or "")]
    indexed = list(enumerate(sections))
    indexed.sort(
        key=lambda item: (
            ATS_SECTION_PRIORITY.get(_plain_text(item[1].title).lower(), 100),
            item[0],
        )
    )
    return [section for _, section in indexed]


def _normalize_ats_contact_value(key: str, raw_value: object) -> str:
    value = _plain_text(raw_value)
    if not value:
        return ""

    lowered_key = key.lower()
    lowered_value = value.lower()
    if lowered_key == "email" and lowered_value.startswith("mailto:"):
        value = value[len("mailto:") :]
    if lowered_key == "linkedin":
        value = re.sub(r"^https?://", "", value, flags=re.IGNORECASE).lstrip("/")
    return value


def _normalize_ats_parser_text(value: object) -> str:
    text = _plain_text(value)
    if not text:
        return ""
    # Normalize punctuation to parser-friendly ASCII forms for broad ATS compatibility.
    text = (
        text.replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2015", "-")
        .replace("\u2212", "-")
        .replace("\u00a0", " ")
    )
    text = re.sub(r"\s*-\s*", " - ", text)
    return re.sub(r"\s+", " ", text).strip()


def _ats_contact_lines(document: ResumeDocument) -> List[str]:
    contact = document.profile.contact or {}
    if not contact:
        return []

    preferred_keys = ("phone", "email", "location", "linkedin", "github", "portfolio", "website")
    label_map = {
        "phone": "Phone",
        "email": "Email",
        "location": "Location",
        "linkedin": "LinkedIn",
        "github": "GitHub",
        "portfolio": "Portfolio",
        "website": "Website",
    }
    parts: List[str] = []
    seen: set[str] = set()

    for key in preferred_keys:
        value = _normalize_ats_contact_value(key, contact.get(key))
        if not value:
            continue
        seen.add(key)
        label = label_map.get(key, key.title())
        parts.append(f"{label}: {value}")

    for key, value in contact.items():
        if key in seen:
            continue
        cleaned = _normalize_ats_contact_value(key, value)
        if not cleaned:
            continue
        parts.append(f"{key.title()}: {cleaned}")

    return parts


def _build_ats_header(document: ResumeDocument, styles: StyleSheet1) -> List:
    flowables: List = []
    name = _plain_text(document.profile.name)
    headline = _plain_text(document.profile.headline)
    contact_lines = _ats_contact_lines(document)

    if name:
        flowables.append(Paragraph(_escape_text(name), styles["ATSName"]))
    if headline:
        flowables.append(Paragraph(_escape_text(headline), styles["ATSHeadline"]))
        flowables.append(Spacer(1, 1.5))
    if contact_lines:
        grouped_contact_lines: List[str] = []
        current_line = ""
        max_line_chars = 88
        for contact_line in contact_lines:
            candidate = contact_line if not current_line else f"{current_line} | {contact_line}"
            if current_line and len(candidate) > max_line_chars:
                grouped_contact_lines.append(current_line)
                current_line = contact_line
            else:
                current_line = candidate
        if current_line:
            grouped_contact_lines.append(current_line)

        for line in grouped_contact_lines:
            line_markup_parts: List[str] = []
            for chunk in line.split(" | "):
                if ":" in chunk:
                    label, value = chunk.split(":", 1)
                    line_markup_parts.append(
                        f"<b>{_escape_text(label)}:</b> {_escape_text(value)}"
                    )
                else:
                    line_markup_parts.append(_escape_text(chunk))
            flowables.append(Paragraph(" | ".join(line_markup_parts), styles["ATSContact"]))
    if flowables:
        header_rule = getattr(styles, "_ats_rule_color", colors.HexColor("#d1d5db"))
        flowables.append(HRFlowable(width="100%", thickness=0.9, color=header_rule))
        flowables.append(Spacer(1, 7))
    return flowables


def _collect_ats_experience_entries(document: ResumeDocument, section: ResumeSection) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    section_meta_entries = section.meta.get("entries", []) if isinstance(section.meta, dict) else []
    for item in section_meta_entries or []:
        if not isinstance(item, dict):
            continue
        role = _normalize_ats_parser_text(item.get("role") or item.get("title"))
        company = _normalize_ats_parser_text(item.get("company"))
        location = _normalize_ats_parser_text(item.get("location"))
        date_range = _normalize_ats_parser_text(item.get("date_range"))
        if not date_range and (item.get("start") or item.get("end")):
            date_range = _normalize_ats_parser_text(
                _format_hackajob_date_range(
                _plain_text(item.get("start")) or None,
                _plain_text(item.get("end")) or None,
            )
            )
        bullets = [_clean_bullet_text(_plain_text(bullet)) for bullet in (item.get("bullets", []) or [])]
        bullets = [_normalize_ats_parser_text(bullet) for bullet in bullets if bullet]
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

    if entries:
        return entries

    for item in document.profile.experience:
        if not isinstance(item, dict):
            continue
        role = _normalize_ats_parser_text(item.get("role") or item.get("title"))
        company = _normalize_ats_parser_text(item.get("company"))
        location = _normalize_ats_parser_text(item.get("location"))
        date_range = _normalize_ats_parser_text(_format_hackajob_date_range(
            _plain_text(item.get("start")) or None,
            _plain_text(item.get("end")) or None,
        ))
        bullets = [_clean_bullet_text(_plain_text(bullet)) for bullet in (item.get("bullets", []) or [])]
        bullets = [_normalize_ats_parser_text(bullet) for bullet in bullets if bullet]
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


def _append_ats_bullets(
    flowables: List,
    bullets: List[object],
    styles: StyleSheet1,
    bullet_style: ParagraphStyle | None = None,
    highlight_terms: List[str] | None = None,
) -> None:
    active_bullet_style = bullet_style or styles["ATSBullet"]
    terms = highlight_terms or []
    for bullet in bullets:
        cleaned = _clean_bullet_text(_plain_text(bullet))
        if not cleaned:
            continue
        highlighted = _format_highlighted_text(cleaned, terms)
        bold_font = _ats_weight_to_font("bold", styles, active_bullet_style.fontName)
        highlighted = highlighted.replace("<b>", f'<font face="{bold_font}">').replace("</b>", "</font>")
        flowables.append(Paragraph(highlighted, active_bullet_style, bulletText="-"))


def _ats_section_elements(document: ResumeDocument, section: ResumeSection, styles: StyleSheet1) -> List:
    flowables: List = []
    section_title_style, body_style, experience_header_style, meta_style, bullet_style = _ats_section_style_overrides(
        section,
        styles,
    )
    highlight_terms = (
        list(section.meta.get("highlight_terms", []))
        if isinstance(section.meta, dict) and isinstance(section.meta.get("highlight_terms"), list)
        else []
    )
    title = _plain_text(section.title)
    if not title:
        return flowables

    flowables.append(Paragraph(_escape_text(title), section_title_style))
    rule_color = getattr(styles, "_ats_rule_color", colors.HexColor("#d1d5db"))
    flowables.append(HRFlowable(width="100%", thickness=0.45, color=rule_color))
    flowables.append(Spacer(1, 5.5))

    title_lower = title.lower()
    if _is_experience_section_title(title_lower):
        entries = _collect_ats_experience_entries(document, section)
        total_entries = len(entries)
        for idx, entry in enumerate(entries):
            entry_flow: List = []
            role_value = _normalize_ats_parser_text(entry.get("role"))
            company_value = _normalize_ats_parser_text(entry.get("company"))
            header_parts: List[str] = []
            if role_value:
                header_parts.append(f"Role: {role_value}")
            if company_value:
                header_parts.append(f"Company: {company_value}")
            header_line = " | ".join(header_parts)
            if header_line:
                entry_flow.append(Paragraph(_escape_text(header_line), experience_header_style))

            location_value = _normalize_ats_parser_text(entry.get("location"))
            timeline_value = _normalize_ats_parser_text(entry.get("date_range"))
            meta_parts: List[str] = []
            if location_value:
                meta_parts.append(f"Location: {location_value}")
            if timeline_value:
                meta_parts.append(f"Timeline: {timeline_value}")
            meta_line = " | ".join(meta_parts)
            if meta_line:
                entry_flow.append(Paragraph(_escape_text(meta_line), meta_style))
            bullet_items = list(entry.get("bullets", []) or [])
            if bullet_items:
                entry_flow.append(Spacer(1, 1.8))
            _append_ats_bullets(entry_flow, bullet_items, styles, bullet_style, highlight_terms)
            if entry_flow:
                flowables.append(KeepTogether(entry_flow))
            if idx < total_entries - 1:
                flowables.append(Spacer(1, 2))
                flowables.append(HRFlowable(width="100%", thickness=0.25, color=rule_color))
            flowables.append(Spacer(1, 4))

        if not entries:
            for paragraph in section.paragraphs:
                cleaned = _plain_text(paragraph)
                if cleaned:
                    flowables.append(Paragraph(_escape_text(cleaned), body_style))
            _append_ats_bullets(flowables, section.bullets, styles, bullet_style, highlight_terms)
            flowables.append(Spacer(1, 5))
        return flowables

    if title_lower in {"skills", "technical skills"}:
        category_lines = section.meta.get("category_lines", []) if isinstance(section.meta, dict) else []
        skill_lines: List[str] = []
        skills_label_bold_font = _ats_weight_to_font("bold", styles, body_style.fontName)
        for line in category_lines or []:
            category = ""
            items: List[str] = []
            if isinstance(line, dict):
                category = _plain_text(line.get("category"))
                raw_items = line.get("items", []) or []
            elif isinstance(line, (list, tuple)) and len(line) == 2:
                category = _plain_text(line[0])
                raw_items = line[1] if isinstance(line[1], (list, tuple)) else []
            else:
                continue
            for item in raw_items:
                clean_item = _plain_text(item)
                if clean_item:
                    items.append(clean_item)
            if category and items:
                skill_lines.append(f"{category}: {', '.join(items)}")

        if skill_lines:
            for line in skill_lines:
                if ":" in line:
                    category, values = line.split(":", 1)
                    category_clean = _plain_text(category)
                    category_lower = category_clean.lower()
                    highlight_hex = getattr(styles, "_ats_emphasis_hex", "#1f2937")
                    if category_lower in ATS_SKILL_LABEL_HIGHLIGHT:
                        category_markup = (
                            f'<font color="{highlight_hex}"><font face="{skills_label_bold_font}">{_escape_text(category_clean)}:</font></font>'
                        )
                    else:
                        category_markup = f"{_escape_text(category_clean)}:"
                    skill_markup = f"{category_markup} {_escape_text(values)}"
                    flowables.append(Paragraph(skill_markup, body_style))
                else:
                    flowables.append(Paragraph(_escape_text(line), body_style))
        else:
            raw_skills = [_plain_text(value) for value in section.bullets if _plain_text(value)]
            if not raw_skills:
                raw_skills = [_plain_text(value) for value in document.profile.skills if _plain_text(value)]
            if raw_skills:
                flowables.append(Paragraph(_escape_text(", ".join(raw_skills)), body_style))
        flowables.append(Spacer(1, 4))
        return flowables

    for paragraph in section.paragraphs:
        cleaned = _plain_text(paragraph)
        if not cleaned:
            continue
        if cleaned.startswith(("•", "■", "-")):
            _append_ats_bullets(flowables, [cleaned], styles, bullet_style, highlight_terms)
        else:
            flowables.append(Paragraph(_escape_text(cleaned), body_style))
    _append_ats_bullets(flowables, section.bullets, styles, bullet_style, highlight_terms)
    flowables.append(Spacer(1, 4))
    return flowables


def render_ats_resume(document: ResumeDocument, output_path: str | Path) -> Path:
    """Render an ATS-optimized plain resume PDF with minimal layout complexity."""
    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    theme = document.theme
    pagesize = (theme.page_width, theme.page_height) if theme.page_width and theme.page_height else A4
    styles = _build_ats_styles(theme)

    doc = SimpleDocTemplate(
        str(dest),
        pagesize=pagesize,
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=32,
    )

    elements: List = []
    elements.extend(_build_ats_header(document, styles))

    rendered_experience = False
    for section in _ordered_sections_for_ats(document):
        title_lower = _plain_text(section.title).lower()
        if _is_experience_section_title(title_lower):
            if rendered_experience:
                continue
            rendered_experience = True
        elements.extend(_ats_section_elements(document, section, styles))

    doc.build(elements)
    return dest


def render_resume(document: ResumeDocument, output_path: str | Path) -> Path:
    """Render the resume document into a PDF."""
    template = (document.theme.template or "").lower()
    if template == "hackajob":
        return render_hackajob_resume(document, output_path)
    if template in ATS_TEMPLATE_NAMES:
        return render_ats_resume(document, output_path)

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
