# Configuring `ossify-cogents.json`

## Top-level shape

```json
{
  "$schema": "https://raw.githubusercontent.com/VZhuck/ossify-cogents/main/schema/v1.json",
  "ossify-skills-registry": [ /* SkillSource[] */ ],
  "discovery-definitions": [ /* DiscoveryDefinition[] */ ]
}
```

The full shape is defined in [`schema/v1.json`](../schema/v1.json) — a JSON Schema you can read directly, or let your editor read for you (see below). `ossify-cogents init` scaffolds a starting file with one example of each section.

## `$schema` and editor autocomplete

`ossify-cogents init` writes a `"$schema"` field pointing at the raw GitHub URL for `schema/v1.json`. Editors that understand the JSON Schema `$schema` convention (VS Code's built-in JSON support, IntelliJ, etc.) pick this up automatically — you get autocomplete, inline docs, and validation on `ossify-cogents.json` with no extra setup.

This is currently pinned to `main`, not to a release version — the project has no versioned-release convention yet, so the schema your editor validates against is always the latest on `main`, which may occasionally be ahead of whatever CLI version you have installed. If your editor can't reach `raw.githubusercontent.com` (offline, restrictive proxy), you just lose autocomplete — the CLI itself doesn't depend on `$schema` at all.

## Registry entries (`ossify-skills-registry`)

Each entry is a `SkillSource`: an `id`/`name`/`description`, a `source` (git URL + ref, or a local path), a `discovery` list (which discovery strategies to run against that source), and an `install` block (what to actually select for installation).

```json
{
  "id": "agent-pack",
  "name": "Agent Pack",
  "description": "",
  "source-type": "git",
  "source": { "uri": "https://github.com/acme-org/agent-pack.git", "ref": "main" },
  "discovery": ["ossify-open-standard"],
  "install": {
    "mode": "copy",
    "target-platforms": ["claude"],
    "agents": [],
    "skills": [],
    "commands": [],
    "rules": [],
    "by-pattern": []
  }
}
```

`ossify-cogents registry add <uri>` appends an entry like this (id/name/description inferred from the uri unless overridden). There is currently **no command to edit `install.*` or `discovery` on an existing entry** — that's a hand-edit of the JSON, followed by `ossify-cogents config verify`.

## Discovery: turning files into selectable ids

A `discovery` strategy maps a source's file layout to a flat list of ids per category (`agents`, `skills`, `commands`, `rules`, plus a free-form `by-pattern`). Those ids are what your `install` selections match against — not raw file paths.

- **Folder rule** (`{"type": "folder", "path": "agents"}`): each immediate child under `agents/` becomes a discoverable id. A child *directory* keeps its name; a child *file* contributes its stem.
- **File rule** (`{"type": "file", "path": "<glob>"}`): the file stem of each match becomes a discoverable id.

Discovered ids are always **extension-free canonical names**, whichever rule produced them: `commands/md-to-word.md` discovers as `md-to-word`. The extension belongs to the destination, not the id — the same id installs as `.claude/commands/md-to-word.md` for Claude and `.github/instructions/md-to-word.instructions.md` for Copilot. Write your `install` selections against the bare name; a literal that includes the extension matches nothing and fails the run.

The built-in `ossify-open-standard` strategy (referenced by id, never written into your config) expects this layout at a source's root:

```
agents/
skills/
commands/
rules/
```

Each immediate child of those folders is one discoverable id. If a source uses a different layout, define your own strategy under `discovery-definitions` — `ossify-cogents init` writes an `example-standard` entry mirroring the built-in, purely to document the shape:

```json
{
  "id": "example-standard",
  "type": "custom",
  "mappings": {
    "agents": [{ "type": "folder", "path": "agents" }],
    "skills": [{ "type": "folder", "path": "skills" }],
    "commands": [{ "type": "folder", "path": "commands" }],
    "rules": [{ "type": "folder", "path": "rules" }],
    "by-pattern": []
  }
}
```

Custom discovery ids must not collide with a built-in id (like `ossify-open-standard`) and shouldn't use the reserved `ossify-` prefix.

## Install selections: globs against discovered ids

Each fixed category in `install` (`agents`, `skills`, `commands`, `rules`) is a list of [`fnmatch`](https://docs.python.org/3/library/fnmatch.html) glob patterns, matched against the ids that `discovery` produced for that category:

- **Empty or absent** → selects nothing.
- **`"*"`** → matches every discovered id in that category.
- **A literal name** (e.g. `"code-reviewer"`) → must match an existing id exactly, or `install` fails with an error.
- **A glob** (e.g. `"review-*"`) → matches whatever it matches; if it matches nothing, `install` emits a warning rather than failing.

### `mode`: copy or link

`install.mode` decides how the selected files reach your workspace:

- **`"copy"`** (the default, and what you get when the field is absent) writes the bytes into the destination.
- **`"link"`** points the destination at the source with a symbolic link, so the installed capability *is* the source file. Edits propagate both ways with no re-install, which is what you want while authoring a shared toolkit that several repos consume.

`mode: "link"` requires `source-type: "local"`. A `git` entry declaring it is rejected as an invalid registry entry (offline, by `config verify`) because ossify hard-resets its git cache on every fetch — an edit made through a link into that cache would be destroyed on the next run without warning.

There is no CLI flag for this. Linking is a per-entry decision, and a config routinely mixes a `git` source with one or more `local` ones.

**Link geometry is derived, not configured.** A source resolving *inside* the workspace root links relatively (`.claude/skills/pdf -> ../../tools/toolkit/skills/pdf`), which survives a clone and is meant to be committed. A source *outside* the workspace links absolutely, which is machine-specific — those destinations are recorded in `.git/info/exclude`, never `.gitignore`. See [install-process.md](install-process.md) for the full link semantics.

> **`target-platforms` takes literal platform names, and the usable set is narrower than `config verify` accepts.** Two lists disagree today, so check both before you commit a value:
>
> | Value | `config verify` | `install` |
> |---|---|---|
> | `"claude"` | accepted | works (`skills`, `agents`, `commands`, `rules`) |
> | `"copilot"` | accepted | works (`skills`, `agents`, `rules`; no `commands`) |
> | `"codex"` | **rejected** — `unknown target platform 'codex'` | would work (`skills` only) |
> | `"cursor"`, `"windsurf"` | accepted | fails — `TargetLayoutUnavailableError`, no layout wired |
> | `"*"` | accepted | fails — `TargetLayoutUnavailableError`, there is no wildcard fan-out |
>
> Unlike the fixed-category lists above, `"*"` is **not** expanded here. In practice, `"claude"` and `"copilot"` are the two values that work end to end; list them explicitly.

## Walkthrough: from the empty scaffold to a real install

`ossify-cogents init` writes a config that installs nothing on purpose. To make it do something:

1. Point the registry entry's `discovery` at a strategy that matches the source's layout (built-in `ossify-open-standard`, or your own custom one).
2. Pick what to install. To grab everything discovered in a category:
   ```json
   "install": {
     "target-platforms": ["claude"],
     "agents": ["*"],
     "skills": ["*"],
     "commands": [],
     "rules": [],
     "by-pattern": []
   }
   ```
   Or select specific items by id/glob:
   ```json
   "agents": ["code-reviewer", "release-*"]
   ```
3. For a category the fixed list doesn't cover, add a `by-pattern` selection referencing a `category` your `discovery-definitions` defines under `mappings.by-pattern`, plus a write `action` (`init`, `replace`, or `json_merge`):
   ```json
   "by-pattern": [{ "category": "prompts", "action": "replace" }]
   ```
4. Re-validate:
   ```bash
   ossify-cogents config verify
   ```
5. Install:
   ```bash
   ossify-cogents install
   ```

There's no CLI shortcut for step 2/3 today — editing `ossify-cogents.json` directly (with `$schema`-powered autocomplete to help) is the current workflow.
