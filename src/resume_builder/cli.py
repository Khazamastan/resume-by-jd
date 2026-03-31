from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from . import io_utils
from .jd_analyzer import analyze_job_description
from .pdf_generator import render_resume
from .reference_parser import extract_reference_structure
from .resume_updater import build_resume_document


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Update a resume based on a job description while preserving the original theme."
    )
    parser.add_argument("--reference", required=True, help="Path to the reference resume PDF.")
    parser.add_argument("--profile", required=True, help="Path to the structured resume profile (YAML or JSON).")
    parser.add_argument("--job-description", required=True, help="Path to the job description text file.")
    parser.add_argument("--output", required=True, help="Destination PDF path for the updated resume.")
    parser.add_argument("--debug-dir", help="Optional directory to dump intermediate JSON artifacts.")
    return parser


def _read_job_description(path: str | Path) -> str:
    job_path = Path(path)
    if not job_path.exists():
        raise FileNotFoundError(f"Job description not found: {job_path}")
    return job_path.read_text()


def _dump_reference_structure(structure, insights, debug_dir: Path) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    structure_payload: Dict[str, Any] = {
        "theme": structure.theme.__dict__,
        "sections": [
            {
                "title": section.title,
                "paragraphs": section.paragraphs,
                "bullets": section.bullets,
                "meta": section.meta,
            }
            for section in structure.sections
        ],
    }
    insights_payload = {
        "mandatory": insights.mandatory,
        "preferred": insights.preferred,
        "keywords": insights.keywords,
    }
    io_utils.dump_json(structure_payload, debug_dir / "reference_structure.json")
    io_utils.dump_json(insights_payload, debug_dir / "jd_skills.json")


def main(argv: List[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    profile = io_utils.load_profile(args.profile)
    reference = extract_reference_structure(args.reference)
    job_description = _read_job_description(args.job_description)
    insights = analyze_job_description(job_description)

    document = build_resume_document(reference, profile, insights)
    output_path = render_resume(document, args.output)

    if args.debug_dir:
        _dump_reference_structure(reference, insights, Path(args.debug_dir))

    print(f"Updated resume generated at {output_path}")


if __name__ == "__main__":
    main()
