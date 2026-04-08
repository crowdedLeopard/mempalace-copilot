#!/usr/bin/env python3
"""
watcher.py — Background auto-save for MemPalace in VS Code.

Watches a project directory for file changes and periodically mines
new or modified files into the palace. Designed to run as a VS Code
background task to complement the instruction-driven auto-save.

The instruction-based save (in copilot-instructions.md) handles
conversation context — decisions, architecture, debugging outcomes.
This watcher handles file-level changes — new code, modified docs,
config changes.

Usage:
    python -m mempalace.watcher ~/projects/myapp
    python -m mempalace.watcher ~/projects/myapp --interval 300
    python -m mempalace.watcher ~/projects/myapp --wing myapp --dry-run

As a VS Code task (added by copilot-setup):
    Ctrl+Shift+P → "Run Task" → "MemPalace: Watch & Auto-Save"
"""

import argparse
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path

from .config import MempalaceConfig


# Files to ignore — common non-content paths
IGNORE_PATTERNS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build",
    ".eggs", "*.egg-info", ".tox", ".cache",
}

WATCH_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".md", ".txt", ".yaml", ".yml", ".toml", ".json", ".cfg",
    ".html", ".css", ".sql", ".sh", ".bash", ".ps1",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php",
}


def _should_ignore(path: Path) -> bool:
    """Check if a path should be ignored."""
    parts = path.parts
    for part in parts:
        if part in IGNORE_PATTERNS:
            return True
        for pattern in IGNORE_PATTERNS:
            if pattern.startswith("*") and part.endswith(pattern[1:]):
                return True
    return False


def _file_hash(filepath: Path) -> str:
    """Quick hash of file content for change detection."""
    try:
        content = filepath.read_bytes()
        return hashlib.md5(content).hexdigest()
    except (OSError, PermissionError):
        return ""


def scan_directory(project_dir: Path) -> dict:
    """Scan directory and return {relative_path: hash} for watched files."""
    files = {}
    try:
        for filepath in project_dir.rglob("*"):
            if not filepath.is_file():
                continue
            if filepath.suffix.lower() not in WATCH_EXTENSIONS:
                continue
            rel = filepath.relative_to(project_dir)
            if _should_ignore(rel):
                continue
            files[str(rel)] = _file_hash(filepath)
    except (OSError, PermissionError):
        pass
    return files


def find_changes(old_snapshot: dict, new_snapshot: dict) -> dict:
    """Compare two snapshots and return changes."""
    added = []
    modified = []
    removed = []

    for path, new_hash in new_snapshot.items():
        if path not in old_snapshot:
            added.append(path)
        elif old_snapshot[path] != new_hash:
            modified.append(path)

    for path in old_snapshot:
        if path not in new_snapshot:
            removed.append(path)

    return {"added": added, "modified": modified, "removed": removed}


def mine_changes(project_dir: str, wing: str = None, dry_run: bool = False):
    """Run mempalace mine on the project directory."""
    from .miner import mine

    palace_path = MempalaceConfig().palace_path
    mine(
        project_dir=project_dir,
        palace_path=palace_path,
        wing_override=wing,
        dry_run=dry_run,
    )


def run_watcher(
    project_dir: str,
    interval: int = 300,
    wing: str = None,
    dry_run: bool = False,
):
    """
    Watch a directory and mine changes periodically.

    Args:
        project_dir: Directory to watch.
        interval: Seconds between scans (default: 300 = 5 minutes).
        wing: Wing name override for mining.
        dry_run: If True, report changes but don't mine.
    """
    project_path = Path(project_dir).expanduser().resolve()
    if not project_path.is_dir():
        print(f"  Error: {project_path} is not a directory")
        sys.exit(1)

    wing_name = wing or project_path.name

    print()
    print("=" * 55)
    print("  MemPalace — File Watcher")
    print("=" * 55)
    print()
    print(f"  Watching:  {project_path}")
    print(f"  Wing:      {wing_name}")
    print(f"  Interval:  {interval}s")
    print(f"  Dry run:   {dry_run}")
    print()
    print("  Taking initial snapshot...")

    snapshot = scan_directory(project_path)
    print(f"  Tracking {len(snapshot)} files")
    print()
    print("  Watching for changes (Ctrl+C to stop)...")
    print()

    # State file to persist snapshot across restarts
    state_dir = Path.home() / ".mempalace" / "watcher_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"{wing_name}.json"

    # Load previous snapshot if available
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                old_snapshot = json.load(f)
            # Check for changes since last run
            changes = find_changes(old_snapshot, snapshot)
            total = len(changes["added"]) + len(changes["modified"])
            if total > 0:
                print(f"  Changes since last run: {len(changes['added'])} added, "
                      f"{len(changes['modified'])} modified, {len(changes['removed'])} removed")
                print("  Mining changes...")
                if not dry_run:
                    mine_changes(str(project_path), wing=wing)
                print()
        except (json.JSONDecodeError, OSError):
            pass

    # Save current snapshot
    with open(state_file, "w") as f:
        json.dump(snapshot, f)

    # Watch loop
    try:
        while True:
            time.sleep(interval)

            new_snapshot = scan_directory(project_path)
            changes = find_changes(snapshot, new_snapshot)
            total_changes = len(changes["added"]) + len(changes["modified"])

            if total_changes > 0:
                timestamp = time.strftime("%H:%M:%S")
                print(f"  [{timestamp}] {len(changes['added'])} added, "
                      f"{len(changes['modified'])} modified, "
                      f"{len(changes['removed'])} removed")

                if changes["added"]:
                    for f_path in changes["added"][:5]:
                        print(f"    + {f_path}")
                    if len(changes["added"]) > 5:
                        print(f"    ... and {len(changes['added']) - 5} more")

                if changes["modified"]:
                    for f_path in changes["modified"][:5]:
                        print(f"    ~ {f_path}")
                    if len(changes["modified"]) > 5:
                        print(f"    ... and {len(changes['modified']) - 5} more")

                if not dry_run:
                    print(f"  [{timestamp}] Mining {total_changes} changed files...")
                    try:
                        mine_changes(str(project_path), wing=wing)
                        print(f"  [{timestamp}] Done.")
                    except Exception as e:
                        print(f"  [{timestamp}] Mining error: {e}")
                else:
                    print(f"  [{timestamp}] (dry run — not mining)")

                snapshot = new_snapshot
                with open(state_file, "w") as f_out:
                    json.dump(snapshot, f_out)

                print()

    except KeyboardInterrupt:
        print("\n  Watcher stopped.")
        # Save final snapshot
        with open(state_file, "w") as f:
            json.dump(snapshot, f)


def main():
    parser = argparse.ArgumentParser(
        description="MemPalace file watcher — auto-mine changes periodically",
    )
    parser.add_argument("dir", help="Project directory to watch")
    parser.add_argument(
        "--interval", type=int, default=300,
        help="Seconds between scans (default: 300 = 5 minutes)",
    )
    parser.add_argument("--wing", default=None, help="Wing name (default: directory name)")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without mining")

    args = parser.parse_args()
    run_watcher(
        project_dir=args.dir,
        interval=args.interval,
        wing=args.wing,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
