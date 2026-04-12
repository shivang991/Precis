from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared import StorageService, get_db

from .document_service import DocumentService
from .parser_service import ParserService


async def get_document_service(
    db: AsyncSession = Depends(get_db),
) -> DocumentService:
    return DocumentService(db=db, parser=ParserService(), storage=StorageService())
