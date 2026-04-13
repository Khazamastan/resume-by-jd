from pathlib import Path

from pypdf import PdfReader

from resume_builder.models import ResumeDocument, ResumeProfile, ResumeSection, Theme
from resume_builder.pdf_generator import _ats_section_style_overrides, _build_ats_styles, _format_highlighted_text, _ats_weight_to_font, render_resume


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


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
    assert "Email: jane@example.com" in text
    assert "LinkedIn: linkedin.com/in/janedoe" in text
    assert "Role: Senior Frontend Engineer | Company: Example Corp" in text
    assert "Location: Remote | Timeline: Jan 2022 - Present" in text
    assert "Built scalable UI systems for enterprise workflows." in text
    assert "Skills" in text
    assert "Core: React, TypeScript, Accessibility" in text


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


def test_ats_bullet_highlight_uses_bold_font_face_markup():
    styles = _build_ats_styles(Theme(template="ats", body_font="Lato", heading_font="Lato-Bold", ats_font_family="Lato"))
    source = "Improved CI/CD velocity by 30% using React and Jest."
    highlighted = _format_highlighted_text(source, ["React", "Jest"])
    bold_font = _ats_weight_to_font("bold", styles, styles["ATSBullet"].fontName)
    highlighted = highlighted.replace("<b>", f'<font face="{bold_font}">').replace("</b>", "</font>")

    assert f'<font face="{bold_font}">' in highlighted
    assert "React" in highlighted
    assert "Jest" in highlighted
