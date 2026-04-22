from resume_builder.resume_text_parser import parse_resume_text


def test_parse_resume_text_extracts_profile_sections_and_entries():
    raw_resume = """
Khajamastan Bellamkonda
Mobile: +91-7207810602 | Email: khazamastan@gmail.com | Location: Pune, India
LinkedIn: www.linkedin.com/in/khazamastan
Available to Join: May 6, 2026

Professional Summary
Lead Software Developer with 10+ years of experience leading technical teams.

Technical Skills
Frontend: React.js, TypeScript, JavaScript
Backend: Node.js, GraphQL

Professional Experience
Company: Oracle | Principal Member Technical Staff
Location: Bangalore | April 2022 - Present
Mentored 5+ mid-level developers.
Automated canary health checks every 15 minutes.

Company: Xactly Corp | Senior Software Developer
Location: Bangalore | June 2021 - April 2022
Built a high-concurrency real-time application utilizing WebSockets.

Education
B.Tech in Mechanical Engineering | Rajiv Gandhi University of Knowledge Technologies

Awards
Spot Award for Best Performance | Thrymr Software
"""

    profile, sections = parse_resume_text(raw_resume)

    assert profile.name == "Khajamastan Bellamkonda"
    assert profile.contact["phone"] == "+91-7207810602"
    assert profile.contact["email"] == "khazamastan@gmail.com"
    assert profile.contact["location"] == "Pune, India"
    assert profile.contact["linkedin"] == "www.linkedin.com/in/khazamastan"
    assert profile.contact["notice_note"] == "Available to Join: May 6, 2026"
    assert profile.headline == "Principal Member Technical Staff at Oracle"

    section_titles = [section.title for section in sections]
    assert "Professional Summary" in section_titles
    assert "Technical Skills" in section_titles
    assert "Professional Experience" in section_titles
    assert "Education" in section_titles
    assert "Awards" in section_titles

    skills_section = next(section for section in sections if section.title == "Technical Skills")
    category_lines = skills_section.meta.get("category_lines", [])
    assert category_lines
    assert category_lines[0][0] == "Frontend"
    assert "React.js" in category_lines[0][1]

    experience_section = next(section for section in sections if section.title == "Professional Experience")
    entries = experience_section.meta.get("entries", [])
    assert len(entries) == 2
    assert entries[0]["company"] == "Oracle"
    assert entries[0]["role"] == "Principal Member Technical Staff"
    assert entries[0]["location"] == "Bangalore"
    assert entries[0]["date_range"] == "April 2022 - Present"
    assert any("Mentored 5+ mid-level developers." in bullet for bullet in entries[0]["bullets"])


def test_parse_resume_text_falls_back_to_summary_when_headings_missing():
    profile, sections = parse_resume_text("Jane Doe\nSenior frontend engineer with React and TypeScript experience.")

    assert profile.name == "Jane Doe"
    assert sections
    assert sections[0].title == "Professional Summary"
    assert sections[0].paragraphs


def test_parse_resume_text_extracts_education_year_and_grade():
    raw_resume = """
Jane Doe
Email: jane@example.com

Education
B.Tech in Mechanical Engineering | Rajiv Gandhi University of Knowledge Technologies | R.K. Valley | 2010-2014 | 8.4 CGPA
"""

    profile, _ = parse_resume_text(raw_resume)

    assert profile.education
    education = profile.education[0]
    assert education["institution"] == "Rajiv Gandhi University of Knowledge Technologies"
    assert education["degree"] == "B.Tech in Mechanical Engineering"
    assert education["location"] == "R.K. Valley"
    assert education["year"] == "2010-2014"
    assert education["grade"] == "8.4 CGPA"


