"""Domain structures recognized on GitHub."""

from gitrecon.models.base import Entity
from gitrecon.models.event import Event
from gitrecon.models.gist import Gist, GistFile
from gitrecon.models.label import Label
from gitrecon.models.organization import Organization
from gitrecon.models.project import Project
from gitrecon.models.records import from_record
from gitrecon.models.repository import Repository
from gitrecon.models.star import Star
from gitrecon.models.user import User

__all__ = [
    "Entity",
    "Event",
    "Gist",
    "GistFile",
    "Label",
    "Organization",
    "Project",
    "Repository",
    "Star",
    "User",
    "from_record",
]
