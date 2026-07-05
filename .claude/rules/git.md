# src/ossify/git/

The only layer allowed to shell out to the `git` binary or touch the shared cache directory.

- Every git operation (`ls-remote`, clone/fetch, exporting a subpath at a commit) is wrapped
  in a function here — nothing outside this folder calls `subprocess` for git directly.
- Keeping this boundary narrow is what lets `core/` be unit-tested by mocking this module
  instead of mocking `subprocess` calls scattered across the codebase.
- Cache layout: one bare clone per source repo under `~/.ossify/cache/<host>/<owner>/<repo>`,
  shared across projects — never clone the same repo twice on disk.
- Fail loudly (raise) on any non-zero git exit code; don't swallow git errors here.
