"""End-to-end integration test of the full Code Compass pipeline."""

from pathlib import Path
import pytest

from compass.config.settings import CompassConfig
from compass.ingestion.repository import RepositoryIngestor
from compass.knowledge.builder import KnowledgeBuilder
from compass.knowledge.models import KnowledgeNodeType
from compass.knowledge.writer import KnowledgeWriter
from compass.mcp.server import KnowledgeService


def test_full_pipeline_from_source_to_mcp_query(tmp_path: Path):
    # 1. Source repo
    src_dir = tmp_path / "source_repo"
    src_dir.mkdir()
    
    # Create sample Python files
    (src_dir / "models.py").write_text(
        """class Item:\n    def __init__(self, name: str):\n        self.name = name\n""",
        encoding="utf-8",
    )
    (src_dir / "service.py").write_text(
        """from models import Item\n\nclass ItemService:\n    def create(self, name: str) -> Item:\n        return Item(name=name)\n""",
        encoding="utf-8",
    )

    # 2. Configure
    out_dir = tmp_path / "output_knowledge"
    config = CompassConfig()
    config.project.name = "e2e-demo"
    config.source.path = str(src_dir)
    config.knowledge.path = str(out_dir)

    # 3. Ingestion
    ingestor = RepositoryIngestor(config)
    repo_data = ingestor.ingest()
    assert repo_data.scan_result.total_files == 2

    # 4. Knowledge Builder & Graph
    builder = KnowledgeBuilder(config)
    graph = builder.build(repo_data)

    assert graph.node_count >= 5  # Project, 2 files, 2 modules, 2 classes, methods
    classes = graph.find_nodes_by_type(KnowledgeNodeType.CLASS)
    class_names = [c.name for c in classes]
    assert "Item" in class_names
    assert "ItemService" in class_names

    # 5. Knowledge Writer
    writer = KnowledgeWriter(config)
    res_dir = writer.write(graph, repo_data)
    assert (res_dir / "architecture" / "overview.md").exists()
    assert (res_dir / "graph" / "graph.json").exists()

    # 6. MCP Knowledge Service Query
    service = KnowledgeService(res_dir)
    comp = service.get_component("ItemService")
    assert comp["name"] == "ItemService"

    surface = service.get_change_surface("Item")
    assert surface["found"] is True
