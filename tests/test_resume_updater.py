from resume_builder.models import ReferenceStructure, ResumeProfile, ResumeSection, Theme, SkillInsights
from resume_builder.resume_updater import build_resume_document


def test_build_resume_document_adds_mandatory_skills():
    theme = Theme()
    reference = ReferenceStructure(theme=theme, sections=[ResumeSection(title="Skills")])
    profile = ResumeProfile(name="Alex Taylor", skills=["Python"])
    insights = SkillInsights(mandatory=["AWS", "Python"], preferred=[])

    document = build_resume_document(reference, profile, insights)

    skills_section = next(section for section in document.sections if section.title == "Skills")
    assert "AWS" in skills_section.bullets
    assert document.profile.skills == ["Python"]