def test_parse_resume_text_supports_company_role_and_location_date_lines():
    raw_resume = """
Khajamastan Bellamkonda
Email: khazamastan@gmail.com

Professional Experience
Oracle | Principal Member Technical Staff
Bangalore | April 2022 – Present
Built and mentored platform teams.

Xactly Corp | Senior Software Developer
Bangalore | June 2021 – April 2022
Delivered Objectives application at scale.

Nineleaps Technology | Software Development Engineer II
Bangalore | May 2020 – June 2021
Led migration to module federation.

Education & Awards
Bachelor of Technology in Mechanical Engineering | Rajiv Gandhi University of Knowledge Technologies (2014)
Awards: Thrymr Software Spot Award (Best Performance); 2021 Tech Champion (Nineleaps)
Note: Serving Notice Period — Available to Join: May 5, 2026.
"""

    profile, sections = parse_resume_text(raw_resume)

    experience_section = next(section for section in sections if section.title == "Professional Experience")
    entries = experience_section.meta.get("entries", [])
    assert len(entries) == 3

    assert entries[0]["company"] == "Oracle"
    assert entries[0]["role"] == "Principal Member Technical Staff"
    assert entries[0]["location"] == "Bangalore"
    assert entries[0]["date_range"] == "April 2022 – Present"
    assert entries[0]["bullets"] == ["Built and mentored platform teams."]

    assert entries[1]["company"] == "Xactly Corp"
    assert entries[1]["role"] == "Senior Software Developer"
    assert entries[1]["location"] == "Bangalore"
    assert entries[1]["date_range"] == "June 2021 – April 2022"
    assert entries[1]["bullets"] == ["Delivered Objectives application at scale."]

    assert entries[2]["company"] == "Nineleaps Technology"
    assert entries[2]["role"] == "Software Development Engineer II"
    assert entries[2]["location"] == "Bangalore"
    assert entries[2]["date_range"] == "May 2020 – June 2021"
    assert entries[2]["bullets"] == ["Led migration to module federation."]

    education_section = next(section for section in sections if section.title == "Education")
    assert education_section.paragraphs
    assert "Rajiv Gandhi University" in education_section.paragraphs[0]
    assert profile.education[0]["institution"] == "Rajiv Gandhi University of Knowledge Technologies (2014)"

    awards_section = next(section for section in sections if section.title == "Awards")
    assert awards_section.bullets
    assert "Spot Award" in awards_section.bullets[0]
    assert all("Available to Join" not in bullet for bullet in awards_section.bullets)
    assert profile.contact["notice_note"] == "Serving Notice Period — Available to Join: May 5, 2026."


def test_parse_resume_text_supports_linkedin_style_resume_export_format():
    raw_resume = """
Khajamastan Bellamkonda

Pamur, A.P, India

khazamastan@gmail.com
+91-7207810602
https://www.linkedin.com/in/khazamastan
Summary

Rewrite

Lead Front-End Developer with 10+ years of experience scaling web applications.

Experience

Principal Member Technical Staff
Oracle
Apr 2022 – Present (4 yrs 1 mo)

Accelerated incident resolution by building an AI agent for build ticket triage.

Rewrite

Senior Software Developer
Xactly Corp
Jun 2021 – Apr 2022 (11 mos)

Improved application load times by 20-30% by migrating front-end builds to Webpack.

Education

Rajiv Gandhi University of Knowledge Technologies
B.Tech, Mechanical Engineering

Licenses & certifications

This section is empty and won’t appear in your resume.

Skills

React.js  Next.js  Angular  TypeScript  JavaScript
Honors & awards

Thrymr Software Spot Award for Best Performance - Thrymr Software
Tech Champion - Nineleaps Technology Solutions
"""

    profile, sections = parse_resume_text(raw_resume)

    assert profile.name == "Khajamastan Bellamkonda"
    assert profile.contact["location"] == "Pamur, A.P, India"
    assert profile.contact["email"] == "khazamastan@gmail.com"
    assert profile.contact["phone"] == "+91-7207810602"
    assert profile.contact["linkedin"] == "https://www.linkedin.com/in/khazamastan"

    titles = [section.title for section in sections]
    assert "Professional Summary" in titles
    assert "Professional Experience" in titles
    assert "Technical Skills" in titles
    assert "Education" in titles
    assert "Awards" in titles
    assert "Certifications" not in titles

    experience_section = next(section for section in sections if section.title == "Professional Experience")
    entries = experience_section.meta.get("entries", [])
    assert len(entries) == 2
    assert entries[0]["role"] == "Principal Member Technical Staff"
    assert entries[0]["company"] == "Oracle"
    assert entries[0]["date_range"] == "Apr 2022 – Present"
    assert "Rewrite" not in entries[0]["bullets"]
    assert entries[1]["role"] == "Senior Software Developer"
    assert entries[1]["company"] == "Xactly Corp"
    assert entries[1]["date_range"] == "Jun 2021 – Apr 2022"

    assert profile.headline == "Principal Member Technical Staff at Oracle"
    assert any(skill == "React.js" for skill in profile.skills)
    assert any(skill == "Next.js" for skill in profile.skills)

    education = profile.education[0]
    assert education["institution"] == "Rajiv Gandhi University of Knowledge Technologies"
    assert education["degree"] == "B.Tech, Mechanical Engineering"

    awards_section = next(section for section in sections if section.title == "Awards")
    assert len(awards_section.bullets) == 2


