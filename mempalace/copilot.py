#!/usr/bin/env python3
"""
copilot.py — GitHub Copilot integration for MemPalace.

Generates VS Code MCP configuration, copilot-instructions.md with wake-up
context, and VS Code tasks for periodic saves.
"""

import json
import os
import sys
from pathlib import Path

from .config import MempalaceConfig
from .layers import MemoryStack


def get_python_executable() -> str:
    """Return the current Python executable path, normalized for JSON."""
    return sys.executable.replace("\\", "/")


def generate_mcp_config(project_dir: str = ".") -> dict:
    """Generate .vscode/mcp.json content for MemPalace MCP server."""
    python_exe = get_python_executable()
    return {
        "servers": {
            "mempalace": {
                "type": "stdio",
                "command": python_exe,
                "args": ["-m", "mempalace.mcp_server"],
            }
        }
    }


def write_mcp_config(project_dir: str = ".") -> Path:
    """Write .vscode/mcp.json to the project directory."""
    project_path = Path(project_dir).resolve()
    vscode_dir = project_path / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)

    mcp_file = vscode_dir / "mcp.json"
    config = generate_mcp_config(project_dir)

    # Merge with existing config if present
    if mcp_file.exists():
        try:
            with open(mcp_file, "r") as f:
                existing = json.load(f)
            if "servers" not in existing:
                existing["servers"] = {}
            existing["servers"]["mempalace"] = config["servers"]["mempalace"]
            config = existing
        except (json.JSONDecodeError, OSError):
            pass

    with open(mcp_file, "w") as f:
        json.dump(config, f, indent=2)

    return mcp_file


def generate_copilot_instructions(wing: str = None) -> str:
    """Generate copilot-instructions.md content with MemPalace wake-up context."""
    cfg = MempalaceConfig()
    stack = MemoryStack(palace_path=cfg.palace_path)

    lines = [
        "# Copilot Instructions — MemPalace Memory System",
        "",
        "You have access to MemPalace, a persistent memory system with 19 MCP tools.",
        "Use these tools to recall past decisions, search conversations, and store new memories.",
        "",
        "## Memory Protocol",
        "",
        "1. **ON WAKE-UP**: Call `mempalace_status` to load palace overview. Then call `mempalace_list_wings` to see which projects exist. Identify the current project from the workspace folder name.",
        "2. **BEFORE RESPONDING** about any person, project, or past event: call `mempalace_search` or `mempalace_kg_query` FIRST. Never guess — verify.",
        "3. **IF UNSURE** about a fact: say \"let me check\" and query the palace.",
        "4. **WHEN FACTS CHANGE**: call `mempalace_kg_invalidate` on the old fact, `mempalace_kg_add` for the new one.",
        "5. **TO SAVE MEMORIES**: call `mempalace_add_drawer` with verbatim content organized into wings and rooms.",
        "",
        "## Auto-Save Protocol",
        "",
        "You are responsible for saving important context to the palace during this session.",
        "Follow these rules:",
        "",
        "### Determining the Wing (project isolation)",
        "",
        "The palace uses WINGS to separate projects. Every save must include the correct wing.",
        "To determine the wing for this session:",
        "",
        "1. Look at the workspace folder name from any file paths you see (e.g., if files are under",
        "   `/home/user/projects/acme-api/`, the wing is `acme-api`).",
        "2. If unsure, call `mempalace_list_wings` to see existing wings and match the current project.",
        "3. If this is a new project not yet in the palace, use the workspace folder name as the wing.",
        "4. Use this wing consistently for ALL saves in this session — never mix wings.",
        "",
        "### What and when to save",
        "",
        "- **AFTER EVERY SIGNIFICANT DECISION OR OUTCOME**: immediately call `mempalace_add_drawer`",
        "  with the verbatim exchange. Use the wing determined above and a descriptive slug as the room",
        "  (e.g., wing=\"acme-api\", room=\"auth-migration\").",
        "- **EVERY 10-15 EXCHANGES**: call `mempalace_diary_write` with a compressed summary of the session",
        "  so far. Include: topics discussed, decisions made, code changes, open questions.",
        "  Use your agent name as the agent_name parameter.",
        "- **BEFORE THE USER ENDS THE SESSION** (if they say goodbye, thanks, done, etc.):",
        "  do a final save of any unsaved decisions, code changes, or important context.",
        "- **WHAT TO SAVE** (always verbatim, never summarized):",
        "  - Decisions: \"We chose X because Y\"",
        "  - Architecture changes: \"Switched from X to Y\"",
        "  - Debugging outcomes: \"The bug was caused by X, fixed by Y\"",
        "  - Preferences expressed: \"Use tabs not spaces\", \"Prefer composition over inheritance\"",
        "  - People and roles: \"Kai is handling the auth migration\"",
        "- **WHAT NOT TO SAVE**: greetings, small talk, trivial clarifications, repeated information",
        "  already in the palace (check with `mempalace_check_duplicate` if unsure).",
        "",
        "## Key Tools",
        "",
        "- `mempalace_search` — Find anything by semantic search",
        "- `mempalace_kg_query` — Query knowledge graph for entity relationships",
        "- `mempalace_add_drawer` — Store new memories (verbatim, never summarized)",
        "- `mempalace_status` — Palace overview with wing/room counts",
        "- `mempalace_diary_write` — Write session diary entries",
        "- `mempalace_check_duplicate` — Check before filing to avoid duplicates",
        "",
    ]

    # Try to add wake-up context if palace exists
    try:
        wake_up = stack.wake_up(wing=wing)
        if "No palace found" not in wake_up and "No memories yet" not in wake_up:
            lines.extend([
                "## Your World (auto-generated from palace)",
                "",
                wake_up,
                "",
            ])
    except Exception:
        lines.extend([
            "## Getting Started",
            "",
            "No palace data yet. Run `mempalace init <dir>` and `mempalace mine <dir>` to populate.",
            "",
        ])

    return "\n".join(lines)


