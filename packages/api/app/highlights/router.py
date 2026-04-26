import uuid

from fastapi import APIRouter, Body, Depends, status

from app.users import User, get_current_user

from .dependencies import get_highlight_service
from .schemas import HighlightCreate, HighlightRead, TextHighlightRead
from .service import HighlightService

router = APIRouter(prefix="/documents/{document_id}/highlights", tags=["highlights"])


@router.get(
    "/",
    response_model=list[HighlightRead],
    operation_id="list_highlights",
)
async def list_highlights(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: HighlightService = Depends(get_highlight_service),
):
    rows = await svc.list_highlights(document_id, current_user)
    return [TextHighlightRead.model_validate(r) for r in rows]


@router.post(
    "/",
    response_model=list[HighlightRead],
    status_code=status.HTTP_201_CREATED,
    operation_id="add_highlights",
)
async def add_highlights(
    document_id: uuid.UUID,
    body: list[HighlightCreate] = Body(...),
    current_user: User = Depends(get_current_user),
    svc: HighlightService = Depends(get_highlight_service),
):
    rows = await svc.add_highlights(document_id, body, current_user)
    return [TextHighlightRead.model_validate(r) for r in rows]


@router.delete(
    "/", status_code=status.HTTP_204_NO_CONTENT, operation_id="remove_highlights"
)
async def remove_highlights(
    document_id: uuid.UUID,
    highlight_ids: list[uuid.UUID],
    current_user: User = Depends(get_current_user),
    svc: HighlightService = Depends(get_highlight_service),
):
    await svc.remove_highlights(document_id, highlight_ids, current_user)
