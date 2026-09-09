## Context

Install is a one-way copy: fetch, discover, select, write bytes. That is correct for a `git` source, whose cache ossify owns and hard-resets on every fetch. It is a poor fit for a `local` source the user is actively authoring, where the consuming repo and the source repo are both live working copies on the same machine.

Symlinking collapses the two into one file. The plumbing already exists: `SourcePort.materialize` returns a real filesystem path for both source types, so the only thing that changes is the final write.

```
 entry (mode=link, source-type=local)
   |
   +-> SourcePort.materialize            -> tree_root (real path)
   +-> DiscoveryExecution                -> id -> (location, shape)
   +-> TargetLayout                      -> destination path + expected shape
   |
   +-> write
         destination exists, not a symlink?  -> same bytes: ADOPT (replace with link)
                                             -> different:  SEVERED, refuse, report
         source inside workspace root?       -> relative link (portable, committable)
         source outside workspace root?      -> absolute link (+ .git/info/exclude)
```

## Goals / Non-Goals

**Goals**
- Bidirectional authoring against a `local` source, with no sync step in either direction.
- No silent degradation: anything that cannot be linked is reported, never quietly copied.
- Correct multi-platform fan-out — one canonical file, several names, no divergence.

**Non-Goals**
- A lock file. Deliberately deferred; see "Why no lock file" below.
- Linking a `git` source.
- Pruning stale *copies*. That requires an inventory the tool does not have.
- Drift detection or a `status` command.

## Decisions

### Configuration only; no CLI flag

An earlier draft had `--link` / `--no-link` overriding the config. Dropped: a flag applies uniformly to every registry entry, and linking is inherently per-entry — a config routinely mixes a `git` source with one or more `local` ones. Per-entry is also how every other install decision is already expressed.

The escape-hatch argument for a flag ("produce a self-contained repo before committing") is weaker than it appears: **a `local` source is already machine-specific regardless of mode.** A config carrying `/Users/someone/toolkit` is unusable by a teammate whether that entry copies or links. Link mode does not reduce shareability; `source.uri` already did.

That leaves two cases, both served correctly without a flag:

| Source position | Link form | Shareable? |
|---|---|---|
| inside workspace root (`tools/toolkit/`) | relative | yes — teammates and CI run plain `install` and it works |
| outside workspace root | absolute | no — same as the copy-mode local source it replaces |

### `mode: link` on a `git` source is a hard error

Not a warning, not a silent downgrade. `GitSourceAdapter.materialize` runs `git fetch --all` and `git checkout -B <ref> origin/<ref>` on every install, hard-resetting the cache. An edit made through a link into that cache is destroyed on the next install with no warning. Since the declaration is per-entry and deliberate, it can only be a mistake, so it is rejected at parse time in `SkillSource._apply_source_type_rules` — beside the existing "a local source must not set `ref`" rule.

This also means `ossify-cogents config verify` catches it offline for free: verify already validates the registry section against the model, and the model validator is where the rule lives. No new verification code.

### Link geometry is derived from position, not configured

```
resolved source path is relative to workspace root  -> relative symlink
   .claude/skills/pdf -> ../../tools/toolkit/skills/pdf
   committable; works on every clone; NOT added to .git/info/exclude

otherwise                                           -> absolute symlink
   .claude/skills/pdf -> /Users/…/toolkit/skills/pdf
   machine-specific; added to .git/info/exclude
```

One check drives both the link form and the exclude decision, so they cannot disagree. **Alternative rejected —** a `link-style: relative|absolute` config knob: it asks the user to reason about path geometry to arrive at the answer the tool can compute exactly.

### `.git/info/exclude`, not `.gitignore`

An absolute link is one developer's private arrangement, so the ignore belongs in the per-developer, never-committed file. Writing `.gitignore` would push a personal workflow into a shared file and — worse — would cause a teammate who *copies* the same entry to have their legitimately-committed capabilities ignored.

The block is delimited by markers and **rewritten wholesale** on every install from current state, so it is idempotent and self-correcting: an entry that stops linking loses its exclusion automatically, with no lock file and no stale accumulation.

Edge cases the adapter owns: `.git` present as a *file* (worktrees and submodules — resolve the `gitdir:` pointer), and `.git` absent (not a git repo — skip and warn rather than fail; linking still works, git hygiene is simply not applicable).

### Where the exclude write lives

`.git/info/exclude` is under the workspace root, so `TargetPort.override` could technically write it. Rejected: that would put marker-block parsing and git-layout knowledge (`.git`-as-file, worktrees) into the install use case. Instead a new `ports_out.VcsExcludePort` with `set_excluded(root, paths)`, implemented by a `GitExcludeAdapter` in a new `adapters/persistence/` package and registered in `container.py` — the same shape every other backend follows.

`TargetPort.link(path, source)` does relax the port's "all paths are relative to the root" invariant, since `source` is a path outside the root. This is documented on the port. Consistent with the existing precedent that action *support* is a per-adapter capability, an adapter that cannot link raises `UnsupportedTargetActionError`.

### `by-pattern`: only `replace` can be linked

The three actions differ in **who owns the destination**, which is exactly what decides linkability:

```
replace     "the source owns this file"          -> link. same semantic.
init        "seed it, the repo owns it after"    -> copy. a link is the opposite.
json_merge  "the repo owns it, source contributes" -> copy. structurally impossible:
                                                     merging writes through into the source.
```

`init` and `json_merge` copy and emit a warning line, so the downgrade is visible in the report rather than inferred.


### Per-item shape is absorbed from the discovery layer

Link mode has to choose between a directory symlink and a file symlink, so it needs to know an item's shape. Discovery records only `id -> location` today; shape is asserted by `TargetLayout`'s destination templates.

