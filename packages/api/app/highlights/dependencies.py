from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.dependencies import get_document_service
from app.documents.document_service import DocumentService
from app.shared import get_db

from .service import HighlightService


async def get_highlight_service(
    db: AsyncSession = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service),
) -> HighlightService:
    return HighlightService(db=db, document_service=document_service)
