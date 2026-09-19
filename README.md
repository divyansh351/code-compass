# Code Compass 🧭

**Local-First Agent Knowledge Framework & MCP Server for Software Repositories**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Local-First](https://img.shields.io/badge/Privacy-100%25%20Local-success.svg)](#privacy-guarantee)

---

## What is Code Compass?

**Code Compass** gives AI coding agents a map of a software project.

When pointed at a local source repository, Code Compass deterministically analyzes the codebase, builds a structured knowledge layer (architecture, components, dependencies, conventions, provenance, and relationships), persists that knowledge in human-readable and version-controllable formats, and exposes it to AI coding agents through a **local Model Context Protocol (MCP) server**.

```text
┌─────────────────────────┐
│ Local Source Repository │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│    Code Compass CLI     │
│  ├── File/Lang Scanner  │
│  ├── AST/Symbol Engine  │
│  ├── Dependency Mapper  │
│  └── Graph Builder      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Local Knowledge Repo    │
│  ├── manifest.yaml      │
│  ├── architecture/      │
│  ├── components/        │
│  ├── graph/graph.json   │
│  └── metadata/          │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│    Local MCP Server     │ (stdio transport)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│     AI Coding Agent     │ (Claude, Cursor, Cline, etc.)
└─────────────────────────┘
```

---

## Why Code Compass?

AI coding agents often have direct access to source files but lack **persistent, structured architectural knowledge**. Without an explicit map:
- They waste context tokens repeatedly searching for relationships.
- They fail to appreciate the change surface / blast radius of modifications.
- They miss key conventions, dependencies, and component boundaries.

Code Compass bridges this gap by providing an explicit, deterministic knowledge layer before any LLM inference occurs.

---

## 🔒 Privacy Guarantee

> **Code Compass is local-first. The Code Compass project does not receive, store, or process your source code.**

- **No Remote Telemetry**: Zero tracking, zero analytics, zero phone-home calls.
- **No Cloud Backend**: Everything runs 100% locally on your machine.
- **Default Offline Mode**: By default, `llm.provider` is set to `none`, requiring **zero network access**.
- **User-Controlled LLMs**: If you choose to configure an LLM (e.g., local Ollama or direct API keys), communication occurs directly from your machine to the provider with no intermediary proxy.

---

## Prerequisites & Installation

### Prerequisites
- Python 3.12+
- Git (optional, for commit history extraction)

### Installation

From the project root:

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies in editable mode
pip install -e .

# Or install with development dependencies:
pip install -e ".[dev]"
```

Required dependencies installed automatically:
- `typer` (CLI interface)
- `pydantic` & `pydantic-settings` (data models & configuration)
- `pyyaml` (YAML parsing & manifest generation)
- `networkx` (knowledge graph engine)
- `mcp` / `fastmcp` (Model Context Protocol server)
- `rich` (CLI terminal output)
- `pytest` (test suite)

---

## Quick Start

### 1. Initialize Configuration
```bash
compass init
```
This generates a starter `compass.yaml`:

```yaml
project:
  name: my-project
  version: 0.1.0

source:
  path: .
  ignore_patterns:
    - ".git"
    - "node_modules"
    - ".venv"
    - "__pycache__"
    - "dist"
    - "build"

knowledge:
  path: ./knowledge

analysis:
  languages:
    - python
  files: true
  imports: true
  symbols: true
  git_history: true

llm:
  provider: none
  model: null
```

### 2. Check System Health
```bash
compass doctor --config compass.yaml
```

### 3. Analyze Codebase
```bash
compass analyze --config compass.yaml
```
Output:
```text
Code Compass Analysis

Project: my-project

Files analyzed: 147
Python files: 112
Classes: 86
Functions/Methods: 431
Imports & Dependencies: 624
External Packages: 14
Git commits analyzed: 100

Knowledge graph:
Nodes: 517
Relationships: 843
```

### 4. Build Knowledge Repository
```bash
compass build --config compass.yaml
```
Generates a structured, human-readable directory:
```text
knowledge/
├── manifest.yaml
├── architecture/
│   └── overview.md
├── components/
│   └── components.json
├── conventions/
├── workflows/
├── decisions/
├── graph/
│   └── graph.json
└── metadata/
    └── build.json
```

### 5. Launch MCP Server
```bash
compass serve --config compass.yaml
```

---

## Connecting AI Agents (MCP Configuration)

Code Compass exposes standard Model Context Protocol (MCP) tools over `stdio`.

### Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "code-compass": {
      "command": "compass",
      "args": ["serve", "--config", "/path/to/compass.yaml"]
    }
  }
}
```

### Cursor / Cline / Roo Code
Configure the MCP server command as:
- **Command**: `compass`
- **Args**: `["serve", "--config", "compass.yaml"]`

---

## Available MCP Tools

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `search_knowledge` | `query: str` | Search components, classes, functions, and docstrings in the knowledge repository. |
| `get_project_overview` | None | Get the high-level deterministic architecture overview markdown. |
| `get_component` | `name: str` | Retrieve full signature, docstring, source provenance, and details of a component. |
| `get_dependencies` | `name: str` | Get all upstream dependencies and downstream dependents for a component. |
| `get_file_context` | `path: str` | Return all symbols, containment relationships, and metadata for a source file. |
| `get_change_surface` | `component: str` | Compute blast radius and directly impacted nodes from the knowledge graph. |

---

## Running Tests

Execute the complete test suite:

```bash
pytest
```

To run with verbose output:

```bash
pytest -v
```

---

## Project Structure

```text
code-compass/
├── src/
│   └── compass/
│       ├── cli/             # Typer CLI application (init, analyze, build, serve, doctor)
│       ├── config/          # Pydantic Settings and YAML loader
│       ├── ingestion/       # Filesystem scanner and Git history extractor
│       ├── analyzers/       # AST parsing, symbol extraction, import classifier
│       ├── knowledge/       # NetworkX knowledge graph, models, builder, and writer
│       ├── llm/             # LLM provider abstraction (NoneProvider, Ollama, etc.)
│       ├── mcp/             # Local MCP server & KnowledgeService
│       └── sync/            # Change detection & incremental synchronization
├── templates/               # Default knowledge repository templates
├── examples/                # Example configuration files
└── tests/
    ├── unit/                # Unit tests for analyzers, graph, scanner, CLI, LLM
    ├── integration/         # Integration tests for MCP server & pipeline
    └── fixtures/            # Sample test codebases
```

---

## Roadmap

- [ ] TypeScript / JavaScript AST analyzer (Tree-sitter integration)
- [ ] Go & Rust analyzer modules
- [ ] Local embedding search & vector indexing for natural language knowledge retrieval
- [ ] Automated Architecture Decision Record (ADR) extraction
- [ ] Architecture rule validation & linting (e.g. boundary enforcement)
- [ ] Incremental graph synchronization via file watcher
- [ ] Git pre-commit & PR integration for continuous knowledge maintenance

---

## License

This project is licensed under the [MIT License](LICENSE).
