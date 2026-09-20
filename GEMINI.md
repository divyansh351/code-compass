# Antigravity Workspace Guidelines for Code Compass

## Code Compass Integration
This repository is configured with **Code Compass**, a local-first agent knowledge framework exposed via local MCP.

### Guidelines for AI Agent:
1. **Architectural Awareness**:
   - Call `get_project_overview` or `search_knowledge` when exploring project architecture and module structure.
   - Call `get_file_context` or `get_dependencies` before making cross-module modifications.
   - Call `get_change_surface` before refactoring core components to understand the blast radius.

2. **Continuous Learning & Knowledge Updates**:
   - When a new convention, pattern, workflow, or architecture decision is established or corrected by the user, call the `update_knowledge` MCP tool to persist it in `knowledge/conventions/`, `knowledge/workflows/`, or `knowledge/decisions/`.
