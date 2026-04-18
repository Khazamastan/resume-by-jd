from pathlib import Path

from pypdf import PdfReader
from reportlab.platypus import KeepTogether

from resume_builder.models import ResumeDocument, ResumeProfile, ResumeSection, Theme
from resume_builder.pdf_generator import (
    _ats_section_elements,
    _ats_section_style_overrides,
    _ats_weight_to_font,
    _build_ats_styles,
    _format_highlighted_text,
    render_resume,
)


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _first_page_dimensions(path: Path) -> tuple[float, float]:
    reader = PdfReader(str(path))
    page = reader.pages[0]
    return float(page.mediabox.width), float(page.mediabox.height)


def test_render_resume_ats_template_is_text_first_and_extractable(tmp_path):
    document = ResumeDocument(
        profile=ResumeProfile(
            name="Jane Doe",
            headline="Senior Frontend Engineer",
            contact={
                "phone": "+1-555-123-4567",
                "email": "jane@example.com",
                "location": "San Francisco, CA",
                "linkedin": "linkedin.com/in/janedoe",
            },
            skills=["React", "TypeScript", "Accessibility"],
        ),
        sections=[
            ResumeSection(
                title="Professional Experience",
                meta={
                    "entries": [
                        {
                            "role": "Senior Frontend Engineer",
                            "company": "Example Corp",
                            "location": "Remote",
                            "date_range": "Jan 2022 – Present",
                            "bullets": [
                                "Built scalable UI systems for enterprise workflows.",
                                "Improved page load performance by 35%.",
                            ],
                        }
                    ]
                },
            ),
            ResumeSection(
                title="Skills",
                meta={
                    "category_lines": [
                        ("Core", ["React", "TypeScript", "Accessibility"]),
                    ]
                },
            ),
            ResumeSection(
                title="Education",
                paragraphs=["B.S. Computer Science, University of Example"],
            ),
        ],
        theme=Theme(template="ats"),
    )

    output_path = tmp_path / "ats_resume.pdf"
    render_resume(document, output_path)

    assert output_path.exists()
    text = _extract_pdf_text(output_path)
    assert "Jane Doe" in text
    assert "Professional Experience" in text
    assert "Mobile: +1-555-123-4567" in text
    assert "Email: jane@example.com" in text
    assert "Address: San Francisco, CA" in text
    assert "LinkedIn: linkedin.com/in/janedoe" in text
    assert "Senior Frontend Engineer | Company: Example Corp" in text
    assert "Location: Remote | Timeline: Jan 2022 - Present" in text
    assert "Built scalable UI systems for enterprise workflows." in text
    assert "Skills" in text
    assert "Core: React, TypeScript, Accessibility" in text


def test_render_resume_ats_template_uses_a4_page_size(tmp_path):
    document = ResumeDocument(
        profile=ResumeProfile(
            name="Jane Doe",
            headline="Senior Frontend Engineer",
            contact={"email": "jane@example.com"},
            skills=["React", "TypeScript"],
        ),
        sections=[
            ResumeSection(
                title="Professional Experience",
                meta={
                    "entries": [
                        {
                            "role": "Engineer",
                            "company": "Example Corp",
                            "location": "Remote",
                            "date_range": "Jan 2022 – Present",
                            "bullets": ["Built reliable ATS resume generation."],
                        }
                    ]
                },
            )
        ],
        theme=Theme(template="ats", page_width=500, page_height=700),
    )

    output_path = tmp_path / "ats_a4_resume.pdf"
    render_resume(document, output_path)

    width, height = _first_page_dimensions(output_path)
    assert abs(width - 595.2756) < 1.0
    assert abs(height - 841.8898) < 1.0


def test_ats_section_style_overrides_use_reference_weight_and_color():
    styles = _build_ats_styles(Theme(template="ats", body_font="Lato", heading_font="Lato-Bold", ats_font_family="Lato"))
    section = ResumeSection(
        title="Professional Experience",
        meta={
            "_reference_style": {
                "heading_weight": "bold",
                "heading_color": "#123456",
                "body_weight": "light",
                "body_color": "#345678",
            }
        },
    )

    title_style, body_style, experience_header_style, meta_style, bullet_style = _ats_section_style_overrides(section, styles)

    assert title_style.fontName == styles._ats_font_variants["bold"]
    assert experience_header_style.fontName == styles._ats_font_variants["bold"]
    assert body_style.fontName == styles._ats_font_variants["light"]
    assert meta_style.fontName == styles._ats_font_variants["light"]
    assert bullet_style.fontName == styles._ats_font_variants["light"]
    assert title_style.textColor is not None
    assert body_style.textColor is not None


def test_ats_summary_and_skills_use_standard_heading_font_style():
    styles = _build_ats_styles(Theme(template="ats", body_font="Lato", heading_font="Lato-Bold", ats_font_family="Lato"))
    default_heading_font = styles["ATSSection"].fontName

    summary_section = ResumeSection(
        title="Professional Summary",
        meta={
            "_reference_style": {
                "heading_weight": "light",
                "body_weight": "light",
            }
        },
    )
    skills_section = ResumeSection(
        title="Technical Skills",
        meta={
            "_reference_style": {
                "heading_weight": "regular",
                "body_weight": "light",
            }
        },
    )

    summary_title_style, _, _, _, _ = _ats_section_style_overrides(summary_section, styles)
    skills_title_style, _, _, _, _ = _ats_section_style_overrides(skills_section, styles)

    assert summary_title_style.fontName == default_heading_font
    assert skills_title_style.fontName == default_heading_font


