import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db
from app.shared.dependencies import get_current_user
from app.users.models import User
from app.documents import DocumentService
from app.highlights.schemas import HighlightCreate, HighlightRead
from app.highlights.service import HighlightService

router = APIRouter(prefix="/documents/{document_id}/highlights", tags=["highlights"])


def _get_service(db: AsyncSession = Depends(get_db)) -> HighlightService:
    return HighlightService(db, DocumentService(db))


@router.get("/", response_model=list[HighlightRead])
async def list_highlights(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: HighlightService = Depends(_get_service),
):
    return await svc.list_highlights(document_id, current_user)


@router.post("/", response_model=list[HighlightRead], status_code=status.HTTP_201_CREATED)
async def add_highlight(
    document_id: uuid.UUID,
    body: list[HighlightCreate],
    current_user: User = Depends(get_current_user),
    svc: HighlightService = Depends(_get_service),
):
    return await svc.add_highlights(document_id, body, current_user)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_highlights(
    document_id: uuid.UUID,
    highlight_ids: list[uuid.UUID],
    current_user: User = Depends(get_current_user),
    svc: HighlightService = Depends(_get_service),
):
    await svc.remove_highlights(document_id, highlight_ids, current_user)
