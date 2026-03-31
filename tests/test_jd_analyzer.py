from resume_builder.jd_analyzer import analyze_job_description


def test_analyze_job_description_extracts_mandatory_skills():
    jd = """
    Must have: Python, AWS Lambda, PostgreSQL.
    Nice to have: Terraform.
    """
    insights = analyze_job_description(jd)
    assert "Python" in insights.mandatory
    assert "AWS Lambda" in insights.mandatory
    assert "PostgreSQL" in insights.mandatory
    assert "Terraform" in insights.preferred
    assert "Python" in insights.keywords
