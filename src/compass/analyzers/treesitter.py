"""Multi-language AST analyzer using tree-sitter for symbol extraction."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

# ---------------------------------------------------------------------------
# Language → tree-sitter language name mapping
# ---------------------------------------------------------------------------
LANGUAGE_MAP: Dict[str, str] = {
    "javascript": "javascript",
    "typescript": "typescript",
    "go": "go",
    "rust": "rust",
    "java": "java",
    "ruby": "ruby",
    "c": "c",
    "cpp": "cpp",
}

# ---------------------------------------------------------------------------
# Per-language tree-sitter S-expression query strings
# Each tuple: (node_type, extraction_kind)
# We walk the tree manually for portability across tree-sitter query API versions.
# ---------------------------------------------------------------------------

# Node types we care about per language
SYMBOL_NODE_TYPES: Dict[str, Dict[str, str]] = {
    "javascript": {
        "class_declaration": "class",
        "class_expression": "class",
        "function_declaration": "function",
        "function_expression": "function",
        "arrow_function": "function",
        "method_definition": "method",
        "generator_function_declaration": "function",
    },
    "typescript": {
        "class_declaration": "class",
        "abstract_class_declaration": "class",
        "function_declaration": "function",
        "arrow_function": "function",
        "method_definition": "method",
        "function_signature": "function",
        "method_signature": "method",
        "interface_declaration": "class",  # treat interface as class-like
        "type_alias_declaration": "class",
    },
    "go": {
        "function_declaration": "function",
        "method_declaration": "method",
        "type_spec": "class",           # struct/interface definitions (child of type_declaration)
    },
    "rust": {
        "function_item": "function",
        "struct_item": "class",         # impl_item excluded — it duplicates struct_item
        "enum_item": "class",
        "trait_item": "class",
    },
    "java": {
        "class_declaration": "class",
        "interface_declaration": "class",
        "enum_declaration": "class",
        "method_declaration": "method",
        "constructor_declaration": "method",
    },
    "ruby": {
        "class": "class",
        "module": "class",
        "method": "method",
        "singleton_method": "method",
    },
    "c": {
        "function_definition": "function",
        "struct_specifier": "class",
    },
    "cpp": {
        "function_definition": "function",
        "class_specifier": "class",
        "struct_specifier": "class",
        "template_declaration": "function",
    },
}

IMPORT_NODE_TYPES: Dict[str, List[str]] = {
    "javascript": ["import_statement", "call_expression"],   # call_expression catches require()
    "typescript": ["import_statement", "import_require_clause"],
    "go": ["import_declaration"],                              # import_spec is a child; handled inside
    "rust": ["use_declaration"],
    "java": ["import_declaration"],
    "ruby": ["call"],  # require / require_relative
    "c": ["preproc_include"],
    "cpp": ["preproc_include"],
}


def _get_node_text(node: Any, source: bytes) -> str:
    """Extract the UTF-8 text for a tree-sitter node."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _find_child_by_type(node: Any, *types: str) -> Optional[Any]:
    """Return the first direct child matching one of the given node types."""
    for child in node.children:
        if child.type in types:
            return child
    return None


def _find_name(node: Any, source: bytes, lang: str) -> str:
    """Best-effort extraction of a symbol name from a node."""
    # Try common name-bearing child types
    for name_type in ("identifier", "type_identifier", "field_identifier", "property_identifier"):
        child = _find_child_by_type(node, name_type)
        if child:
            return _get_node_text(child, source)

    # Go: type_spec has a name as first identifier child inside type_declaration
    if lang == "go" and node.type == "type_declaration":
        for child in node.children:
            if child.type == "type_spec":
                id_child = _find_child_by_type(child, "type_identifier")
                if id_child:
                    return _get_node_text(id_child, source)

    # Rust: impl_item — use the type being implemented
    if lang == "rust" and node.type == "impl_item":
        for child in node.children:
            if child.type in ("type_identifier", "scoped_type_identifier"):
                return _get_node_text(child, source)

    # Java: fallback to first type_identifier
    for child in node.children:
        if child.type in ("type_identifier",):
            return _get_node_text(child, source)

    return "<anonymous>"


def _extract_parameters(node: Any, source: bytes) -> List[str]:
    """Extract parameter names from a parameter list node."""
    params: List[str] = []
    param_node = _find_child_by_type(node, "formal_parameters", "parameters", "parameter_list")
    if not param_node:
        return params
    for child in param_node.children:
        if child.type in ("identifier", "required_parameter", "optional_parameter",
                          "rest_pattern", "parameter_declaration", "variadic_parameter"):
            id_child = _find_child_by_type(child, "identifier") or child
            text = _get_node_text(id_child, source).strip("()\n ")
            if text and text not in (",", "(", ")"):
                params.append(text)
    return params


