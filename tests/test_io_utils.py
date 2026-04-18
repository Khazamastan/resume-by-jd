import pytest

from resume_builder.io_utils import load_profile, profile_to_canonical
from resume_builder.models import ResumeProfile


def test_load_profile_strips_citation_artifacts(tmp_path):
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        """
name: Ammu Candidate
headline: Recruiter
contact:
  [cite_start]phone: "+91-1234567890" [cite: 3]
  [cite_start]email: ammu@example.com [cite: 3, 7]
summary:
  - [cite_start]Strong in recruitment operations. [cite: 10]
experience: []
education: []
skills: []
"""
    )

    profile = load_profile(profile_path)

    assert profile.name == "Ammu Candidate"
    assert profile.contact["phone"] == "+91-1234567890"
    assert profile.contact["email"] == "ammu@example.com"
    assert profile.summary == ["Strong in recruitment operations."]


def test_load_profile_raises_value_error_for_invalid_yaml(tmp_path):
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text("name: [broken")

    with pytest.raises(ValueError, match="Invalid YAML profile file"):
        load_profile(profile_path)


def test_load_profile_supports_categorized_skills_mapping(tmp_path):
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        """
name: Khaja
headline: Engineer
contact:
  email: khaja@example.com
summary: []
experience: []
education: []
skills:
  frontend: [React.js, Next.js]
  backend: [Node.js, Express.js]
  testing_profiling: [Jest, Playwright]
  ai_devops: [Codex, AWS]
"""
    )

    profile = load_profile(profile_path)

    assert profile.skills == [
        "frontend: React.js, Next.js",
        "backend: Node.js, Express.js",
        "testing_profiling: Jest, Playwright",
        "ai_devops: Codex, AWS",
    ]


def test_load_profile_maps_availability_to_notice_note(tmp_path):
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        """
name: Candidate
headline: Engineer
contact:
  email: candidate@example.com
summary: []
experience: []
education: []
skills: []
availability:
  status: Serving Notice Period
  available_to_join: 2026-05-05
"""
    )

    profile = load_profile(profile_path)

    assert profile.contact["notice_note"] == "Serving Notice Period – Available to Join: May 5, 2026"


def test_profile_to_canonical_serializes_categorized_skills_mapping():
    profile = ResumeProfile(
        name="Khaja",
        skills=[
            "frontend: React.js, Next.js",
            "backend: Node.js, Express.js",
            "ai_devops: Codex, AWS",
        ],
    )

    canonical = profile_to_canonical(profile)

    assert canonical["skills"] == {
        "frontend": ["React.js", "Next.js"],
        "backend": ["Node.js", "Express.js"],
        "ai_devops": ["Codex", "AWS"],
    }


def test_profile_to_canonical_preserves_education_year_field():
    profile = ResumeProfile(
        name="Khaja",
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

    canonical = profile_to_canonical(profile)

    assert canonical["education"][0]["year"] == "2010-2014"
    assert canonical["education"][0]["grade"] == "8.4 CGPA"
