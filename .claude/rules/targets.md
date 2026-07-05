# src/ossify/targets/

One adapter per supported AI tool (Claude Code, GitHub Copilot, ...) — the extension point for
adding support for a new tool later (e.g. Codex).

- Each adapter maps ossify's internal artifact vocabulary (skill/agent/rule/command/...) onto
  that tool's own file layout and naming conventions, for both project-level and global
  (user-home) installs.
- Adding a new tool means adding one new adapter file here and registering it — nothing in
  `core/` or `cli/` should need to change.
- Adapters only compute destination paths; they don't perform file I/O themselves (that's
  `core/installer.py`'s job).