def _extract_imports_from_node(node: Any, source: bytes, lang: str) -> List[str]:
    """Return a list of module/path strings imported by this node."""
    modules: List[str] = []
    raw = _get_node_text(node, source)

    if lang in ("javascript", "typescript"):
        # import ... from 'module'  /  require('module')
        if node.type == "import_statement":
            src = _find_child_by_type(node, "string")
            if src:
                modules.append(_get_node_text(src, source).strip("\"'` "))
        elif node.type == "call_expression":
            fn = _find_child_by_type(node, "identifier")
            if fn and _get_node_text(fn, source) == "require":
                args = _find_child_by_type(node, "arguments")
                if args:
                    for child in args.children:
                        if child.type == "string":
                            modules.append(_get_node_text(child, source).strip("\"' "))

    elif lang == "go":
        # import_spec: "path/to/pkg"
        if node.type in ("import_declaration", "import_spec"):
            for child in node.children:
                if child.type == "string" or child.type == "interpreted_string_literal":
                    modules.append(_get_node_text(child, source).strip("\"` "))
            for child in node.children:
                if child.type == "import_spec_list":
                    for spec in child.children:
                        if spec.type == "import_spec":
                            path = _find_child_by_type(spec, "interpreted_string_literal", "string")
                            if path:
                                modules.append(_get_node_text(path, source).strip("\"` "))

    elif lang == "rust":
        # use std::io::Write;
        text = raw.replace("use ", "").replace(";", "").strip()
        modules.append(text)

    elif lang == "java":
        # import com.example.Foo;
        text = raw.replace("import ", "").replace(";", "").strip()
        modules.append(text)

    elif lang == "ruby":
        # require 'json'  /  require_relative '../base'
        if node.type == "call":
            fn = _find_child_by_type(node, "identifier")
            if fn and _get_node_text(fn, source) in ("require", "require_relative"):
                arg_list = _find_child_by_type(node, "argument_list")
                if arg_list:
                    for child in arg_list.children:
                        if child.type in ("string", "simple_string"):
                            modules.append(_get_node_text(child, source).strip("\"' "))

    elif lang in ("c", "cpp"):
        # #include <stdio.h>  /  #include "myheader.h"
        raw_stripped = raw.replace("#include", "").strip().strip("<>\"")
        modules.append(raw_stripped)

    return [m for m in modules if m]


def _walk(node: Any) -> Any:
    """Depth-first traversal of a tree-sitter tree."""
    yield node
    for child in node.children:
        yield from _walk(child)


