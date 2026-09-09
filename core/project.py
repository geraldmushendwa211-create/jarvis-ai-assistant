"""VideoProject: the structured "job ticket" every pipeline stage reads/writes.

One project = one video attempt. Saved as JSON under workspace/projects/ so
runs are resumable, debuggable, and form the seed of a content library
(scripts, outputs, and stage history per video).

Later slices may move storage to SQLite — the fields stay the same, so the
migration is mechanical.
"""

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime

PROJECTS_DIR = "workspace/projects"


def _slugify(text, max_len=40):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len] or "untitled"


def new_project_id(topic):
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{stamp}_{_slugify(topic)}"


@dataclass
class VideoProject:
    id: str
    topic: str
    niche: str = "generic"
    format: str = "short"       # short | long
    status: str = "created"     # created|scripted|voiced|edited|captioned|done|failed
    script: str = ""
    script_path: str = ""
    audio_path: str = ""
    footage_path: str = ""
    ass_path: str = ""
    output_path: str = ""
    error: str = ""
    created_at: str = ""
    stages: list = field(default_factory=list)

    @classmethod
    def new(cls, topic, niche="generic", format="short"):
        return cls(
            id=new_project_id(topic),
            topic=topic,
            niche=niche,
            format=format,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )

    def mark(self, status, detail=""):
        """Advance the project to a new stage (auto-saves the ticket)."""
        self.status = status
        self.stages.append({
            "stage": status,
            "at": datetime.now().isoformat(timespec="seconds"),
            "detail": detail,
        })
        self.save()
        return self

    def fail(self, error):
        self.error = str(error)
        self.mark("failed", self.error)
        return self

    @property
    def path(self):
        return os.path.join(PROJECTS_DIR, f"{self.id}.json")

    def save(self):
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
        return self.path

    @classmethod
    def load(cls, project_id):
        path = os.path.join(PROJECTS_DIR, f"{project_id}.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    @classmethod
    def list_recent(cls, limit=5):
        if not os.path.isdir(PROJECTS_DIR):
            return []
        files = sorted(
            (f for f in os.listdir(PROJECTS_DIR) if f.endswith(".json")),
            reverse=True,
        )
        projects = []
        for filename in files[:limit]:
            try:
                projects.append(cls.load(filename[:-len(".json")]))
            except (OSError, ValueError):
                continue
        return projects
