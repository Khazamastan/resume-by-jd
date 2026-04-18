from resume_builder.models import ReferenceStructure, ResumeProfile, ResumeSection, Theme, SkillInsights
from resume_builder.resume_updater import build_resume_document
from resume_builder.pdf_generator import _build_styles, _section_elements


def test_build_resume_document_adds_mandatory_skills():
    theme = Theme()
    reference = ReferenceStructure(theme=theme, sections=[ResumeSection(title="Skills")])
    profile = ResumeProfile(name="Alex Taylor", skills=["Python"])
    insights = SkillInsights(mandatory=["React", "Python"], preferred=[])

    document = build_resume_document(reference, profile, insights)

    skills_section = next(
        section for section in document.sections if section.title in {"Skills", "Technical Skills"}
    )
    collected_skills: list[str] = []
    for category, values in skills_section.meta.get("category_lines", []):
        if isinstance(values, (list, tuple)):
            collected_skills.extend(str(value) for value in values)
    collected_skills.extend(skills_section.bullets)
    assert "React" in collected_skills
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
        paragraphs=["Senior Engineer @ Example Corp | Remote | Jan 2020 – Present"],
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
    assert entries[0]["role"] == "Senior Engineer"
    assert entries[0]["company"] == "Example Corp"
    assert entries[0]["location"] == "Remote"
    assert entries[0]["date_range"] == "Jan 2020 - Present"
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


def test_education_section_reads_institution_degree_location_year_from_profile():
    theme = Theme()
    reference = ReferenceStructure(theme=theme, sections=[ResumeSection(title="Education")])
    profile = ResumeProfile(
        name="Alex Taylor",
        education=[
            {
                "institution": "Rajiv Gandhi University of Knowledge Technologies",
                "degree": "B.Tech in Mechanical Engineering",
                "location": "R.K. Valley, Andhra Pradesh",
                "year": "2010-2014",
                "grade": "8.4 CGPA",
            }
        ],
    )
    insights = SkillInsights()

    document = build_resume_document(reference, profile, insights)

    education_section = next(section for section in document.sections if section.title == "Education")
    assert (
        "Rajiv Gandhi University of Knowledge Technologies | B.Tech in Mechanical Engineering | "
        "R.K. Valley, Andhra Pradesh | 2010-2014 | Grade: 8.4 CGPA"
    ) in education_section.paragraphs


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


def test_build_resume_document_carries_reference_section_style_metadata():
    reference = ReferenceStructure(
        theme=Theme(),
        sections=[
            ResumeSection(
                title="Skills",
                meta={
                    "_reference_style": {
                        "heading_weight": "bold",
                        "heading_color": "#112233",
                        "body_weight": "regular",
                        "body_color": "#223344",
                    }
                },
            ),
            ResumeSection(
                title="Professional Experience",
                meta={
                    "_reference_style": {
                        "heading_weight": "bold",
                        "heading_color": "#334455",
                        "body_weight": "light",
                        "body_color": "#445566",
                    }
                },
            ),
        ],
    )
    profile = ResumeProfile(
        name="Alex Taylor",
        skills=["React", "TypeScript"],
        experience=[
            {
                "role": "Senior Engineer",
                "company": "Example",
                "start": "2022-01-01",
                "end": "Present",
                "location": "Remote",
                "bullets": ["Built ATS-safe resumes."],
            }
        ],
    )

    document = build_resume_document(reference, profile, SkillInsights())

    skills_section = next(section for section in document.sections if section.title == "Technical Skills")
    experience_section = next(section for section in document.sections if section.title == "Professional Experience")

    assert skills_section.meta.get("_reference_style", {}).get("heading_color") == "#112233"
    assert experience_section.meta.get("_reference_style", {}).get("body_weight") == "light"


def test_build_resume_document_uses_explicit_skill_categories_from_profile_schema():
    reference = ReferenceStructure(theme=Theme(), sections=[ResumeSection(title="Skills")])
    profile = ResumeProfile(
        name="Khaja",
        skills=[
            "frontend: React.js, Next.js",
            "backend: Node.js, Express.js",
            "testing_profiling: Jest, Playwright",
            "ai_devops: Codex, AWS",
        ],
    )

    document = build_resume_document(reference, profile, SkillInsights())
    skills_section = next(section for section in document.sections if section.title == "Technical Skills")
    category_lines = skills_section.meta.get("category_lines", [])
    categories = [category for category, _ in category_lines]

    assert "Frontend" in categories
    assert "Backend" in categories
    assert "Testing & DevOps" in categories
    assert "AI Tools" in categories


def test_build_resume_document_prefers_profile_summary_over_default_template():
    reference = ReferenceStructure(theme=Theme(), sections=[ResumeSection(title="Summary")])
    profile = ResumeProfile(
        name="Ammu",
        summary=[
            "First custom summary line.",
            "Second custom summary line.",
        ],
    )

    document = build_resume_document(reference, profile, SkillInsights())
    summary_section = next(section for section in document.sections if section.title == "Summary")

    assert summary_section.paragraphs == [
        "First custom summary line.",
        "Second custom summary line.",
    ]
