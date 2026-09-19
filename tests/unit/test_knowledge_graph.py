"""Unit tests for NetworkX-backed knowledge graph."""

import pytest

from compass.knowledge.graph import KnowledgeGraph
from compass.knowledge.models import (
    ClassNode,
    FunctionNode,
    KnowledgeEdge,
    KnowledgeNodeType,
    ModuleNode,
    Provenance,
    RelationshipType,
)


def test_knowledge_graph_node_and_edge_operations():
    graph = KnowledgeGraph()

    mod = ModuleNode(
        id="module:auth",
        name="auth",
        module_path="auth",
        file_path="src/auth.py",
    )
    cls = ClassNode(
        id="class:auth.AuthService",
        name="AuthService",
        source=Provenance(file="src/auth.py", line_start=10, line_end=50, method="ast"),
    )
    fn = FunctionNode(
        id="function:auth.AuthService.login",
        name="login",
        signature="def login(username, password)",
        source=Provenance(file="src/auth.py", line_start=20, line_end=30, method="ast"),
    )

    graph.add_node(mod)
    graph.add_node(cls)
    graph.add_node(fn)

    # Add containment relationships
    graph.add_edge(
        KnowledgeEdge(
            source_id="module:auth",
            target_id="class:auth.AuthService",
            type=RelationshipType.CONTAINS,
        )
    )
    graph.add_edge(
        KnowledgeEdge(
            source_id="class:auth.AuthService",
            target_id="function:auth.AuthService.login",
            type=RelationshipType.CONTAINS,
        )
    )

    assert graph.node_count == 3
    assert graph.edge_count == 2

    # Query node
    retrieved = graph.get_node("class:auth.AuthService")
    assert retrieved is not None
    assert retrieved.name == "AuthService"
    assert retrieved.source.line_start == 10

    # Dependencies / Dependents
    deps = graph.get_dependencies("module:auth")
    assert len(deps) == 1
    assert deps[0]["id"] == "class:auth.AuthService"

    dependents = graph.get_dependents("class:auth.AuthService")
    assert len(dependents) == 1
    assert dependents[0]["id"] == "module:auth"


def test_knowledge_graph_change_surface():
    graph = KnowledgeGraph()

    mod_a = ModuleNode(id="module:service", name="service", module_path="service", file_path="service.py")
    mod_b = ModuleNode(id="module:repo", name="repo", module_path="repo", file_path="repo.py")

    graph.add_node(mod_a)
    graph.add_node(mod_b)

    # service IMPORTS repo
    graph.add_edge(
        KnowledgeEdge(
            source_id="module:service",
            target_id="module:repo",
            type=RelationshipType.IMPORTS,
        )
    )

    surface = graph.get_change_surface("module:repo")
    assert surface["found"] is True
    assert surface["total_impact_count"] == 1
    assert surface["dependents"][0]["id"] == "module:service"


def test_knowledge_graph_serialization_roundtrip():
    graph = KnowledgeGraph()
    cls = ClassNode(id="class:test.A", name="A")
    graph.add_node(cls)
    graph.add_edge(
        KnowledgeEdge(source_id="class:test.A", target_id="class:test.B", type=RelationshipType.INHERITS)
    )

    data = graph.to_dict()
    assert data["stats"]["total_nodes"] == 2
    assert data["stats"]["total_edges"] == 1

    restored = KnowledgeGraph.from_dict(data)
    assert restored.node_count == 2
    assert restored.edge_count == 1
    assert restored.get_node("class:test.A") is not None
