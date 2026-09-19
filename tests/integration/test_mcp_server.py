"""Integration tests for MCP KnowledgeService and Tools."""

import json
from pathlib import Path
import pytest

from compass.config.settings import CompassConfig
from compass.ingestion.repository import RepositoryIngestor
from compass.knowledge.builder import KnowledgeBuilder
from compass.knowledge.writer import KnowledgeWriter
from compass.mcp.server import KnowledgeService, create_mcp_server


@pytest.fixture
def setup_knowledge_fixture(tmp_path: Path):
    fixture_dir = Path(__file__).parent.parent / "fixtures" / "sample_project"
    knowledge_dir = tmp_path / "test_knowledge"

    config = CompassConfig()
    config.project.name = "sample-service"
    config.source.path = str(fixture_dir)
    config.knowledge.path = str(knowledge_dir)

    ingestor = RepositoryIngestor(config)
    repo_data = ingestor.ingest()
    builder = KnowledgeBuilder(config)
    graph = builder.build(repo_data)
    writer = KnowledgeWriter(config)
    writer.write(graph, repo_data)

    return knowledge_dir


def test_mcp_knowledge_service_tools(setup_knowledge_fixture: Path):
    service = KnowledgeService(setup_knowledge_fixture)

    # 1. get_project_overview
    overview = service.get_project_overview()
    assert "# Architecture Overview" in overview
    assert "sample-service" in overview

    # 2. search_knowledge
    search_results = service.search_knowledge("UserService")
    assert len(search_results) >= 1
    assert any("UserService" in r["name"] for r in search_results)

    # 3. get_component
    comp = service.get_component("UserService")
    assert "error" not in comp
    assert comp["name"] == "UserService"
    assert comp["type"] == "class"
    assert comp["source"]["file"] == "service.py"
    assert comp["source"]["method"] == "ast"

    # 4. get_dependencies
    deps = service.get_dependencies("UserService")
    assert "dependencies" in deps

    # 5. get_file_context
    ctx = service.get_file_context("service.py")
    assert ctx["file"] == "service.py"
    assert ctx["symbols_count"] >= 1

    # 6. get_change_surface
    surface = service.get_change_surface("UserRepository")
    assert surface["found"] is True
    assert "dependents" in surface

    # 7. update_knowledge
    update_res = service.update_knowledge(
        category="conventions",
        title="error-handling-rules",
        content="Always use custom DomainException instead of raw Exception.",
    )
    assert update_res["success"] is True
    assert "error-handling-rules.md" in update_res["file"]

    # Verify search finds the newly recorded knowledge
    search_res = service.search_knowledge("DomainException")
    assert len(search_res) >= 1
    assert any("Error Handling Rules" in r["name"] for r in search_res)


def test_fastmcp_server_instance_creation(setup_knowledge_fixture: Path):
    mcp = create_mcp_server(setup_knowledge_fixture)
    assert mcp is not None
    # Check name attribute in either FastMCP v1 or MCPServer v2
    server_name = getattr(mcp, "name", None) or getattr(getattr(mcp, "server", None), "name", None)
    if server_name:
        assert server_name == "code-compass"
