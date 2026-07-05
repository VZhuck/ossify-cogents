# src/ossify/core/

The engine: config/lock-file models and the resolve/plan/install logic. This is the layer that
matters most to keep clean, since it's what `ossify update`'s correctness depends on.

- No direct filesystem or subprocess calls here — route git operations through `git/` and
  path/hash helpers through `utils/`. This is what keeps resolve/plan/install logic testable
  by mocking one narrow seam instead of `subprocess` everywhere.
- All config/lock-file shapes are `pydantic` models (see `models.py`) — never pass raw dicts
  across module boundaries.
- Functions here should take and return plain data; side effects (writing files, calling git)
  happen at the edges (`config.py`/`lockfile.py` for file I/O), not buried inside planning logic.
- Every dependency is copied, never symlinked — the lock file's commit + integrity hash is what
  lets `ossify status` detect local edits before an update would silently overwrite them.
