from resume_builder.hackajob_renderer import _header_companies
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
