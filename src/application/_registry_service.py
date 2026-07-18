from pathlib import Path
from typing import Literal

from application.services import RegistryValidator, SourceInferenceService
from domain.errors import ConfigNotFoundError
from domain.skill_registry import SkillSource, Source
from ports_out import RegistryRepository


class RegistryService:
    """Implements `ports_in.RegistryPort` — get_all + add, the deliberate one-port exception."""

    def __init__(
        self,
        registry_repository: RegistryRepository,
        inference_service: SourceInferenceService,
        validator: RegistryValidator,
    ) -> None:
        self._registry_repository = registry_repository
        self._inference_service = inference_service
        self._validator = validator

    def get_all(self, root: Path) -> list[SkillSource]:
        return self._registry_repository.get_all(root)

    def add(
        self,
        root: Path,
        *,
        uri: str,
        source_type: Literal["git", "local"] = "git",
        ref: str | None = None,
        id: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> SkillSource:
        entry = SkillSource(
            id=id or self._inference_service.infer_id(uri),
            name=name or self._inference_service.infer_name(uri),
            description=(
                description
                if description is not None
                else self._inference_service.infer_description(uri)
            ),
            source_type=source_type,
            source=Source(uri=uri, ref=ref),
        )

        try:
            existing = self._registry_repository.get_all(root)
        except ConfigNotFoundError:
            existing = []

        self._validator.validate([*existing, entry])
        self._registry_repository.add(root, entry)
        return entry
