"""Unit tests for repository file scanner and language detection."""

from pathlib import Path
import pytest

from compass.ingestion.filesystem import FileScanner


def test_file_scanner_discovers_files(tmp_path: Path):
    # Setup temporary directory structure
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("print('hello')", encoding="utf-8")
    (src_dir / "utils.py").write_text("def add(a, b): return a + b", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Test Repo", encoding="utf-8")

    scanner = FileScanner(root_path=tmp_path)
    result = scanner.scan()

    assert result.total_files == 3
    rel_paths = [f.relative_path for f in result.files]
    assert "src/app.py" in rel_paths
    assert "src/utils.py" in rel_paths
    assert "README.md" in rel_paths
    assert "python" in result.languages_detected
    assert "markdown" in result.languages_detected


def test_file_scanner_respects_ignores(tmp_path: Path):
    # Setup ignored folders
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("git config", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "pyvenv.cfg").write_text("", encoding="utf-8")
    (tmp_path / "custom_ignored").mkdir()
    (tmp_path / "custom_ignored" / "secret.py").write_text("SECRET=1", encoding="utf-8")

    # Valid file
    (tmp_path / "main.py").write_text("import os", encoding="utf-8")

    scanner = FileScanner(
        root_path=tmp_path,
        ignore_patterns=[".git", "node_modules", ".venv", "custom_ignored"],
    )
    result = scanner.scan()

    assert result.total_files == 1
    assert result.files[0].relative_path == "main.py"
    assert result.ignored_count >= 3
