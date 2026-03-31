from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from .models import ResumeProfile, ResumeSection


def _ensure_path(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path


def load_profile(profile_path: str | Path) -> ResumeProfile:
    """Load structured resume profile data from YAML or JSON."""
    path = _ensure_path(Path(profile_path))
    data: Dict[str, Any]
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text()) or {}
    elif path.suffix.lower() == ".json":
        data = json.loads(path.read_text())
    else:
        raise ValueError("Profile file must be YAML or JSON.")

    name = data.get("name")
    if not name:
        raise ValueError("Profile data must include a 'name' field.")

    resume = ResumeProfile(
        name=name,
        headline=data.get("headline"),
        contact=data.get("contact", {}),
        summary=data.get("summary", []) or [],
        experience=data.get("experience", []) or [],
        education=data.get("education", []) or [],
        projects=data.get("projects", []) or [],
        certifications=data.get("certifications", []) or [],
        skills=data.get("skills", []) or [],
    )

    for section in data.get("additional_sections", []) or []:
        resume.additional_sections.append(
            ResumeSection(
                title=section.get("title", "Additional"),
                bullets=section.get("bullets", []) or [],
                paragraphs=section.get("paragraphs", []) or [],
                meta=section.get("meta", {}) or {},
            )
        )

    return resume


def ensure_directory(path: str | Path) -> Path:
    """Create parent directory for the given output path."""
    output_path = Path(path)
    if output_path.is_dir():
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def dump_json(obj: Any, destination: str | Path) -> None:
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(obj, indent=2, ensure_ascii=False))
