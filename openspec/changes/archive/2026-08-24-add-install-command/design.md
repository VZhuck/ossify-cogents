## Context

Fetch → enumerate → select → translate → write is the full "install from remote"
spine. Only *select* (`InstallResolver`) and *write-primitive*
(`FilesystemTargetAdapter`) exist. This change builds the rest as the imperative
`ossify install` command (Fork A), respecting the hexagonal layout: domain has no
outward deps, ports are `Protocol`s, adapters wire only in `container.py`,
OS/infra concerns (git, `platformdirs`) live strictly in adapters.

```
  ossify install
    └─ for each registry entry:
         SourcePort.materialize(entry) ─▶ working-tree root (git cache | local dir)
         DiscoveryExecution.enumerate(root, resolved strategies)
              ─▶ { category: { id: location } }         (fixed + by-pattern categories)
         InstallResolver.select(entry.install[cat], ids)  per fixed category
         TargetLayout.path_for(platform, category, id)  translate  (Claude v1)
         write:  fixed-category ─▶ replace (remove + override, tree-walked)
                 by-pattern     ─▶ init | replace | json_merge, verbatim to discovery path
```

## Goals / Non-Goals

**Goals:**
- One imperative command that fetches and installs selected capabilities end to end.
- Durable, OS-specific, reboot-surviving per-source cache with an env override.
- Keep target-layout knowledge in the application layer; keep git/OS concerns in
  adapters; reuse the existing selection + write pieces unchanged.

**Non-Goals:**
- No lock file, no drift detection, no declarative `sync` reconciler (Fork B).
- No SHA persistence — the git SHA is resolvable at fetch time but not recorded.
- No non-Claude target layouts in v1 (structured so they are additive later).
- No pure-Python git — the runtime shells out to the `git` binary.

## Decisions

### Imperative install, no lock (Fork A)
`install` re-materializes and re-writes on every run; it does not diff against a
prior state. This is the smallest thing that makes "fetch from remote → files in
my repo" real. Fork B later wraps this pipeline in a reconciler and persists a
lock; the git SHA that the fetch already resolves becomes the natural lock input.
- *Consequence:* running `install` twice is idempotent only insofar as the source
  is unchanged; it always overwrites (fixed-category `replace`).

### Durable per-source cache; `platformdirs`, `OSSIFY_CACHE_DIR` override
Cache root = `$OSSIFY_CACHE_DIR` if set, else
`platformdirs.user_cache_dir("ossify-cogents")` (macOS `~/Library/Caches`, Linux
`$XDG_CACHE_HOME`/`~/.cache`, Windows `%LOCALAPPDATA%\…\Cache`). Per source:
`<root>/repos/<short-slug>-<sha256[:8]>/`, where `short-slug` is the uri's last
path segment (`.git` stripped, sanitized to filesystem-safe chars) and the suffix
is the first 8 hex chars of `sha256(normalized uri)`. The hash is over the *full*
normalized uri, so uniqueness/collision behavior derives from the full digest;
`short-slug` is a cosmetic prefix so `ls`ing the cache is legible. If `.git`
exists → `git fetch` + checkout `ref`; else `git clone` + checkout. The tree is
left in place to survive between runs and across reboots (until the cache is
cleaned).
- *Alternative considered:* pure `sha256(normalized uri)` directory name.
  Rejected: opaque — a cache dir tells the user nothing about which source it is.
  The `short-slug-` prefix costs nothing (name is cosmetic; hash still carries
  uniqueness) and makes the cache debuggable.

*Normalization* (what "normalized uri" means, feeding both the hash and the
cache-reuse decision) is deterministic and defined in the `source-fetch` spec:
git uris collapse scp/ssh/https spellings to `host/path` (lowercased host, `.git`
and trailing `/` stripped, query/fragment dropped); local uris resolve to an
absolute symlink-resolved canonical path. The `ref` is deliberately *not* part of
identity — one repo cache holds whichever ref is checked out.
- *Alternative considered:* `tempfile.gettempdir()` (no dependency). Rejected: `/tmp`
  and macOS `/var/folders` are wiped on reboot/cleanup, failing the
  "survive reboots" requirement. Cache is the correct semantic home (safe to
  delete → rebuilt), and `platformdirs` gets the three OS paths right without
  hand-rolled `sys.platform` branching. The dependency lives only in the git
  adapter, at the edge of the hexagon.
- *Alternative considered:* ephemeral temp clone per run. Rejected: re-clones every
  run; the user explicitly wants the cache to survive between commands.

