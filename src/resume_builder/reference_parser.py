from __future__ import annotations

import math
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
    values = list(color)
    if not values:
        return "#000000"
    if len(values) == 1:
        values = values * 3
    if all(v <= 1 for v in values):
        rgb = [max(0, min(255, int(round(v * 255)))) for v in values[:3]]
    else:
        rgb = [max(0, min(255, int(round(v)))) for v in values[:3]]
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _infer_theme(chars: List[Dict[str, object]], page_width: float, page_height: float) -> Theme:
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
    accent_color = _color_to_hex(colors[1]) if len(colors) > 1 else primary_color

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
        is_bullet = first_word.get("text", "").startswith(("-", "•", "·"))
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

        theme = _infer_theme(
            all_chars,
            pdf.pages[0].width if pdf.pages else 595.0,
            pdf.pages[0].height if pdf.pages else 842.0,
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
            current_section.bullets.append(line.text.lstrip("-•· ").strip())
        else:
            current_section.paragraphs.append(line.text)

    if current_section:
        sections.append(current_section)

    return ReferenceStructure(theme=theme, sections=sections)
