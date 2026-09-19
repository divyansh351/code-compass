"""Unit tests for knowledge repository writer."""

from pathlib import Path
import json
import yaml
import pytest

from compass.config.settings import CompassConfig
from compass.ingestion.filesystem import ScanResult, ScannedFile
from compass.ingestion.git import GitRepoSummary
from compass.ingestion.repository import RepositoryData
from compass.knowledge.graph import KnowledgeGraph
from compass.knowledge.models import ClassNode, ExternalDependencyNode, ModuleNode, Provenance
from compass.knowledge.writer import KnowledgeWriter


def test_knowledge_writer_creates_structured_repo(tmp_path: Path):
    out_dir = tmp_path / "knowledge_output"

    config = CompassConfig()
    config.project.name = "test-project"
    config.knowledge.path = str(out_dir)

    graph = KnowledgeGraph()
    mod = ModuleNode(id="module:auth", name="auth", module_path="auth", file_path="auth.py")
    cls = ClassNode(id="class:auth.User", name="User", source=Provenance(file="auth.py", line_start=1, line_end=10))
    dep = ExternalDependencyNode(id="external:pydantic", name="pydantic", package_name="pydantic")

    graph.add_node(mod)
    graph.add_node(cls)
    graph.add_node(dep)

    repo_data = RepositoryData(
        root_path=tmp_path,
        scan_result=ScanResult(
            root_path=tmp_path,
            files=[
                ScannedFile("auth.py", tmp_path / "auth.py", ".py", "python", 100, 10, "abc123hash"),
            ],
            languages_detected={"python"},
            total_files=1,
            total_lines=10,
            total_size_bytes=100,
        ),
        git_summary=GitRepoSummary(is_git_repo=False),
    )

    writer = KnowledgeWriter(config)
    res_path = writer.write(graph, repo_data)

    assert res_path.exists()
    assert (res_path / "manifest.yaml").exists()
    assert (res_path / "architecture" / "overview.md").exists()
    assert (res_path / "components" / "components.json").exists()
    assert (res_path / "graph" / "graph.json").exists()
    assert (res_path / "metadata" / "build.json").exists()

    # Verify manifest YAML
    manifest = yaml.safe_load((res_path / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["project"]["name"] == "test-project"
    assert manifest["statistics"]["total_files"] == 1

    # Verify Architecture Overview
    overview_text = (res_path / "architecture" / "overview.md").read_text(encoding="utf-8")
    assert "test-project" in overview_text
    assert "auth" in overview_text
    assert "pydantic" in overview_text

    # Verify components JSON
    components = json.loads((res_path / "components" / "components.json").read_text(encoding="utf-8"))
    assert len(components) == 3
