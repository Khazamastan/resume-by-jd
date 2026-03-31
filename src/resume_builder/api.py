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
from .io_utils import load_profile
from .models import ResumeDocument, ResumeProfile, ResumeSection, Theme


class SectionUpdate(BaseModel):
    title: str
    paragraphs: List[str] = Field(default_factory=list)
    bullets: List[str] = Field(default_factory=list)
    meta: Optional[Dict[str, object]] = None


class UpdatePayload(BaseModel):
    sections: List[SectionUpdate]


RESUME_SESSIONS: Dict[str, ResumeDocument] = {}


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
                derived_paragraphs.append(" • ".join(header_parts))
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
                    header = " • ".join([part for part in header_parts if part])
                    if header:
                        derived_paragraphs.append(header)
                    derived_bullets.extend(entry["bullets"])
                section.paragraphs = derived_paragraphs
                section.bullets = derived_bullets
            elif "entries" in section.meta:
                section.meta.pop("entries")


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

    @app.post("/api/generate")
    async def generate_resume(
        reference: UploadFile = File(...),
        profile: UploadFile = File(...),
        job_description: UploadFile | None = File(default=None),
        job_text: str | None = Form(default=None),
    ) -> Dict[str, object]:
        if job_description is None and not job_text:
            raise HTTPException(status_code=400, detail="Provide job description text or file.")

        async with _temporary_workspace() as workspace:
            reference_path = workspace.path(_sanitize_filename(reference.filename, "reference.pdf"))
            profile_path = workspace.path(_sanitize_filename(profile.filename, "profile.yml"))
            output_path = workspace.path("resume.pdf")

            await _persist_upload(reference, reference_path)
            await _persist_upload(profile, profile_path)

            if job_description:
                jd_path = workspace.path(_sanitize_filename(job_description.filename, "job.txt"))
                await _persist_upload(job_description, jd_path)
                job_contents = jd_path.read_text()
            else:
                job_contents = job_text or ""

            try:
                profile_data = load_profile(profile_path)
                reference_structure = extract_reference_structure(reference_path)
                insights = analyze_job_description(job_contents)
                document = build_resume_document(reference_structure, profile_data, insights)
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
            raise HTTPException(status_code=404, detail="Resume session not found.")
        if len(payload.sections) != len(document.sections):
            raise HTTPException(status_code=400, detail="Section count mismatch.")

        for section, update in zip(document.sections, payload.sections, strict=False):
            _apply_section_update(section, update)

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
