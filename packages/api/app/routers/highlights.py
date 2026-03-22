import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.highlight import Highlight
from app.schemas.highlight import (
    HighlightCreate, HighlightRead, HighlightUpdate, SummaryView, SummarySection,
)
from app.services.standard_format import get_ancestors, build_summary_sections

router = APIRouter(prefix="/documents/{document_id}/highlights", tags=["highlights"])


async def _get_owned_doc(document_id: uuid.UUID, user: User, db: AsyncSession) -> Document:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.standard_format is None:
        raise HTTPException(status_code=409, detail="Document is not ready yet.")
    return doc


@router.get("/", response_model=list[HighlightRead])
async def list_highlights(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_doc(document_id, current_user, db)
    result = await db.execute(
        select(Highlight).where(Highlight.document_id == document_id)
        .order_by(Highlight.created_at)
    )
    return result.scalars().all()


@router.post("/", response_model=HighlightRead, status_code=status.HTTP_201_CREATED)
async def create_highlight(
    document_id: uuid.UUID,
    body: HighlightCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_owned_doc(document_id, current_user, db)

    ancestor_ids = get_ancestors(doc.standard_format, body.node_id)

    highlight = Highlight(
        document_id=document_id,
        node_id=body.node_id,
        start_offset=body.start_offset,
        end_offset=body.end_offset,
        ancestor_node_ids=ancestor_ids,
        color=body.color,
        note=body.note,
    )
    db.add(highlight)
    await db.flush()
    await db.refresh(highlight)
    return highlight


@router.patch("/{highlight_id}", response_model=HighlightRead)
async def update_highlight(
    document_id: uuid.UUID,
    highlight_id: uuid.UUID,
    body: HighlightUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_doc(document_id, current_user, db)
    result = await db.execute(
        select(Highlight).where(
            Highlight.id == highlight_id,
            Highlight.document_id == document_id,
        )
    )
    highlight = result.scalar_one_or_none()
    if highlight is None:
        raise HTTPException(status_code=404, detail="Highlight not found.")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(highlight, field, value)
    await db.flush()
    return highlight


@router.delete("/{highlight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_highlight(
    document_id: uuid.UUID,
    highlight_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_doc(document_id, current_user, db)
    result = await db.execute(
        select(Highlight).where(
            Highlight.id == highlight_id,
            Highlight.document_id == document_id,
        )
    )
    highlight = result.scalar_one_or_none()
    if highlight is None:
        raise HTTPException(status_code=404, detail="Highlight not found.")
    await db.delete(highlight)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_highlights(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_doc(document_id, current_user, db)
    result = await db.execute(
        select(Highlight).where(Highlight.document_id == document_id)
    )
    for h in result.scalars().all():
        await db.delete(h)


@router.get("/summary", response_model=SummaryView)
async def get_summary(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Build the Summary View from all highlights on this document."""
    doc = await _get_owned_doc(document_id, current_user, db)

    result = await db.execute(
        select(Highlight).where(Highlight.document_id == document_id)
        .order_by(Highlight.created_at)
    )
    highlights = result.scalars().all()

    include_headings = (
        doc.include_headings_in_summary
        if doc.include_headings_in_summary is not None
        else current_user.include_headings_in_summary
    )

    sections = build_summary_sections(doc.standard_format, highlights, include_headings)

    return SummaryView(
        document_id=document_id,
        document_title=doc.title,
        sections=[SummarySection(**s) for s in sections],
    )
