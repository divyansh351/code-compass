"""Filesystem scanning and language detection utilities."""

import fnmatch
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set

LANGUAGE_EXTENSIONS: Dict[str, List[str]] = {
    "python": [".py", ".pyw", ".pyi"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx", ".mts", ".cts"],
    "rust": [".rs"],
    "go": [".go"],
    "java": [".java"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".hpp", ".cc", ".cxx", ".hxx"],
    "ruby": [".rb"],
    "php": [".php"],
    "markdown": [".md", ".markdown"],
    "json": [".json"],
    "yaml": [".yaml", ".yml"],
    "toml": [".toml"],
    "html": [".html", ".htm"],
    "css": [".css", ".scss", ".sass", ".less"],
    "sql": [".sql"],
    "shell": [".sh", ".bash", ".zsh"],
}

EXTENSION_TO_LANGUAGE: Dict[str, str] = {
    ext: lang for lang, exts in LANGUAGE_EXTENSIONS.items() for ext in exts
}


@dataclass
class ScannedFile:
    """Represents a source file discovered during filesystem scanning."""
    relative_path: str
    absolute_path: Path
    extension: str
    language: Optional[str]
    size_bytes: int
    line_count: int
    content_hash: str


@dataclass
class ScanResult:
    """Summary of a filesystem scan."""
    root_path: Path
    files: List[ScannedFile] = field(default_factory=list)
    languages_detected: Set[str] = field(default_factory=set)
    total_files: int = 0
    total_lines: int = 0
    total_size_bytes: int = 0
    ignored_count: int = 0


class FileScanner:
    """Scans repository directories respecting ignore rules and calculating file metadata."""

    def __init__(self, root_path: Path | str, ignore_patterns: Optional[List[str]] = None):
        self.root_path = Path(root_path).resolve()
        self.ignore_patterns = ignore_patterns or [
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            "dist",
            "build",
            "coverage",
            ".env",
            ".pytest_cache",
            "*.egg-info",
        ]

    def is_ignored(self, path: Path) -> bool:
        """Check if a path matches any ignore pattern."""
        try:
            rel_path = path.relative_to(self.root_path)
            parts = rel_path.parts
        except ValueError:
            parts = path.parts

        for part in parts:
            for pattern in self.ignore_patterns:
                if fnmatch.fnmatch(part, pattern):
                    return True

        rel_str = str(rel_path).replace("\\", "/")
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(rel_str, pattern):
                return True

        return False

    def scan(self) -> ScanResult:
        """Scan the directory recursively and return structured file metadata."""
        result = ScanResult(root_path=self.root_path)

        if not self.root_path.exists():
            return result

        for root, dirs, files in os.walk(self.root_path):
            current_dir = Path(root)

            # Filter and count ignored subdirectories to avoid descending into them
            ignored_dirs = [d for d in dirs if self.is_ignored(current_dir / d)]
            result.ignored_count += len(ignored_dirs)
            dirs[:] = [d for d in dirs if not self.is_ignored(current_dir / d)]

            for file_name in files:
                file_path = current_dir / file_name

                if self.is_ignored(file_path):
                    result.ignored_count += 1
                    continue

                scanned_file = self._analyze_file(file_path)
                if scanned_file:
                    result.files.append(scanned_file)
                    result.total_files += 1
                    result.total_lines += scanned_file.line_count
                    result.total_size_bytes += scanned_file.size_bytes
                    if scanned_file.language:
                        result.languages_detected.add(scanned_file.language)

        return result

    def _analyze_file(self, file_path: Path) -> Optional[ScannedFile]:
        """Read and compute metadata for a single file."""
        try:
            rel_path = str(file_path.relative_to(self.root_path)).replace("\\", "/")
            stat = file_path.stat()
            size_bytes = stat.st_size
            ext = file_path.suffix.lower()
            lang = EXTENSION_TO_LANGUAGE.get(ext)

            # Read content to compute hash and line count
            try:
                content = file_path.read_bytes()
                content_hash = hashlib.sha256(content).hexdigest()
                # Count lines accurately for text files
                line_count = len(content.splitlines()) if size_bytes < 10 * 1024 * 1024 else 0
            except Exception:
                content_hash = ""
                line_count = 0

            return ScannedFile(
                relative_path=rel_path,
                absolute_path=file_path,
                extension=ext,
                language=lang,
                size_bytes=size_bytes,
                line_count=line_count,
                content_hash=content_hash,
            )
        except Exception:
            return None