def write_copilot_instructions(project_dir: str = ".", wing: str = None) -> Path:
    """Write .github/copilot-instructions.md to the project directory."""
    project_path = Path(project_dir).resolve()
    github_dir = project_path / ".github"
    github_dir.mkdir(parents=True, exist_ok=True)

    instructions_file = github_dir / "copilot-instructions.md"
    content = generate_copilot_instructions(wing=wing)

    # If file exists, append MemPalace section rather than overwriting
    if instructions_file.exists():
        existing = instructions_file.read_text()
        if "MemPalace" not in existing:
            content = existing.rstrip() + "\n\n---\n\n" + content
        else:
            # Already has MemPalace section — update it
            # Find and replace the MemPalace block
            marker_start = "# Copilot Instructions — MemPalace Memory System"
            if marker_start in existing:
                before = existing[:existing.index(marker_start)].rstrip()
                if before:
                    content = before + "\n\n---\n\n" + content
            # else: full replace is fine

    instructions_file.write_text(content)
    return instructions_file


def generate_vscode_tasks() -> dict:
    """Generate .vscode/tasks.json with MemPalace save and wake-up tasks."""
    python_exe = get_python_executable()
    return {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "MemPalace: Save Session",
                "type": "shell",
                "command": python_exe,
                "args": ["-m", "mempalace", "mine", "${workspaceFolder}", "--mode", "projects"],
                "group": "none",
                "presentation": {
                    "echo": True,
                    "reveal": "silent",
                    "focus": False,
                    "panel": "shared",
                },
                "problemMatcher": [],
            },
            {
                "label": "MemPalace: Search",
                "type": "shell",
                "command": python_exe,
                "args": ["-m", "mempalace", "search", "${input:searchQuery}"],
                "group": "none",
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": True,
                    "panel": "shared",
                },
                "problemMatcher": [],
            },
            {
                "label": "MemPalace: Status",
                "type": "shell",
                "command": python_exe,
                "args": ["-m", "mempalace", "status"],
                "group": "none",
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": True,
                    "panel": "shared",
                },
                "problemMatcher": [],
            },
            {
                "label": "MemPalace: Wake-up Context",
                "type": "shell",
                "command": python_exe,
                "args": ["-m", "mempalace", "wake-up"],
                "group": "none",
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": True,
                    "panel": "shared",
                },
                "problemMatcher": [],
            },
            {
                "label": "MemPalace: Watch & Auto-Save",
                "type": "shell",
                "command": python_exe,
                "args": ["-m", "mempalace", "watch", "${workspaceFolder}", "--interval", "300"],
                "group": "none",
                "isBackground": True,
                "presentation": {
                    "echo": True,
                    "reveal": "silent",
                    "focus": False,
                    "panel": "dedicated",
                },
                "problemMatcher": [],
            },
        ],
        "inputs": [
            {
                "id": "searchQuery",
                "description": "What do you want to search for in your palace?",
                "type": "promptString",
            }
        ],
    }


