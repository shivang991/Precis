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
from app.users import get_current_user
from app.users import User
from .models import DocumentSource
from .schemas import (
    DocumentRead,
    DocumentReadWithContent,
    DocumentUpdateSettings,
    DocumentUpdateContent,
)
from .document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=list[DocumentRead], operation_id="list_documents")
async def list_documents(
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(DocumentService),
):
    return await svc.list_documents(current_user)


@router.post(
    "/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED, operation_id="upload_document",
)
async def upload_document(
    file: UploadFile = File(...),
    source: DocumentSource = Form(DocumentSource.DIGITAL),
    title: str = Form(""),
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(DocumentService),
):
    return await svc.upload_document(
        file.filename,
        await file.read(),
        file.content_type,
        source,
        title,
        current_user,
    )


@router.post("/{document_id}/process", operation_id="process_document")
async def process_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(DocumentService),
):
    return StreamingResponse(
        svc.document_content_tree_generator(document_id, current_user),
        media_type="text/event-stream",
    )


@router.get("/{document_id}", response_model=DocumentReadWithContent, operation_id="get_document")
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(DocumentService),
):
    return await svc.get_document(document_id, current_user)


@router.patch("/{document_id}/settings", response_model=DocumentRead, operation_id="update_document_settings")
async def update_document_settings(
    document_id: uuid.UUID,
    body: DocumentUpdateSettings,
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(DocumentService),
):
    return await svc.update_document_settings(document_id, body, current_user)


@router.patch("/{document_id}/content", response_model=DocumentRead, operation_id="update_document_content")
async def update_document_content(
    document_id: uuid.UUID,
    body: DocumentUpdateContent,
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(DocumentService),
):
    return await svc.update_document_content(document_id, body, current_user)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="delete_document")
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(DocumentService),
):
    await svc.delete_document(document_id, current_user)
