from pathlib import Path
import subprocess

import pytest

from resume_builder.latex_renderer import build_latex_resume_source, render_latex_resume
from resume_builder.models import ResumeDocument, ResumeProfile, ResumeSection, Theme


def _sample_document() -> ResumeDocument:
    return ResumeDocument(
        profile=ResumeProfile(
            name="Khajamastan Bellamkonda",
            headline="Principal Member Technical Staff at Oracle",
            contact={
                "phone": "+91-7207810602",
                "email": "khazamastan@gmail.com",
                "location": "Pamur, A.P, India, 523108",
                "linkedin": "https://www.linkedin.com/in/khazamastan",
                "github": "https://github.com/khazamastan",
                "notice_note": "Serving Notice Period -- Available to Join: May 5, 2026",
            },
            summary=[
                "Front End Developer with 10+ years of expertise in scalable web applications.",
            ],
            education=[
                {
                    "institution": "Rajiv Gandhi University of Knowledge Technologies",
                    "degree": "Bachelors Degree (B.Tech) in Mechanical Engineering",
                    "location": "R.K. Valley, Andhra Pradesh",
                    "year": "2010 -- 2014",
                }
            ],
        ),
        sections=[
            ResumeSection(
                title="Technical Skills",
                meta={
                    "category_lines": [
                        ("Frontend", ["React.js", "TypeScript", "React_18"]),
                        ("Testing & DevOps", ["Jest", "CI/CD"]),
                    ]
                },
            ),
            ResumeSection(
                title="Work Experience",
                meta={
                    "entries": [
                        {
                            "role": "Principal Member Technical Staff",
                            "company": "Oracle",
                            "location": "Bangalore, India",
                            "date_range": "April 2022 -- Present",
                            "bullets": [
                                "Improved canary triage workflows by 60%.",
                                "Modernized CI/CD & reliability standards.",
                            ],
                        }
                    ]
                },
            ),
            ResumeSection(
                title="Awards",
                bullets=["Won Spot Award for Best Performance."],
            ),
        ],
        theme=Theme(template="latex"),
    )


def test_build_latex_resume_source_matches_expected_structure():
    source = build_latex_resume_source(_sample_document())

    assert "\\documentclass[a4paper,10pt]{article}" in source
    assert "\\section*{\\fontsize{13pt}{15pt}\\selectfont Professional Summary}" in source
    assert source.count("\\noindent\\rule{\\textwidth}{0.5pt}") == 5
    assert "Principal Member Technical Staff at \\textbf{Oracle}" in source
    assert "\\href{mailto:khazamastan@gmail.com}{khazamastan@gmail.com}" in source
    assert "\\section*{\\fontsize{13pt}{15pt}\\selectfont Technical Skills}" in source
    assert "\\textbf{Frontend:} React.js, TypeScript, React\\_18" in source
    assert "\\textbf{Testing \\& DevOps:} Jest, CI/CD" in source
    assert "\\section*{\\fontsize{13pt}{15pt}\\selectfont Work Experience}" in source
    assert "\\begin{tabular*}{\\textwidth}{@{}l@{\\extracolsep{\\fill}}r@{}}" in source
    assert "\\textbf{Principal Member Technical Staff} & April 2022 -- Present \\\\" in source
    assert "\\textit{Oracle} & \\textit{Bangalore, KA} \\\\" in source
    assert "Front End Developer with \\textbf{10+} years of expertise in scalable web applications." in source
    assert "Improved canary triage workflows by \\textbf{60\\%}." in source
    assert "Modernized \\textbf{CI/CD} \\& reliability standards." in source
    assert "\\section*{\\fontsize{13pt}{15pt}\\selectfont Awards}" in source
    assert "Note: Serving Notice Period -- Available to Join: May 5, 2026" in source


def test_render_latex_resume_raises_clear_error_when_pdflatex_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("resume_builder.latex_renderer._resolve_pdflatex", lambda: None)

    with pytest.raises(FileNotFoundError, match="pdflatex"):
        render_latex_resume(_sample_document(), tmp_path / "resume.pdf")


def test_render_latex_resume_writes_pdf_when_compilation_succeeds(tmp_path, monkeypatch):
    def _fake_run(command, capture_output, text, check):  # type: ignore[no-untyped-def]
        output_dir = Path(command[command.index("-output-directory") + 1])
        tex_path = Path(command[-1])
        compiled_pdf = output_dir / f"{tex_path.stem}.pdf"
        compiled_pdf.write_bytes(b"%PDF-1.4\n%mock")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("resume_builder.latex_renderer._resolve_pdflatex", lambda: "/usr/bin/pdflatex")
    monkeypatch.setattr("resume_builder.latex_renderer.subprocess.run", _fake_run)

    output_pdf = tmp_path / "latex_resume.pdf"
    output_tex = tmp_path / "latex_resume.tex"
    render_latex_resume(_sample_document(), output_pdf, tex_output_path=output_tex)

    assert output_pdf.exists()
    assert output_pdf.read_bytes().startswith(b"%PDF-1.4")
    assert output_tex.exists()
    assert "\\begin{document}" in output_tex.read_text()


def test_latex_work_experience_backfills_missing_right_column_and_styles_dates():
    document = ResumeDocument(
        profile=ResumeProfile(
            name="Khajamastan Bellamkonda",
            experience=[
                {
                    "role": "Senior Front-End Developer",
                    "company": "Minewhat Inc",
                    "location": "Bangalore",
                    "start": "2016-08-01",
                    "end": "2018-07-01",
                    "bullets": ["Built recommendation widgets."],
                }
            ],
        ),
        sections=[
            ResumeSection(
                title="Work Experience",
                meta={
                    "entries": [
                        {
                            "role": "Senior Front-End Developer",
                            "company": "Minewhat Inc",
                            "location": "",
                            "date_range": "",
                            "bullets": ["Built recommendation widgets."],
                        }
                    ]
                },
            )
        ],
        theme=Theme(template="latex"),
    )

    source = build_latex_resume_source(document)

    assert "\\textbf{Senior Front-End Developer} & Aug. 2016 -- Jul. 2018 \\\\" in source
    assert "\\textit{Minewhat Inc} & \\textit{Bangalore, KA} \\\\" in source
