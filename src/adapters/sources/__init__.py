"""Source adapters: concrete `ports_out.SourcePort` implementations (git, local)."""

from adapters.sources.git_source_adapter import GitSourceAdapter
from adapters.sources.local_source_adapter import LocalSourceAdapter

__all__ = ["GitSourceAdapter", "LocalSourceAdapter"]
