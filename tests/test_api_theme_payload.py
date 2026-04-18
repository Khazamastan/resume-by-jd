import pytest

from resume_builder import api as api_module
from resume_builder.models import ResumeProfile, ResumeSection, Theme
from resume_builder.resume_text_parser import parse_resume_text


def test_theme_from_payload_preserves_existing_values_when_partial_theme_is_sent():
    base_theme = Theme(
        body_font="Garamond",
        heading_font="Garamond-Bold",
        primary_color="#123456",
        accent_color="#123456",
        ats_font_family="Calibri",
    )

    updated = api_module._theme_from_payload({"accent_color": "#f97316"}, base_theme)

    assert updated.accent_color == "#f97316"
    assert updated.primary_color == "#123456"
    assert updated.body_font == "Garamond"
    assert updated.heading_font == "Garamond-Bold"


def test_theme_from_payload_normalizes_hex_without_hash():
    updated = api_module._theme_from_payload({"primary_color": "14b8a6", "accent_color": "14b8a6"})
    assert updated.primary_color == "#14b8a6"
    assert updated.accent_color == "#14b8a6"


def test_theme_from_payload_normalizes_ats_font_family_aliases():
    updated = api_module._theme_from_payload({"ats_font_family": "space grotesk"})
    assert updated.ats_font_family == "SpaceGrotesk"


def test_theme_from_payload_updates_font_sizes():
    base_theme = Theme(body_size=10.0, heading_size=12.0)
    updated = api_module._theme_from_payload({"body_size": 9.5, "heading_size": 13}, base_theme)
    assert updated.body_size == 9.5
    assert updated.heading_size == 13.0


def test_build_ats_theme_preserves_selected_font_sizes():
    base_theme = Theme(
        body_size=11.5,
        heading_size=15.0,
        primary_color="#123456",
        accent_color="#14b8a6",
        ats_font_family="Lato",
    )

    ats_theme = api_module._build_ats_theme(base_theme)

    assert ats_theme.template == "ats"
    assert ats_theme.body_size == 11.5
    assert ats_theme.heading_size == 15.0
    assert ats_theme.body_font == "Lato"
    assert ats_theme.heading_font == "Lato-Bold"


def test_theme_from_payload_rejects_out_of_range_font_sizes():
    with pytest.raises(ValueError):
        api_module._theme_from_payload({"body_size": 5})

    with pytest.raises(ValueError):
        api_module._theme_from_payload({"heading_size": 25})


def test_theme_from_payload_rejects_invalid_hex():
    with pytest.raises(ValueError):
        api_module._theme_from_payload({"accent_color": "not-a-color"})


def test_resume_text_parse_stays_stable_for_edit_modal_override_flow():
    raw_resume = """
Khajamastan Bellamkonda
Mobile: +91-7207810602 | Email: khazamastan@gmail.com | Location: Pune, India

Professional Summary
Lead Software Developer with 10+ years of experience.

Professional Experience
Company: Oracle | Principal Member Technical Staff
Location: Bangalore | April 2022 - Present
Mentored 5+ mid-level developers.
Automated canary health checks every 15 minutes.
"""
    profile, sections = parse_resume_text(raw_resume)

    assert profile.name == "Khajamastan Bellamkonda"
    assert profile.headline == "Principal Member Technical Staff at Oracle"

    experience_section = next(section for section in sections if section.title == "Professional Experience")
    entries = experience_section.meta.get("entries", [])

    assert entries
    assert entries[0]["company"] == "Oracle"
    assert entries[0]["role"] == "Principal Member Technical Staff"
    assert any("Mentored 5+ mid-level developers." in bullet for bullet in entries[0]["bullets"])


def test_fill_missing_contact_from_profile_uses_fallback_without_overriding_existing_values():
    parsed_profile = ResumeProfile(
        name="Khajamastan Bellamkonda",
        contact={
            "email": "khazamastan@gmail.com",
        },
    )
    fallback_profile = ResumeProfile(
        name="Khajamastan Bellamkonda",
        contact={
            "phone": "+91-7207810602",
            "email": "legacy@example.com",
            "location": "Bangalore, India",
            "linkedin": "https://www.linkedin.com/in/khazamastan",
            "notice_note": "Serving Notice Period - Available to Join: May 5, 2026",
        },
    )

    api_module._fill_missing_contact_from_profile(parsed_profile, fallback_profile)

    assert parsed_profile.contact["email"] == "khazamastan@gmail.com"
    assert parsed_profile.contact["phone"] == "+91-7207810602"
    assert parsed_profile.contact["location"] == "Bangalore, India"
    assert parsed_profile.contact["linkedin"] == "https://www.linkedin.com/in/khazamastan"
    assert parsed_profile.contact["notice_note"] == "Serving Notice Period - Available to Join: May 5, 2026"


