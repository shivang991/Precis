import json
import uuid
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.shared import storage
from app.shared.standard_format import build_standard_format
from app.shared.config import get_settings
from app.users.models import User
from app.documents.models import Document, DocumentStatus, DocumentSource
from app.documents.schemas import DocumentUpdateSettings, DocumentUpdateContent
from app.documents.services import extract_pdf
from app.documents.errors import (
    DocumentNotFoundError,
    DocumentNotProcessedError,
    InvalidFileTypeError,
    FileTooLargeError,
)

settings = get_settings()


class DocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_owned_doc(self, document_id: uuid.UUID, user: User) -> Document:
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.owner_id == user.id,
            )
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise DocumentNotFoundError()
        return doc

    def _sse(self, event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    async def standard_format_generator(
        self, document_id: uuid.UUID, user: User
    ) -> AsyncIterator[str]:
        doc = await self._get_owned_doc(document_id, user)

        try:
            doc.status = DocumentStatus.PROCESSING
            await self.db.flush()
            yield "started"

            pdf_bytes = await storage.download_file(doc.storage_key)
            extraction = extract_pdf(pdf_bytes, doc.source)

            doc.standard_format = build_standard_format(
                title=doc.title,
                nodes=extraction.nodes,
                source=doc.source.value,
                page_count=extraction.page_count,
            )
            doc.page_count = extraction.page_count
            doc.status = DocumentStatus.READY
            await self.db.commit()
            yield "ready"

        except Exception as e:
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            await self.db.commit()
            yield "error"

    async def list_documents(self, user: User) -> list[Document]:
        result = await self.db.execute(
            select(Document)
            .where(Document.owner_id == user.id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def upload_document(
        self,
        filename: str,
        file_bytes: bytes,
        file_content_type: str,
        source: DocumentSource,
        title: str,
        user: User,
    ) -> Document:
        if file_content_type not in ("application/pdf",):
            raise InvalidFileTypeError()

        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise FileTooLargeError()

        storage_key = await storage.upload_file(file_bytes)

        doc = Document(
            owner_id=user.id,
            title=title or filename or "Untitled",
            original_filename=filename or "upload.pdf",
            storage_key=storage_key,
            source=source,
            status=DocumentStatus.PENDING,
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def get_document(self, document_id: uuid.UUID, user: User) -> Document:
        return await self._get_owned_doc(document_id, user)

    async def update_document_settings(
        self,
        document_id: uuid.UUID,
        body: DocumentUpdateSettings,
        user: User,
    ) -> Document:
        doc = await self._get_owned_doc(document_id, user)
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(doc, field, value)
        await self.db.flush()
        return doc

    async def update_document_content(
        self,
        document_id: uuid.UUID,
        body: DocumentUpdateContent,
        user: User,
    ) -> Document:
        doc = await self._get_owned_doc(document_id, user)
        if doc.standard_format is None:
            raise DocumentNotProcessedError()

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
        await self.db.flush()
        return doc

    async def delete_document(self, document_id: uuid.UUID, user: User) -> None:
        doc = await self._get_owned_doc(document_id, user)
        await storage.delete_file(doc.storage_key)
        await self.db.delete(doc)
