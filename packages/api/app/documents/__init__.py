from .dependencies import get_document_service
from .document_service import DocumentService
from .router import router

__all__ = ["DocumentService", "get_document_service", "router"]
