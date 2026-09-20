"""Local MCP Server exposing Code Compass repository knowledge."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

try:
    # MCP 2.x
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:
        # MCP 1.x
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        # Generic fallback shim if MCP SDK structure differs
        class FastMCP:  # type: ignore
            def __init__(self, name: str, **kwargs):
                self.name = name
                self.tools = {}

            def tool(self, *args, **kwargs):
                def decorator(fn):
                    self.tools[fn.__name__] = fn
                    return fn
                return decorator

            def run(self, transport: str = "stdio"):
                logger.info(f"Running MCP server '{self.name}' on {transport}")

from compass.config.settings import CompassConfig
from compass.knowledge.graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service layer reading and querying generated local knowledge repository files."""

    def __init__(self, knowledge_path: Path | str):
        self.knowledge_path = Path(knowledge_path).resolve()
        self._graph: Optional[KnowledgeGraph] = None
        self._components_cache: Optional[List[Dict[str, Any]]] = None

    def _ensure_graph(self) -> KnowledgeGraph:
        """Load and cache the knowledge graph from disk."""
        if self._graph is None:
            graph_file = self.knowledge_path / "graph" / "graph.json"
            if graph_file.exists():
                try:
                    data = json.loads(graph_file.read_text(encoding="utf-8"))
                    self._graph = KnowledgeGraph.from_dict(data)
                except Exception as e:
                    logger.error(f"Error loading graph from {graph_file}: {e}")
                    self._graph = KnowledgeGraph()
            else:
                self._graph = KnowledgeGraph()
        return self._graph

    def _get_components(self) -> List[Dict[str, Any]]:
        """Load component records from components.json."""
        if self._components_cache is None:
            comp_file = self.knowledge_path / "components" / "components.json"
            if comp_file.exists():
                try:
                    self._components_cache = json.loads(comp_file.read_text(encoding="utf-8"))
                except Exception:
                    self._components_cache = []
            else:
                self._components_cache = []
        return self._components_cache

    def get_project_overview(self) -> str:
        """Retrieve the deterministic architecture overview."""
        overview_file = self.knowledge_path / "architecture" / "overview.md"
        if overview_file.exists():
            return overview_file.read_text(encoding="utf-8")
        return "Architecture overview not found. Run 'compass build' to generate knowledge."

    def search_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Search components, modules, symbols, and human-curated documentation matching query string."""
        q_lower = query.lower()
        results: List[Dict[str, Any]] = []

        # 1. Search components (AST-extracted)
        components = self._get_components()
        for comp in components:
            name = comp.get("name", "")
            comp_id = comp.get("id", "")
            doc = comp.get("docstring") or ""
            if (
                q_lower in name.lower()
                or q_lower in comp_id.lower()
                or q_lower in doc.lower()
            ):
                results.append({
                    "id": comp_id,
                    "name": name,
                    "type": comp.get("type"),
                    "source": comp.get("source"),
                    "docstring": (doc[:150] + "...") if len(doc) > 150 else doc,
                })

        # 2. Search human-curated folders (conventions, workflows, decisions, architecture)
        doc_dirs = ["conventions", "workflows", "decisions", "architecture"]
        for dir_name in doc_dirs:
            target_dir = self.knowledge_path / dir_name
            if target_dir.exists() and target_dir.is_dir():
                for md_file in target_dir.glob("*.md"):
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        if q_lower in md_file.name.lower() or q_lower in content.lower():
                            snippet = content[:200].replace("\n", " ")
                            results.append({
                                "id": f"doc:{dir_name}/{md_file.name}",
                                "name": md_file.stem.replace("-", " ").title(),
                                "type": f"documentation ({dir_name})",
                                "source": {"file": f"{dir_name}/{md_file.name}", "method": "manual"},
                                "docstring": snippet + ("..." if len(content) > 200 else ""),
                            })
                    except Exception:
                        pass

        return results[:30]

    def get_component(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a component by name or ID."""
        components = self._get_components()
        name_lower = name.lower()
        
        # Try exact ID match first
        for comp in components:
            if comp.get("id") == name:
                return comp

        # Try exact name match
        for comp in components:
            if comp.get("name", "").lower() == name_lower:
                return comp

        # Try substring match
        for comp in components:
            if name_lower in comp.get("name", "").lower() or name_lower in comp.get("id", "").lower():
                return comp

        return {"error": f"Component '{name}' not found in knowledge repository."}

    def get_dependencies(self, name: str) -> Dict[str, Any]:
        """Get outgoing dependencies and incoming dependents for a component."""
        graph = self._ensure_graph()
        deps = graph.get_dependencies(name)
        dependents = graph.get_dependents(name)
        return {
            "component": name,
            "dependencies": deps,
            "dependents": dependents,
            "dependencies_count": len(deps),
            "dependents_count": len(dependents),
        }

    def get_file_context(self, path: str) -> Dict[str, Any]:
        """Get all symbols, modules, and metadata associated with a source file path."""
        norm_path = path.replace("\\", "/")
        components = self._get_components()
        file_symbols = []

        for comp in components:
            src = comp.get("source") or {}
            file_in_src = src.get("file", "")
            if file_in_src and (file_in_src == norm_path or norm_path.endswith(file_in_src) or file_in_src.endswith(norm_path)):
                file_symbols.append(comp)

        graph = self._ensure_graph()
        file_node_id = f"file:{norm_path}"
        edges_out = graph.get_outgoing_edges(file_node_id)
        edges_in = graph.get_incoming_edges(file_node_id)

        # Check for mirrored Markdown file in knowledge/files/
        file_md_path = self.knowledge_path / "files" / f"{norm_path}.md"
        markdown_summary = ""
        if file_md_path.exists():
            try:
                markdown_summary = file_md_path.read_text(encoding="utf-8")
            except Exception:
                markdown_summary = ""

        return {
            "file": norm_path,
            "symbols_count": len(file_symbols),
            "symbols": file_symbols,
            "markdown_summary": markdown_summary,
            "relationships": {
                "outgoing": edges_out,
                "incoming": edges_in,
            },
        }

    def get_change_surface(self, component: str) -> Dict[str, Any]:
        """Compute the change surface / blast radius for a component."""
        graph = self._ensure_graph()
        return graph.get_change_surface(component)


    def update_knowledge(
        self,
        category: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Record or update findings, conventions, workflows, architecture decisions, or per-file notes."""
        import datetime
        import re

        allowed_categories = ["conventions", "workflows", "decisions", "architecture", "notes", "files"]
        cat = category.lower().strip()
        if cat not in allowed_categories:
            return {
                "success": False,
                "error": f"Invalid category '{category}'. Allowed: {', '.join(allowed_categories)}",
            }

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        tag_str = f"> **Tags**: {', '.join(tags)}\n" if tags else ""

        if cat == "files":
            # Direct update to mirrored file in knowledge/files/<title>.md
            target_dir = self.knowledge_path / "files"
            target_dir.mkdir(parents=True, exist_ok=True)
            norm_rel = title.replace("\\", "/").strip("/")
            file_path = target_dir / (norm_rel if norm_rel.endswith(".md") else f"{norm_rel}.md")
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if file_path.exists():
                existing = file_path.read_text(encoding="utf-8")
                addition = f"\n\n### Update ({now_iso})\n{tag_str}{content.strip()}\n"
                file_path.write_text(existing + addition, encoding="utf-8")
            else:
                doc_content = f"# File Knowledge: `{norm_rel}`\n\n> **Updated**: `{now_iso}` | **Origin**: `agent-curated`\n{tag_str}\n{content.strip()}\n"
                file_path.write_text(doc_content, encoding="utf-8")

            return {
                "success": True,
                "category": "files",
                "title": title,
                "file": f"files/{norm_rel}.md",
                "message": f"Successfully updated file knowledge in knowledge/files/{norm_rel}.md",
            }

        target_dir = self.knowledge_path / cat
        target_dir.mkdir(parents=True, exist_ok=True)

        # Generate a clean filename slug
        clean_slug = re.sub(r"[^\w\-_]", "-", title.lower().strip()).strip("-")
        filename = clean_slug if clean_slug.endswith(".md") else f"{clean_slug}.md"
        if not filename or filename == ".md":
            filename = "note.md"

        file_path = target_dir / filename

        doc_content = f"""# {title}

> **Category**: `{cat}` | **Updated**: `{now_iso}` | **Origin**: `agent-curated`
{tag_str}
{content.strip()}
"""
        file_path.write_text(doc_content, encoding="utf-8")
        logger.info(f"Updated knowledge document: {file_path}")

        return {
            "success": True,
            "category": cat,
            "title": title,
            "file": f"{cat}/{filename}",
            "message": f"Successfully recorded '{title}' in knowledge/{cat}/{filename}",
        }

    def update_overview(self, summary: str) -> Dict[str, Any]:
        """Update or enrich the Executive AI Overview in architecture/overview.md."""
        import datetime

        overview_file = self.knowledge_path / "architecture" / "overview.md"
        if not overview_file.exists():
            return {"success": False, "error": "architecture/overview.md not found. Run compass build first."}

        text = overview_file.read_text(encoding="utf-8")
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        new_header = f"## Executive Overview\n> {summary.strip()}\n>\n> *Curated by AI agent ({now_iso})*"

        if "## Executive Overview" in text:
            parts = text.split("## Executive Overview", 1)
            rest = parts[1]
            if "## Repository" in rest:
                after_repo = "## Repository" + rest.split("## Repository", 1)[1]
                updated_text = f"{parts[0]}{new_header}\n\n{after_repo}"
            else:
                updated_text = f"{parts[0]}{new_header}\n\n{rest}"
        else:
            if "## Repository" in text:
                updated_text = text.replace("## Repository", f"{new_header}\n\n## Repository", 1)
            else:
                updated_text = f"{new_header}\n\n{text}"

    def commit_knowledge(self, message: Optional[str] = None) -> Dict[str, Any]:
        """Commit changes in the local knowledge repository using Git on-demand."""
        import shutil
        import subprocess

        if not self.knowledge_path.exists():
            return {"success": False, "error": f"Knowledge directory not found at {self.knowledge_path}"}

        git_cmd = shutil.which("git")
        if not git_cmd:
            return {"success": False, "error": "Git executable not found in system PATH"}

        try:
            # Check if knowledge directory is initialized as a git repo
            if not (self.knowledge_path / ".git").exists():
                subprocess.run(["git", "init"], cwd=self.knowledge_path, capture_output=True, text=True, check=True)

            # Stage all changes
            subprocess.run(["git", "add", "."], cwd=self.knowledge_path, capture_output=True, text=True, check=True)

            # Check if there are changes to commit
            status_res = subprocess.run(["git", "status", "--porcelain"], cwd=self.knowledge_path, capture_output=True, text=True)
            if not status_res.stdout.strip():
                return {"success": True, "committed": False, "message": "No uncommitted changes in knowledge repository."}

            commit_msg = message.strip() if message and message.strip() else "docs(knowledge): update repository knowledge and conventions"
            commit_res = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.knowledge_path,
                capture_output=True,
                text=True,
                check=True,
            )

            # Get latest commit hash
            hash_res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=self.knowledge_path, capture_output=True, text=True)
            commit_hash = hash_res.stdout.strip() if hash_res.returncode == 0 else ""

            return {
                "success": True,
                "committed": True,
                "commit_hash": commit_hash,
                "message": f"Successfully committed knowledge changes ({commit_hash}): {commit_msg}",
            }
        except Exception as e:
            return {"success": False, "error": f"Git commit failed: {e}"}


def create_mcp_server(knowledge_path: Path | str) -> FastMCP:
    """Instantiate and configure FastMCP server with Code Compass knowledge tools."""
    service = KnowledgeService(knowledge_path)
    mcp = FastMCP("code-compass", description="Code Compass local repository knowledge provider")

    @mcp.tool()
    def search_knowledge(query: str) -> str:
        """Search the local knowledge repository for components, classes, functions, and modules."""
        results = service.search_knowledge(query)
        return json.dumps(results, indent=2)

    @mcp.tool()
    def get_project_overview() -> str:
        """Return the high-level architecture overview of the repository."""
        return service.get_project_overview()

    @mcp.tool()
    def get_component(name: str) -> str:
        """Return detailed information, signature, provenance, and docstring of a module/class/function."""
        comp = service.get_component(name)
        return json.dumps(comp, indent=2)

    @mcp.tool()
    def get_dependencies(name: str) -> str:
        """Return direct dependencies and dependents for a given component or symbol."""
        deps = service.get_dependencies(name)
        return json.dumps(deps, indent=2)

    @mcp.tool()
    def get_file_context(path: str) -> str:
        """Return knowledge, symbols, and relationships associated with a source file."""
        ctx = service.get_file_context(path)
        return json.dumps(ctx, indent=2)

    @mcp.tool()
    def get_change_surface(component: str) -> str:
        """Return the blast radius and directly related components from the graph for a component."""
        surface = service.get_change_surface(component)
        return json.dumps(surface, indent=2)

    @mcp.tool()
    def update_knowledge(category: str, title: str, content: str) -> str:
        """Save or update a project convention, workflow, architecture decision, finding, or file note."""
        res = service.update_knowledge(category=category, title=title, content=content)
        return json.dumps(res, indent=2)

    @mcp.tool()
    def update_overview(summary: str) -> str:
        """Save or update the high-level AI Executive Overview in architecture/overview.md."""
        res = service.update_overview(summary=summary)
        return json.dumps(res, indent=2)

    @mcp.tool()
    def commit_knowledge(message: Optional[str] = None) -> str:
        """Commit staged and modified knowledge files to the knowledge repository Git history on user demand."""
        res = service.commit_knowledge(message=message)
        return json.dumps(res, indent=2)

    return mcp


def run_server(config: CompassConfig) -> None:
    """Run the FastMCP server over stdio transport."""
    server = create_mcp_server(config.knowledge.path)
    logger.info(f"Starting Code Compass MCP server for knowledge at: {config.knowledge.path}")
    server.run(transport="stdio")
