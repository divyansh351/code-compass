"""CLI interface for Code Compass using Typer."""

import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from compass import __version__
from compass.config.settings import CompassConfig, load_config
from compass.ingestion.repository import RepositoryIngestor
from compass.knowledge.builder import KnowledgeBuilder
from compass.knowledge.models import KnowledgeNodeType
from compass.knowledge.writer import KnowledgeWriter
from compass.mcp.server import run_server

app = typer.Typer(
    name="compass",
    help="Code Compass — Local-First Agent Knowledge Framework",
    no_args_is_help=True,
)
console = Console()


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


@app.command()
def init(
    project_name: Optional[str] = typer.Option(None, "--name", "-n", help="Project name"),
    source_path: Optional[str] = typer.Option(None, "--source", "-s", help="Source repository path"),
    knowledge_path: Optional[str] = typer.Option(None, "--knowledge", "-k", help="Knowledge output directory"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Primary language"),
    output: str = typer.Option("compass.yaml", "--output", "-o", help="Configuration file output path"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Run without interactive prompts"),
):
    """Initialize a starter Code Compass configuration."""
    console.print(Panel(f"[bold cyan]Code Compass v{__version__}[/bold cyan] — Project Setup", border_style="cyan"))

    default_name = Path.cwd().name
    if non_interactive:
        name = project_name or default_name
        src = source_path or "."
        know = knowledge_path or "./knowledge"
        lang = language or "python"
    else:
        name = project_name or typer.prompt("Project name", default=default_name)
        src = source_path or typer.prompt("Source repository path", default=".")
        know = knowledge_path or typer.prompt("Knowledge repository destination", default="./knowledge")
        lang = language or typer.prompt("Primary language", default="python")

    config = CompassConfig()
    config.project.name = name
    config.source.path = src
    config.knowledge.path = know
    config.analysis.languages = [lang]

    config_path = Path(output)
    config.to_yaml(config_path)

    console.print(f"[bold green]✓[/bold green] Configuration written to [bold]{config_path}[/bold]")
    console.print("\nNext steps:")
    console.print(f"  1. [cyan]compass analyze --config {output}[/cyan] (analyze source code)")
    console.print(f"  2. [cyan]compass build --config {output}[/cyan]   (build knowledge repository)")
    console.print(f"  3. [cyan]compass serve --config {output}[/cyan]   (launch local MCP server)\n")


@app.command()
def analyze(
    config_file: str = typer.Option("compass.yaml", "--config", "-c", help="Path to compass.yaml"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug logging"),
):
    """Analyze source repository and print knowledge summary statistics."""
    setup_logging(verbose)
    try:
        config = load_config(config_file)
    except Exception as e:
        console.print(f"[bold red]Error loading configuration:[/bold red] {e}")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]Code Compass Analysis[/bold]\n")
    console.print(f"Project: [bold cyan]{config.project.name}[/bold cyan]\n")

    # Ingestion & Analysis
    with console.status("[cyan]Scanning repository and analyzing AST...[/cyan]"):
        ingestor = RepositoryIngestor(config)
        repo_data = ingestor.ingest()
        builder = KnowledgeBuilder(config)
        graph = builder.build(repo_data)

    # Compute breakdown statistics
    py_files = len(repo_data.get_files_by_language("python"))
    classes = len(graph.find_nodes_by_type(KnowledgeNodeType.CLASS))
    functions = len(graph.find_nodes_by_type(KnowledgeNodeType.FUNCTION)) + len(
        graph.find_nodes_by_type(KnowledgeNodeType.METHOD)
    )
    ext_deps = len(graph.find_nodes_by_type(KnowledgeNodeType.EXTERNAL_DEPENDENCY))
    commits = len(repo_data.git_summary.commits)

    # Count import edges
    import_edges = sum(
        1 for _, _, d in graph._graph.edges(data=True) if d.get("type") in ["IMPORTS", "DEPENDS_ON"]
    )

    console.print(f"Files analyzed: [bold]{repo_data.scan_result.total_files}[/bold]")
    console.print(f"Python files: [bold]{py_files}[/bold]")
    console.print(f"Classes: [bold]{classes}[/bold]")
    console.print(f"Functions/Methods: [bold]{functions}[/bold]")
    console.print(f"Imports & Dependencies: [bold]{import_edges}[/bold]")
    console.print(f"External Packages: [bold]{ext_deps}[/bold]")
    console.print(f"Git commits analyzed: [bold]{commits}[/bold]\n")

    console.print("[bold]Knowledge graph:[/bold]")
    console.print(f"Nodes: [bold green]{graph.node_count}[/bold green]")
    console.print(f"Relationships: [bold green]{graph.edge_count}[/bold green]\n")


@app.command()
def build(
    config_file: str = typer.Option("compass.yaml", "--config", "-c", help="Path to compass.yaml"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose debug logging"),
):
    """Analyze repository and generate the standalone local knowledge repository."""
    setup_logging(verbose)
    try:
        config = load_config(config_file)
    except Exception as e:
        console.print(f"[bold red]Error loading configuration:[/bold red] {e}")
        raise typer.Exit(code=1)

    console.print(Panel(f"Building Knowledge Repository for [bold cyan]{config.project.name}[/bold cyan]", border_style="cyan"))

    with console.status("[cyan]Ingesting repository & constructing knowledge graph...[/cyan]"):
        ingestor = RepositoryIngestor(config)
        repo_data = ingestor.ingest()
        builder = KnowledgeBuilder(config)
        graph = builder.build(repo_data)
        writer = KnowledgeWriter(config)
        out_path = writer.write(graph, repo_data)

    console.print(f"[bold green]✓[/bold green] Knowledge repository successfully generated at: [bold]{out_path}[/bold]\n")
    console.print("Generated Artifacts:")
    console.print(f"  • [cyan]{out_path}/manifest.yaml[/cyan]")
    console.print(f"  • [cyan]{out_path}/architecture/overview.md[/cyan]")
    console.print(f"  • [cyan]{out_path}/components/components.json[/cyan]")
    console.print(f"  • [cyan]{out_path}/graph/graph.json[/cyan]")
    console.print(f"  • [cyan]{out_path}/metadata/build.json[/cyan]\n")
    console.print("Run [bold cyan]compass serve[/bold cyan] to connect your AI agent via MCP.\n")


@app.command()
def serve(
    config_file: str = typer.Option("compass.yaml", "--config", "-c", help="Path to compass.yaml"),
):
    """Launch the local MCP server over stdio transport."""
    try:
        config = load_config(config_file)
    except Exception as e:
        console.print(f"[bold red]Error loading configuration:[/bold red] {e}")
        raise typer.Exit(code=1)

    knowledge_path = Path(config.knowledge.path)
    if not knowledge_path.exists():
        console.print(f"[bold yellow]Knowledge repository not found at {knowledge_path}. Running build first...[/bold yellow]")
        ingestor = RepositoryIngestor(config)
        repo_data = ingestor.ingest()
        builder = KnowledgeBuilder(config)
        graph = builder.build(repo_data)
        writer = KnowledgeWriter(config)
        writer.write(graph, repo_data)

    run_server(config)


@app.command()
def doctor(
    config_file: str = typer.Option("compass.yaml", "--config", "-c", help="Path to compass.yaml"),
):
    """Check health, prerequisites, configuration, and environment."""
    console.print(Panel("[bold]Code Compass Doctor — Health Check[/bold]", border_style="cyan"))

    table = Table(title="System & Configuration Status")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")

    # 1. Python Version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    table.add_row(
        "Python Runtime",
        "[green]PASS[/green]" if py_ok else "[yellow]WARN[/yellow]",
        f"Python {py_ver}",
    )

    # 2. Git CLI
    git_path = shutil.which("git")
    table.add_row(
        "Git Executable",
        "[green]PASS[/green]" if git_path else "[yellow]WARN[/yellow]",
        git_path or "git not found in PATH (git history will be skipped)",
    )

    # 3. Config File
    cfg_exists = Path(config_file).exists()
    table.add_row(
        "Configuration File",
        "[green]PASS[/green]" if cfg_exists else "[yellow]NOT FOUND[/yellow]",
        str(Path(config_file).resolve()) if cfg_exists else f"Run 'compass init' to create {config_file}",
    )

    if cfg_exists:
        try:
            config = load_config(config_file)
            src_path = Path(config.source.path).resolve()
            src_ok = src_path.exists()
            table.add_row(
                "Source Repository Path",
                "[green]PASS[/green]" if src_ok else "[red]FAIL[/red]",
                str(src_path),
            )

            table.add_row(
                "Privacy & Architecture Mode",
                "[green]100% LOCAL[/green]",
                "Zero external API keys, zero network telemetry, zero cloud dependencies",
            )
        except Exception as e:
            table.add_row("Config Validation", "[red]FAIL[/red]", str(e))

    console.print(table)


@app.command()
def commit(
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Git commit message"),
    config_file: str = typer.Option("compass.yaml", "--config", "-c", help="Path to compass.yaml"),
):
    """Commit changes in the local knowledge repository using Git on demand."""
    try:
        config = load_config(config_file)
    except Exception as e:
        console.print(f"[bold red]Error loading configuration:[/bold red] {e}")
        raise typer.Exit(code=1)

    from compass.mcp.server import KnowledgeService
    service = KnowledgeService(config.knowledge.path)
    res = service.commit_knowledge(message=message)

    if res.get("success"):
        if res.get("committed"):
            console.print(f"[bold green]✓[/bold green] {res.get('message')}")
        else:
            console.print(f"[bold yellow]•[/bold yellow] {res.get('message')}")
    else:
        console.print(f"[bold red]✗ Commit error:[/bold red] {res.get('error')}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
