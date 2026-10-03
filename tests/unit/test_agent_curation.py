"""Unit tests verifying zero external LLM dependencies and agent knowledge curation."""

from pathlib import Path
import pytest

from compass.config.settings import CompassConfig
from compass.mcp.server import KnowledgeService


def test_zero_llm_credentials_required():
    """Verify Code Compass config has zero LLM credentials or API configurations."""
    config = CompassConfig()
    assert not hasattr(config, "llm")
    assert config.project.name == "my-project"


def test_agent_can_update_overview_directly(tmp_path: Path):
    """Verify that an active agent can supply and update the Executive AI overview directly via MCP service."""
    knowledge_dir = tmp_path / "knowledge"
    arch_dir = knowledge_dir / "architecture"
    arch_dir.mkdir(parents=True)
    (arch_dir / "overview.md").write_text("# Architecture Overview\n\n## Repository\n`test-app`\n", encoding="utf-8")

    service = KnowledgeService(knowledge_dir)
    res = service.update_overview("This is an AI-curated summary supplied by the active agent.")
    assert res["success"] is True

    overview_text = service.get_project_overview()
    assert "This is an AI-curated summary supplied by the active agent." in overview_text
    assert "## Executive Overview" in overview_text


def test_agent_can_update_knowledge_conventions(tmp_path: Path):
    """Verify that an active agent can persist conventions and notes directly into the knowledge repo."""
    knowledge_dir = tmp_path / "knowledge"
    service = KnowledgeService(knowledge_dir)

    res = service.update_knowledge(
        category="conventions",
        title="Router Boundary Rule",
        content="Do not query SQL models directly from router endpoints.",
        tags=["architecture", "security"],
    )
    assert res["success"] is True
    convention_file = knowledge_dir / "conventions" / "router-boundary-rule.md"
    assert convention_file.exists()
    content = convention_file.read_text(encoding="utf-8")
    assert "Router Boundary Rule" in content
    assert "Do not query SQL models directly" in content
