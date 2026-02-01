"""
Project Detector - Detect new vs existing projects.

Determines whether we need onboarding questions or can
use existing project context.
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

log = logging.getLogger("spark.onboarding")

PROJECTS_FILE = Path.home() / ".spark" / "projects.json"


def _hash_path(path: str) -> str:
    """Create a stable hash for a project path."""
    normalized = str(Path(path).resolve()).lower().replace("\\", "/")
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


def _load_projects() -> Dict:
    """Load known projects from disk."""
    if not PROJECTS_FILE.exists():
        return {"projects": {}}
    try:
        with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Failed to load projects: {e}")
        return {"projects": {}}


def _save_projects(data: Dict):
    """Save projects to disk."""
    try:
        PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log.error(f"Failed to save projects: {e}")


class ProjectDetector:
    """Detect and track projects."""

    def __init__(self):
        self._data = _load_projects()

    def is_new_project(self, cwd: str) -> bool:
        """Check if this is a new (unseen) project."""
        project_id = _hash_path(cwd)
        return project_id not in self._data["projects"]

    def get_project_id(self, cwd: str) -> str:
        """Get stable project ID for a path."""
        return _hash_path(cwd)

    def get_project_info(self, cwd: str) -> Optional[Dict]:
        """Get stored info for a project."""
        project_id = _hash_path(cwd)
        return self._data["projects"].get(project_id)

    def register_project(self, cwd: str, context: Dict):
        """Register a new project with context."""
        project_id = _hash_path(cwd)
        self._data["projects"][project_id] = {
            "path": str(Path(cwd).resolve()),
            "context": context,
            "created_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "session_count": 1,
        }
        _save_projects(self._data)
        log.info(f"Registered new project: {project_id}")

    def update_project(self, cwd: str, updates: Dict):
        """Update project context."""
        project_id = _hash_path(cwd)
        if project_id in self._data["projects"]:
            self._data["projects"][project_id]["context"].update(updates)
            self._data["projects"][project_id]["last_seen"] = datetime.now().isoformat()
            self._data["projects"][project_id]["session_count"] += 1
            _save_projects(self._data)

    def infer_domain_from_path(self, cwd: str) -> Optional[str]:
        """Try to infer domain from project path and files."""
        path = Path(cwd)

        # Check for common project indicators
        indicators = {
            "game": ["game", "unity", "godot", "phaser", "three.js", "assets/sprites"],
            "web": ["src/pages", "src/components", "next.config", "vite.config"],
            "api": ["routes", "controllers", "endpoints", "swagger"],
            "ml": ["models", "training", "datasets", "notebooks"],
            "cli": ["bin", "cli", "commands", "args"],
            "marketing": ["campaigns", "content", "copy", "brand"],
        }

        path_str = str(path).lower()

        # Check path name
        for domain, patterns in indicators.items():
            for pattern in patterns:
                if pattern in path_str:
                    return domain

        # Check for key files
        files_to_check = {
            "game": ["game.js", "main.gd", "Assets/Scripts"],
            "web": ["package.json", "next.config.js", "vite.config.js"],
            "api": ["routes.py", "app.py", "server.js"],
            "ml": ["train.py", "model.py", "requirements.txt"],
        }

        for domain, files in files_to_check.items():
            for file in files:
                if (path / file).exists():
                    return domain

        return None

    def get_all_projects(self) -> List[Dict]:
        """Get all known projects."""
        return list(self._data["projects"].values())


# Convenience function
def is_new_project(cwd: str) -> bool:
    """Check if a project is new (convenience function)."""
    detector = ProjectDetector()
    return detector.is_new_project(cwd)
