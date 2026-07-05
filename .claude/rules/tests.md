# tests/

- `tests/unit/` — tests `core/` and `utils/` logic with the `git/` layer mocked; no real
  network or subprocess calls.
- `tests/integration/` — exercises the real Typer app (`typer.testing.CliRunner`) end to end,
  including real git operations against a local git fixture repo (a plain local repo is enough
  to exercise clone/fetch/resolve — no network access required for tests to pass).
- Every new CLI command needs at least one integration test; every new `core/` function needs
  a unit test.
