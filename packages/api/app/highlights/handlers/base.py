import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.documents.models import NodeType
from app.shared.database import Base


@dataclass
class ExistingHighlight:
    id: uuid.UUID
    node_id: uuid.UUID
    payload: dict[str, Any]


@dataclass
class ReconcileResult:
    to_delete: list[uuid.UUID] = field(default_factory=list)
    to_create: list[dict[str, Any]] = field(default_factory=list)


class HighlightHandler[CreateT, ModelT: Base](ABC):
    node_type: NodeType
    model: type[ModelT]

    @abstractmethod
    def to_existing(self, row: ModelT) -> ExistingHighlight: ...

    @abstractmethod
    def reconcile(
        self,
        existing: list[ExistingHighlight],
        incoming: list[CreateT],
    ) -> ReconcileResult: ...
