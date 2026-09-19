"""Base analyzer interfaces and abstract definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SourceLocation:
    """Source code coordinates for provenance."""
    file: str
    line_start: int
    line_end: int
    method: str = "ast"


@dataclass
class SymbolInfo:
    """Represents a code symbol (class, function, method, variable)."""
    id: str
    name: str
    kind: str  # "class", "function", "method", "variable"
    source: SourceLocation
    docstring: Optional[str] = None
    signature: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImportInfo:
    """Represents an imported module, class, or function."""
    module: str
    name: Optional[str] = None
    alias: Optional[str] = None
    is_relative: bool = False
    level: int = 0
    source: SourceLocation = field(
        default_factory=lambda: SourceLocation(file="", line_start=0, line_end=0)
    )
    is_external: bool = False


@dataclass
class CallInfo:
    """Represents a function or method invocation."""
    caller_id: str
    callee_name: str
    source: SourceLocation


@dataclass
class InheritanceInfo:
    """Represents class inheritance."""
    subclass_id: str
    superclass_name: str
    source: SourceLocation


@dataclass
class AnalysisResult:
    """Result of analyzing a file or repository."""
    file_path: str
    language: str
    symbols: List[SymbolInfo] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    calls: List[CallInfo] = field(default_factory=list)
    inheritances: List[InheritanceInfo] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAnalyzer(ABC):
    """Abstract base class for language analyzers."""

    @abstractmethod
    def can_analyze(self, file_path: Path | str, language: Optional[str] = None) -> bool:
        """Return True if this analyzer handles the given file."""
        pass

    @abstractmethod
    def analyze_file(self, file_path: Path, relative_path: str) -> AnalysisResult:
        """Analyze a single file and extract symbols, imports, and relationships."""
        pass
