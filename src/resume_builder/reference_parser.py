from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pdfplumber

from .models import ReferenceStructure, ResumeSection, Theme


@dataclass
class _Line:
    page: int
    top: float
    text: str
    avg_size: float
    dominant_font: str
    dominant_color: str
    is_bullet: bool


def _color_to_hex(color: Iterable[float] | None) -> str:
    if not color:
        return "#000000"
    if isinstance(color, str):
        candidate = color.strip()
        if re.fullmatch(r"#?[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", candidate):
            if not candidate.startswith("#"):
                candidate = f"#{candidate}"
            if len(candidate) == 4:
                candidate = "#" + "".join(ch * 2 for ch in candidate[1:])
            return candidate.lower()
        return "#000000"
    if isinstance(color, (int, float)):
        value = float(color)
        if value <= 1:
            value *= 255
        gray = max(0, min(255, int(round(value))))
        return f"#{gray:02x}{gray:02x}{gray:02x}"
    try:
        values = list(color)
    except TypeError:
        return "#000000"
    if not values:
        return "#000000"
    if len(values) == 1:
        values = values * 3
    if all(isinstance(v, (int, float)) and v <= 1 for v in values[:3]):
        rgb = [max(0, min(255, int(round(float(v) * 255)))) for v in values[:3]]
    else:
        rgb = [max(0, min(255, int(round(float(v))))) for v in values[:3]]
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _hex_to_rgb(value: str) -> Tuple[float, float, float]:
    hex_value = value.lstrip("#")
    if len(hex_value) == 3:
        hex_value = "".join(ch * 2 for ch in hex_value)
    if len(hex_value) != 6:
        return 0.0, 0.0, 0.0
    r = int(hex_value[0:2], 16) / 255.0
    g = int(hex_value[2:4], 16) / 255.0
    b = int(hex_value[4:6], 16) / 255.0
    return r, g, b


def _is_accent_candidate(color_hex: str, primary_hex: str) -> bool:
    if not color_hex or color_hex == "#000000":
        return False
    if color_hex.lower() == (primary_hex or "").lower():
        return False
    red, green, blue = _hex_to_rgb(color_hex)
    span = max(red, green, blue) - min(red, green, blue)
    luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
    if span < 0.08:
        return False
    if luminance < 0.10 or luminance > 0.96:
        return False
    return True


def _infer_theme(
    chars: List[Dict[str, object]],
    page_width: float,
    page_height: float,
    graphic_colors: List[str] | None = None,
) -> Theme:
    if not chars:
        return Theme()

    sizes = [float(ch.get("size", 0)) for ch in chars if float(ch.get("size", 0)) > 0]
    fonts = [ch.get("fontname") or "Helvetica" for ch in chars]
    colors = [ch.get("non_stroking_color") for ch in chars if ch.get("non_stroking_color") is not None]

    body_size = statistics.median_low(sizes) if sizes else 10.0
    heading_size = max(sizes) if sizes else body_size * 1.4

    def _dominant(items: List[str]) -> str:
        counts: Dict[str, int] = {}
        for item in items:
            counts[item] = counts.get(item, 0) + 1
        if not counts:
            return "Helvetica"
        return max(counts, key=counts.get)

    body_font = _dominant([font for font, size in zip(fonts, sizes) if size <= body_size + 0.5]) or "Helvetica"
    heading_font = _dominant([font for font, size in zip(fonts, sizes) if size >= heading_size - 1])
    primary_color = _color_to_hex(colors[0]) if colors else "#000000"
    accent_color = primary_color

    if graphic_colors:
        color_counts: Dict[str, int] = {}
        for color_hex in graphic_colors:
            color_counts[color_hex] = color_counts.get(color_hex, 0) + 1
        ordered_graphic_colors = [color_hex for color_hex, _ in sorted(color_counts.items(), key=lambda item: item[1], reverse=True)]
        for color_hex in ordered_graphic_colors:
            if _is_accent_candidate(color_hex, primary_color):
                accent_color = color_hex
                break

    if accent_color == primary_color and len(colors) > 1:
        fallback_accent = _color_to_hex(colors[1])
        if _is_accent_candidate(fallback_accent, primary_color):
            accent_color = fallback_accent

    template = "hackajob"
    if any("SpaceGroteskLight" in str(font) for font in fonts):
        template = "hackajob"

    return Theme(
        body_font=body_font,
        body_size=round(body_size, 1),
        heading_font=heading_font or f"{body_font}-Bold",
        heading_size=round(max(heading_size, body_size + 2), 1),
        primary_color=primary_color,
        accent_color=accent_color,
        margin_left=page_width * 0.09,
        margin_right=page_width * 0.09,
        margin_top=page_height * 0.1,
        margin_bottom=page_height * 0.08,
        page_width=page_width,
        page_height=page_height,
        template=template,
    )


