import pytest

from resume_builder.io_utils import load_profile


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