def test_parse_resume_text_handles_hidden_heading_chars_without_misclassifying_sentences():
    raw_resume = """
Jane Doe
Pamur, A.P, India
jane@example.com

\u200bSummary\u200b
Lead engineer with deep experience building data platforms and strong technical skills in mentoring.

\u200bExperience\u2060
Senior Software Engineer
Example Corp
Jan 2022 – Present (4 yrs 1 mo)
Improved objective-setting and team delivery cadence.

\u00a0Skills\u00a0
Python  TypeScript  React

Honors & awards
Employee of the Year - Example Corp
"""

    profile, sections = parse_resume_text(raw_resume)

    assert profile.name == "Jane Doe"
    assert profile.contact["location"] == "Pamur, A.P, India"
    assert profile.contact["email"] == "jane@example.com"
    assert profile.headline == "Senior Software Engineer at Example Corp"

    titles = [section.title for section in sections]
    assert "Professional Summary" in titles
    assert "Professional Experience" in titles
    assert "Technical Skills" in titles
    assert "Awards" in titles

    summary_section = next(section for section in sections if section.title == "Professional Summary")
    assert len(summary_section.paragraphs) == 1
    assert "deep experience building data platforms" in summary_section.paragraphs[0]

    experience_section = next(section for section in sections if section.title == "Professional Experience")
    entries = experience_section.meta.get("entries", [])
    assert len(entries) == 1
    assert entries[0]["role"] == "Senior Software Engineer"
    assert entries[0]["company"] == "Example Corp"
    assert entries[0]["date_range"] == "Jan 2022 – Present"
    assert entries[0]["bullets"] == ["Improved objective-setting and team delivery cadence."]

    assert profile.skills == ["Python", "TypeScript", "React"]

    awards_section = next(section for section in sections if section.title == "Awards")
    assert awards_section.bullets == ["Employee of the Year - Example Corp"]


def test_parse_resume_text_handles_bidirectional_marks_inside_heading_words():
    raw_resume = """
Khajamastan Bellamkonda
Pamur, A.P, India
khazamastan@gmail.com

Sum\u200emary
Lead Front-End Developer with over a decade of experience in scaling web applications.

Ex\u200eperience
Principal Member Technical Staff
Oracle
Apr 2022 – Present (4 yrs 1 mo)
Built reliable internal platforms.

Edu\u200ecation
Rajiv Gandhi University of Knowledge Technologies
B.Tech, Mechanical Engineering

Lice\u200enses & certif\u200fications
This section is empty and won’t appear in your resume.

Skills
React.js  Next.js  TypeScript
Hon\u200fors & awards
Thrymr Software Spot Award - Thrymr Software
"""

    profile, sections = parse_resume_text(raw_resume)

    titles = [section.title for section in sections]
    assert "Professional Summary" in titles
    assert "Professional Experience" in titles
    assert "Technical Skills" in titles
    assert "Education" in titles
    assert "Awards" in titles
    assert "Certifications" not in titles

    assert profile.headline == "Principal Member Technical Staff at Oracle"
    assert profile.skills == ["React.js", "Next.js", "TypeScript"]
    assert len(profile.experience) == 1
    assert profile.experience[0]["role"] == "Principal Member Technical Staff"
    assert profile.experience[0]["company"] == "Oracle"

    education_section = next(section for section in sections if section.title == "Education")
    assert "Licenses & certifications" not in education_section.paragraphs
    assert all("won’t appear in your resume" not in line for line in education_section.paragraphs)

    awards_section = next(section for section in sections if section.title == "Awards")
    assert awards_section.bullets == ["Thrymr Software Spot Award - Thrymr Software"]


def test_parse_resume_text_maps_heading_synonyms_to_canonical_sections():
    raw_resume = """
Jane Doe
jane@example.com

Career Objective
Lead engineer with 9+ years of experience building scalable web platforms.

Core Competencies
React.js, TypeScript, Node.js, GraphQL

Employment History
Senior Software Engineer
Example Corp
Jan 2022 - Present
Built resilient multi-tenant APIs.

Academic Background
B.Tech in Computer Science | Example University

Achievements
Engineering Excellence Award - Example Corp
"""

    profile, sections = parse_resume_text(raw_resume)

    titles = [section.title for section in sections]
    assert "Professional Summary" in titles
    assert "Technical Skills" in titles
    assert "Professional Experience" in titles
    assert "Education" in titles
    assert "Awards" in titles

    assert profile.summary
    assert "Lead engineer" in profile.summary[0]
    assert "React.js" in profile.skills
    assert profile.headline == "Senior Software Engineer at Example Corp"
    assert len(profile.experience) == 1
    assert profile.experience[0]["company"] == "Example Corp"
    assert profile.education
    assert profile.education[0]["institution"] == "Example University"

    awards_section = next(section for section in sections if section.title == "Awards")
    assert awards_section.bullets == ["Engineering Excellence Award - Example Corp"]


