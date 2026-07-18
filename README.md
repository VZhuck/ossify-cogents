# ossify-cogents

   
=========================================================

     [⚙️ AI Capabilities] ---> [📂 Version Control] ---> [📦 Local Workspace]

Small cli/tui tool to manage your ai configuration (project &amp; system level). Kind of package manager for your ai skills, agents, plugins &amp; more

## Getting started

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

This installs the project and its CLI into a local virtual environment.

## Running the CLI

```bash
uv run ossify-cogents --version
```

If the virtual environment is already activated (e.g. via `source .venv/bin/activate`), you can drop the `uv run` prefix:

```bash
ossify-cogents --version
```

## Skill registry

`ossify-cogents.json` tracks third-party skill sources (git repos or local folders) your project draws from:

```json
{
  "ossify-skills-registry": [
    {
      "id": "agent-pack",
      "name": "Agent Pack",
      "description": "",
      "source_type": "git",
      "source": { "uri": "https://github.com/acme-org/agent-pack.git", "ref": "main" }
    }
  ]
}
```

```bash
# add a source — id/name/description are inferred from the uri unless overridden
ossify-cogents registry add https://github.com/acme-org/agent-pack.git
ossify-cogents registry add ./experiments/my-skills --source-type local

# list registered sources
ossify-cogents registry get

# validate ossify-cogents.json
ossify-cogents config verify
```

By default the workspace root (where `ossify-cogents.json` lives) is resolved by walking up from the current directory for a `.git` folder or an existing `ossify-cogents.json`, falling back to the current directory. Override it explicitly with `--workspace`/`-ws`:

```bash
ossify-cogents --workspace ../some-repo registry get
```
