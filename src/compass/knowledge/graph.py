"""Knowledge graph abstraction wrapping NetworkX."""

import json
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple
import networkx as nx

from compass.knowledge.models import (
    KnowledgeEdge,
    KnowledgeNode,
    KnowledgeNodeType,
    RelationshipType,
)


class KnowledgeGraph:
    """In-memory directed graph representing repository knowledge and relationships."""

    def __init__(self):
        self._graph = nx.DiGraph()
        self._nodes_by_id: Dict[str, KnowledgeNode] = {}

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def add_node(self, node: KnowledgeNode) -> None:
        """Add a knowledge node to the graph."""
        self._nodes_by_id[node.id] = node
        self._graph.add_node(
            node.id,
            type=node.type.value if hasattr(node.type, "value") else str(node.type),
            name=node.name,
            node_data=node.model_dump(),
        )

    def add_edge(self, edge: KnowledgeEdge) -> None:
        """Add a directed relationship between two nodes."""
        # Ensure endpoints exist in graph structure even if full node object is pending
        if not self._graph.has_node(edge.source_id):
            self._graph.add_node(edge.source_id, type="unknown", name=edge.source_id)
        if not self._graph.has_node(edge.target_id):
            self._graph.add_node(edge.target_id, type="unknown", name=edge.target_id)

        edge_type_val = (
            edge.type.value if hasattr(edge.type, "value") else str(edge.type)
        )
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            type=edge_type_val,
            is_deterministic=edge.is_deterministic,
            metadata=edge.metadata,
        )

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """Retrieve a node by its unique ID."""
        return self._nodes_by_id.get(node_id)

    def get_node_data(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve raw dictionary node data."""
        if self._graph.has_node(node_id):
            return self._graph.nodes[node_id].get("node_data")
        return None

    def find_nodes_by_name(self, name: str) -> List[KnowledgeNode]:
        """Find nodes matching a given symbol or component name (case-insensitive substring or exact)."""
        results: List[KnowledgeNode] = []
        name_lower = name.lower()
        for node in self._nodes_by_id.values():
            if node.name.lower() == name_lower or name_lower in node.id.lower():
                results.append(node)
        return results

    def find_nodes_by_type(self, node_type: KnowledgeNodeType | str) -> List[KnowledgeNode]:
        """Find all nodes of a specific entity type."""
        target_type = node_type.value if hasattr(node_type, "value") else str(node_type)
        return [
            node for node in self._nodes_by_id.values()
            if (node.type.value if hasattr(node.type, "value") else str(node.type)) == target_type
        ]

    def get_outgoing_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """Get all edges originating from node_id."""
        if not self._graph.has_node(node_id):
            return []
        edges = []
        for target, data in self._graph[node_id].items():
            edges.append({
                "source": node_id,
                "target": target,
                "type": data.get("type"),
                "metadata": data.get("metadata", {}),
            })
        return edges

    def get_incoming_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """Get all edges pointing into node_id."""
        if not self._graph.has_node(node_id):
            return []
        edges = []
        for source in self._graph.predecessors(node_id):
            data = self._graph[source][node_id]
            edges.append({
                "source": source,
                "target": node_id,
                "type": data.get("type"),
                "metadata": data.get("metadata", {}),
            })
        return edges

    def get_dependencies(self, node_id: str) -> List[Dict[str, Any]]:
        """Get direct and indirect dependencies of a node (imports, calls, inherits, depends_on)."""
        if not self._graph.has_node(node_id):
            # Try to resolve by name
            matches = self.find_nodes_by_name(node_id)
            if matches:
                node_id = matches[0].id
            else:
                return []

        deps = []
        for target, data in self._graph[node_id].items():
            rel_type = data.get("type")
            target_node = self.get_node(target)
            deps.append({
                "id": target,
                "name": target_node.name if target_node else target,
                "type": target_node.type.value if target_node else "unknown",
                "relationship": rel_type,
            })
        return deps

    def get_dependents(self, node_id: str) -> List[Dict[str, Any]]:
        """Get components that depend on / import / call the given node."""
        if not self._graph.has_node(node_id):
            matches = self.find_nodes_by_name(node_id)
            if matches:
                node_id = matches[0].id
            else:
                return []

        dependents = []
        for source in self._graph.predecessors(node_id):
            data = self._graph[source][node_id]
            rel_type = data.get("type")
            src_node = self.get_node(source)
            dependents.append({
                "id": source,
                "name": src_node.name if src_node else source,
                "type": src_node.type.value if src_node else "unknown",
                "relationship": rel_type,
            })
        return dependents

    def get_change_surface(self, identifier: str) -> Dict[str, Any]:
        """Compute the direct impact/change surface for a given component or file."""
        target_node = self.get_node(identifier)
        if not target_node:
            matches = self.find_nodes_by_name(identifier)
            if matches:
                target_node = matches[0]
                identifier = target_node.id
            else:
                return {"component": identifier, "found": False, "dependents": [], "dependencies": []}

        dependencies = self.get_dependencies(identifier)
        dependents = self.get_dependents(identifier)

        return {
            "component": identifier,
            "name": target_node.name,
            "type": target_node.type.value,
            "found": True,
            "dependencies": dependencies,
            "dependents": dependents,
            "total_impact_count": len(dependents),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize knowledge graph to clean dictionary format."""
        nodes = []
        for node_id, data in self._graph.nodes(data=True):
            node_obj = self._nodes_by_id.get(node_id)
            if node_obj:
                nodes.append(node_obj.model_dump())
            else:
                nodes.append({
                    "id": node_id,
                    "type": data.get("type", "unknown"),
                    "name": data.get("name", node_id),
                    "is_deterministic": True,
                })

        edges = []
        for u, v, data in self._graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "type": data.get("type", "DEPENDS_ON"),
                "is_deterministic": data.get("is_deterministic", True),
                "metadata": data.get("metadata", {}),
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
            }
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize graph to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeGraph":
        """Reconstruct a KnowledgeGraph instance from serialized dictionary."""
        graph = cls()
        type_mapping = {
            "project": KnowledgeNodeType.PROJECT,
            "file": KnowledgeNodeType.FILE,
            "package": KnowledgeNodeType.PACKAGE,
            "module": KnowledgeNodeType.MODULE,
            "class": KnowledgeNodeType.CLASS,
            "function": KnowledgeNodeType.FUNCTION,
            "method": KnowledgeNodeType.METHOD,
            "external_dependency": KnowledgeNodeType.EXTERNAL_DEPENDENCY,
            "git_commit": KnowledgeNodeType.GIT_COMMIT,
        }

        for n in data.get("nodes", []):
            node_type = type_mapping.get(n.get("type", "unknown"), KnowledgeNodeType.MODULE)
            node = KnowledgeNode(
                id=n["id"],
                type=node_type,
                name=n.get("name", n["id"]),
                is_deterministic=n.get("is_deterministic", True),
                source=n.get("source"),
                docstring=n.get("docstring"),
                metadata=n.get("metadata", {}),
            )
            graph.add_node(node)

        for e in data.get("edges", []):
            rel_type_str = e.get("type", "DEPENDS_ON")
            try:
                rel_type = RelationshipType(rel_type_str)
            except ValueError:
                rel_type = RelationshipType.DEPENDS_ON

            edge = KnowledgeEdge(
                source_id=e["source"],
                target_id=e["target"],
                type=rel_type,
                is_deterministic=e.get("is_deterministic", True),
                metadata=e.get("metadata", {}),
            )
            graph.add_edge(edge)

        return graph