That assertion is already wrong. `_enumerate_folder` takes the child's *name*, extension included, so a `folder` rule over a directory of `.md` files yields ids that already carry `.md`, and the layout re-appends its own:

```
category   source is   discovered location            ->  destination written
skills     DIR         skills/word-to-md              ->  .claude/skills/word-to-md      OK
commands   FILE        commands/md-to-word.md         ->  .claude/commands/md-to-word.md.md
```

Under copy mode that is a cosmetically wrong filename. Under link mode those same names become the link destinations, the entries written into `.git/info/exclude`, and the paths stale-link pruning matches — so the fix cannot be deferred past this change.

So discovery gains `DiscoveredItem(location, shape)`, `folder`-rule ids become the child *stem* when the child is a file, and the layout's `shape` is reinterpreted as an *expectation* checked against discovery's *observation* (`ShapeMismatchError` on disagreement) rather than an assertion about the source.

### Adopt on match, sever on divergence

POSIX `rename()` replaces the symlink itself, not its target. An editor that saves atomically (write temp, rename over) therefore replaces a **file** symlink with a regular file. The edit lands in the consuming repo; the toolkit never sees it.

```
.claude/agents/foo.md -> toolkit/agents/foo.md      linked
editor atomic-saves foo.md
.claude/agents/foo.md == regular file               link severed, silently
next install overwrites it                          edit lost
```

Directory links are immune: the rename happens *inside* the linked directory and reaches the real file. So the exposure is exactly the file-shaped categories — `agents`, `commands`, `rules`, and `replace` by-pattern items.

Detection needs no lock file: the config says the entry links, and `is_symlink()` says the destination does not.

But "not a symlink" is two different situations, and only one of them is dangerous:

```
destination is a regular file, bytes == source   -> a copy-mode install. ADOPT.
destination is a regular file, bytes != source   -> an edit that never reached the
                                                    source. SEVERED, refuse.
```

Refusing both would make `mode: link` unadoptable: every destination that copy mode has ever written is a regular file, and every `by-pattern` `replace` target exists by construction, so the first link run would fail on all of them with no way forward except manual deletion. Comparing content separates the migration case from the data-loss case exactly, with no new config and no lock file — a byte-identical destination carries nothing a link would lose.

On divergence, install **refuses to overwrite** and reports the path, so the diverged content survives for the user to inspect and merge.

**Alternative rejected —** an `adopt: true` opt-in: it asks the user to authorize an operation that provably loses nothing, and leaves the default unusable.

**Alternative rejected —** link file-shaped items but skip detection: the failure is silent and destructive, which is the one outcome bidirectional authoring cannot absorb. **Alternative rejected —** copy file-shaped items and link only directories: it makes `mode: link` mean different things per category and silently drops the loop for single-file capabilities.

### Stale-link pruning without a lock file

A symlink carries its own provenance in its target path:

```
.claude/skills/docx -> /Users/…/toolkit/skills/docx
                       ------- a configured local source root -------
                       ossify demonstrably created this
```

So a destination that is a symlink resolving into a configured local source root, but is no longer selected by any entry, can be pruned with certainty and no recorded state. Unlinking is non-destructive: the source file is untouched.

This applies to links only. A copied file is indistinguishable from a hand-written one, so copies stay unpruned exactly as today.

### Windows: junction for directories, hard failure for files

- **Directory:** `os.symlink(..., target_is_directory=True)`; on `OSError` fall back to a junction (`mklink /J`), which needs no elevation. A real workaround.
- **File:** no junction equivalent. Fail with `LinkNotSupportedError` naming the destination and pointing at Developer Mode.

**A hard link is not a substitute.** It would appear to work, but it is indistinguishable from a regular file, so severance after an atomic save becomes undetectable — strictly worse than failing.

Falling back to a copy is rejected for the same reason throughout this change: under bidirectional authoring, a silent copy means edits stop flowing back and are overwritten on the next install.

### `InstallReport` carries structure, not formatted strings

`installed: list[str]` built from f-strings cannot express mode without the CLI parsing its own output. It becomes `list[InstalledItem]` with platform, category, id, destination, and mode, so `cli/_install.py` renders `->` for copies and `=>` for links from data, and any future `status` reuses the model rather than re-deriving it.

## Why no lock file

Every problem this change raises is solvable without one:

| Problem | Needs a lock? | Why not |
|---|---|---|
| severed-link detection | no | config says link, `is_symlink()` disagrees |
| stale-link pruning | no | the symlink target proves provenance |
| stale exclude entries | no | marker block is rewritten wholesale each run |
| link drift | no | a link cannot drift; it *is* the source |

A lock file remains necessary for reproducible `git` installs, drift detection over copies, uninstall, and pruning copies — but none of those is in this change's path.

Building link mode *first* is also the better order for the eventual lock file. A hash means "this is what we installed; deviation is drift", but a linked file's content changes on every toolkit edit **by design**, so hashing one produces permanent false drift. The lock must therefore record linked entries as `{ destination, link-target }` with no hash, and define drift for them as "still a symlink to the right place". Shipping link mode first forces the lock schema to confront that from the start rather than retrofitting a special case into a hash-centric design.

## Risks / Trade-offs

- **A linked toolkit is shared mutable state.** If two repos link the same toolkit, an edit through one changes the other. That is the point, and it is the `npm link` footgun. Mitigation is visibility, not prevention: the report always prints each link's target.
- **Absolute links are machine-specific.** Bounded by `.git/info/exclude` and by the fact that the `local` source they come from was already machine-specific.
- **A linked directory exposes the source directory wholesale**, including files a copy install would also have copied. Parity with copy mode; no new exposure.
- **A missing local source now fails the install** instead of silently installing nothing. Intended, but it turns a previously-quiet config into a loud error for anyone whose local path has moved.
