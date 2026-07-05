# src/ossify/utils/

Small, stateless helpers shared by other layers — hashing, path/URL parsing, and similar.

- Pure functions only: no filesystem writes, no git/network calls, no dependency on `core/`
  or `cli/`. If a helper needs those, it belongs in `core/` or `git/` instead.
- Every function here should be trivially unit-testable with plain inputs/outputs.
