import pytest

from resume_builder.hackajob_renderer import (
    _HackajobRenderer,
    _education_entries,
    _fallback_font_pair,
    _flatten_skills,
    _header_companies,
    _normalize_company_key,
    _resolve_hackajob_font_token,
    _skill_category_lines,
)
from resume_builder.models import ResumeDocument, ResumeProfile, ResumeSection, Theme


def test_header_companies_uses_profile_experience_in_order():
    document = ResumeDocument(
        profile=ResumeProfile(
            name="Candidate",
            experience=[
                {"company": "Elocity Technologies"},
                {"company": "Peepal Consulting"},
                {"company": "Talent Flake Pvt. Ltd"},
                {"company": "Elocity"},
            ],
        ),
        sections=[],
        theme=Theme(template="hackajob"),
    )

    assert _header_companies(document) == [
        "Elocity Technologies",
        "Peepal Consulting",
        "Talent Flake Pvt. Ltd",
    ]


def test_header_companies_falls_back_to_experience_section_meta():
    document = ResumeDocument(
        profile=ResumeProfile(name="Candidate", experience=[]),
        sections=[
            ResumeSection(
                title="Experience",
                meta={
                    "entries": [
                        {"company": "Oracle"},
                        {"company": "Xactly"},
                    ]
                },
            )
        ],
        theme=Theme(template="hackajob"),
    )

    assert _header_companies(document) == ["Oracle", "Xactly"]


def test_hackajob_font_token_uses_selected_font_when_non_default():
    theme = Theme(template="hackajob", body_font="SpaceGrotesk-Regular", ats_font_family="Lato")
    assert _resolve_hackajob_font_token(theme) == "lato"


def test_hackajob_font_token_keeps_reference_family_for_default_ats_font():
    theme = Theme(template="hackajob", body_font="SpaceGrotesk-Regular", ats_font_family="Calibri")
    assert _resolve_hackajob_font_token(theme) == "spacegrotesk"


def test_hackajob_font_token_uses_calibri_when_reference_font_is_not_supported():
    theme = Theme(template="hackajob", body_font="UnknownFont", ats_font_family="Calibri")
    assert _resolve_hackajob_font_token(theme) == "calibri"


def test_hackajob_font_fallback_pair_is_serif_for_serif_fonts():
    assert _fallback_font_pair("times new roman") == ("Times-Roman", "Times-Bold")


def test_normalize_company_key_handles_common_variant_formats():
    assert _normalize_company_key("Xactly Corporation") == "xactly"
    assert _normalize_company_key("Nineleaps Technology Solutions") == "nineleaps"
    assert _normalize_company_key("PricewaterhouseCoopers") == "pwc"
    assert _normalize_company_key("Talent Flake Private Limited") == "talentflake"
    assert _normalize_company_key("Thrymr Software Pvt. Ltd.") == "thrymr"


def test_hackajob_renderer_applies_theme_font_sizes(tmp_path):
    document = ResumeDocument(
        profile=ResumeProfile(name="Candidate"),
        sections=[],
        theme=Theme(template="hackajob", body_size=12.5, heading_size=16.0),
    )

    renderer = _HackajobRenderer(document, tmp_path / "resume.pdf")

    assert renderer.body_style.fontSize == pytest.approx(12.5)
    assert renderer.experience_bullet_style.fontSize == pytest.approx(12.5)
    assert renderer.section_title_style.fontSize == pytest.approx(16.0)
    assert renderer.company_style.fontSize == pytest.approx(16.0)


def test_hackajob_education_uses_explicit_year_and_grade_from_profile():
    document = ResumeDocument(
        profile=ResumeProfile(
            name="Candidate",
            education=[
                {
                    "institution": "Rajiv Gandhi University of Knowledge Technologies",
                    "degree": "B.Tech in Mechanical Engineering",
                    "location": "R.K. Valley, Andhra Pradesh",
                    "year": "2010-2014",
                    "grade": "8.4 CGPA",
                }
            ],
        ),
        sections=[],
        theme=Theme(template="hackajob"),
    )

    records = _education_entries(document)

    assert len(records) == 1
    assert records[0].institution == "Rajiv Gandhi University of Knowledge Technologies"
    assert records[0].degree == "B.Tech in Mechanical Engineering"
    assert "2010-2014" in records[0].location_year
    assert "8.4 CGPA" in records[0].location_year


def test_hackajob_education_fallback_parses_single_pipe_line():
    document = ResumeDocument(
        profile=ResumeProfile(name="Candidate", education=[]),
        sections=[
            ResumeSection(
                title="Education",
                paragraphs=[
                    "Rajiv Gandhi University of Knowledge Technologies | B.Tech in Mechanical Engineering | "
                    "R.K. Valley, Andhra Pradesh | 2010-2014 | 8.4 CGPA"
                ],
            )
        ],
        theme=Theme(template="hackajob"),
    )

    records = _education_entries(document)

    assert len(records) == 1
    assert records[0].institution == "Rajiv Gandhi University of Knowledge Technologies"
    assert records[0].degree == "B.Tech in Mechanical Engineering"
    assert "2010-2014" in records[0].location_year
    assert "8.4 CGPA" in records[0].location_year


def test_skill_category_lines_prefers_section_bullets_over_fallback_profile_skills():
    section = ResumeSection(title="Technical Skills", bullets=["React.js", "TypeScript"])
    lines = _skill_category_lines(section, ["Python", "AWS"])
    assert lines == [("Additional Skills", ["React.js", "TypeScript"])]


def test_flatten_skills_does_not_merge_fallback_when_section_has_skills():
    section = ResumeSection(title="Technical Skills", bullets=["React.js", "TypeScript"])
    flattened = _flatten_skills(section, ["Python", "AWS"])
    assert flattened == ["React.js", "TypeScript"]