def test_fill_missing_contact_from_profile_supports_alias_fields():
    parsed_profile = ResumeProfile(name="Candidate", contact={})
    fallback_profile = ResumeProfile(
        name="Candidate",
        contact={
            "mobile": "+1-111-111-1111",
            "notice": "Available to Join: May 5, 2026",
        },
    )

    api_module._fill_missing_contact_from_profile(parsed_profile, fallback_profile)

    assert parsed_profile.contact["phone"] == "+1-111-111-1111"
    assert parsed_profile.contact["notice_note"] == "Available to Join: May 5, 2026"


def test_fill_missing_headline_from_profile_backfills_when_missing():
    parsed_profile = ResumeProfile(name="Candidate", headline=None)
    fallback_profile = ResumeProfile(name="Candidate", headline="Principal Member Technical Staff")

    api_module._fill_missing_headline_from_profile(parsed_profile, fallback_profile)

    assert parsed_profile.headline == "Principal Member Technical Staff"


def test_normalize_headline_order_swaps_company_role_when_reversed():
    profile = ResumeProfile(
        name="Candidate",
        experience=[{"company": "Oracle", "role": "Principal Member Technical Staff"}],
    )

    normalized = api_module._normalize_headline_order(
        "Oracle at Principal Member Technical Staff",
        profile,
    )

    assert normalized == "Principal Member Technical Staff at Oracle"


def test_normalize_headline_order_keeps_role_company_when_already_correct():
    profile = ResumeProfile(
        name="Candidate",
        experience=[{"company": "Oracle", "role": "Principal Member Technical Staff"}],
    )

    normalized = api_module._normalize_headline_order(
        "Principal Member Technical Staff at Oracle",
        profile,
    )

    assert normalized == "Principal Member Technical Staff at Oracle"


def test_normalize_headline_order_uses_generic_company_and_role_hints():
    normalized = api_module._normalize_headline_order(
        "Xactly Corp at Senior Software Developer",
        None,
    )

    assert normalized == "Senior Software Developer at Xactly Corp"


def test_normalize_headline_order_swaps_for_unknown_company_name_when_role_is_clear():
    normalized = api_module._normalize_headline_order(
        "Teradata at Senior Software Engineer",
        None,
    )

    assert normalized == "Senior Software Engineer at Teradata"


def test_fill_missing_headline_from_profile_uses_fallback_experience_when_needed():
    parsed_profile = ResumeProfile(name="Candidate", headline=None)
    fallback_profile = ResumeProfile(
        name="Candidate",
        headline=None,
        experience=[
            {"company": "Oracle", "role": "Principal Member Technical Staff"},
        ],
    )

    api_module._fill_missing_headline_from_profile(parsed_profile, fallback_profile)

    assert parsed_profile.headline == "Principal Member Technical Staff at Oracle"


def test_fill_missing_headline_from_profile_preserves_existing_value():
    parsed_profile = ResumeProfile(name="Candidate", headline="Lead Engineer")
    fallback_profile = ResumeProfile(name="Candidate", headline="Principal Member Technical Staff")

    api_module._fill_missing_headline_from_profile(parsed_profile, fallback_profile)

    assert parsed_profile.headline == "Lead Engineer"


def test_apply_profile_update_normalizes_reversed_headline():
    profile = ResumeProfile(
        name="Candidate",
        experience=[{"company": "Oracle", "role": "Principal Member Technical Staff"}],
    )
    update = api_module.ProfileUpdate(headline="Oracle at Principal Member Technical Staff")

    api_module._apply_profile_update(profile, update)

    assert profile.headline == "Principal Member Technical Staff at Oracle"


def test_backfill_missing_awards_from_profile_adds_awards_when_resume_text_omits_them():
    parsed_profile = ResumeProfile(name="Candidate")
    parsed_sections = [ResumeSection(title="Professional Summary", paragraphs=["Experienced engineer."])]
    fallback_profile = ResumeProfile(
        name="Candidate",
        additional_sections=[
            ResumeSection(
                title="Awards",
                bullets=["Spot Award for Best Performance."],
            )
        ],
    )

    api_module._backfill_missing_awards_from_profile(parsed_profile, parsed_sections, fallback_profile)

    awards_section = next(section for section in parsed_sections if section.title == "Awards")
    assert awards_section.bullets == ["Spot Award for Best Performance."]
    assert parsed_profile.additional_sections
    assert parsed_profile.additional_sections[0].title == "Awards"
    assert parsed_profile.additional_sections[0].bullets == ["Spot Award for Best Performance."]


