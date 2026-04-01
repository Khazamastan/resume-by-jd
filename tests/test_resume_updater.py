from resume_builder.models import ReferenceStructure, ResumeProfile, ResumeSection, Theme, SkillInsights
from resume_builder.resume_updater import build_resume_document
from resume_builder.pdf_generator import _build_styles, _section_elements


def test_build_resume_document_adds_mandatory_skills():
    theme = Theme()
    reference = ReferenceStructure(theme=theme, sections=[ResumeSection(title="Skills")])
    profile = ResumeProfile(name="Alex Taylor", skills=["Python"])
    insights = SkillInsights(mandatory=["AWS", "Python"], preferred=[])

    document = build_resume_document(reference, profile, insights)

    skills_section = next(section for section in document.sections if section.title == "Skills")
    assert "AWS" in skills_section.bullets
    assert document.profile.skills == ["Python"]


def test_mandatory_sections_render_even_when_empty():
    theme = Theme()
    styles = _build_styles(theme)
    required_titles = ["Professional Experience", "Education", "Awards"]

    for title in required_titles:
        section = ResumeSection(title=title)
        elements = _section_elements(section, styles)
        assert elements, f"{title} should render even when empty"

    optional_section = ResumeSection(title="Community")
    assert _section_elements(optional_section, styles) == []


def test_experience_section_uses_additional_fallback_when_profile_missing():
    theme = Theme()
    reference = ReferenceStructure(theme=theme, sections=[ResumeSection(title="Professional Experience")])
    additional = ResumeSection(
        title="Professional Experience",
        paragraphs=["Senior Engineer @ Example Corp — Jan 2020 – Present"],
        bullets=["Led cross-functional team", "Delivered features on time"],
    )
    profile = ResumeProfile(name="Alex Taylor", additional_sections=[additional])
    insights = SkillInsights()

    document = build_resume_document(reference, profile, insights)

    titles = [section.title for section in document.sections]
    assert titles.count("Professional Experience") == 1

    experience_section = next(section for section in document.sections if section.title == "Professional Experience")
    entries = experience_section.meta.get("entries") or []
    assert entries, "Fallback entries should populate experience meta"
    assert entries[0]["bullets"] == ["Led cross-functional team", "Delivered features on time"]


def test_education_section_uses_additional_fallback_when_profile_missing():
    theme = Theme()
    reference = ReferenceStructure(theme=theme, sections=[])
    additional = ResumeSection(
        title="Education",
        paragraphs=["B.S. Computer Science | State University (2016)"],
        bullets=["Dean's List 2014-2016"],
    )
    profile = ResumeProfile(name="Alex Taylor", additional_sections=[additional])
    insights = SkillInsights()

    document = build_resume_document(reference, profile, insights)

    education_section = next(section for section in document.sections if section.title == "Education")
    assert "B.S. Computer Science | State University (2016)" in education_section.paragraphs
    assert "Dean's List 2014-2016" in education_section.bullets


def test_format_experience_entry_trims_leading_dash_when_no_start_date():
    profile = ResumeProfile(
        name="Taylor",
        experience=[
            {
                "role": "Principal Member Technical Staff",
                "company": "Oracle",
                "start": "",
                "end": "Present",
                "location": "Remote",
                "bullets": [],
            }
        ],
    )
    theme = Theme()
    reference = ReferenceStructure(theme=theme, sections=[ResumeSection(title="Professional Experience")])
    document = build_resume_document(reference, profile, SkillInsights())
    experience_section = next(section for section in document.sections if section.title == "Professional Experience")
    entry = experience_section.meta["entries"][0]
    assert entry["date_range"] == "Present"