### `SourcePort` = materialize + read side; dispatch by `source_type`
`SourcePort` exposes `materialize(entry) -> Path` plus a read side (walk the tree,
read a file's bytes). Two adapters — git and local — differ only in `materialize`
(git clones/fetches into the cache; local returns `source.uri` as-is); walk/read
are a shared working-tree implementation. The container injects a
`{ "git": …, "local": … }` map keyed by `source_type` (mirroring how built-in
discovery strategies are injected); the use case picks per entry.
- *Alternative considered:* one adapter branching on `source_type` internally.
  Rejected: mixes git and filesystem concerns in one adapter; the map keeps each
  adapter single-purpose.

### Discovery execution belongs to `skill-discovery`
`skill-discovery` already owns *how to find* capabilities (strategy resolution).
Executing a resolved strategy's `Mapping` globs against a materialized tree —
turning `{type: folder, path: "skills"}` into discovered ids and their locations —
is the same capability's runtime half, so it lands there, not in `install-apply`.
- *Enumeration semantics:* a `folder` rule enumerates the immediate children of the
  folder (id = child name; the item payload is that child, which may be a whole
  subtree); a `file` rule enumerates matching files (id = file stem). `by-pattern`
  rules enumerate the same way but under their free-form `category`.

### Apply is a new capability (`install-apply`), not folded into `capability-install`
`capability-install` was deliberately scoped to the *declarative* model + selection
+ resolution; its Purpose carries a "apply deferred" note. Rather than contradict
that, the apply/write behavior lands in a sibling `install-apply` capability that
consumes the model. (Sync-time note: `capability-install`'s scope note should be
updated to point at `install-apply` as the imperative apply, with the lock/sync
reconciler still future.)

### Fixed-category `replace` = tree-walked remove + override; `TargetPort.remove`
A selected fixed-category item can be a directory tree, but `TargetPort` writes a
single `(path, bytes)`. To keep the port dumb and layout in the application, the
use case walks the item's subtree (via `SourcePort` read side), computes each
file's destination under the translated layout path, and writes each via
`override`. For true wholesale `replace`, the use case first calls a new
`TargetPort.remove(path)` on the destination item root (delete-then-write),
avoiding stale leftover files.
- *Alternative considered:* a `copy_tree(src, dst)` on `TargetPort`. Rejected:
  pushes source-tree/path knowledge into the target port; the archived design
  keeps the port at single-file granularity with layout owned by the application.

### Target layout: application-owned const registry, selected by platform key
The canonical-item → per-platform-path translation is a **constant registry** in
the application layer, keyed `(platform, category) -> [(destination, shape)]`. The
layout is selected **dynamically by the platform key** from
`install.target-platforms`, so the same const can later be overridden from config
without touching the pipeline (the future config-driven approach). A
`(platform, category)` with no registry entry is a clear error, not a silent skip.
Installs are **verbatim content copy** — the registry only relocates and renames;
it never transforms bytes.

v1 populates three platforms (normative copy lives in the `install-apply` spec;
this is the rationale mirror):

| `(platform, category)` | destination | shape |
|---|---|---|
| `(claude, skills)`   | `.claude/skills/<id>/`     | **directory** (walk subtree; entry `SKILL.md`) |
| `(claude, agents)`   | `.claude/agents/<id>.md`   | **file** |
| `(claude, commands)` | `.claude/commands/<id>.md` | **file** |
| `(claude, rules)`    | `.claude/rules/<id>.md`    | **file** |
| `(copilot, skills)`  | `.github/skills/<id>/`     | **directory** |
| `(copilot, agents)`  | `.github/agents/<id>.agent.md` | **file** |
| `(copilot, rules)`   | `.github/instructions/<id>.instructions.md` | **file** |
| `(codex, skills)`    | `.agents/skills/<id>/`     | **directory** |

The template re-adds the per-platform extension (`.md` / `.agent.md`), since
discovery ids are bare stems; skills-type categories are directory-shaped.
- *Why these and not others:* verbatim copy works wherever the item is the same
  content at a different path/extension. It **cannot** produce `(codex, agents)`
  (Codex agents are TOML — a format change) or `(codex, rules)` (a single merged
  `AGENTS.md`, not per-item files), so those cells are deliberately absent → error
  if selected. Bringing them in later means adding a translator layer, not just
  data. `(copilot, commands)` is likewise absent (no Copilot commands concept).
- *Verbatim caveat:* a `copilot` rule keeps its source frontmatter, so Claude's
  `paths:` scoping is not rewritten to Copilot's `applyTo:` — body installs,
  scoping metadata doesn't translate. Accepted v1 limitation.
- *List-valued values:* retained even though every v1 entry is single-element, so a
  future platform whose one category fans out to several dirs is a data-only add.

## Risks / Trade-offs

- **`git` binary dependency** → documented runtime prerequisite; a missing/failed
  `git` surfaces as a `SourceFetchError` with the git stderr.
- **Cache concurrency** → two concurrent `install` runs could race on one repo dir;
  v1 assumes single-process use. A per-repo lockfile is a later hardening.
- **Partial platform coverage** → v1 registers Claude (all categories), Copilot
  (skills/agents/rules), and Codex (skills only). A selected `(platform, category)`
  with no entry (e.g. `codex` agents) errors rather than silently skipping;
  filling those cells needs a content translator, not just data.
- **No lock / always overwrite** → `install` cannot detect or preserve local edits
  to installed files; that is Fork B's job. Documented so it is not mistaken for a
  bug.
- **`replace` remove-then-write is not atomic** → a crash mid-write can leave a
  partially written item tree; acceptable for an imperative re-runnable command,
  revisited if it bites.

## Reference: verified per-platform config layouts

The full verified layout data, against each platform's **official** docs (dates in
Sources). The `skills / agents / commands / rules` rows are the source for the
fixed-category layout registry above — v1 installs the verbatim-portable subset
(all Claude, Copilot skills/agents/rules, Codex skills); the remaining rows
(Codex agents/rules, Copilot commands) and the `MCP / hooks` rows are **not
implemented in v1** and are kept here for the translator/`sync` work that adds
them (see the note after the tables).

