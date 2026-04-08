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
        "1. **ON WAKE-UP**: Call `mempalace_status` to load palace overview.",
        "2. **BEFORE RESPONDING** about any person, project, or past event: call `mempalace_search` or `mempalace_kg_query` FIRST. Never guess — verify.",
        "3. **IF UNSURE** about a fact: say \"let me check\" and query the palace.",
        "4. **WHEN FACTS CHANGE**: call `mempalace_kg_invalidate` on the old fact, `mempalace_kg_add` for the new one.",
        "5. **TO SAVE MEMORIES**: call `mempalace_add_drawer` with verbatim content organized into wings and rooms.",
        "",
        "## Key Tools",
        "",
        "- `mempalace_search` — Find anything by semantic search",
        "- `mempalace_kg_query` — Query knowledge graph for entity relationships",
        "- `mempalace_add_drawer` — Store new memories (verbatim, never summarized)",
        "- `mempalace_status` — Palace overview with wing/room counts",
        "- `mempalace_diary_write` — Write session diary entries",
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
    print(f"\n{'=' * 55}\n")

    return results
