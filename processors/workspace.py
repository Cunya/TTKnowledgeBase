from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .utils import read_yaml

KB_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class KnowledgeBasePaths:
    root: Path
    id: str
    name: str
    description: str

    @property
    def config(self) -> Path:
        return self.root / "config" / "kbs" / self.id

    @property
    def content(self) -> Path:
        return self.root / "content" / "kbs" / self.id

    def data(self, kind: str) -> Path:
        return self.root / "data" / kind / self.id


def load_knowledge_base(root: Path, requested: str | None = None) -> KnowledgeBasePaths:
    project = read_yaml(root / "config" / "project.yaml")
    kb_id = requested or project["default_knowledge_base"]
    if not KB_ID.fullmatch(kb_id):
        raise ValueError(f"Invalid knowledge-base ID: {kb_id}")
    registry = read_yaml(root / "config" / "knowledge-bases.yaml")
    match = next((item for item in registry["knowledge_bases"] if item["id"] == kb_id), None)
    if not match or not match.get("enabled", True):
        raise ValueError(f"Unknown or disabled knowledge base: {kb_id}")
    return KnowledgeBasePaths(root, kb_id, match["name"], match["description"])
