"""Serve the optional production web build from source or a frozen bundle."""
from pathlib import Path

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles


def mount_web_client(app: FastAPI, directory: Path | None = None) -> bool:
    """Mount last so API routes retain priority; an unbuilt checkout stays API-only."""
    if directory is None:
        directory = Path(__file__).resolve().parents[2] / "web" / "dist"
    if not (directory / "index.html").is_file():
        return False
    app.mount("/", StaticFiles(directory=directory, html=True), name="web-client")
    return True