### Claude Code — `code.claude.com/docs`

| Feature | Path | Shape | Notes |
|---|---|---|---|
| Skills   | `.claude/skills/<id>/SKILL.md` | dir  | `SKILL.md` required |
| Agents   | `.claude/agents/<id>.md`       | file | identity from `name` frontmatter |
| Commands | `.claude/commands/<id>.md`     | file | merged into skills; skills win on clash |
| Rules    | `.claude/rules/<id>.md`        | dir of files | optional `paths:` frontmatter = path-scoped |
| MCP      | `.mcp.json` (repo root)        | file | `mcpServers` object, JSON |
| Hooks    | `.claude/settings.json`        | file | under `hooks` key |

### GitHub Copilot — `docs.github.com`

| Feature | Path | Shape | Notes |
|---|---|---|---|
| Skills          | `.github/skills/` (also reads `.claude/skills/`, `.agents/skills/`) | dir | **fans out to 3 dirs**; `SKILL.md` required |
| Agents          | `.github/agents/<id>.agent.md`          | dir of files | **`.agent.md`** extension; `.claude/agents/` not official |
| Rules (scoped)  | `.github/instructions/*.instructions.md` | dir of files | `.instructions.md` + `applyTo` glob |
| Rules (repo)    | `.github/copilot-instructions.md`       | file | fixed name |
| MCP             | `.vscode/mcp.json` (IDE) · `~/.copilot/mcp-config.json` (CLI) · repo settings UI (cloud) | file | **not** `.mcp.json` |
| Hooks           | `.github/hooks/<id>.json`                | dir of JSON | CLI also reads `.claude/settings.json` subset |

### OpenAI Codex — `developers.openai.com/codex`

| Feature | Path | Shape | Notes |
|---|---|---|---|
| Skills | `.agents/skills/<id>/SKILL.md`        | dir | **`.agents/`**, not `.codex/` |
| Agents | `.codex/agents/<id>.toml` (+ `[agents]` in `config.toml`) | dir of TOML | **TOML**, not `.md` |
| Rules  | nested `AGENTS.md`                    | file (many) | upward-walk merge (closest wins), not glob-scoped |
| MCP    | `[mcp_servers.<id>]` in `.codex/config.toml` | file section | **TOML** |
| Hooks  | `.codex/hooks.json` or `[hooks]` in `config.toml` | file | JSON or TOML |

### What the verification tells the design

- **Multi-destination is real.** Copilot skills legitimately install to three dirs,
  so the map value is a *list* of destinations, not one path. v1 (Claude) uses
  single-element lists.
- **Per-platform extension / format.** Agents are `.md` (Claude), `.agent.md`
  (Copilot), `.toml` (Codex). Codex agents are a *format translation* (md→toml),
  not a copy — a translator, not just a path, is needed there. Out of v1.
- **MCP and Hooks do not portably by-pattern-mirror.** Only Claude uses
  `.mcp.json` / `.claude/settings.json`; Copilot uses `.vscode/mcp.json` or a
  settings UI; Codex uses TOML *sections*. Verbatim mirroring works only within
  Claude, and even there via the generic `by-pattern` lane (`json_merge` into
  `.mcp.json` / `settings.json`) — there is **no dedicated MCP or Hooks feature in
  v1**. Cross-platform MCP/Hooks need format translation and are deferred.
- **Path-scoped rules differ per platform** (Claude `paths:` frontmatter, Copilot
  `applyTo`, Codex upward-walk `AGENTS.md`) — not portable verbatim; deferred.

Sources (official, verified July 2026): Claude —
`code.claude.com/docs/en/{skills,mcp,sub-agents,commands,memory,hooks}`; Copilot —
`docs.github.com/en/copilot/**` (skills, custom-agents-configuration,
custom-instructions-support, use-mcp-in-your-ide, use-hooks); Codex —
`developers.openai.com/codex/{skills,mcp,config-advanced,hooks}` and
`learn.chatgpt.com/docs/**`.