def _collect_lines(words: List[Dict[str, object]]) -> List[_Line]:
    lines: List[_Line] = []
    grouped: Dict[Tuple[int, int], List[Dict[str, object]]] = {}
    for word in words:
        page = int(word.get("page_number", 1)) - 1
        top = float(word.get("top", 0))
        key = (page, int(round(top / 4.0)))
        grouped.setdefault(key, []).append(word)

    for (page, _), group in sorted(grouped.items(), key=lambda item: (item[0][0], min(word.get("top", 0) for word in item[1]))):
        group_sorted = sorted(group, key=lambda w: w.get("x0", 0))
        text = " ".join(w.get("text", "") for w in group_sorted).strip()
        if not text:
            continue
        sizes = [float(w.get("size", 0)) for w in group_sorted if float(w.get("size", 0)) > 0]
        avg_size = sum(sizes) / len(sizes) if sizes else 10.0
        fonts = [w.get("fontname") or "Helvetica" for w in group_sorted]
        colors = [w.get("non_stroking_color") for w in group_sorted if w.get("non_stroking_color") is not None]
        dominant_font = max(set(fonts), key=fonts.count)
        dominant_color = _color_to_hex(colors[0]) if colors else "#000000"
        first_word = group_sorted[0]
        is_bullet = first_word.get("text", "").startswith(("-", "■", "·"))
        lines.append(
            _Line(
                page=page,
                top=float(min(w.get("top", 0) for w in group_sorted)),
                text=text,
                avg_size=avg_size,
                dominant_font=dominant_font,
                dominant_color=dominant_color,
                is_bullet=is_bullet,
            )
        )
    return lines


def _is_heading(line: _Line, body_size: float) -> bool:
    if line.avg_size >= body_size + 2:
        return True
    normalized = line.text.replace(":", "").strip()
    if not normalized:
        return False
    alpha_chars = [c for c in normalized if c.isalpha()]
    if alpha_chars and sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars) > 0.6:
        return True
    return False


def extract_reference_structure(reference_pdf: str | Path) -> ReferenceStructure:
    """Parse the reference resume PDF to infer theme and high-level sections."""
    ref_path = Path(reference_pdf)
    if not ref_path.exists():
        raise FileNotFoundError(f"Reference resume not found: {ref_path}")

    with pdfplumber.open(ref_path) as pdf:
        all_chars: List[Dict[str, object]] = []
        all_words: List[Dict[str, object]] = []
        graphic_colors: List[str] = []
        for page_index, page in enumerate(pdf.pages):
            for char in page.chars:
                char = dict(char)
                char["page_number"] = page_index + 1
                all_chars.append(char)
            words = page.extract_words(
                use_text_flow=True,
                extra_attrs=["size", "fontname", "non_stroking_color"],
            )
            for word in words:
                word["page_number"] = page_index + 1
            all_words.extend(words)

            for shape in page.rects + page.curves + page.lines:
                fill_hex = _color_to_hex(shape.get("non_stroking_color"))
                stroke_hex = _color_to_hex(shape.get("stroking_color"))
                if fill_hex != "#000000":
                    graphic_colors.append(fill_hex)
                if stroke_hex != "#000000":
                    graphic_colors.append(stroke_hex)

        theme = _infer_theme(
            all_chars,
            pdf.pages[0].width if pdf.pages else 595.0,
            pdf.pages[0].height if pdf.pages else 842.0,
            graphic_colors=graphic_colors,
        )

    lines = _collect_lines(all_words)
    sections: List[ResumeSection] = []
    current_section: ResumeSection | None = None
    for line in lines:
        if _is_heading(line, theme.body_size):
            if current_section:
                sections.append(current_section)
            current_section = ResumeSection(title=line.text.title())
            continue
        if not current_section:
            current_section = ResumeSection(title="Summary")
        if line.is_bullet:
            current_section.bullets.append(line.text.lstrip("-■· ").strip())
        else:
            current_section.paragraphs.append(line.text)

    if current_section:
        sections.append(current_section)

    return ReferenceStructure(theme=theme, sections=sections)
