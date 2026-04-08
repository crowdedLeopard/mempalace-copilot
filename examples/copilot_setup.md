# MCP Integration — GitHub Copilot (VS Code)

## Quick Setup (recommended)

One command sets up everything:

```bash
mempalace copilot-setup
```

This creates three files in your project:

| File | What it does |
|------|-------------|
| `.vscode/mcp.json` | Registers MemPalace as an MCP server — Copilot discovers all 19 tools |
| `.github/copilot-instructions.md` | Loads your palace context + memory protocol into Copilot |
| `.vscode/tasks.json` | Adds VS Code tasks for save, search, status, and wake-up |

Reload VS Code after running this (`Ctrl+Shift+P` → "Reload Window").

## Manual Setup

### 1. MCP Server Configuration

Create `.vscode/mcp.json` in your project root:

```json
{
  "servers": {
    "mempalace": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mempalace.mcp_server"]
    }
  }
}
```

> **Note:** Use the full path to your Python executable if `python` isn't on your PATH, or if you're using a virtual environment:
> ```json
> "command": "/path/to/venv/bin/python"
> ```

### 2. Copilot Instructions (optional but recommended)

Create `.github/copilot-instructions.md` in your project root:

```markdown
You have access to MemPalace, a persistent memory system with 19 MCP tools.

## Memory Protocol

1. Call `mempalace_status` to see what's in the palace.
2. Before answering about past decisions or people, call `mempalace_search` first.
3. Use `mempalace_add_drawer` to save important decisions and context.
4. Use `mempalace_kg_query` to check entity relationships.
```

Or generate it automatically with current palace context:

```bash
mempalace copilot-instructions
```

### 3. Verify It Works

1. Open VS Code in your project
2. Open Copilot Chat (`Ctrl+Shift+I` or click the Copilot icon)
3. Ask: *"What MemPalace tools do you have available?"*
4. Copilot should list the 19 MCP tools

Then try a real query:
> *"Search my palace for authentication decisions"*

Copilot will call `mempalace_search` automatically and return verbatim results.

## Available MCP Tools

Once configured, Copilot has access to all 19 MemPalace tools:

### Palace (read)
| Tool | What |
|------|------|
| `mempalace_status` | Palace overview + AAAK spec + memory protocol |
| `mempalace_list_wings` | Wings with counts |
| `mempalace_list_rooms` | Rooms within a wing |
| `mempalace_get_taxonomy` | Full wing → room → count tree |
| `mempalace_search` | Semantic search with wing/room filters |
| `mempalace_check_duplicate` | Check before filing |
| `mempalace_get_aaak_spec` | AAAK dialect reference |

### Palace (write)
| Tool | What |
|------|------|
| `mempalace_add_drawer` | File verbatim content |
| `mempalace_delete_drawer` | Remove by ID |

### Knowledge Graph
| Tool | What |
|------|------|
| `mempalace_kg_query` | Entity relationships with time filtering |
| `mempalace_kg_add` | Add facts |
| `mempalace_kg_invalidate` | Mark facts as ended |
| `mempalace_kg_timeline` | Chronological entity story |
| `mempalace_kg_stats` | Graph overview |

### Navigation
| Tool | What |
|------|------|
| `mempalace_traverse` | Walk the graph from a room across wings |
| `mempalace_find_tunnels` | Find rooms bridging two wings |
| `mempalace_graph_stats` | Graph connectivity overview |

### Agent Diary
| Tool | What |
|------|------|
| `mempalace_diary_write` | Write AAAK diary entry |
| `mempalace_diary_read` | Read recent diary entries |

## Saving Memories

MemPalace auto-save works in two layers:

### Layer 1: Instruction-driven (automatic)

The generated `copilot-instructions.md` includes an auto-save protocol. Copilot will:
- Save decisions and outcomes immediately via `mempalace_add_drawer`
- Write a diary summary every 10-15 exchanges via `mempalace_diary_write`
- Do a final save when the session ends (goodbye, thanks, done, etc.)

This happens automatically. You don't need to ask Copilot to save — the instructions tell it when and what to save.

### Layer 2: File watcher (background task)

Start the watcher as a VS Code background task:
- `Ctrl+Shift+P` → "Run Task" → "MemPalace: Watch & Auto-Save"

Or from the CLI:
```bash
mempalace watch ~/projects/myapp
mempalace watch ~/projects/myapp --interval 120  # scan every 2 minutes
```

The watcher scans for new or modified files every 5 minutes and mines them into the palace. It persists state between restarts so it only mines actual changes.

### Manual saves

You can still save manually:

- Tell Copilot: *"Save what we discussed about auth to the palace"*
- Run `Ctrl+Shift+P` → "Run Task" → "MemPalace: Save Session"
- CLI: `mempalace mine ~/projects/myapp`

## Updating Instructions

When your palace grows, regenerate the instructions to include fresh context:

```bash
mempalace copilot-instructions
mempalace copilot-instructions --wing myproject  # project-specific
```

## Differences from Claude Code Setup

| Feature | Claude Code | VS Code + Copilot |
|---------|------------|-------------------|
| MCP config | `claude mcp add mempalace` | `.vscode/mcp.json` |
| Instructions | `CLAUDE.md` | `.github/copilot-instructions.md` |
| Auto-save (conversation) | Stop/PreCompact hooks (shell scripts) | Instruction-driven (AI saves via MCP tools) |
| Auto-save (files) | Not built-in | File watcher background task |
| Wake-up context | Injected via hooks | Loaded from instructions file |
| Tool discovery | Automatic | Automatic (MCP protocol) |

The core MCP server and all 19 tools are identical — only the configuration layer differs.
