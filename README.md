# Resume by Job Description

A CLI tool that ingests a reference resume and a job description, then produces an updated resume PDF that preserves the reference theme while highlighting mandatory skills from the job description.

## Key Features
- Extracts structural and style cues from a reference resume PDF.
- Parses job descriptions to identify required and preferred skills.
- Updates the resume content and skills inventory to reflect the job requirements.
- Generates a polished PDF that mirrors the reference theme.
- Auto-detects Hackajob-style references (Space Grotesk template) and renders the card-based layout with matching header/cards/chips/logos.

## Installation
```
uv pip install -e .
```
If `uv` is unavailable, fall back to:
```
python3 -m pip install -e .
```

## Usage
```
resume-by-jd \
  --reference path/to/reference_resume.pdf \
  --profile path/to/profile.yml \
  --job-description path/to/jd.txt \
  --output output/resume.pdf
```

- `--reference`: PDF of your current resume, used to infer styling cues.
- `--profile`: YAML or JSON file describing your structured resume data (experiences, projects, education, skills).
- `--job-description`: Plain text job description.
- `--output`: Path to the updated resume PDF.

Use `--debug-dir` to emit intermediate artifacts (parsed structure JSON, skill extraction report) for inspection.

## Profile Schema
Refer to [`samples/profile.yml`](samples/profile.yml) for an annotated example.

## Web App
Run the FastAPI service, which also serves the static frontend:
```
resume-by-jd-api
```
Then open [http://localhost:8000](http://localhost:8000) in your browser. The web form lets you upload the same inputs as the CLI and downloads the generated PDF.

## Development
- Run `pytest` to execute unit tests.
- Store temporary PDFs in `tmp/pdfs/` and outputs in `output/pdf/`.

## Limitations
- Automatic layout inference works best on single-column resumes with clear heading hierarchy.
- Fonts embedded in the reference resume must be available on your system or they will fall back to similar fonts in ReportLab.
- Mandatory skills are identified heuristically; review the generated resume to ensure accuracy.
