from app.shared.exceptions import DomainError


class DocumentNotFoundError(DomainError):
    status_code = 404
    detail = "Document not found."


class DocumentNotReadyError(DomainError):
    status_code = 409
    detail = "Document is not ready yet."


class HighlightNotFoundError(DomainError):
    status_code = 404
    detail = "Highlight not found."
