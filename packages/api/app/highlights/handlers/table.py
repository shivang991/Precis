from app.documents.models import NodeType
from app.highlights.models import TableHighlight
from app.highlights.schemas import TableHighlightCreate

from .base import ExistingHighlight, HighlightHandler, ReconcileResult


class TableHighlightHandler(HighlightHandler[TableHighlightCreate, TableHighlight]):
    node_type = NodeType.table
    model = TableHighlight

    def to_existing(self, row: TableHighlight) -> ExistingHighlight:
        return ExistingHighlight(
            id=row.id,
            node_id=row.node_id,
            payload={
                "node_id": row.node_id,
                "rows": list(row.rows or []),
                "columns": list(row.columns or []),
                "note": row.note,
            },
        )

    def reconcile(
        self,
        existing: list[ExistingHighlight],
        incoming: list[TableHighlightCreate],
    ) -> ReconcileResult:
        # Group existing + incoming by (node_id, note); union rows[]/columns[]
        # so each (node_id, note) collapses to a single persisted row.
        groups: dict[tuple, tuple[set[int], set[int]]] = {}
        for e in existing:
            key = (e.payload["node_id"], e.payload["note"])
            rows_set, cols_set = groups.setdefault(key, (set(), set()))
            rows_set.update(e.payload["rows"])
            cols_set.update(e.payload["columns"])
        for h in incoming:
            key = (h.node_id, h.note)
            rows_set, cols_set = groups.setdefault(key, (set(), set()))
            rows_set.update(h.rows)
            cols_set.update(h.columns)

        merged: list[dict] = []
        for (node_id, note), (rows_set, cols_set) in groups.items():
            if not rows_set and not cols_set:
                continue
            merged.append(
                {
                    "node_id": node_id,
                    "rows": sorted(rows_set),
                    "columns": sorted(cols_set),
                    "note": note,
                }
            )

        return ReconcileResult(
            to_delete=[e.id for e in existing],
            to_create=merged,
        )