def write_vscode_tasks(project_dir: str = ".") -> Path:
    """Write .vscode/tasks.json with MemPalace tasks."""
    project_path = Path(project_dir).resolve()
    vscode_dir = project_path / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)

    tasks_file = vscode_dir / "tasks.json"
    tasks_config = generate_vscode_tasks()

    # Merge with existing tasks if present
    if tasks_file.exists():
        try:
            with open(tasks_file, "r") as f:
                existing = json.load(f)
            # Remove any existing MemPalace tasks
            if "tasks" in existing:
                existing["tasks"] = [
                    t for t in existing["tasks"]
                    if not t.get("label", "").startswith("MemPalace:")
                ]
                existing["tasks"].extend(tasks_config["tasks"])
            else:
                existing["tasks"] = tasks_config["tasks"]
            # Add inputs if not already present
            if "inputs" not in existing:
                existing["inputs"] = []
            existing_input_ids = {i.get("id") for i in existing["inputs"]}
            for inp in tasks_config.get("inputs", []):
                if inp["id"] not in existing_input_ids:
                    existing["inputs"].append(inp)
            tasks_config = existing
        except (json.JSONDecodeError, OSError):
            pass

    with open(tasks_file, "w") as f:
        json.dump(tasks_config, f, indent=2)

    return tasks_file


def setup_copilot(project_dir: str = ".", wing: str = None) -> dict:
    """
    Full Copilot setup: MCP config + instructions + tasks.
    Returns paths of all generated files.
    """
    results = {}

    print(f"\n{'=' * 55}")
    print("  MemPalace — GitHub Copilot Setup")
    print(f"{'=' * 55}\n")

    # 1. MCP config
    mcp_path = write_mcp_config(project_dir)
    results["mcp_config"] = str(mcp_path)
    print(f"  MCP config:     {mcp_path}")

    # 2. Copilot instructions
    instructions_path = write_copilot_instructions(project_dir, wing=wing)
    results["instructions"] = str(instructions_path)
    print(f"  Instructions:   {instructions_path}")

    # 3. VS Code tasks
    tasks_path = write_vscode_tasks(project_dir)
    results["tasks"] = str(tasks_path)
    print(f"  Tasks:          {tasks_path}")

    print(f"\n{'─' * 55}")
    print("  Setup complete! Copilot now has access to your palace.")
    print()
    print("  What happens next:")
    print("    1. Reload VS Code window (Ctrl+Shift+P → 'Reload Window')")
    print("    2. Copilot will discover the MemPalace MCP tools automatically")
    print("    3. Ask Copilot: \"What do you know about my projects?\"")
    print()
    print("  VS Code Tasks available (Ctrl+Shift+P → 'Run Task'):")
    print("    - MemPalace: Save Session")
    print("    - MemPalace: Search")
    print("    - MemPalace: Status")
    print("    - MemPalace: Wake-up Context")
    print("    - MemPalace: Watch & Auto-Save  (background — mines changes every 5 min)")
    print()
    print("  Auto-save is two-layer:")
    print("    1. Copilot saves decisions/context via MCP tools (instruction-driven)")
    print("    2. File watcher mines code changes (run the Watch task above)")
    print(f"\n{'=' * 55}\n")

    return results


