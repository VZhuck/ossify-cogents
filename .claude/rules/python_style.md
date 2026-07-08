---
paths:
  - "/src/**"
description: Python code style conventions for ossify-cogents, beyond what ruff/mypy already enforce.
---

# Python Style Rules

These fill the gaps ruff/mypy config doesn't cover — they don't restate what the linters already catch.

## Typing

- Every function signature is fully typed (params + return), including private helpers. `mypy --strict`-clean is the bar.
- Prefer `Protocol` over `ABC` for ports (`ports_in/`, `ports_out/`) — structural typing keeps adapters decoupled from a shared base class, and fakes in tests don't need to subclass anything.
- Use `X | None`, not `Optional[X]`. Use built-in generics (`list[str]`, `dict[str, int]`), not `typing.List`/`typing.Dict`.

## Domain models

- Domain models are `pydantic.BaseModel`. Default to frozen (`model_config = ConfigDict(frozen=True)`) unless a model has a real reason to mutate — most of this domain (config, lock entries, mappings) is read, diffed, and replaced, not mutated in place.
- Validation lives on the model (`field_validator`/`model_validator`), not scattered in call sites.

## Errors

- Domain errors subclass a single `OssifyError` base (`domain/errors.py`) so callers can catch at the right granularity. Raise the most specific subclass available; never raise a bare `Exception`.
- `application/` translates low-level adapter exceptions (git errors, filesystem errors, `importlib.metadata.PackageNotFoundError`, ...) into domain errors before they escape — `cli/`/`tui/` should never need to catch a third-party exception type.

## Naming

- Classes are named as nouns (the thing or capability they represent), not verbs. Methods are named as verbs (the action taken).
- This applies to ports (`ports_in/`, `ports_out/`) in particular: a `Protocol` names the capability, not an action — e.g. `VersionPort` with a `get_version()` method, not `GetVersionPort`.
- Exception: `application/` use cases are deliberately named as verb phrases (commands) — e.g. `GetVersion`, `SyncCapabilities`, `CheckStatus` (see `.claude/rules/architecture.md`). They're single-purpose command objects, not general-purpose nouns, and the verb name signals "run this one operation."

## Functions & structure

- No mutable default arguments (`def f(items: list = [])` is a bug magnet — use `None` + assign inside).
- Prefer `pathlib.Path` over `os.path` string manipulation everywhere.
- Small, single-purpose functions over deeply nested conditionals; prefer early returns/guard clauses over nested `if`.
- Composition over inheritance for adapters — a new source/target is a new class implementing a `Protocol`, not a subclass of some shared "BaseAdapter."

## CLI (Typer)

- Command functions stay thin: parse/validate input, resolve a use case from `container.py` via its `ports_in` interface, call it, render the result with Rich. No business logic in a command body.
- Shared Rich rendering (tables, drift diffs) lives in one place under `cli/`, not duplicated per command.

## Dependency injection

- Only `container.py` constructs concrete adapters and use cases. Nothing else calls an adapter or use-case constructor directly — `application`/`cli`/`tui` receive already-wired instances from the container.
