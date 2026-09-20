# Code Compass 🧭

**Local-First Agent Knowledge Framework & Local MCP Server for Software Repositories**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/Protocol-MCP-green.svg)](https://modelcontextprotocol.io/)
[![Privacy: 100% Local](https://img.shields.io/badge/Privacy-100%25%20Local-success.svg)](#-privacy--security-guarantee)

---

## Table of Contents

1. [Product Vision & Philosophy](#-product-vision--philosophy)
2. [Architecture Overview](#-architecture-overview)
3. [Prerequisites & Installation](#-prerequisites--installation)
4. [Quick Start Tutorial](#-quick-start-tutorial)
5. [CLI Command Reference](#-cli-command-reference)
   - [`compass init`](#1-compass-init)
   - [`compass doctor`](#2-compass-doctor)
   - [`compass analyze`](#3-compass-analyze)
   - [`compass build`](#4-compass-build)
   - [`compass serve`](#5-compass-serve)
6. [Configuration Reference (`compass.yaml`)](#-configuration-reference-compassyaml)
7. [Knowledge Repository Specification](#-knowledge-repository-specification)
8. [Knowledge Models & Provenance](#-knowledge-models--provenance)
9. [Connecting AI Coding Agents (MCP Server Integration)](#-connecting-ai-coding-agents-mcp-server-integration)
   - [Claude Desktop](#1-claude-desktop)
   - [Cursor IDE](#2-cursor-ide)
   - [Cline / Roo-Code](#3-cline--roo-code)
   - [Continue.dev](#4-continuedev)
   - [Windsurf & Zed](#5-windsurf--zed)
10. [MCP Tools Reference & Examples](#-mcp-tools-reference--examples)
11. [Extending Code Compass](#-extending-code-compass)
12. [Testing & Verification](#-testing--verification)
13. [Privacy & Security Guarantee](#-privacy--security-guarantee)
14. [Roadmap](#-roadmap)
15. [License](#-license)

---

## 🌟 Product Vision & Philosophy

AI coding agents (such as Claude, Cursor, Cline, and Copilot) have access to individual source files, but they fundamentally lack a **persistent, structured map of the overall repository**. When faced with large codebases, agents:
- Waste valuable context window tokens performing brute-force text searches.
- Miss critical architectural boundaries and module dependencies.
- Fail to calculate the true blast radius / change surface of proposed modifications.
- Hallucinate relationships between components.

**Code Compass** solves this by generating an explicit, deterministic knowledge layer and serving it directly to agents over the **Model Context Protocol (MCP)**.

### Core Principles

1. **Local-First & Private**: No hosted API, no telemetry, no cloud backend, no phone-home mechanism. Everything runs locally on your machine.
2. **Deterministic Facts First**: Distinguishes verified facts extracted from AST/code analysis from probabilistic LLM interpretations.
3. **Human-Readable Knowledge**: Knowledge is persisted as clean Markdown, YAML, and JSON files that developers can inspect, version control with Git, and edit.
4. **MCP as an Interface**: The MCP server is a thin access layer over the knowledge graph, not a proprietary database.

---

## 🏛 Architecture Overview

```text
┌────────────────────────────────────────────────────────┐
│               Local Source Repository                  │
│             (Python, Modules, Git History)             │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                    Code Compass CLI                    │
│                                                        │
│  ┌──────────────────┐         ┌─────────────────────┐  │
│  │ Repository       │         │ Python AST          │  │
│  │ Scanner          ├────────►│ Analyzer            │  │
│  └──────────────────┘         └──────────┬──────────┘  │
│                                          │             │
│  ┌──────────────────┐         ┌──────────▼──────────┐  │
│  │ Git History      │         │ NetworkX Knowledge  │  │
│  │ Extractor        ├────────►│ Graph Engine        │  │
│  └──────────────────┘         └──────────┬──────────┘  │
│                                          │             │
│                               ┌──────────▼──────────┐  │
│                               │ Knowledge Writer    │  │
│                               └─────────────────────┘  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             Local Knowledge Repository                 │
│                                                        │
│  ├── manifest.yaml           (Project meta & stats)    │
│  ├── architecture/                                     │
│  │   └── overview.md         (Deterministic overview)  │
│  ├── components/                                       │
│  │   └── components.json     (Symbols, signatures)     │
│  ├── graph/                                            │
│  │   └── graph.json          (Nodes & relationships)   │
│  ├── conventions/            (Coding rules)            │
│  ├── workflows/              (Dev guides)              │
│  ├── decisions/              (ADRs)                    │
│  └── metadata/                                         │
│      └── build.json          (Timestamps & Git stats)  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             Local MCP Server (FastMCP)                 │
│                 (stdio transport)                      │
│                                                        │
│   • search_knowledge         • get_dependencies        │
│   • get_project_overview     • get_file_context        │
│   • get_component            • get_change_surface      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                 AI Coding Agents                       │
│    (Claude Desktop, Cursor, Cline, Continue, Zed)      │
└────────────────────────────────────────────────────────┘
```

---

## 📦 Prerequisites & Installation

### Prerequisites
- **Python**: Version 3.12 or newer
- **Git**: Optional (used for extracting commit metadata and change history)

### Installation Steps

```bash
# 1. Clone your project or navigate to code-compass
cd code-compass

# 2. Create and activate a Python virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Linux / macOS:
source .venv/bin/activate

# 3. Install in editable mode with development dependencies:
pip install -e ".[dev]"
```

Alternatively, install using `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## 🚀 Quick Start Tutorial

Follow these steps to analyze a repository and connect an AI agent in under 2 minutes:

### Step 1: Initialize Configuration
Run `compass init` to generate a `compass.yaml` file:
```bash
compass init --name my-app --source . --knowledge ./knowledge
```

### Step 2: Check System Health
Run `compass doctor` to verify that Python, Git, and directories are properly configured:
```bash
compass doctor --config compass.yaml
```

### Step 3: Analyze the Codebase
Inspect your repository without writing anything to disk:
```bash
compass analyze --config compass.yaml
```

### Step 4: Build the Knowledge Repository
Generate the full knowledge repository on disk:
```bash
compass build --config compass.yaml
```

### Step 5: Start the MCP Server
Launch the MCP server to serve the generated knowledge to coding agents:
```bash
compass serve --config compass.yaml
```

---

## 💻 CLI Command Reference

### 1. `compass init`
Creates a starter configuration file (`compass.yaml`).

```bash
compass init [OPTIONS]
```

**Options:**
- `--name`, `-n`: Project name (defaults to current directory name).
- `--source`, `-s`: Path to the source code repository (default: `.`).
- `--knowledge`, `-k`: Destination directory for the knowledge repository (default: `./knowledge`).
- `--language`, `-l`: Primary language to analyze (default: `python`).
- `--output`, `-o`: Config filename (default: `compass.yaml`).
- `--non-interactive`: Run in batch mode without interactive prompts.

### 2. `compass doctor`
Runs a diagnostic health check on your environment.

```bash
compass doctor --config compass.yaml
```

**Checks Performed:**
- Python runtime version (>= 3.10 required, 3.12+ recommended).
- Git CLI executable availability.
- Configuration file syntax and validity.
- Source repository path existence.
- LLM Privacy Mode verification (confirms offline status).

### 3. `compass analyze`
Performs an in-memory scan and AST analysis of the repository and prints a summary.

```bash
compass analyze [--config compass.yaml] [--verbose]
```

**Sample Output:**
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

### 4. `compass build`
Analyzes the codebase and writes the complete standalone knowledge repository to the directory configured in `knowledge.path`.

```bash
compass build [--config compass.yaml] [--verbose]
```

### 5. `compass serve`
Launches the local Model Context Protocol (MCP) server over `stdio`. If the knowledge repository has not been generated yet, it automatically builds it first.

```bash
compass serve [--config compass.yaml]
```

---

## ⚙️ Configuration Reference (`compass.yaml`)

```yaml
# ====================================================================
# Code Compass Configuration File
# ====================================================================

# Project Metadata
project:
  name: "my-project"
  description: "Core backend service for authentication and payments"
  version: "0.1.0"

# Source Code Repository Configuration
source:
  path: "."
  ignore_patterns:
    - ".git"
    - "node_modules"
    - ".venv"
    - "venv"
    - "__pycache__"
    - "dist"
    - "build"
    - "coverage"
    - ".env"
    - ".pytest_cache"
    - "*.egg-info"

# Knowledge Repository Destination
knowledge:
  path: "./knowledge"

# Analysis Engine Flags
analysis:
  languages:
    - python
  files: true              # File structure & role classification
  imports: true            # Import resolution & stdlib/external classification
  symbols: true            # Class, function, parameter & AST analysis
  git_history: true        # Git commit metadata & file modification analysis
  max_git_commits: 100     # Max commits to extract
```

> **Note on AI Overviews**: Code Compass does not require any external LLM API keys or configurations. When you build the repository, Code Compass deterministically maps the architecture. Your **active AI coding agent** (Claude, Cursor, Antigravity, etc.) can directly supply and enrich the executive AI overview using the `update_overview` MCP tool!

---

## 📂 Knowledge Repository Specification

When `compass build` runs, it generates the following directory structure:

```text
knowledge/
├── manifest.yaml
├── architecture/
│   └── overview.md
├── components/
│   └── components.json
├── conventions/
│   └── README.md
├── workflows/
│   └── README.md
├── decisions/
│   └── README.md
├── graph/
│   └── graph.json
└── metadata/
    └── build.json
```

### File Breakdown

1. **`manifest.yaml`**: Contains metadata, generator version, scan statistics, and detected languages.
2. **`architecture/overview.md`**: A deterministic Markdown overview detailing:
   - Top-level folder structure
   - Discovered internal modules
   - External package dependencies
   - Inter-module relationship map (`module_a → module_b`)
3. **`components/components.json`**: An array of discovered classes, functions, and modules, complete with docstrings, signatures, and line-level source provenance.
4. **`graph/graph.json`**: The complete NetworkX knowledge graph serialized into JSON (`nodes` and `edges`).
5. **`conventions/`**, **`workflows/`**, **`decisions/`**: Human-maintainable folders for coding rules, runbooks, and Architecture Decision Records (ADRs).
6. **`metadata/build.json`**: Build timestamps, scan metrics, and Git commit summaries.

---

## 🧠 Knowledge Models & Provenance

Every node and relationship in the knowledge graph includes explicit metadata and provenance:

### Node Types
* **`Project`**: The root software repository.
* **`File`**: A physical file on disk (size, line count, language).
* **`Module`**: A logical code module.
* **`Class`**: Class definition, docstring, base classes, decorators.
* **`Function` / `Method`**: Function definition, signature, parameters, return type, docstring.
* **`ExternalDependency`**: Third-party package (e.g. `pydantic`, `fastapi`).
* **`GitCommit`**: Commit hash, author, date, message.

### Relationship Types
* `CONTAINS`: Structural hierarchy (`Project CONTAINS File`, `Module CONTAINS Class`).
* `IMPORTS`: Import dependency (`Module IMPORTS Module`).
* `CALLS`: Function invocation (`Function CALLS Function`).
* `INHERITS`: Class inheritance (`Class INHERITS Class`).
* `DEPENDS_ON`: Dependency on external package (`Module DEPENDS_ON ExternalDependency`).
* `MODIFIED_BY`: File change history (`File MODIFIED_BY GitCommit`).

### Provenance Example
```json
{
  "id": "class:src/services.UserService",
  "type": "class",
  "name": "UserService",
  "is_deterministic": true,
  "source": {
    "file": "src/services.py",
    "line_start": 12,
    "line_end": 45,
    "method": "ast"
  },
  "docstring": "Service handling user business logic."
}
```

---

## 🔌 Connecting AI Coding Agents (MCP Server Integration)

Code Compass provides a standard **Model Context Protocol (MCP)** server communicating over `stdio`.

### 1. Claude Desktop
Add Code Compass to your `claude_desktop_config.json`:

* **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
* **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "code-compass": {
      "command": "compass",
      "args": ["serve", "--config", "C:/path/to/your/project/compass.yaml"]
    }
  }
}
```

### 2. Cursor IDE
In Cursor settings or `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "code-compass": {
      "command": "compass",
      "args": ["serve", "--config", "./compass.yaml"]
    }
  }
}
```

### 3. Cline / Roo-Code
Add to `cline_mcp_settings.json`:
```json
{
  "mcpServers": {
    "code-compass": {
      "command": "compass",
      "args": ["serve", "--config", "compass.yaml"],
      "disabled": false,
      "autoApprove": [
        "get_project_overview",
        "search_knowledge",
        "get_component",
        "get_dependencies",
        "get_file_context",
        "get_change_surface",
        "update_knowledge"
      ]
    }
  }
}
```

### 4. Continue.dev
In `~/.continue/config.json`:
```json
{
  "mcpServers": [
    {
      "name": "code-compass",
      "command": "compass",
      "args": ["serve", "--config", "compass.yaml"]
    }
  ]
}
```

### 5. Windsurf & Zed
Set the executable command to `compass` with arguments `["serve", "--config", "compass.yaml"]`.

---

## 🛠 MCP Tools Reference & Examples

When connected via MCP, the AI agent has access to 8 specialized tools:

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `get_project_overview` | *None* | Returns the high-level architecture overview markdown. |
| `search_knowledge` | `query: str` | Searches symbols, classes, functions, docstrings, and curated markdown documents. |
| `get_component` | `name: str` | Retrieves full signature, docstring, source provenance, and metadata for a component. |
| `get_dependencies` | `name: str` | Returns upstream dependencies and downstream dependents for a component. |
| `get_file_context` | `path: str` | Returns all symbols, containment relationships, and metadata for a source file. |
| `get_change_surface` | `component: str` | Calculates the blast radius / impacted nodes in the knowledge graph. |
| `update_knowledge` | `category: str`, `title: str`, `content: str` | Allows the AI agent to save new rules, conventions, workflows, ADRs, findings, or file notes directly into the knowledge repository. |
| `update_overview` | `summary: str` | Allows the active AI agent to generate or update the executive AI overview section in `architecture/overview.md`. |

### Example Agent Interactions

#### 1. Exploring Architecture
> **User Prompt**: "Give me an overview of how authentication is structured in this repository."  
> **Agent Action**: Calls `get_project_overview()` followed by `get_component("AuthService")`.

#### 2. Planning Refactors & Blast Radius
> **User Prompt**: "I want to modify the `UserRepository` interface. What other components will be impacted?"  
> **Agent Action**: Calls `get_change_surface("UserRepository")` to receive the exact list of dependent services.

#### 3. Updating Knowledge When Finding a Gap or Rule
> **User Prompt**: "You shouldn't query the SQL session inside route handlers; always use the Service layer. Record this in Code Compass so we don't repeat this."  
> **Agent Action**: Calls `update_knowledge(category="conventions", title="router-database-boundary", content="Never query DB sessions directly inside route handlers. Route handlers must only call Service classes.")`.

---

## 🔧 Extending Code Compass

### Adding a New Language Analyzer
Create a class inheriting from `BaseAnalyzer`:

```python
from pathlib import Path
from typing import Optional
from compass.analyzers.base import BaseAnalyzer, AnalysisResult

class RustAnalyzer(BaseAnalyzer):
    def can_analyze(self, file_path: Path | str, language: Optional[str] = None) -> bool:
        return Path(file_path).suffix == ".rs"

    def analyze_file(self, file_path: Path, relative_path: str) -> AnalysisResult:
        # Parse AST and return AnalysisResult
        ...
```

### Adding a Custom LLM Provider
Implement the `LLMProvider` interface in `compass/llm/base.py`:

```python
from compass.llm.base import LLMProvider

class CustomLocalLLM(LLMProvider):
    def generate(self, prompt: str, context: str = "") -> str:
        # Direct local generation
        return "response"
```

---

## 🧪 Testing & Verification

Code Compass includes a comprehensive unit and integration test suite:

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v
```

### Test Coverage Highlights
- **Repository Scanner Tests**: Validates file discovery, language classification, and ignore rules.
- **Python Analyzer Tests**: Validates AST symbol extraction, classes, functions, decorators, calls, and imports.
- **Knowledge Graph Tests**: Validates NetworkX node/edge operations, queries, serialization, and blast radius calculation.
- **Knowledge Writer Tests**: Validates deterministic markdown generation and JSON schemas.
- **Privacy & LLM Tests**: Verifies that the default `NoneProvider` makes zero network requests.
- **MCP Server & Tool Integration**: Tests end-to-end knowledge querying via MCP tools.

---

## 🔒 Privacy & Security Guarantee

> **Code Compass is strictly local-first. The Code Compass project does not receive, store, transmit, or process your source code.**

- **No Remote Telemetry**: Zero analytics, zero logging to external servers.
- **Zero Cloud Infrastructure**: No proprietary cloud backend or hosted database.
- **Deterministic Offline Analysis**: All AST and graph analysis runs entirely on your local CPU.
- **Opt-in Network Access**: Network requests only occur if you explicitly configure an external LLM provider with your own API credentials.

---

## 🗺 Roadmap

- [ ] Tree-sitter integration for TypeScript, JavaScript, Go, and Rust.
- [ ] Local vector embedding and semantic search over docstrings and code context.
- [ ] Automated Architecture Decision Record (ADR) generation.
- [ ] Architecture rule validation & linting (e.g., preventing illegal layer imports).
- [ ] Incremental file-watching synchronization daemon.
- [ ] Pre-commit hooks & GitHub Actions for automated knowledge repository updates.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
