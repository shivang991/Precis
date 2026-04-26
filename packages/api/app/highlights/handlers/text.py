from app.documents.models import NodeType
from app.highlights.models import TextHighlight
from app.highlights.schemas import TextHighlightCreate

from .base import ExistingHighlight, HighlightHandler, ReconcileResult


class TextHighlightHandler(HighlightHandler[TextHighlightCreate, TextHighlight]):
    node_type = NodeType.text
    model = TextHighlight

    def to_existing(self, row: TextHighlight) -> ExistingHighlight:
        return ExistingHighlight(
            id=row.id,
            node_id=row.node_id,
            payload={
                "node_id": row.node_id,
                "start_offset": row.start_offset,
                "end_offset": row.end_offset,
                "note": row.note,
            },
        )

    def reconcile(
        self,
        existing: list[ExistingHighlight],
        incoming: list[TextHighlightCreate],
    ) -> ReconcileResult:
        # Combine existing + incoming, group by (node_id, note), merge
        # overlapping/adjacent ranges, return the minimal set.
        combined = []
        for e in existing:
            combined.append(
                (
                    e.payload["node_id"],
                    e.payload["start_offset"],
                    e.payload["end_offset"],
                    e.payload["note"],
                )
            )
        for h in incoming:
            combined.append((h.node_id, h.start_offset, h.end_offset, h.note))

        groups: dict = {}
        for node_id, start, end, note in combined:
            groups.setdefault((node_id, note), []).append((start, end))

        merged: list[dict] = []
        for (node_id, note), segments in groups.items():
            segments.sort(key=lambda s: s[0])
            cur_start, cur_end = segments[0]
            for start, end in segments[1:]:
                if start <= cur_end:
                    cur_end = max(cur_end, end)
                else:
                    merged.append(
                        {
                            "node_id": node_id,
                            "start_offset": cur_start,
                            "end_offset": cur_end,
                            "note": note,
                        }
                    )
                    cur_start, cur_end = start, end
            merged.append(
                {
                    "node_id": node_id,
                    "start_offset": cur_start,
                    "end_offset": cur_end,
                    "note": note,
                }
            )

        return ReconcileResult(
            to_delete=[e.id for e in existing],
            to_create=merged,
        )
