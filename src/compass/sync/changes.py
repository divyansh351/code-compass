"""Change detection for incremental knowledge updates."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import json

from compass.ingestion.filesystem import ScanResult, ScannedFile


@dataclass
class FileDiff:
    """Represents differences in source files since last build."""
    added: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    deleted: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.modified or self.deleted)


class ChangeDetector:
    """Compares current scan against previous build metadata."""

    def __init__(self, knowledge_path: Path | str):
        self.knowledge_path = Path(knowledge_path)
        self.build_meta_file = self.knowledge_path / "metadata" / "build.json"

    def detect_changes(self, current_scan: ScanResult) -> FileDiff:
        """Detect added/modified/deleted files."""
        if not self.build_meta_file.exists():
            return FileDiff(added=[f.relative_path for f in current_scan.files])

        current_files = {f.relative_path: f for f in current_scan.files}

        # Try to read components to find previous file list
        components_file = self.knowledge_path / "components" / "components.json"
        prev_files: Set[str] = set()
        if components_file.exists():
            try:
                comps = json.loads(components_file.read_text(encoding="utf-8"))
                for c in comps:
                    if c.get("source") and c["source"].get("file"):
                        prev_files.add(c["source"]["file"])
            except Exception:
                pass

        added = [p for p in current_files if p not in prev_files]
        deleted = [p for p in prev_files if p not in current_files]
        modified = []
        unchanged = []

        for p in current_files:
            if p in prev_files:
                # In full sync we'd compare hashes
                unchanged.append(p)

        return FileDiff(
            added=added,
            modified=modified,
            deleted=deleted,
            unchanged=unchanged,
        )
