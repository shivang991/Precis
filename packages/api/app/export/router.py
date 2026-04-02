import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.shared.database import get_db
from app.shared.dependencies import get_current_user
from app.shared.standard_format import build_summary_sections
from app.users.models import User
from app.documents.models import Document
from app.documents.schemas import StandardFormat
from app.highlights.models import Highlight
from app.highlights.schemas import SummaryView
from app.export.services import export_standard_format_to_pdf, export_summary_to_pdf

router = APIRouter(prefix="/export", tags=["export"])


async def _get_ready_doc(document_id: uuid.UUID, user: User, db: AsyncSession) -> Document:
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


@router.get("/documents/{document_id}/pdf")
async def export_document_pdf(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export the full Standard Format document as PDF."""
    doc = await _get_ready_doc(document_id, current_user, db)
    theme = doc.theme or current_user.default_theme

    standard_format = StandardFormat.model_validate(doc.standard_format)
    pdf_bytes = export_standard_format_to_pdf(standard_format, theme=theme)

    filename = f"{doc.title}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/documents/{document_id}/summary/pdf")
async def export_summary_pdf(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export the Summary View (highlighted sections + headings) as PDF."""
    doc = await _get_ready_doc(document_id, current_user, db)

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
    summary = SummaryView(
        document_id=document_id,
        document_title=doc.title,
        sections=sections,
    )

    theme = doc.theme or current_user.default_theme
    pdf_bytes = export_summary_to_pdf(summary, theme=theme)

    filename = f"{doc.title} — Summary.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
