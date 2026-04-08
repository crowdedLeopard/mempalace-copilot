# mempalace-copilot

**Alpha** -- Fork of [MemPalace](https://github.com/milla-jovovich/mempalace) optimized for GitHub Copilot in VS Code.

MemPalace stores every AI conversation you have locally on your machine, organizes it into a searchable structure, and gives your AI tools access to it via MCP. This fork adds first-class GitHub Copilot support: one command generates the VS Code config, Copilot instructions, and tasks you need.

The core retrieval engine is unchanged from upstream. 96.6% Recall@5 on LongMemEval, zero API calls, everything local.

## Status

This is an alpha. The Copilot integration layer is new. The underlying palace engine (ChromaDB storage, semantic search, knowledge graph) is stable upstream code. Expect rough edges in the Copilot-specific tooling.

What works:
- MCP server with all 19 tools, discoverable by Copilot
- One-command VS Code setup (mcp.json, copilot-instructions.md, tasks.json)
- Copilot chat history parsing for mining
- All existing MemPalace features (mining, search, knowledge graph, AAAK, etc.)
- Retrieval smoke test for regression checking

What is untested or incomplete:
- Auto-save equivalent for Copilot (Claude Code has hooks; Copilot relies on manual saves or tasks)
- Copilot chat export format parsing (the format isn't standardized yet)
- Windows-specific edge cases in test cleanup (non-critical, see Known Issues)

## Quick Start

```
pip install mempalace
```

### Set up for Copilot

```
mempalace copilot-setup
```

That creates three files in your project:

```
.vscode/mcp.json                  -- registers MemPalace as an MCP server
.github/copilot-instructions.md   -- loads memory protocol + palace context into Copilot
.vscode/tasks.json                -- adds Save, Search, Status, Wake-up tasks
```

Reload VS Code after running this (Ctrl+Shift+P, "Reload Window").

### Mine your data

```
mempalace init ~/projects/myapp
mempalace mine ~/projects/myapp
mempalace mine ~/chats/ --mode convos
```

### Use it

Open Copilot Chat and ask anything about your past work:

- "What did we decide about authentication?"
- "Why did we choose Postgres?"
- "What has Kai been working on?"

Copilot calls `mempalace_search` or `mempalace_kg_query` automatically via MCP.

### Check retrieval quality

```
mempalace benchmark
```

Runs a synthetic smoke test against the retrieval pipeline. No downloads, no API keys, takes a few seconds. Reports pass/fail against minimum recall thresholds.

For full academic benchmarks (LongMemEval, LoCoMo, ConvoMem), see the `benchmarks/` directory and `benchmarks/README.md`.

## Commands

```
mempalace init <dir>                  Guided onboarding + entity detection
mempalace mine <dir>                  Mine project files into the palace
mempalace mine <dir> --mode convos    Mine conversation exports (Claude, ChatGPT, Copilot, Slack)
mempalace search "query"              Semantic search across all memories
mempalace search "query" --wing app   Search within a specific project
mempalace wake-up                     Show L0 + L1 wake-up context
mempalace status                      Palace overview
mempalace benchmark                   Retrieval smoke test
mempalace copilot-setup               Full Copilot setup (MCP + instructions + tasks)
mempalace copilot-instructions        Regenerate copilot-instructions.md with current palace context
mempalace compress --wing app         AAAK compression (experimental)
mempalace split <dir>                 Split concatenated chat transcripts
mempalace repair                      Rebuild palace index after corruption
```

## How It Works

MemPalace stores your conversations verbatim in ChromaDB. No summarization, no extraction. The structure makes it searchable:

```
WING (person or project)
  ROOM (topic: auth-migration, pricing, ci-pipeline)
    CLOSET (summary pointing to original content)
      DRAWER (verbatim original text)
```

Wings connect via tunnels when the same topic appears in different projects. Rooms connect via halls (memory types: facts, events, discoveries, preferences, advice).

The palace loads in layers:
- L0: Identity (~50 tokens, always loaded)
- L1: Critical facts (~120 tokens, always loaded)
- L2: Room recall (on demand, when a topic comes up)
- L3: Deep search (on demand, full semantic query)

Wake-up cost is ~170 tokens. The rest fires only when needed.

## MCP Tools

The MCP server exposes 19 tools. Copilot discovers them automatically via `.vscode/mcp.json`.

Palace (read): `mempalace_status`, `mempalace_list_wings`, `mempalace_list_rooms`, `mempalace_get_taxonomy`, `mempalace_search`, `mempalace_check_duplicate`, `mempalace_get_aaak_spec`

Palace (write): `mempalace_add_drawer`, `mempalace_delete_drawer`

Knowledge Graph: `mempalace_kg_query`, `mempalace_kg_add`, `mempalace_kg_invalidate`, `mempalace_kg_timeline`, `mempalace_kg_stats`

Navigation: `mempalace_traverse`, `mempalace_find_tunnels`, `mempalace_graph_stats`

Agent Diary: `mempalace_diary_write`, `mempalace_diary_read`

## Saving Memories

Copilot doesn't have auto-save hooks like Claude Code. Three options:

1. **Ask Copilot directly** -- "Save what we discussed about auth to the palace." Copilot calls `mempalace_add_drawer`.
2. **VS Code Tasks** -- Ctrl+Shift+P, "Run Task", "MemPalace: Save Session".
3. **CLI** -- `mempalace mine ~/projects/myapp`

## Benchmarks

All benchmarks from upstream are included and reproducible:

| Benchmark | Mode | Score | API Calls |
|-----------|------|-------|-----------|
| LongMemEval R@5 | Raw (ChromaDB only) | 96.6% | Zero |
| LongMemEval R@5 | Hybrid + Haiku rerank | 100% (500/500) | ~500 |
| LoCoMo R@10 | Raw, session level | 60.3% | Zero |
| ConvoMem | All categories, 50 each | 92.9% | Zero |

Quick regression check:
```
mempalace benchmark
```

Full benchmark suite:
```
python benchmarks/longmemeval_bench.py /path/to/longmemeval_s_cleaned.json --limit 20
python benchmarks/convomem_bench.py --category user_evidence --limit 10
```

See `benchmarks/README.md` for data download instructions and full reproduction steps.

## Differences from Upstream

This fork adds:
- `mempalace copilot-setup` -- generates .vscode/mcp.json, .github/copilot-instructions.md, .vscode/tasks.json
- `mempalace copilot-instructions` -- regenerates instructions with current palace context
- `mempalace benchmark` -- retrieval smoke test for regression checking
- Copilot chat history parsing in the normalizer
- MCP server docs updated for multi-client use (Copilot, Claude, Cursor, etc.)

The core engine (ChromaDB storage, search, mining, knowledge graph, AAAK, palace graph) is unchanged from upstream.

## Requirements

- Python 3.9+
- chromadb >= 0.5.0
- pyyaml >= 6.0
- VS Code with GitHub Copilot

No API key. No internet after install. Everything local.

## Known Issues

- Two test files (`test_miner.py`, `test_convo_miner.py`) fail on Windows during temp directory cleanup. This is a ChromaDB file lock issue on Windows, not a functional problem. The actual mining and search operations complete successfully.
- AAAK compression is experimental and currently regresses retrieval quality (84.2% vs 96.6% raw). Use raw mode (the default) for best results.
- Copilot chat export format is not yet standardized. The parser handles several known formats but may need updates.

## Project Structure

```
mempalace/
  cli.py              CLI entry point
  mcp_server.py       MCP server (19 tools)
  copilot.py          Copilot integration (MCP config, instructions, tasks)
  smoke_test.py       Retrieval regression test
  searcher.py         Semantic search via ChromaDB
  miner.py            Project file ingest
  convo_miner.py      Conversation ingest
  normalize.py        Chat format normalization (Claude, ChatGPT, Copilot, Slack, Codex)
  knowledge_graph.py  Temporal entity graph (SQLite)
  palace_graph.py     Room navigation graph
  layers.py           4-layer memory stack
  dialect.py          AAAK compression
  onboarding.py       Guided setup
benchmarks/
  longmemeval_bench.py
  locomo_bench.py
  convomem_bench.py
hooks/
  mempal_save_hook.sh       Claude Code auto-save hook
  mempal_precompact_hook.sh Claude Code pre-compaction hook
examples/
  copilot_setup.md    Copilot integration guide
  mcp_setup.md        MCP setup for all clients
```

## License

MIT -- see LICENSE.

Fork of [MemPalace](https://github.com/milla-jovovich/mempalace) by milla-jovovich.