def test_backfill_missing_awards_from_profile_does_not_override_existing_awards():
    parsed_profile = ResumeProfile(name="Candidate")
    parsed_sections = [
        ResumeSection(title="Awards", bullets=["Text-provided award."]),
    ]
    fallback_profile = ResumeProfile(
        name="Candidate",
        additional_sections=[
            ResumeSection(
                title="Awards",
                bullets=["Profile award."],
            )
        ],
    )

    api_module._backfill_missing_awards_from_profile(parsed_profile, parsed_sections, fallback_profile)

    awards_section = next(section for section in parsed_sections if section.title == "Awards")
    assert awards_section.bullets == ["Text-provided award."]


def test_backfill_missing_core_sections_from_profile_populates_missing_sections():
    parsed_profile = ResumeProfile(name="Candidate")
    parsed_sections: list[ResumeSection] = []
    fallback_profile = ResumeProfile(
        name="Candidate",
        summary=["Experienced engineer building scalable products."],
        skills=["React.js", "TypeScript", "Node.js"],
        experience=[
            {
                "role": "Senior Software Engineer",
                "company": "Example Corp",
                "location": "Bangalore, India",
                "start": "2022-04-01",
                "end": "Present",
                "bullets": ["Built high-throughput APIs."],
            }
        ],
        education=[
            {
                "degree": "B.Tech in Computer Science",
                "institution": "Example University",
                "location": "India",
                "start": "2010-08-01",
                "end": "2014-05-01",
            }
        ],
        additional_sections=[
            ResumeSection(title="Awards", bullets=["Engineering Excellence Award."]),
        ],
    )

    api_module._backfill_missing_core_sections_from_profile(parsed_profile, parsed_sections, fallback_profile)

    titles = [section.title for section in parsed_sections]
    assert "Professional Summary" in titles
    assert "Technical Skills" in titles
    assert "Professional Experience" in titles
    assert "Education" in titles
    assert "Awards" in titles

    assert parsed_profile.summary == ["Experienced engineer building scalable products."]
    assert parsed_profile.skills == ["React.js", "TypeScript", "Node.js"]
    assert parsed_profile.experience
    assert parsed_profile.experience[0]["role"] == "Senior Software Engineer"
    assert parsed_profile.education
    assert parsed_profile.education[0]["institution"] == "Example University"
    assert parsed_profile.headline == "Senior Software Engineer at Example Corp"

    experience_section = next(section for section in parsed_sections if section.title == "Professional Experience")
    entries = experience_section.meta.get("entries", [])
    assert len(entries) == 1
    assert entries[0]["company"] == "Example Corp"
    assert entries[0]["date_range"] == "Apr 2022 - Present"


def test_backfill_missing_core_sections_does_not_override_existing_content():
    parsed_profile = ResumeProfile(
        name="Candidate",
        summary=["Text-provided summary."],
        skills=["Go"],
        experience=[{"role": "Staff Engineer", "company": "Current Corp", "bullets": ["Owned platform."]}],
        education=[{"degree": "MS", "institution": "Current University"}],
    )
    parsed_sections = [
        ResumeSection(title="Professional Summary", paragraphs=["Text-provided summary."]),
        ResumeSection(title="Technical Skills", bullets=["Go"]),
        ResumeSection(
            title="Professional Experience",
            meta={
                "entries": [
                    {
                        "role": "Staff Engineer",
                        "company": "Current Corp",
                        "location": "",
                        "date_range": "",
                        "bullets": ["Owned platform."],
                    }
                ]
            },
        ),
        ResumeSection(title="Education", paragraphs=["MS | Current University"]),
    ]
    fallback_profile = ResumeProfile(
        name="Candidate",
        summary=["Fallback summary."],
        skills=["React.js"],
        experience=[{"role": "Fallback Role", "company": "Fallback Corp"}],
        education=[{"degree": "Fallback Degree", "institution": "Fallback University"}],
        additional_sections=[ResumeSection(title="Awards", bullets=["Fallback award."])],
    )

    api_module._backfill_missing_core_sections_from_profile(parsed_profile, parsed_sections, fallback_profile)

    assert parsed_profile.summary == ["Text-provided summary."]
    assert parsed_profile.skills == ["Go"]
    assert parsed_profile.experience[0]["company"] == "Current Corp"
    assert parsed_profile.education[0]["institution"] == "Current University"

    summary_section = next(section for section in parsed_sections if section.title == "Professional Summary")
    assert summary_section.paragraphs == ["Text-provided summary."]
    skills_section = next(section for section in parsed_sections if section.title == "Technical Skills")
    assert skills_section.bullets == ["Go"]
    experience_section = next(section for section in parsed_sections if section.title == "Professional Experience")
    assert experience_section.meta["entries"][0]["company"] == "Current Corp"

    awards_section = next(section for section in parsed_sections if section.title == "Awards")
    assert awards_section.bullets == ["Fallback award."]
