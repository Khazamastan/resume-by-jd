from __future__ import annotations

import os
import base64
from contextlib import asynccontextmanager
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import (
    analyze_job_description,
    build_resume_document,
    extract_reference_structure,
    render_resume,
)
from .io_utils import load_profile, profile_to_canonical, save_profile
from .models import ResumeDocument, ResumeProfile, ResumeSection, Theme
from .profile_generator import build_profile_from_reference
import yaml
import re


class SectionUpdate(BaseModel):
    title: str
    paragraphs: List[str] = Field(default_factory=list)
    bullets: List[str] = Field(default_factory=list)
    meta: Optional[Dict[str, object]] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    headline: Optional[str] = None
    contact: Optional[Dict[str, str]] = None


class UpdatePayload(BaseModel):
    sections: List[SectionUpdate]
    profile: Optional[ProfileUpdate] = None
    theme: Optional[Dict[str, object]] = None


RESUME_SESSIONS: Dict[str, ResumeDocument] = {}

_HEX_COLOR_PATTERN = re.compile(r"^#?(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REFERENCE_PATH = PROJECT_ROOT / "resume.pdf"
DEFAULT_PROFILE_PATH = PROJECT_ROOT / "profile.yaml"
SAMPLES_ROOT = PROJECT_ROOT / "samples"
DEFAULT_SAMPLE_PROFILE = "Khaja"
PROFILE_FILE_CANDIDATES = ("profile.yaml", "profile.yml", "profile.json")


def _find_profile_file(profile_dir: Path) -> Optional[Path]:
    for filename in PROFILE_FILE_CANDIDATES:
        candidate = profile_dir / filename
        if candidate.exists():
            return candidate
    return None


def _discover_sample_profiles() -> List[Dict[str, str]]:
    if not SAMPLES_ROOT.exists():
        return []

    profiles: List[Dict[str, str]] = []
    for entry in sorted(SAMPLES_ROOT.iterdir(), key=lambda item: item.name.lower()):
        if not entry.is_dir():
            continue
        reference_path = entry / "resume.pdf"
        profile_path = _find_profile_file(entry)
        if not reference_path.exists() or profile_path is None:
            continue
        profiles.append(
            {
                "id": entry.name,
                "label": entry.name,
                "reference_path": str(reference_path),
                "profile_path": str(profile_path),
            }
        )
    return profiles


def _resolve_sample_profile_paths(sample_profile: Optional[str]) -> tuple[Path | None, Path | None]:
    discovered_profiles = _discover_sample_profiles()
    if not discovered_profiles:
        return None, None

    requested_profile = (sample_profile or DEFAULT_SAMPLE_PROFILE).strip()
    if not requested_profile:
        requested_profile = DEFAULT_SAMPLE_PROFILE

    for profile in discovered_profiles:
        if profile["id"].lower() == requested_profile.lower():
            return Path(profile["reference_path"]), Path(profile["profile_path"])

    available_profiles = ", ".join(profile["id"] for profile in discovered_profiles)
    raise HTTPException(
        status_code=400,
        detail=f"Unknown sample_profile '{requested_profile}'. Available options: {available_profiles}.",
    )


def _normalize_hex_color(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        raise ValueError("Color value is empty.")
    if not _HEX_COLOR_PATTERN.fullmatch(candidate):
        raise ValueError(f"Invalid color value: {value!r}")
    if not candidate.startswith("#"):
        candidate = f"#{candidate}"
    if len(candidate) == 4:
        candidate = "#" + "".join(ch * 2 for ch in candidate[1:])
    return candidate.lower()


def _apply_theme_overrides(theme: Theme, overrides: Dict[str, str]) -> None:
    accent_color = overrides.get("accent_color")
    if accent_color:
        theme.accent_color = accent_color
    primary_color = overrides.get("primary_color")
    if primary_color:
        theme.primary_color = primary_color


def _theme_from_payload(payload: Optional[Dict[str, object]]) -> Theme:
    theme = Theme()
    if not isinstance(payload, dict):
        return theme

    text_fields = ("body_font", "heading_font", "primary_color", "accent_color", "template")
    for field_name in text_fields:
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            setattr(theme, field_name, value.strip())

    numeric_fields = (
        "body_size",
        "heading_size",
        "line_height",
        "margin_left",
        "margin_right",
        "margin_top",
        "margin_bottom",
        "page_width",
        "page_height",
    )
    for field_name in numeric_fields:
        value = payload.get(field_name)
        if value is None:
            continue
        try:
            setattr(theme, field_name, float(value))
        except (TypeError, ValueError):
            continue

    return theme


def _encode_pdf(pdf_bytes: bytes) -> str:
    return base64.b64encode(pdf_bytes).decode("utf-8")


def _profile_payload(profile: ResumeProfile) -> Dict[str, object]:
    return {
        "name": profile.name,
        "headline": profile.headline,
        "contact": profile.contact,
    }


def _section_payload(section: ResumeSection) -> Dict[str, object]:
    payload: Dict[str, object] = {
        "title": section.title,
        "paragraphs": list(section.paragraphs),
        "bullets": list(section.bullets),
    }
    section_meta = section.meta or {}
    if (
        section.title.lower() in {"professional experience", "experience"}
        and "entries" in section_meta
        and not payload["paragraphs"]
        and not payload["bullets"]
    ):
        derived_paragraphs: List[str] = []
        derived_bullets: List[str] = []
        for entry in section_meta.get("entries", []):
            role = str(entry.get("role") or "").strip()
            company = str(entry.get("company") or "").strip()
            location = str(entry.get("location") or "").strip()
            date_range = str(entry.get("date_range") or "").strip()
            header_parts = [part for part in [role, f"@ {company}" if company else "", location, date_range] if part]
            if header_parts:
                derived_paragraphs.append(" | ".join(header_parts))
            for bullet in entry.get("bullets", []) or []:
                clean = str(bullet).strip()
                if clean:
                    derived_bullets.append(clean)
        if derived_paragraphs:
            payload["paragraphs"] = derived_paragraphs
        if derived_bullets:
            payload["bullets"] = derived_bullets
        section.paragraphs = list(payload["paragraphs"])
        section.bullets = list(payload["bullets"])
    if section_meta:
        payload["meta"] = section_meta
    return payload


def _document_payload(resume_id: str, document: ResumeDocument, pdf_bytes: bytes) -> Dict[str, object]:
    return {
        "resume_id": resume_id,
        "profile": _profile_payload(document.profile),
        "sections": [_section_payload(section) for section in document.sections],
        "theme": asdict(document.theme),
        "pdf": _encode_pdf(pdf_bytes),
    }


def _apply_section_update(section: ResumeSection, update: SectionUpdate) -> None:
    new_title = update.title.strip()
    if new_title:
        section.title = new_title
    section.paragraphs = [paragraph.strip() for paragraph in update.paragraphs if paragraph.strip()]
    section.bullets = [bullet.strip() for bullet in update.bullets if bullet.strip()]
    if (section.paragraphs or section.bullets) and "entries" in section.meta:
        section.meta.pop("entries", None)

    if update.meta and isinstance(update.meta, dict):
        if "category_lines" in update.meta:
            normalized: List[tuple[str, List[str]]] = []
            raw_lines = update.meta.get("category_lines") or []
            for entry in raw_lines:
                if isinstance(entry, dict):
                    category = str(entry.get("category", "")).strip()
                    items = entry.get("items", [])
                elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                    category = str(entry[0]).strip()
                    items = entry[1]
                else:
                    continue
                if not category:
                    continue
                item_values = [
                    str(item).strip()
                    for item in (items or [])
                    if str(item).strip()
                ]
                normalized.append((category, item_values))
            if normalized:
                section.meta["category_lines"] = normalized
            elif "category_lines" in section.meta:
                section.meta.pop("category_lines")

        if "entries" in update.meta:
            normalized_entries: List[Dict[str, object]] = []
            raw_entries = update.meta.get("entries") or []
            for raw_entry in raw_entries:
                if not isinstance(raw_entry, dict):
                    continue
                role = str(raw_entry.get("role", "") or "").strip()
                company = str(raw_entry.get("company", "") or "").strip()
                location = str(raw_entry.get("location", "") or "").strip()
                date_range = str(raw_entry.get("date_range", "") or "").strip()
                raw_bullets = raw_entry.get("bullets", [])
                if isinstance(raw_bullets, str):
                    bullets = [line.strip() for line in raw_bullets.splitlines() if line.strip()]
                else:
                    bullets = [
                        str(item).strip()
                        for item in (raw_bullets or [])
                        if str(item).strip()
                    ]
                if not any([role, company, location, date_range, bullets]):
                    continue
                normalized_entries.append(
                    {
                        "role": role,
                        "company": company,
                        "location": location,
                        "date_range": date_range,
                        "bullets": bullets,
                    }
                )

            if normalized_entries:
                section.meta["entries"] = normalized_entries
                derived_paragraphs: List[str] = []
                derived_bullets: List[str] = []
                for entry in normalized_entries:
                    header_parts = [
                        entry["role"],
                        f"@ {entry['company']}" if entry["company"] else "",
                        entry["location"],
                        entry["date_range"],
                    ]
                    header = " | ".join([part for part in header_parts if part])
                    if header:
                        derived_paragraphs.append(header)
                    derived_bullets.extend(entry["bullets"])
                section.paragraphs = derived_paragraphs
                section.bullets = derived_bullets
            elif "entries" in section.meta:
                section.meta.pop("entries")


def _apply_profile_update(profile: ResumeProfile, update: Optional[ProfileUpdate]) -> None:
    if update is None:
        return

    if update.name is not None:
        cleaned_name = update.name.strip()
        if cleaned_name:
            profile.name = cleaned_name

    if update.headline is not None:
        profile.headline = update.headline.strip()

    if update.contact is not None:
        existing_contact = dict(profile.contact or {})
        normalized_contact: Dict[str, str] = {}
        for key in ("phone", "email", "location", "linkedin", "notice_note"):
            raw_value = update.contact.get(key, existing_contact.get(key, ""))
            clean_value = str(raw_value or "").strip()
            if clean_value:
                normalized_contact[key] = clean_value
        profile.contact = normalized_contact


def _maybe_mount_frontend(app: FastAPI) -> None:
    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    index_file = frontend_dir / "index.html"
    if not index_file.exists():
        return

    static_dir = frontend_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:  # pragma: no cover - FastAPI handles response
        return FileResponse(index_file)


@asynccontextmanager
async def _temporary_workspace() -> TemporaryDirectory:
    with TemporaryDirectory() as tmpdir:
        yield TemporaryDirectoryWrapper(Path(tmpdir))


class TemporaryDirectoryWrapper:
    """Wrapper adding helpers for FastAPI request handling."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, relative: str) -> Path:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        return target


def _sanitize_filename(original: Optional[str], default: str) -> str:
    if not original:
        return default
    candidate = Path(original).name.strip()
    return candidate or default


async def _persist_upload(upload: UploadFile, destination: Path) -> Path:
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"{upload.filename} is empty.")
    destination.write_bytes(data)
    await upload.close()
    return destination


def _build_app() -> FastAPI:
    app = FastAPI(
        title="Resume by Job Description API",
        description="Expose resume generation as an HTTP service.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _maybe_mount_frontend(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/sample-profiles")
    async def list_sample_profiles() -> Dict[str, object]:
        profiles = _discover_sample_profiles()
        return {
            "default_profile": DEFAULT_SAMPLE_PROFILE,
            "profiles": [{"id": profile["id"], "label": profile["label"]} for profile in profiles],
        }

    @app.post("/api/generate")
    async def generate_resume(
        reference: UploadFile | None = File(default=None),
        profile: UploadFile | None = File(default=None),
        job_description: UploadFile | None = File(default=None),
        job_text: str | None = Form(default=None),
        sample_profile: str | None = Form(default=None),
        accent_color: str | None = Form(default=None),
        primary_color: str | None = Form(default=None),
    ) -> Dict[str, object]:
        async with _temporary_workspace() as workspace:
            sample_reference_path: Path | None = None
            sample_profile_path: Path | None = None
            if reference is None or profile is None:
                sample_reference_path, sample_profile_path = _resolve_sample_profile_paths(sample_profile)

            if reference is not None:
                reference_path = workspace.path(_sanitize_filename(reference.filename, "reference.pdf"))
                await _persist_upload(reference, reference_path)
            elif sample_reference_path is not None:
                reference_path = workspace.path("reference.pdf")
                reference_path.write_bytes(sample_reference_path.read_bytes())
            else:
                if not DEFAULT_REFERENCE_PATH.exists():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Default reference resume not found at {DEFAULT_REFERENCE_PATH}. Upload a reference PDF.",
                    )
                reference_path = workspace.path("reference.pdf")
                reference_path.write_bytes(DEFAULT_REFERENCE_PATH.read_bytes())

            profile_path: Path | None = None
            if profile is not None:
                profile_path = workspace.path(_sanitize_filename(profile.filename, "profile.yml"))
                await _persist_upload(profile, profile_path)
            elif sample_profile_path is not None:
                profile_path = workspace.path("profile.yaml")
                profile_path.write_bytes(sample_profile_path.read_bytes())
            elif DEFAULT_PROFILE_PATH.exists():
                profile_path = workspace.path("profile.yaml")
                profile_path.write_bytes(DEFAULT_PROFILE_PATH.read_bytes())
            output_path = workspace.path("resume.pdf")

            if job_description:
                jd_path = workspace.path(_sanitize_filename(job_description.filename, "job.txt"))
                await _persist_upload(job_description, jd_path)
                job_contents = jd_path.read_text()
            elif job_text and job_text.strip():
                job_contents = job_text.strip()
            else:
                job_contents = "N/A"

            try:
                reference_structure = extract_reference_structure(reference_path)
                if profile_path:
                    profile_data = load_profile(profile_path)
                else:
                    profile_data = build_profile_from_reference(reference_structure)
                    generated_profile_path = workspace.path("generated_profile.yml")
                    save_profile(profile_data, generated_profile_path)
                    print("--- Auto-generated profile ---")
                    canonical_profile = profile_to_canonical(profile_data)
                    print(yaml.safe_dump(canonical_profile, sort_keys=False, allow_unicode=True))
                    print(f"Profile saved to: {generated_profile_path}")
                insights = analyze_job_description(job_contents)
                document = build_resume_document(reference_structure, profile_data, insights)
                overrides: Dict[str, str] = {}
                if accent_color:
                    try:
                        overrides["accent_color"] = _normalize_hex_color(accent_color)
                    except ValueError as exc:
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid accent_color. Provide a hex value like #1a2b3c.",
                        ) from exc
                if primary_color:
                    try:
                        overrides["primary_color"] = _normalize_hex_color(primary_color)
                    except ValueError as exc:
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid primary_color. Provide a hex value like #1a2b3c.",
                        ) from exc
                if overrides:
                    _apply_theme_overrides(document.theme, overrides)
                render_resume(document, output_path)
            except (ValueError, FileNotFoundError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except Exception as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=500, detail="Failed to build resume.") from exc

            pdf_bytes = output_path.read_bytes()

        resume_id = uuid4().hex
        RESUME_SESSIONS[resume_id] = document
        return _document_payload(resume_id, document, pdf_bytes)

    @app.put("/api/resume/{resume_id}")
    async def update_resume(resume_id: str, payload: UpdatePayload) -> Dict[str, object]:
        document = RESUME_SESSIONS.get(resume_id)
        if document is None:
            # Serverless/cold starts can evict in-memory sessions. Rebuild from client payload.
            base_name = "Candidate"
            if payload.profile and payload.profile.name:
                candidate_name = payload.profile.name.strip()
                if candidate_name:
                    base_name = candidate_name
            document = ResumeDocument(
                profile=ResumeProfile(name=base_name),
                sections=[],
                theme=_theme_from_payload(payload.theme),
            )

        _apply_profile_update(document.profile, payload.profile)

        existing_sections = list(document.sections)
        updated_sections: List[ResumeSection] = []

        for index, update in enumerate(payload.sections):
            if index < len(existing_sections):
                section = existing_sections[index]
            else:
                section = ResumeSection(title=update.title.strip() or "Untitled Section")
            _apply_section_update(section, update)
            updated_sections.append(section)

        document.sections = updated_sections

        async with _temporary_workspace() as workspace:
            output_path = workspace.path("resume.pdf")
            render_resume(document, output_path)
            pdf_bytes = output_path.read_bytes()

        RESUME_SESSIONS[resume_id] = document
        return _document_payload(resume_id, document, pdf_bytes)

    @app.get("/api/resume/{resume_id}/pdf")
    async def download_resume(resume_id: str) -> StreamingResponse:
        document = RESUME_SESSIONS.get(resume_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Resume session not found.")

        async with _temporary_workspace() as workspace:
            output_path = workspace.path("resume.pdf")
            render_resume(document, output_path)
            pdf_bytes = output_path.read_bytes()

        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename=\"resume.pdf\"'},
        )

    return app


app = _build_app()


def run() -> None:
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    reload_env = os.environ.get("RESUME_BY_JD_RELOAD", os.environ.get("UVICORN_RELOAD", "true")).lower()
    reload_enabled = reload_env not in {"0", "false", "no"}
    project_root = Path(__file__).resolve().parents[2]
    reload_targets = [
        project_root / "src",
        project_root / "frontend",
    ]
    reload_dirs = [str(path) for path in reload_targets if path.exists()]
    uvicorn.run(
        "resume_builder.api:app",
        host=host,
        port=port,
        reload=reload_enabled,
        reload_dirs=reload_dirs,
    )
