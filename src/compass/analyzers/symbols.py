"""Symbol extraction and formatting utilities."""

from typing import Any, Dict, List, Optional
from compass.analyzers.base import SourceLocation, SymbolInfo


def build_symbol_id(file_path: str, symbol_name: str, parent_id: Optional[str] = None) -> str:
    """Generate a unique deterministic ID for a code symbol."""
    norm_file = file_path.replace("\\", "/")
    if parent_id:
        return f"{parent_id}.{symbol_name}"
    return f"{norm_file}::{symbol_name}"


def format_parameters(args_list: List[str]) -> str:
    """Format parameter list into a function signature string."""
    return f"({', '.join(args_list)})"
