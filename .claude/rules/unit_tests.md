---
paths:
  - "/tests/**"
description: Unit testing rules for ossify-cogents. Applies to all files under ./tests.

---

# Unit Test Rules

These rules apply to everything under `./tests`. They override generic testing habits when in conflict.

## Tests Folder Structure
Important! Thre are 3 test categories:  **unit**, **integration** and **e2e**, each of which has own locattion rules (see structure below) 

    tests/                 # Dedicated tests root directory
    ├── __init__.py
    ├── conftest.py        # Global pytest fixtures (e.g., general mocks)
    │
    ├── unit/              # 1. Unit tests are fast, run in milliseconds, and utilize heavy mocking (no dependency on infrastructure). You want to run these on every local code save.
    │   ├── __init__.py
    │   ├── /application/test_example.py   # Mirrors src/application/example.py
    │
    ├── integration/       # 2. Require external infrastructure components (git, databases, spin up mock servers, or initiate HTTP requests). They are slow and prone to network 
    │   ├── __init__.py
    │   ├── conftest.py    # git connections / PAT set up, etc.
    │   └── test_git_connectivity.py  
    │
    └── e2e/               # 3. User workflows (Full stack, UI, or complete CLI) 
        ├── __init__.py
        ├── conftest.py    # Browser, Playwright, or Docker spin-up configs
        └── test_ossify_version_flow.py # example

- Inside `tests/unit/`, duplicate the file names and internal structures of your `src/` directory. For instance, if you have a component at `src/application/login.py`, its corresponding unit test should sit at `tests/unit/application/test_login.py`.
- Use `conftest.py` hierarchically
  - Define global fixtures (like basic configurations) in `tests/conftest.py` 
  - Define test git repos or container life cycles inside `tests/integration/conftest.py`. - will be used for all integration tests (but only for them) 
  - Define `tests/e2e/conftest.py` to provide config for all e2e test (and only for them)

## Framework

- Use **pytest** (not `unittest`) for all new tests: assertions via plain `assert`, fixtures via `@pytest.fixture`, parametrization via `@pytest.mark.parametrize`.

## Structure: Arrange-Act-Assert

- Every test body follows Arrange → Act → Assert, in that order, with a blank line (or `# Arrange` / `# Act` / `# Assert` comments only when the boundaries aren't obvious) separating the phases.
- Do not interleave setup, invocation, and assertions.

## Scope and independence

- A unit test exercises **one unit in isolation**. Mock/stub external dependencies (databases, network/APIs, filesystem, clocks) using `unittest.mock` or pytest fixtures — never hit a real external system from a unit test.
- Tests must not depend on execution order or on state left behind by another test. Each test creates its own data; nothing is shared via module-level mutable state.
- One behavior per test. If you need "and" to describe what a test checks, split it into multiple tests.

## Naming

- Test function names must describe the behavior under test and the expected outcome, e.g. `test_calculate_discount_for_loyal_customer`, not `test_discount` or `test_1`.
- Name the test file after the module under test: `foo.py` → `tests/test_foo.py`.

## Coverage of cases

- For every unit under test, cover: the common/happy path, boundary values (empty input, min/max, off-by-one), and invalid input (wrong type, out-of-range, `None`).
- Use `pytest.raises(...)` to assert expected exceptions instead of try/except blocks in the test body.

## Fixtures

- Extract repeated Arrange logic into `@pytest.fixture` rather than copy-pasting setup code or using shared helper calls at the top of every test.
- Keep fixtures small and named after what they provide (`sample_config`, not `data`).

## Documentation

- Add a one-line comment only when the test's intent isn't obvious from its name and body (e.g. a regression test for a specific bug, or a non-obvious edge case). Do not restate what the assertions already show.

## Coverage philosophy

- Prioritize testing critical logic and complex/branchy code paths over chasing a coverage percentage. A high-coverage suite that never exercises edge cases is worse than a smaller suite that does.
