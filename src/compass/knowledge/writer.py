"""Knowledge repository writer generating human-readable and machine-readable artifacts."""

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Set
import yaml

from compass.config.settings import CompassConfig
from compass.ingestion.repository import RepositoryData
from compass.knowledge.graph import KnowledgeGraph
from compass.knowledge.models import KnowledgeNodeType, RelationshipType


class KnowledgeWriter:
    """Writes the knowledge graph and architecture artifacts to a local directory structure."""

    def __init__(self, config: CompassConfig):
        self.config = config
        self.output_dir = Path(config.knowledge.path).resolve()

    def write(self, graph: KnowledgeGraph, repo_data: RepositoryData) -> Path:
        """Generate the full knowledge repository."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Subdirectories
        for sub in [
            "architecture",
            "components",
            "conventions",
            "workflows",
            "decisions",
            "files",
            "graph",
            "metadata",
        ]:
            (self.output_dir / sub).mkdir(parents=True, exist_ok=True)

        # 2. Write manifest.yaml
        self._write_manifest(graph, repo_data)

        # 3. Write architecture/overview.md
        self._write_architecture_overview(graph, repo_data)

        # 4. Write components/components.json
        self._write_components(graph)

        # 5. Write mirrored per-file knowledge in files/
        self._write_files_knowledge(graph, repo_data)

        # 6. Write graph/graph.json
        self._write_graph(graph)

        # 7. Write metadata/build.json
        self._write_metadata(graph, repo_data)

        return self.output_dir

    def _write_manifest(self, graph: KnowledgeGraph, repo_data: RepositoryData) -> None:
        manifest_data = {
            "version": "1.0",
            "project": {
                "name": self.config.project.name,
                "version": self.config.project.version,
                "description": self.config.project.description,
            },
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "generator": "code-compass 0.1.0",
            "statistics": {
                "total_files": repo_data.scan_result.total_files,
                "total_lines": repo_data.scan_result.total_lines,
                "total_size_bytes": repo_data.scan_result.total_size_bytes,
                "graph_nodes": graph.node_count,
                "graph_edges": graph.edge_count,
            },
            "languages": list(repo_data.scan_result.languages_detected),
        }
        with open(self.output_dir / "manifest.yaml", "w", encoding="utf-8") as f:
            yaml.dump(manifest_data, f, sort_keys=False, default_flow_style=False)

    def _write_architecture_overview(
        self, graph: KnowledgeGraph, repo_data: RepositoryData
    ) -> None:
        overview_file = self.output_dir / "architecture" / "overview.md"
        custom_ai_overview = ""
        if overview_file.exists():
            try:
                old_text = overview_file.read_text(encoding="utf-8")
                if "## Executive Overview" in old_text and "## Repository" in old_text:
                    custom_ai_overview = old_text.split("## Executive Overview", 1)[1].split("## Repository", 1)[0].strip()
            except Exception:
                custom_ai_overview = ""

        # Default overview if not yet supplied by active agent
        if not custom_ai_overview:
            modules = graph.find_nodes_by_type(KnowledgeNodeType.MODULE)
            classes = graph.find_nodes_by_type(KnowledgeNodeType.CLASS)
            ext_deps = graph.find_nodes_by_type(KnowledgeNodeType.EXTERNAL_DEPENDENCY)
            
            deterministic_summary = (
                f"`{self.config.project.name}` is a software project comprising "
                f"{repo_data.scan_result.total_files} files across "
                f"{', '.join(sorted(repo_data.scan_result.languages_detected)) or 'multiple languages'}. "
                f"The codebase defines {len(modules)} internal modules and {len(classes)} classes, "
                f"relying on {len(ext_deps)} external dependencies ({', '.join(sorted([d.name for d in ext_deps])[:5]) or 'standard library'})."
            )
            if self.config.project.description:
                deterministic_summary = f"{self.config.project.description.strip()} — {deterministic_summary}"
            custom_ai_overview = deterministic_summary

        lines: List[str] = []
        lines.append("# Architecture Overview")
        lines.append("")
        lines.append("## Executive Overview")
        lines.append(f"> {custom_ai_overview}")
        lines.append("")
        lines.append("## Repository")
        lines.append(f"`{self.config.project.name}`")
        lines.append("")

        # Languages
        lines.append("## Languages")
        if repo_data.scan_result.languages_detected:
            for lang in sorted(repo_data.scan_result.languages_detected):
                lines.append(f"- {lang.capitalize()}")
        else:
            lines.append("- None detected")
        lines.append("")

        # Structure / Top-level directories
        lines.append("## Structure")
        top_dirs: Set[str] = set()
        for f in repo_data.files:
            parts = Path(f.relative_path).parts
            if len(parts) > 1:
                top_dirs.add(parts[0])
        if top_dirs:
            for d in sorted(top_dirs):
                lines.append(f"- `{d}/`")
        else:
            lines.append("- `.` (flat structure)")
        lines.append("")

        # Internal Modules
        lines.append("## Internal Modules")
        modules = graph.find_nodes_by_type(KnowledgeNodeType.MODULE)
        if modules:
            for mod in sorted(modules, key=lambda m: m.name):
                lines.append(f"- `{mod.name}`")
        else:
            lines.append("- None detected")
        lines.append("")

        # External Dependencies
        lines.append("## External Dependencies")
        ext_deps = graph.find_nodes_by_type(KnowledgeNodeType.EXTERNAL_DEPENDENCY)
        if ext_deps:
            for dep in sorted(ext_deps, key=lambda d: d.name):
                lines.append(f"- `{dep.name}`")
        else:
            lines.append("- Standard Library only / None detected")
        lines.append("")

        # Relationships
        lines.append("## Relationships")
        raw_graph_data = graph.to_dict()
        rel_pairs: Set[str] = set()
        for edge in raw_graph_data.get("edges", []):
            if edge.get("type") in ["IMPORTS", "DEPENDS_ON", "INHERITS"]:
                src = edge["source"].replace("module:", "").replace("class:", "")
                tgt = edge["target"].replace("module:", "").replace("class:", "").replace("external:", "")
                if src != tgt:
                    rel_pairs.add(f"{src} → {tgt}")

        if rel_pairs:
            for rel in sorted(rel_pairs)[:50]:  # Cap at top 50 in markdown
                lines.append(f"- {rel}")
            if len(rel_pairs) > 50:
                lines.append(f"- ... and {len(rel_pairs) - 50} more (see graph/graph.json)")
        else:
            lines.append("- No cross-module relationships detected")
        lines.append("")

        (self.output_dir / "architecture" / "overview.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )

    def _write_components(self, graph: KnowledgeGraph) -> None:
        components_list: List[Dict[str, Any]] = []
        for node in graph._nodes_by_id.values():
            if node.type in [
                KnowledgeNodeType.MODULE,
                KnowledgeNodeType.CLASS,
                KnowledgeNodeType.FUNCTION,
                KnowledgeNodeType.EXTERNAL_DEPENDENCY,
            ]:
                components_list.append(node.model_dump())

        with open(self.output_dir / "components" / "components.json", "w", encoding="utf-8") as f:
            json.dump(components_list, f, indent=2)

    def _write_files_knowledge(self, graph: KnowledgeGraph, repo_data: RepositoryData) -> None:
        """Write mirrored per-file Markdown documentation into knowledge/files/."""
        files_dir = self.output_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        for scanned in repo_data.files:
            rel_norm = scanned.relative_path.replace("\\", "/")
            target_md = files_dir / f"{rel_norm}.md"
            target_md.parent.mkdir(parents=True, exist_ok=True)

            # Preserve existing custom notes if file exists
            custom_notes = ""
            if target_md.exists():
                try:
                    old_text = target_md.read_text(encoding="utf-8")
                    if "## Curated Notes & Agent Learnings" in old_text:
                        custom_notes = old_text.split("## Curated Notes & Agent Learnings", 1)[1]
                except Exception:
                    custom_notes = ""

            # Collect symbols associated with this file
            file_symbols = [
                n for n in graph._nodes_by_id.values()
                if n.source and n.source.file and n.source.file == rel_norm
            ]

            lines = [
                f"# File: `{rel_norm}`",
                "",
                "## Overview",
                f"- **Language**: {scanned.language.capitalize() if scanned.language else 'Unknown'}",
                f"- **Lines**: {scanned.line_count}",
                f"- **Size**: {scanned.size_bytes} bytes",
                "",
            ]

            # Classes
            classes = [s for s in file_symbols if s.type == KnowledgeNodeType.CLASS]
            if classes:
                lines.append("## Classes")
                for cls in classes:
                    lines.append(f"### `class {cls.name}`")
                    if cls.docstring:
                        lines.append(f"> {cls.docstring.strip()}")
                    if hasattr(cls, "bases") and cls.bases:
                        lines.append(f"- **Inherits from**: {', '.join(cls.bases)}")
                    lines.append("")

            # Functions & Methods
            functions = [s for s in file_symbols if s.type in (KnowledgeNodeType.FUNCTION, KnowledgeNodeType.METHOD)]
            if functions:
                lines.append("## Functions & Methods")
                for fn in functions:
                    sig = getattr(fn, "signature", None) or f"def {fn.name}()"
                    lines.append(f"### `{sig}`")
                    if fn.docstring:
                        lines.append(f"> {fn.docstring.strip()}")
                    lines.append("")

            # Dependencies & Dependents
            deps = graph.get_dependencies(f"file:{rel_norm}")
            if not deps:
                # check module node
                mod_id = f"module:{rel_norm.removesuffix('.py').replace('/', '.')}"
                deps = graph.get_dependencies(mod_id)

            if deps:
                lines.append("## Dependencies")
                for d in deps:
                    lines.append(f"- **{d.get('relationship', 'DEPENDS_ON')}** → `{d.get('name', d.get('id'))}`")
                lines.append("")

            # Curated Notes Section
            lines.append("## Curated Notes & Agent Learnings")
            if custom_notes.strip():
                lines.append(custom_notes.strip())
            else:
                lines.append("<!-- Add file-specific gotchas, architectural notes, or agent learnings below -->")
            lines.append("")

            target_md.write_text("\n".join(lines), encoding="utf-8")

    def _write_graph(self, graph: KnowledgeGraph) -> None:
        with open(self.output_dir / "graph" / "graph.json", "w", encoding="utf-8") as f:
            f.write(graph.to_json(indent=2))

    def _write_metadata(
        self, graph: KnowledgeGraph, repo_data: RepositoryData
    ) -> None:
        metadata_content = {
            "build_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_path": str(repo_data.root_path),
            "files_count": repo_data.scan_result.total_files,
            "lines_of_code": repo_data.scan_result.total_lines,
            "size_bytes": repo_data.scan_result.total_size_bytes,
            "git": {
                "is_repo": repo_data.git_summary.is_git_repo,
                "branch": repo_data.git_summary.current_branch,
                "head_commit": repo_data.git_summary.head_commit,
                "commits_analyzed": len(repo_data.git_summary.commits),
            },
            "nodes_count": graph.node_count,
            "edges_count": graph.edge_count,
        }
        with open(self.output_dir / "metadata" / "build.json", "w", encoding="utf-8") as f:
            json.dump(metadata_content, f, indent=2)
