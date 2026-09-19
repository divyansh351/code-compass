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
        """Search components, modules, and symbols matching query string."""
        q_lower = query.lower()
        results: List[Dict[str, Any]] = []

        # 1. Search components
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

        return results[:25]

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

        return {
            "file": norm_path,
            "symbols_count": len(file_symbols),
            "symbols": file_symbols,
            "relationships": {
                "outgoing": edges_out,
                "incoming": edges_in,
            },
        }

    def get_change_surface(self, component: str) -> Dict[str, Any]:
        """Compute the change surface / blast radius for a component."""
        graph = self._ensure_graph()
        return graph.get_change_surface(component)


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

    return mcp


def run_server(config: CompassConfig) -> None:
    """Run the FastMCP server over stdio transport."""
    server = create_mcp_server(config.knowledge.path)
    logger.info(f"Starting Code Compass MCP server for knowledge at: {config.knowledge.path}")
    server.run(transport="stdio")
