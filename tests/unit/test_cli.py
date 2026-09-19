"""Unit tests for Code Compass Typer CLI."""

from pathlib import Path
from typer.testing import CliRunner
import pytest
import yaml

from compass.cli.main import app

runner = CliRunner()


def test_cli_init_non_interactive(tmp_path: Path):
    cfg_file = tmp_path / "test_compass.yaml"
    result = runner.invoke(
        app,
        [
            "init",
            "--non-interactive",
            "--name", "my-test-app",
            "--source", str(tmp_path),
            "--knowledge", str(tmp_path / "my_knowledge"),
            "--language", "python",
            "--output", str(cfg_file),
        ],
    )

    assert result.exit_code == 0
    assert cfg_file.exists()

    data = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    assert data["project"]["name"] == "my-test-app"
    assert data["analysis"]["languages"] == ["python"]


def test_cli_doctor_command(tmp_path: Path):
    result = runner.invoke(app, ["doctor", "--config", "non_existent.yaml"])
    assert result.exit_code == 0
    assert "Doctor" in result.stdout
    assert "Python Runtime" in result.stdout