def test_parse_resume_text_infers_sections_without_explicit_headings():
    raw_resume = """
Jane Doe
jane@example.com

Lead software engineer with over 10 years of experience building distributed systems and frontend platforms.

Principal Software Engineer
Example Corp
Jan 2020 - Present
Designed and delivered mission-critical workflow services at scale.

B.Tech in Computer Science | Example University of Technology

Python  TypeScript  React  GraphQL
Employee Recognition Award - Example Corp
"""

    profile, sections = parse_resume_text(raw_resume)

    titles = [section.title for section in sections]
    assert "Professional Summary" in titles
    assert "Technical Skills" in titles
    assert "Professional Experience" in titles
    assert "Education" in titles
    assert "Awards" in titles

    assert profile.summary
    assert "over 10 years of experience" in profile.summary[0]
    assert profile.headline == "Principal Software Engineer at Example Corp"
    assert len(profile.experience) == 1
    assert profile.experience[0]["company"] == "Example Corp"

    assert "Python" in profile.skills
    assert "TypeScript" in profile.skills
    assert profile.education
    assert profile.education[0]["institution"] == "Example University of Technology"

    awards_section = next(section for section in sections if section.title == "Awards")
    assert awards_section.bullets == ["Employee Recognition Award - Example Corp"]


def test_parse_resume_text_maps_requested_core_headings_to_existing_titles():
    raw_resume = """
Jane Doe
jane@example.com

Summary Section
Experienced engineer with strong backend and frontend delivery track record.

Skills
React.js  TypeScript  Node.js

Experience
Senior Software Engineer
Example Corp
Jan 2021 - Present
Delivered high-impact user-facing and platform features.

Education
B.Tech in Computer Science | Example University

Honors & awards section
Engineering Excellence Award - Example Corp
"""

    profile, sections = parse_resume_text(raw_resume)

    titles = [section.title for section in sections]
    assert "Professional Summary" in titles
    assert "Technical Skills" in titles
    assert "Professional Experience" in titles
    assert "Education" in titles
    assert "Awards" in titles
    assert "Summary Section" not in titles
    assert "Honors & awards section" not in titles

    assert profile.summary
    assert "Experienced engineer" in profile.summary[0]
    assert "React.js" in profile.skills
    assert profile.headline == "Senior Software Engineer at Example Corp"

    awards_section = next(section for section in sections if section.title == "Awards")
    assert awards_section.bullets == ["Engineering Excellence Award - Example Corp"]


def test_parse_resume_text_auto_groups_skills_when_categories_are_missing():
    raw_resume = """
Jane Doe
jane@example.com

Summary
Experienced engineer.

Skills
React.js  TypeScript  Node.js  GraphQL  Jest  Jenkins  OCI
"""

    _, sections = parse_resume_text(raw_resume)

    skills_section = next(section for section in sections if section.title == "Technical Skills")
    category_lines = skills_section.meta.get("category_lines", [])
    assert category_lines

    as_dict = {category: items for category, items in category_lines}
    assert "Frontend" in as_dict
    assert "Backend" in as_dict
    assert "Testing" in as_dict
    assert "DevOps & Tools" in as_dict
    assert "Cloud" in as_dict
    assert "React.js" in as_dict["Frontend"]
    assert "Node.js" in as_dict["Backend"]


