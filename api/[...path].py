"""Catch-all entrypoint for Vercel Serverless functions.

This ensures requests to /api/* routes are forwarded to the FastAPI app."""

from resume_builder.api import app  # noqa: F401
