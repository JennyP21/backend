# app/models/__init__.py

from app.models.project import Project
from app.models.document import Document

__all__ = [
    "Project",
    "Document",
]