def test_parse_resume_text_supports_pdf_export_bullets_and_company_role_commas():
    raw_resume = """
Khajamastan Bellamkonda
khazamastan@gmail.com  •  +91-7207810602  •  Pamur, A.P, India  •  www.linkedin.com/in/khazamastan

Professional Summary
Lead Front-End Developer with over a decade of experience in scaling web applications.

Work Experience
Oracle, Principal Member Technical Staff
Apr 2022 - Present
Improved canary health checks and developer velocity.
Xactly Corp, Senior Software Developer
Jun 2021 - Apr 2022
Delivered the Objectives product at scale.
Khajamastan Bellamkonda - page 1 of 2

EDUCATION
Rajiv Gandhi University of Knowledge Technologies
B.Tech • Mechanical Engineering

SKILLS
React.js   •   Next.js   •   Angular   •   TypeScript   •   JavaScript   •   GraphQL

HONORS & AWARDS
Thrymr Software Spot Award
Thrymr Software •
Tech Champion
"""

    profile, sections = parse_resume_text(raw_resume)

    assert profile.contact["email"] == "khazamastan@gmail.com"
    assert profile.contact["phone"] == "+91-7207810602"
    assert profile.contact["location"] == "Pamur, A.P, India"
    assert profile.contact["linkedin"] == "www.linkedin.com/in/khazamastan"
    assert profile.headline == "Principal Member Technical Staff at Oracle"

    titles = [section.title for section in sections]
    assert "Professional Summary" in titles
    assert "Technical Skills" in titles
    assert "Professional Experience" in titles
    assert "Education" in titles
    assert "Awards" in titles

    experience_section = next(section for section in sections if section.title == "Professional Experience")
    entries = experience_section.meta.get("entries", [])
    assert len(entries) == 2
    assert entries[0]["company"] == "Oracle"
    assert entries[0]["role"] == "Principal Member Technical Staff"
    assert entries[0]["date_range"] == "Apr 2022 - Present"
    assert entries[1]["company"] == "Xactly Corp"
    assert entries[1]["role"] == "Senior Software Developer"

    all_bullets = [bullet for entry in entries for bullet in entry.get("bullets", [])]
    assert all("page 1 of 2" not in bullet.lower() for bullet in all_bullets)

    skills_section = next(section for section in sections if section.title == "Technical Skills")
    category_lines = skills_section.meta.get("category_lines", [])
    assert category_lines
    assert all(item != "•" for _, items in category_lines for item in items)
    assert "React.js" in profile.skills
    assert "GraphQL" in profile.skills
    assert "•" not in profile.skills

    awards_section = next(section for section in sections if section.title == "Awards")
    assert all(not line.endswith("•") for line in awards_section.bullets)


def test_parse_resume_text_supports_company_role_date_pipe_lines_and_backfills_location():
    raw_resume = """
Khazamastan Bellamkonda
Principal Member Technical Staff | Full Stack Developer (AI & Generative Technologies)

Location: Bangalore, India | Phone: +91-7207810602 | Email: khazamastan@gmail.com
Notice Period: Currently Serving (LWD: May 5, 2026)

Professional Experience
Oracle | Principal Member Technical Staff | April 2022 – Present
Developed an AI agent utilizing DevOps MCP to automatically triage build tickets.

Xactly Corp | Senior Software Developer | June 2021 – April 2022
Optimized frontend builds by migrating to Webpack with code splitting.
"""

    profile, sections = parse_resume_text(raw_resume)

    assert profile.contact["location"] == "Bangalore, India"
    assert profile.contact["phone"] == "+91-7207810602"
    assert profile.contact["email"] == "khazamastan@gmail.com"
    assert profile.contact["notice_note"] == "Currently Serving (LWD: May 5, 2026)"

    experience_section = next(section for section in sections if section.title == "Professional Experience")
    entries = experience_section.meta.get("entries", [])
    assert len(entries) == 2

    assert entries[0]["company"] == "Oracle"
    assert entries[0]["role"] == "Principal Member Technical Staff"
    assert entries[0]["date_range"] == "April 2022 – Present"
    assert entries[0]["location"] == "Bangalore, India"

    assert entries[1]["company"] == "Xactly Corp"
    assert entries[1]["role"] == "Senior Software Developer"
    assert entries[1]["date_range"] == "June 2021 – April 2022"
    assert entries[1]["location"] == "Bangalore, India"

    assert profile.experience[0]["start"] == "April 2022"
    assert profile.experience[0]["end"] == "Present"
    assert profile.headline == "Principal Member Technical Staff at Oracle"


def test_parse_resume_text_supports_company_line_with_inline_timeline_and_location():
    raw_resume = """
Khazamastan Bellamkonda
Principal Member Technical Staff

Professional Experience
Company: Minewhat Inc | Senior Front-End Developer | Bangalore, India | Timeline: August 2016 – July 2018
Owned the user experience of an ML-driven recommendation platform.
"""

    profile, sections = parse_resume_text(raw_resume)

    experience_section = next(section for section in sections if section.title == "Professional Experience")
    entries = experience_section.meta.get("entries", [])
    assert len(entries) == 1

    assert entries[0]["company"] == "Minewhat Inc"
    assert entries[0]["role"] == "Senior Front-End Developer"
    assert entries[0]["location"] == "Bangalore, India"
    assert entries[0]["date_range"] == "August 2016 – July 2018"
    assert entries[0]["bullets"] == ["Owned the user experience of an ML-driven recommendation platform."]

    assert len(profile.experience) == 1
    assert profile.experience[0]["start"] == "August 2016"
    assert profile.experience[0]["end"] == "July 2018"
