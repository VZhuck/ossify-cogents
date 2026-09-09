"""Persistence adapters: local state stores that are neither a source nor a target."""

from adapters.persistence.git_exclude_adapter import GitExcludeAdapter

__all__ = ["GitExcludeAdapter"]
