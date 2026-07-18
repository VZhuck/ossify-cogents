"""Infers a registry entry's id/name/description from its uri — pure string parsing, no I/O."""

from pathlib import PurePosixPath


class SourceInferenceService:
    """Derives id/name/description from a uri when the user didn't supply them explicitly."""

    def infer_id(self, uri: str) -> str:
        return self._slug(uri)

    def infer_name(self, uri: str) -> str:
        slug = self._slug(uri)
        return slug.replace("-", " ").replace("_", " ").title()

    def infer_description(self, uri: str) -> str:
        return ""

    @staticmethod
    def _slug(uri: str) -> str:
        cleaned = uri.rstrip("/")
        if cleaned.endswith(".git"):
            cleaned = cleaned[: -len(".git")]
        return PurePosixPath(cleaned).name or cleaned
