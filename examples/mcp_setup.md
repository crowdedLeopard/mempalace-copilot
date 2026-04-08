# MCP Integration

## GitHub Copilot (VS Code) — Recommended

One command sets up everything:

```bash
mempalace copilot-setup
```

This creates `.vscode/mcp.json`, `.github/copilot-instructions.md`, and `.vscode/tasks.json`.

See [copilot_setup.md](copilot_setup.md) for full details.

## Claude Code

```bash
claude mcp add mempalace -- python -m mempalace.mcp_server
```

## Other MCP Clients (Cursor, Gemini CLI, etc.)

Run the MCP server directly:

```bash
python -m mempalace.mcp_server
```

Configure your client to connect via stdio to the above command.

## Available Tools

The server exposes the full MemPalace MCP toolset (19 tools). Common entry points:

- **mempalace_status** — palace stats (wings, rooms, drawer counts)
- **mempalace_search** — semantic search across all memories
- **mempalace_list_wings** — list all projects in the palace
- **mempalace_kg_query** — query the knowledge graph for entity relationships
- **mempalace_add_drawer** — store new verbatim content