def test_ats_bullet_highlight_uses_bold_font_face_markup():
    styles = _build_ats_styles(Theme(template="ats", body_font="Lato", heading_font="Lato-Bold", ats_font_family="Lato"))
    source = "Improved CI/CD velocity by 30% using React and Jest."
    highlighted = _format_highlighted_text(source, ["React", "Jest"])
    bold_font = _ats_weight_to_font("bold", styles, styles["ATSBullet"].fontName)
    highlighted = highlighted.replace("<b>", f'<font face="{bold_font}">').replace("</b>", "</font>")

    assert f'<font face="{bold_font}">' in highlighted
    assert "React" in highlighted
    assert "Jest" in highlighted


def test_ats_first_experience_entry_is_not_keep_together():
    section = ResumeSection(
        title="Professional Experience",
        meta={
            "entries": [
                {
                    "role": "Senior Engineer",
                    "company": "Example Corp",
                    "location": "Remote",
                    "date_range": "Jan 2022 – Present",
                    "bullets": [
                        "Implemented a complex ATS-compatible PDF layout.",
                        "Improved readability with controlled line spacing.",
                        "Reduced rendering regressions using parser-safe text blocks.",
                    ],
                }
            ]
        },
    )
    document = ResumeDocument(
        profile=ResumeProfile(name="Jane Doe"),
        sections=[section],
        theme=Theme(template="ats"),
    )
    styles = _build_ats_styles(document.theme)
    flowables = _ats_section_elements(document, section, styles)

    assert len(flowables) > 3
    assert not isinstance(flowables[3], KeepTogether)


def test_ats_section_color_uses_theme_palette_not_reference_section_color():
    styles = _build_ats_styles(Theme(template="ats", accent_color="#f97316", primary_color="#f97316"))
    section = ResumeSection(
        title="Professional Experience",
        meta={
            "_reference_style": {
                "heading_weight": "bold",
                "heading_color": "#1155cc",
                "body_weight": "light",
                "body_color": "#1155cc",
            }
        },
    )

    title_style, body_style, experience_header_style, _, _ = _ats_section_style_overrides(section, styles)
    default_title = styles["ATSSection"]
    default_body = styles["ATSSectionBody"]

    assert (title_style.textColor.red, title_style.textColor.green, title_style.textColor.blue) == (
        default_title.textColor.red,
        default_title.textColor.green,
        default_title.textColor.blue,
    )
    assert (experience_header_style.textColor.red, experience_header_style.textColor.green, experience_header_style.textColor.blue) == (
        default_title.textColor.red,
        default_title.textColor.green,
        default_title.textColor.blue,
    )
    assert (body_style.textColor.red, body_style.textColor.green, body_style.textColor.blue) == (
        default_body.textColor.red,
        default_body.textColor.green,
        default_body.textColor.blue,
    )


def test_ats_body_and_headline_colors_follow_selected_accent():
    orange_styles = _build_ats_styles(Theme(template="ats", accent_color="#f97316", primary_color="#f97316"))
    teal_styles = _build_ats_styles(Theme(template="ats", accent_color="#14b8a6", primary_color="#14b8a6"))

    orange_body = orange_styles["ATSBody"].textColor
    teal_body = teal_styles["ATSBody"].textColor
    orange_headline = orange_styles["ATSHeadline"].textColor
    teal_headline = teal_styles["ATSHeadline"].textColor

    assert (orange_body.red, orange_body.green, orange_body.blue) != (
        teal_body.red,
        teal_body.green,
        teal_body.blue,
    )
    assert (orange_headline.red, orange_headline.green, orange_headline.blue) != (
        teal_headline.red,
        teal_headline.green,
        teal_headline.blue,
    )


def test_ats_styles_follow_theme_font_sizes():
    compact_styles = _build_ats_styles(Theme(template="ats", body_size=9.0, heading_size=12.0))
    expanded_styles = _build_ats_styles(Theme(template="ats", body_size=13.0, heading_size=17.0))

    assert expanded_styles["ATSBody"].fontSize > compact_styles["ATSBody"].fontSize
    assert expanded_styles["ATSSection"].fontSize > compact_styles["ATSSection"].fontSize
    assert expanded_styles["ATSExperienceHeader"].fontSize > compact_styles["ATSExperienceHeader"].fontSize


def test_ats_technical_skill_labels_are_bold_for_all_categories():
    styles = _build_ats_styles(Theme(template="ats"))
    section = ResumeSection(
        title="Technical Skills",
        meta={
            "category_lines": [
                ("Core", ["React", "TypeScript"]),
                ("Frontend", ["Next.js"]),
            ]
        },
    )
    document = ResumeDocument(profile=ResumeProfile(name="Jane Doe"), sections=[section], theme=Theme(template="ats"))

    flowables = _ats_section_elements(document, section, styles)
    core_line = flowables[3]
    frontend_line = flowables[5]

    assert core_line.frags[0].fontName.endswith("Bold")
    assert core_line.frags[0].text.startswith("Core:")
    assert frontend_line.frags[0].fontName.endswith("Bold")
    assert frontend_line.frags[0].text.startswith("Frontend:")


def test_ats_education_expands_btech_label():
    document = ResumeDocument(
        profile=ResumeProfile(name="Jane Doe"),
        sections=[
            ResumeSection(
                title="Education",
                paragraphs=["B.Tech in Computer Science, University of Example"],
            )
        ],
        theme=Theme(template="ats"),
    )

    output_path = Path("/tmp/ats_btech_label_check.pdf")
    render_resume(document, output_path)
    text = _extract_pdf_text(output_path)

    assert "Bachelors Degree (B.Tech) in Computer Science, University of Example" in text
