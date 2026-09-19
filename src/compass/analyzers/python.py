"""Python AST analyzer for classes, functions, calls, imports, and inheritance."""

import ast
import logging
from pathlib import Path
from typing import Any, List, Optional

from compass.analyzers.base import (
    AnalysisResult,
    BaseAnalyzer,
    CallInfo,
    ImportInfo,
    InheritanceInfo,
    SourceLocation,
    SymbolInfo,
)
from compass.analyzers.symbols import build_symbol_id

logger = logging.getLogger(__name__)


class PythonASTVisitor(ast.NodeVisitor):
    """Visits Python AST nodes to extract symbols, dependencies, and relationships."""

    def __init__(self, relative_path: str, source_code: str):
        self.relative_path = relative_path.replace("\\", "/")
        self.source_code = source_code
        self.symbols: List[SymbolInfo] = []
        self.imports: List[ImportInfo] = []
        self.calls: List[CallInfo] = []
        self.inheritances: List[InheritanceInfo] = []
        self._current_parent_id: Optional[str] = None
        self._current_scope_id: Optional[str] = None

    def _get_decorator_name(self, node: ast.expr) -> str:
        """Extract string representation of a decorator node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_expression_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return ""

    def _get_expression_name(self, node: ast.AST) -> str:
        """Helper to get text name of an expression (attribute or name)."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_expression_name(node.value)}.{node.attr}"
        return ""

    def _format_arg(self, arg: ast.arg) -> str:
        """Format an ast.arg with type annotation if available."""
        name = arg.arg
        if arg.annotation:
            try:
                ann_str = ast.unparse(arg.annotation)
                return f"{name}: {ann_str}"
            except Exception:
                return name
        return name

    def visit_Import(self, node: ast.Import) -> None:
        """Extract `import x, y as z` statements."""
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    module=alias.name,
                    name=None,
                    alias=alias.asname,
                    is_relative=False,
                    level=0,
                    source=SourceLocation(
                        file=self.relative_path,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        method="ast",
                    ),
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Extract `from x import y, z as w` statements."""
        module_name = node.module or ""
        is_relative = (node.level or 0) > 0
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    module=module_name,
                    name=alias.name,
                    alias=alias.asname,
                    is_relative=is_relative,
                    level=node.level or 0,
                    source=SourceLocation(
                        file=self.relative_path,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        method="ast",
                    ),
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Extract class definition, docstring, inheritance, and methods."""
        class_id = build_symbol_id(
            self.relative_path,
            node.name,
            parent_id=self._current_parent_id,
        )

        docstring = ast.get_docstring(node)
        decorators = [self._get_decorator_name(d) for d in node.decorator_list if d]

        # Extract base classes / inheritance
        bases: List[str] = []
        for base in node.bases:
            base_name = self._get_expression_name(base)
            if not base_name and isinstance(base, ast.Constant):
                base_name = str(base.value)
            if base_name:
                bases.append(base_name)
                self.inheritances.append(
                    InheritanceInfo(
                        subclass_id=class_id,
                        superclass_name=base_name,
                        source=SourceLocation(
                            file=self.relative_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                            method="ast",
                        ),
                    )
                )

        self.symbols.append(
            SymbolInfo(
                id=class_id,
                name=node.name,
                kind="class",
                source=SourceLocation(
                    file=self.relative_path,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    method="ast",
                ),
                docstring=docstring,
                parent_id=self._current_parent_id,
                decorators=decorators,
                metadata={"bases": bases},
            )
        )

        # Traverse nested body with updated parent_id and scope
        prev_parent = self._current_parent_id
        prev_scope = self._current_scope_id
        self._current_parent_id = class_id
        self._current_scope_id = class_id

        self.generic_visit(node)

        self._current_parent_id = prev_parent
        self._current_scope_id = prev_scope

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Extract function/method definition."""
        self._handle_function_like(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Extract async function/method definition."""
        self._handle_function_like(node, is_async=True)

    def _handle_function_like(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool
    ) -> None:
        kind = "method" if self._current_parent_id else "function"
        func_id = build_symbol_id(
            self.relative_path,
            node.name,
            parent_id=self._current_parent_id,
        )

        docstring = ast.get_docstring(node)
        decorators = [self._get_decorator_name(d) for d in node.decorator_list if d]
        params = [self._format_arg(a) for a in node.args.args]
        if node.args.vararg:
            params.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            params.append(f"**{node.args.kwarg.arg}")

        return_ann = None
        if node.returns:
            try:
                return_ann = ast.unparse(node.returns)
            except Exception:
                return_ann = None

        sig_str = f"def {node.name}({', '.join(params)})"
        if return_ann:
            sig_str += f" -> {return_ann}"
        if is_async:
            sig_str = f"async {sig_str}"

        self.symbols.append(
            SymbolInfo(
                id=func_id,
                name=node.name,
                kind=kind,
                source=SourceLocation(
                    file=self.relative_path,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    method="ast",
                ),
                docstring=docstring,
                signature=sig_str,
                parameters=params,
                parent_id=self._current_parent_id,
                decorators=decorators,
                metadata={"is_async": is_async, "return_type": return_ann},
            )
        )

        prev_scope = self._current_scope_id
        self._current_scope_id = func_id

        # Visit inner nodes to collect calls inside this function
        self.generic_visit(node)

        self._current_scope_id = prev_scope

    def visit_Call(self, node: ast.Call) -> None:
        """Extract function and method calls."""
        callee_name = self._get_expression_name(node.func)
        if not callee_name and isinstance(node.func, ast.Name):
            callee_name = node.func.id

        if callee_name and self._current_scope_id:
            self.calls.append(
                CallInfo(
                    caller_id=self._current_scope_id,
                    callee_name=callee_name,
                    source=SourceLocation(
                        file=self.relative_path,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        method="ast",
                    ),
                )
            )
        self.generic_visit(node)


class PythonAnalyzer(BaseAnalyzer):
    """Analyzer for Python source files using standard library AST."""

    def can_analyze(self, file_path: Path | str, language: Optional[str] = None) -> bool:
        path = Path(file_path)
        return path.suffix.lower() in [".py", ".pyw", ".pyi"] or language == "python"

    def analyze_file(self, file_path: Path, relative_path: str) -> AnalysisResult:
        rel_str = relative_path.replace("\\", "/")
        try:
            source_code = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source_code, filename=str(file_path))
            visitor = PythonASTVisitor(relative_path=rel_str, source_code=source_code)
            visitor.visit(tree)

            # Module docstring
            module_docstring = ast.get_docstring(tree)

            return AnalysisResult(
                file_path=rel_str,
                language="python",
                symbols=visitor.symbols,
                imports=visitor.imports,
                calls=visitor.calls,
                inheritances=visitor.inheritances,
                metadata={
                    "docstring": module_docstring,
                    "syntax_valid": True,
                },
            )
        except SyntaxError as se:
            logger.warning(f"Syntax error in {rel_str}: {se}")
            return AnalysisResult(
                file_path=rel_str,
                language="python",
                metadata={"syntax_valid": False, "error": str(se)},
            )
        except Exception as e:
            logger.warning(f"Failed to analyze {rel_str}: {e}")
            return AnalysisResult(
                file_path=rel_str,
                language="python",
                metadata={"syntax_valid": False, "error": str(e)},
            )