class TreeSitterAnalyzer(BaseAnalyzer):
    """
    Universal AST analyzer for non-Python source files using tree-sitter.

    Extracts classes, functions/methods, and imports into an AnalysisResult
    with the identical shape to PythonAnalyzer — no downstream changes needed.
    """

    # Class-level parser cache: language_name → Parser instance
    _parser_cache: Dict[str, Any] = {}

    def __init__(self, language: str):
        """
        Args:
            language: Code Compass language name (e.g. 'javascript', 'go', 'rust').
        """
        self.language = language.lower()
        self._ts_lang_name = LANGUAGE_MAP.get(self.language)

    @classmethod
    def _get_parser(cls, ts_lang_name: str) -> Any:
        """Return a cached tree-sitter Parser for the given language."""
        if ts_lang_name not in cls._parser_cache:
            try:
                from tree_sitter_language_pack import get_parser  # type: ignore
                cls._parser_cache[ts_lang_name] = get_parser(ts_lang_name)
            except Exception as e:
                logger.error(f"tree-sitter: failed to load parser for '{ts_lang_name}': {e}")
                cls._parser_cache[ts_lang_name] = None
        return cls._parser_cache[ts_lang_name]

    def supports(self, language: str) -> bool:
        return language.lower() in LANGUAGE_MAP

    def can_analyze(self, file_path: Path | str, language: Optional[str] = None) -> bool:
        """Return True if tree-sitter supports this file's language."""
        if language:
            return language.lower() in LANGUAGE_MAP
        ext = Path(file_path).suffix.lower()
        from compass.ingestion.filesystem import EXTENSION_TO_LANGUAGE
        lang = EXTENSION_TO_LANGUAGE.get(ext, "")
        return lang in LANGUAGE_MAP

    def analyze_file(self, file_path: Path, relative_path: str) -> AnalysisResult:
        result = AnalysisResult(file_path=relative_path, language=self.language)

        if not self._ts_lang_name:
            logger.debug(f"TreeSitterAnalyzer: no grammar registered for '{self.language}'")
            return result

        parser = self._get_parser(self._ts_lang_name)
        if parser is None:
            return AnalysisResult(file_path=relative_path, language=self.language)

        try:
            source_bytes = file_path.read_bytes()
        except OSError as e:
            logger.warning(f"TreeSitterAnalyzer: cannot read {file_path}: {e}")
            return AnalysisResult(file_path=relative_path, language=self.language)

        try:
            tree = parser.parse(source_bytes)
        except Exception as e:
            logger.warning(f"TreeSitterAnalyzer: parse error in {file_path}: {e}")
            return AnalysisResult(file_path=relative_path, language=self.language)

        symbol_types = SYMBOL_NODE_TYPES.get(self.language, {})
        import_types = set(IMPORT_NODE_TYPES.get(self.language, []))
        lang = self.language

        seen_ids: Dict[str, int] = {}

        for node in _walk(tree.root_node):
            ntype = node.type

            # ── Symbols (classes / functions / methods) ──────────────────────
            if ntype in symbol_types:
                # Skip arrow_function nodes that are anonymous callbacks/params —
                # only capture them when the parent is a variable_declarator (named export).
                if ntype == "arrow_function":
                    parent = node.parent
                    if parent is None or parent.type not in (
                        "variable_declarator", "assignment_expression", "pair",
                    ):
                        continue

                kind = symbol_types[ntype]
                raw_name = _find_name(node, source_bytes, lang)

                # Skip truly anonymous or single-char noise (e.g. callback params)
                if not raw_name or raw_name == "<anonymous>" or (
                    len(raw_name) == 1 and lang in ("typescript", "javascript")
                ):
                    continue

                # Make IDs unique when name clashes exist
                base_id = build_symbol_id(relative_path, raw_name)
                seen_ids[base_id] = seen_ids.get(base_id, 0) + 1
                sym_id = base_id if seen_ids[base_id] == 1 else f"{base_id}_{seen_ids[base_id]}"

                loc = SourceLocation(
                    file=relative_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                )

                params: List[str] = []
                if kind in ("function", "method"):
                    params = _extract_parameters(node, source_bytes)
                    sig = f"{raw_name}({', '.join(params)})"
                else:
                    sig = raw_name

                # Inheritance: look for superclass / heritage clause (JS/TS/Java)
                bases: List[str] = []
                for child in node.children:
                    if child.type in ("class_heritage", "superclass", "super_interfaces",
                                       "extends_clause", "implements_clause"):
                        for sub in child.children:
                            if sub.type in ("identifier", "type_identifier"):
                                bases.append(_get_node_text(sub, source_bytes))

                sym = SymbolInfo(
                    id=sym_id,
                    name=raw_name,
                    kind=kind,
                    source=loc,
                    signature=sig,
                    parameters=params,
                    docstring=None,
                    decorators=[],
                    metadata={"bases": bases, "node_type": ntype},
                )
                result.symbols.append(sym)

                # Record inheritance relationships
                if kind == "class" and bases:
                    for base in bases:
                        result.inheritances.append(
                            InheritanceInfo(
                                subclass_id=sym_id,
                                superclass_name=base,
                                source=loc,
                            )
                        )

            # ── Imports ──────────────────────────────────────────────────────
            if ntype in import_types:
                mods = _extract_imports_from_node(node, source_bytes, lang)
                for mod in mods:
                    loc = SourceLocation(
                        file=relative_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    )
                    # Treat the first path segment as top-level module name
                    top = mod.split("/")[0].split("::")[0].split(".")[0].strip()
                    is_relative = mod.startswith(".") or mod.startswith("..")
                    result.imports.append(
                        ImportInfo(
                            module=mod,
                            name=top,
                            alias=None,
                            is_relative=is_relative,
                            source=loc,
                        )
                    )

        result.metadata["line_count"] = source_bytes.count(b"\n") + 1
        result.metadata["language"] = self.language
        result.metadata["analyzer"] = "tree-sitter"

        logger.debug(
            f"TreeSitterAnalyzer [{self.language}] {relative_path}: "
            f"{len(result.symbols)} symbols, {len(result.imports)} imports"
        )
        return result
