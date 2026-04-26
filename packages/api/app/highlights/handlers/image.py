from app.documents.models import NodeType
from app.highlights.models import ImageHighlight
from app.highlights.schemas import ImageHighlightCreate

from .base import ExistingHighlight, HighlightHandler, ReconcileResult


class ImageHighlightHandler(HighlightHandler[ImageHighlightCreate, ImageHighlight]):
    node_type = NodeType.image
    model = ImageHighlight

    def to_existing(self, row: ImageHighlight) -> ExistingHighlight:
        return ExistingHighlight(
            id=row.id,
            node_id=row.node_id,
            payload={"node_id": row.node_id},
        )

    def reconcile(
        self,
        existing: list[ExistingHighlight],
        incoming: list[ImageHighlightCreate],
    ) -> ReconcileResult:
        existing_node_ids = {e.node_id for e in existing}
        to_create: list[dict] = []
        seen: set = set()
        for h in incoming:
            if h.node_id in existing_node_ids or h.node_id in seen:
                continue
            seen.add(h.node_id)
            to_create.append({"node_id": h.node_id})
        return ReconcileResult(to_delete=[], to_create=to_create)
