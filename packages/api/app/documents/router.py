import uuid
from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db
from app.shared.dependencies import get_current_user
from app.users.models import User
from app.documents.models import DocumentSource
from app.documents.schemas import (
    DocumentRead,
    DocumentReadWithContent,
    DocumentUpdateSettings,
    DocumentUpdateContent,
)
from app.documents.service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_service(db: AsyncSession = Depends(get_db)) -> DocumentService:
    return DocumentService(db)


@router.get("/", response_model=list[DocumentRead])
async def list_documents(
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(_get_service),
):
    return await svc.list_documents(current_user)


@router.post(
    "/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    file: UploadFile = File(...),
    source: DocumentSource = Form(DocumentSource.DIGITAL),
    title: str = Form(""),
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(_get_service),
):
    return await svc.upload_document(
        file.filename,
        await file.read(),
        file.content_type,
        source,
        title,
        current_user,
    )


@router.post("/{document_id}/process")
async def process_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(_get_service),
):
    return StreamingResponse(
        svc.standard_format_generator(document_id, current_user),
        media_type="text/event-stream",
    )


@router.get("/{document_id}", response_model=DocumentReadWithContent)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(_get_service),
):
    return await svc.get_document(document_id, current_user)


@router.patch("/{document_id}/settings", response_model=DocumentRead)
async def update_document_settings(
    document_id: uuid.UUID,
    body: DocumentUpdateSettings,
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(_get_service),
):
    return await svc.update_document_settings(document_id, body, current_user)


@router.patch("/{document_id}/content", response_model=DocumentRead)
async def update_document_content(
    document_id: uuid.UUID,
    body: DocumentUpdateContent,
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(_get_service),
):
    return await svc.update_document_content(document_id, body, current_user)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(_get_service),
):
    await svc.delete_document(document_id, current_user)
