"""Knowledge graph builder connecting ingestion and analyzers."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from compass.analyzers.files import FileAnalyzer
from compass.analyzers.imports import classify_import
from compass.analyzers.python import PythonAnalyzer
from compass.config.settings import CompassConfig
from compass.ingestion.repository import RepositoryData
from compass.knowledge.graph import KnowledgeGraph
from compass.knowledge.models import (
    ClassNode,
    ExternalDependencyNode,
    FileNode,
    FunctionNode,
    GitCommitNode,
    KnowledgeEdge,
    KnowledgeNodeType,
    ModuleNode,
    ProjectNode,
    Provenance,
    RelationshipType,
)

logger = logging.getLogger(__name__)


class KnowledgeBuilder:
    """Builds a structured knowledge graph from repository scan and analysis data."""

    def __init__(self, config: CompassConfig):
        self.config = config
        self.python_analyzer = PythonAnalyzer()
        self.file_analyzer = FileAnalyzer()

    def build(self, repo_data: RepositoryData) -> KnowledgeGraph:
        """Construct the knowledge graph from repository data."""
        graph = KnowledgeGraph()

        # 1. Project Root Node
        project_id = f"project:{self.config.project.name}"
        project_node = ProjectNode(
            id=project_id,
            name=self.config.project.name,
            version=self.config.project.version,
            languages=list(repo_data.scan_result.languages_detected),
            source=Provenance(file="", line_start=0, line_end=0, method="filesystem"),
            metadata={
                "total_files": repo_data.scan_result.total_files,
                "total_lines": repo_data.scan_result.total_lines,
                "total_size_bytes": repo_data.scan_result.total_size_bytes,
                "description": self.config.project.description,
            },
        )
        graph.add_node(project_node)

        # 2. File Nodes and Project -> File CONTAINS relationships
        internal_packages: Set[str] = set()
        for scanned in repo_data.files:
            file_id = f"file:{scanned.relative_path}"
            file_node = FileNode(
                id=file_id,
                name=Path(scanned.relative_path).name,
                path=scanned.relative_path,
                extension=scanned.extension,
                size_bytes=scanned.size_bytes,
                line_count=scanned.line_count,
                language=scanned.language,
                source=Provenance(
                    file=scanned.relative_path,
                    line_start=1,
                    line_end=scanned.line_count,
                    method="filesystem",
                ),
            )
            graph.add_node(file_node)
            graph.add_edge(
                KnowledgeEdge(
                    source_id=project_id,
                    target_id=file_id,
                    type=RelationshipType.CONTAINS,
                )
            )

            # Discover top-level directory names to treat as internal package names
            parts = Path(scanned.relative_path).parts
            if len(parts) > 1:
                internal_packages.add(parts[0])
                if parts[0] in ["src", "lib", "app", "pkg"] and len(parts) > 2:
                    internal_packages.add(parts[1])
            elif scanned.extension == ".py":
                internal_packages.add(Path(scanned.relative_path).stem)

        # 3. Analyze Python Source Files
        if self.config.analysis.symbols or self.config.analysis.imports:
            python_files = repo_data.get_files_by_language("python")
            for py_file in python_files:
                self._process_python_file(py_file.absolute_path, py_file.relative_path, graph, project_id, internal_packages)

        # 4. Integrate Git Commits & MODIFIED_BY relationships
        if self.config.analysis.git_history and repo_data.git_summary.is_git_repo:
            for commit in repo_data.git_summary.commits:
                commit_id = f"commit:{commit.hexsha[:8]}"
                commit_node = GitCommitNode(
                    id=commit_id,
                    name=commit.hexsha[:8],
                    hexsha=commit.hexsha,
                    author_name=commit.author_name,
                    committed_datetime=commit.committed_datetime,
                    message=commit.message,
                    source=Provenance(file="", line_start=0, line_end=0, method="git"),
                )
                graph.add_node(commit_node)

                # Connect modified files
                for changed_file in commit.files_changed:
                    f_id = f"file:{changed_file}"
                    graph.add_edge(
                        KnowledgeEdge(
                            source_id=f_id,
                            target_id=commit_id,
                            type=RelationshipType.MODIFIED_BY,
                        )
                    )

        return graph

    def _process_python_file(
        self,
        file_path: Path,
        relative_path: str,
        graph: KnowledgeGraph,
        project_id: str,
        internal_packages: Set[str],
    ) -> None:
        """Analyze a Python file and populate nodes and edges into the knowledge graph."""
        res = self.python_analyzer.analyze_file(file_path, relative_path)
        file_id = f"file:{relative_path}"

        # Create Module Node
        module_path = relative_path.replace("/", ".").replace("\\", ".").removesuffix(".py")
        if module_path.endswith(".__init__"):
            module_path = module_path.removesuffix(".__init__")
        
        module_id = f"module:{module_path}"
        module_node = ModuleNode(
            id=module_id,
            name=module_path,
            module_path=module_path,
            file_path=relative_path,
            docstring=res.metadata.get("docstring"),
            source=Provenance(file=relative_path, line_start=1, line_end=res.metadata.get("line_count", 1), method="ast"),
        )
        graph.add_node(module_node)
        graph.add_edge(
            KnowledgeEdge(
                source_id=file_id,
                target_id=module_id,
                type=RelationshipType.CONTAINS,
            )
        )

        # Symbols: Classes and Functions/Methods
        for sym in res.symbols:
            if sym.kind == "class":
                class_node = ClassNode(
                    id=f"class:{sym.id}",
                    name=sym.name,
                    bases=sym.metadata.get("bases", []),
                    decorators=sym.decorators,
                    docstring=sym.docstring,
                    source=Provenance(
                        file=sym.source.file,
                        line_start=sym.source.line_start,
                        line_end=sym.source.line_end,
                        method="ast",
                    ),
                )
                graph.add_node(class_node)
                
                # Class parent relationship
                parent_container = f"class:{sym.parent_id}" if sym.parent_id else module_id
                graph.add_edge(
                    KnowledgeEdge(
                        source_id=parent_container,
                        target_id=class_node.id,
                        type=RelationshipType.CONTAINS,
                    )
                )

            elif sym.kind in ("function", "method"):
                func_node = FunctionNode(
                    id=f"function:{sym.id}",
                    name=sym.name,
                    signature=sym.signature,
                    parameters=sym.parameters,
                    return_type=sym.metadata.get("return_type"),
                    is_async=sym.metadata.get("is_async", False),
                    decorators=sym.decorators,
                    docstring=sym.docstring,
                    source=Provenance(
                        file=sym.source.file,
                        line_start=sym.source.line_start,
                        line_end=sym.source.line_end,
                        method="ast",
                    ),
                )
                graph.add_node(func_node)

                parent_container = f"class:{sym.parent_id}" if sym.parent_id else module_id
                graph.add_edge(
                    KnowledgeEdge(
                        source_id=parent_container,
                        target_id=func_node.id,
                        type=RelationshipType.CONTAINS,
                    )
                )

        # Inheritance relationships
        for inh in res.inheritances:
            subclass_node_id = f"class:{inh.subclass_id}"
            superclass_name = inh.superclass_name
            # Try to resolve superclass target
            superclass_target_id = f"class:{superclass_name}"
            graph.add_edge(
                KnowledgeEdge(
                    source_id=subclass_node_id,
                    target_id=superclass_target_id,
                    type=RelationshipType.INHERITS,
                    metadata={"superclass_name": superclass_name},
                )
            )

        # Imports and External Dependencies
        for imp in res.imports:
            classification = classify_import(imp.module, imp.is_relative, internal_packages)
            
            if classification == "external":
                top_pkg = imp.module.split(".")[0]
                dep_id = f"external:{top_pkg}"
                if not graph.get_node(dep_id):
                    dep_node = ExternalDependencyNode(
                        id=dep_id,
                        name=top_pkg,
                        package_name=top_pkg,
                        source=Provenance(file=relative_path, line_start=imp.source.line_start, line_end=imp.source.line_end, method="ast"),
                    )
                    graph.add_node(dep_node)
                
                graph.add_edge(
                    KnowledgeEdge(
                        source_id=module_id,
                        target_id=dep_id,
                        type=RelationshipType.DEPENDS_ON,
                    )
                )
            elif classification == "internal":
                target_mod_id = f"module:{imp.module}" if imp.module else module_id
                graph.add_edge(
                    KnowledgeEdge(
                        source_id=module_id,
                        target_id=target_mod_id,
                        type=RelationshipType.IMPORTS,
                        metadata={"imported_name": imp.name, "alias": imp.alias},
                    )
                )

        # Function/Method Calls
        for call in res.calls:
            caller_node_id = f"function:{call.caller_id}"
            target_call_id = f"function:{call.callee_name}"
            graph.add_edge(
                KnowledgeEdge(
                    source_id=caller_node_id,
                    target_id=target_call_id,
                    type=RelationshipType.CALLS,
                    metadata={"callee_name": call.callee_name},
                )
            )
