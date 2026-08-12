"""Vercel Python serverless entry point for the existing FastAPI application."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
