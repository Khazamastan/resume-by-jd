from __future__ import annotations

import os
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import (
    analyze_job_description,
    build_resume_document,
    extract_reference_structure,
    render_resume,
)
from .io_utils import load_profile


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
    ) -> StreamingResponse:
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

        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="resume.pdf"'},
        )

    return app


app = _build_app()


def run() -> None:
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("resume_builder.api:app", host=host, port=port, reload=False)
