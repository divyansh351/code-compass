"""Unit tests for Python AST analyzer."""

from pathlib import Path
import pytest

from compass.analyzers.python import PythonAnalyzer


def test_python_analyzer_extracts_symbols_and_imports(tmp_path: Path):
    source_content = '''"""User service module."""
from repository import UserRepository
import requests

class UserService:
    """Service handling user operations."""

    def __init__(self):
        self.repo = UserRepository()

    def get_user(self, user_id: str) -> dict:
        """Fetch a user."""
        return self.repo.get(user_id)
'''
    py_file = tmp_path / "service.py"
    py_file.write_text(source_content, encoding="utf-8")

    analyzer = PythonAnalyzer()
    assert analyzer.can_analyze(py_file)

    result = analyzer.analyze_file(py_file, "service.py")

    assert result.language == "python"
    assert result.metadata.get("syntax_valid") is True
    assert result.metadata.get("docstring") == "User service module."

    # Check Symbols
    symbol_names = [s.name for s in result.symbols]
    assert "UserService" in symbol_names
    assert "__init__" in symbol_names
    assert "get_user" in symbol_names

    user_service_sym = next(s for s in result.symbols if s.name == "UserService")
    assert user_service_sym.kind == "class"
    assert user_service_sym.docstring == "Service handling user operations."
    assert user_service_sym.source.line_start == 5
    assert user_service_sym.source.method == "ast"

    get_user_sym = next(s for s in result.symbols if s.name == "get_user")
    assert get_user_sym.kind == "method"
    assert "user_id: str" in get_user_sym.parameters
    assert get_user_sym.metadata.get("return_type") == "dict"

    # Check Imports
    import_modules = [i.module for i in result.imports]
    assert "repository" in import_modules
    assert "requests" in import_modules

    user_repo_imp = next(i for i in result.imports if i.name == "UserRepository")
    assert user_repo_imp.module == "repository"
    assert user_repo_imp.source.line_start == 2

    # Check Calls
    calls = [c.callee_name for c in result.calls]
    assert any("get" in c or "UserRepository" in c for c in calls)


def test_python_analyzer_handles_syntax_errors_gracefully(tmp_path: Path):
    invalid_code = "def broken_func(:\n    pass"
    py_file = tmp_path / "broken.py"
    py_file.write_text(invalid_code, encoding="utf-8")

    analyzer = PythonAnalyzer()
    result = analyzer.analyze_file(py_file, "broken.py")

    assert result.metadata.get("syntax_valid") is False
    assert len(result.symbols) == 0
