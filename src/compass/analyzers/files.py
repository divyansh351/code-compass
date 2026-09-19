"""File structure analyzer."""

from pathlib import Path
from typing import Dict, List, Optional
from compass.analyzers.base import AnalysisResult, BaseAnalyzer


class FileAnalyzer(BaseAnalyzer):
    """Analyzes generic file structure, roles, and characteristics."""

    def can_analyze(self, file_path: Path | str, language: Optional[str] = None) -> bool:
        return True

    def analyze_file(self, file_path: Path, relative_path: str) -> AnalysisResult:
        rel_str = relative_path.replace("\\", "/")
        path_obj = Path(rel_str)
        
        file_role = "source"
        if "test" in path_obj.parts or path_obj.name.startswith("test_") or path_obj.name.endswith("_test.py"):
            file_role = "test"
        elif path_obj.suffix in [".md", ".rst", ".txt", ".adoc"]:
            file_role = "documentation"
        elif path_obj.suffix in [".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".env"]:
            file_role = "configuration"
        elif "docs" in path_obj.parts or "doc" in path_obj.parts:
            file_role = "documentation"
        elif "scripts" in path_obj.parts or "bin" in path_obj.parts:
            file_role = "script"

        metadata = {
            "file_name": path_obj.name,
            "directory": str(path_obj.parent).replace("\\", "/"),
            "role": file_role,
            "extension": path_obj.suffix.lower(),
        }

        return AnalysisResult(
            file_path=rel_str,
            language=path_obj.suffix.lstrip(".").lower() or "text",
            metadata=metadata,
        )
