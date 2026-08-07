# ossify-cogents

A lightweight CLI/TUI tool to manage, version, and synchronize AI coding agent configurations — custom skills, agent prompts, system instructions, rules, and more — across your repositories. Point it at git repos or local folders, map what you find there onto target coding agents (Claude Code, GitHub Copilot, Cursor, Windsurf, or custom setups), and keep your AI capabilities structured, up to date, and reproducible.

```
[⚙️ AI Capabilities] ---> [📂 Version Control] ---> [📦 Local Workspace]
```

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)


## Install

```bash
uv tool install git+https://github.com/VZhuck/ossify-cogents.git
```

This puts an `ossify-cogents` executable on your `PATH` — no `uv run` prefix, no virtual environment to activate.

> **PyPI package: under construction.** `ossify-cogents` isn't published to PyPI yet, so `pip install ossify-cogents` / `uv tool install ossify-cogents` won't work today. The git install above is the supported path in the meantime.

## Verify

```bash
ossify-cogents --version
```

## Update

```bash
uv tool upgrade ossify-cogents
```

If that doesn't pick up new commits (uv caches resolved git revisions), force a fresh install instead:

```bash
uv tool install --reinstall git+https://github.com/VZhuck/ossify-cogents.git
```

## Uninstall

```bash
uv tool uninstall ossify-cogents
```

## Getting Started

### Initialize a repo

```bash
ossify-cogents init
```

Creates `ossify-cogents.json` at your workspace root (the nearest `.git` folder, or the current directory — override with `--workspace`/`-ws`). The scaffolded file has one curated registry entry pointing at [anthropics/skills](https://github.com/anthropics/skills), with its `install` selections deliberately empty — it installs nothing until you configure it. Check it's valid any time with:

```bash
ossify-cogents config verify
```

### Add your first registry item

Register a source from the CLI:

```bash
ossify-cogents registry add https://github.com/VZhuck/architect-ai-toolkit.git
```

This appends a new entry to `ossify-skills-registry` (id/name/description inferred from the URL). To actually select what gets installed from it and how it's discovered, you edit `ossify-cogents.json` by hand — `registry add` only appends the source, it doesn't configure discovery or selections.

Here's a fully configured example, with the toolkit above added and wired up alongside the default entry:

```json
{
  "$schema": "https://raw.githubusercontent.com/VZhuck/ossify-cogents/main/schema/v1.json",
  "ossify-skills-registry": [
    {
      "id": "anthropic-skills",
      "name": "Anthropic Skills",
      "description": "Anthropic's library of agent skills.",
      "source-type": "git",
      "source": { "uri": "https://github.com/anthropics/skills", "ref": "main" },
      "discovery": [
        "ossify-open-standard"
      ],
      "install": {
        "target-platforms": [
          "claude"
        ],
        "agents": [],
        "skills": [],
        "commands": [],
        "rules": [],
        "by-pattern": []
      }
    },
    {
      "id": "ai-architect-toolkit",
      "name": "AI Architect Toolkit",
      "description": "ai toolkit",
      "source-type": "git",
      "source": { "uri": "https://github.com/VZhuck/architect-ai-toolkit.git", "ref": "main" },
      "discovery": [
        "ossify-open-standard", "ai-architect-toolkit"
      ],
      "install": {
        "target-platforms": [
          "claude"
        ],
        "agents": [],
        "skills": ["*"],
        "commands": ["*"],
        "rules": ["*"],
        "by-pattern": [
          { "category": "vscode-settings", "action": "json_merge" },
          { "category": "vscode-markdown-styles", "action": "replace" }
        ]
      }
    }
  ],
  "discovery-definitions": [
    {
      "id": "ai-architect-toolkit",
      "type": "custom",
      "mappings": {
        "agents": [
          { "type": "folder", "path": "agents" }
        ],
        "skills": [
          { "type": "folder", "path": "skills" }
        ],
        "commands": [
          { "type": "folder", "path": "commands" }
        ],
        "rules": [
          { "type": "folder", "path": "rules" }
        ],
        "by-pattern": [
          { "type": "file", "path": ".vscode/settings.json", "category": "vscode-settings" },
          { "type": "file", "path": ".vscode/markdown-styles.css", "category": "vscode-markdown-styles" }
        ]
      }
    }
  ]
}
```

A few things this example shows:
-  `discovery` can list more than one strategy per entry (the built-in `ossify-open-standard` plus a custom one); 
-  `"*"` selects every discovered id in a fixed category (`skills`, `commands`, `rules` here); 
-  `by-pattern` selects free-form categories your custom discovery definition maps under `mappings.by-pattern`, each with its own write `action` (`json_merge` merges into an existing file, `replace` overwrites it). See [docs/configuration.md](docs/configuration.md) for the full anatomy and semantics.

Whenever you hand-edit the config, re-validate:

```bash
ossify-cogents config verify
```

### Install dependencies

```bash
ossify-cogents install
```

Fetches every registered source and copies your selected agents/skills/commands/rules into the workspace.

## Advanced Topics

- [docs/configuration.md](docs/configuration.md) — full `ossify-cogents.json` anatomy: discovery definitions, install-selection semantics (globs, wildcards, `by-pattern`), and known limitations like `target-platforms` not supporting `"*"`.
- [docs/install-process.md](docs/install-process.md) — what `install` does under the hood: cache location, always-refetch behavior, copy-from-cache rather than per-file GitHub reads, and why there's no lock file yet.
- [docs/development.md](docs/development.md) — running `ossify-cogents` from a local clone instead of installing it, plus the test/lint/type-check quality gate for contributors.