# ============================================================
# Global (user-level) setup — run once, works in every project
# ============================================================


def _get_vscode_user_settings_path() -> Path:
    """Return the path to VS Code user settings.json."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "settings.json"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / "User" / "settings.json"
    else:
        return Path.home() / ".config" / "Code" / "User" / "settings.json"


def _get_vscode_user_prompts_dir() -> Path:
    """Return the VS Code user prompts directory."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "prompts"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / "User" / "prompts"
    else:
        return Path.home() / ".config" / "Code" / "User" / "prompts"


def write_global_mcp_config() -> Path:
    """Add MemPalace MCP server to VS Code user settings.json."""
    settings_path = _get_vscode_user_settings_path()

    if not settings_path.exists():
        print(f"  Warning: VS Code settings not found at {settings_path}")
        print("  Creating with MCP config only.")
        settings = {}
    else:
        with open(settings_path, "r") as f:
            content = f.read()
        # Handle VS Code's settings.json which may have trailing commas and comments
        # Strip single-line comments (but not :// in URLs)
        import re
        cleaned = re.sub(r'(?<!:)//.*$', '', content, flags=re.MULTILINE)
        # Strip trailing commas before } or ]
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        try:
            settings = json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"  Warning: Could not parse {settings_path}")
            print("  Skipping user settings. Use --project instead for per-project setup.")
            return settings_path

    python_exe = get_python_executable()

    # Add MCP server under "mcp" key (VS Code user-level MCP config)
    if "mcp" not in settings:
        settings["mcp"] = {}
    if "servers" not in settings["mcp"]:
        settings["mcp"]["servers"] = {}

    settings["mcp"]["servers"]["mempalace"] = {
        "type": "stdio",
        "command": python_exe,
        "args": ["-m", "mempalace.mcp_server"],
    }

    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=4)

    return settings_path


def write_global_copilot_instructions(wing: str = None) -> Path:
    """Write MemPalace instructions to VS Code user prompts directory."""
    prompts_dir = _get_vscode_user_prompts_dir()
    prompts_dir.mkdir(parents=True, exist_ok=True)

    instructions_file = prompts_dir / "mempalace.instructions.md"
    content = generate_copilot_instructions(wing=wing)

    instructions_file.write_text(content)
    return instructions_file


def setup_copilot_global(wing: str = None) -> dict:
    """
    Global Copilot setup — run once, works in every project.
    Adds MCP server to VS Code user settings and instructions to user prompts.
    """
    results = {}

    print(f"\n{'=' * 55}")
    print("  MemPalace — Global Copilot Setup")
    print(f"{'=' * 55}\n")

    # 1. Palace init (ensure ~/.mempalace exists)
    cfg = MempalaceConfig()
    cfg.init()
    print(f"  Palace:         {cfg.palace_path}")

    # 2. MCP server in user settings
    settings_path = write_global_mcp_config()
    results["settings"] = str(settings_path)
    print(f"  MCP config:     {settings_path}")

    # 3. Instructions in user prompts
    instructions_path = write_global_copilot_instructions(wing=wing)
    results["instructions"] = str(instructions_path)
    print(f"  Instructions:   {instructions_path}")

    print(f"\n{'─' * 55}")
    print("  Global setup complete! MemPalace is now available in every project.")
    print()
    print("  What happens next:")
    print("    1. Reload VS Code (Ctrl+Shift+P → 'Reload Window')")
    print("    2. Open any project — Copilot already has the 19 MCP tools")
    print("    3. Start working. Copilot auto-saves decisions to the palace.")
    print()
    print("  To mine an existing project into the palace:")
    print("    mempalace mine ~/projects/myapp --wing myapp")
    print()
    print("  To check what's in the palace:")
    print("    mempalace status")
    print(f"\n{'=' * 55}\n")

    return results
