import uuid
from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form,
    BackgroundTasks, status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentStatus, DocumentSource
from app.schemas.document import (
    DocumentRead, DocumentReadWithContent,
    DocumentUpdateSettings, DocumentUpdateContent,
)
from app.services import storage
from app.services.standard_format import build_standard_format
from app.services.pdf_processor import process_digital_pdf
from app.services.ocr_processor import process_scanned_pdf
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/documents", tags=["documents"])


# ── Background processing ─────────────────────────────────────────────────────

async def _process_document(document_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        return

    try:
        doc.status = DocumentStatus.PROCESSING
        await db.flush()

        pdf_bytes = await storage.download_file(doc.storage_key)

        if doc.source == DocumentSource.DIGITAL:
            nodes, page_count = process_digital_pdf(pdf_bytes)
        else:
            nodes, page_count = process_scanned_pdf(pdf_bytes)

        doc.standard_format = build_standard_format(
            title=doc.title,
            nodes=nodes,
            source=doc.source.value,
            page_count=page_count,
        )
        doc.page_count = page_count
        doc.status = DocumentStatus.READY

    except Exception as e:
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)

    await db.commit()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[DocumentRead])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source: DocumentSource = Form(DocumentSource.DIGITAL),
    title: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ("application/pdf",):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(pdf_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail="File exceeds size limit.")

    storage_key = await storage.upload_file(pdf_bytes)

    doc = Document(
        owner_id=current_user.id,
        title=title or file.filename or "Untitled",
        original_filename=file.filename or "upload.pdf",
        storage_key=storage_key,
        source=source,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    background_tasks.add_task(_process_document, doc.id, db)

    return doc


@router.get("/{document_id}", response_model=DocumentReadWithContent)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_owned_doc(document_id, current_user, db)
    return doc


@router.patch("/{document_id}/settings", response_model=DocumentRead)
async def update_document_settings(
    document_id: uuid.UUID,
    body: DocumentUpdateSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_owned_doc(document_id, current_user, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(doc, field, value)
    await db.flush()
    return doc


@router.patch("/{document_id}/content", response_model=DocumentRead)
async def update_document_content(
    document_id: uuid.UUID,
    body: DocumentUpdateContent,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """WYSIWYG editor patch — replaces nodes in the Standard Format."""
    doc = await _get_owned_doc(document_id, current_user, db)
    if doc.standard_format is None:
        raise HTTPException(status_code=409, detail="Document not yet processed.")

    updated_map = {n.id: n.model_dump() for n in body.nodes}

    def _patch_nodes(nodes: list[dict]) -> list[dict]:
        result = []
        for node in nodes:
            if node["id"] in updated_map:
                patched = {**node, **updated_map[node["id"]]}
                patched["children"] = _patch_nodes(node.get("children", []))
                result.append(patched)
            else:
                node["children"] = _patch_nodes(node.get("children", []))
                result.append(node)
        return result

    doc.standard_format["nodes"] = _patch_nodes(doc.standard_format["nodes"])
    await db.flush()
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_owned_doc(document_id, current_user, db)
    await storage.delete_file(doc.storage_key)
    await db.delete(doc)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_owned_doc(
    document_id: uuid.UUID, user: User, db: AsyncSession
) -> Document:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc
