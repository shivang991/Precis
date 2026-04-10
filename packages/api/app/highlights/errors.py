from app.shared.domain_error import DomainError


class DocumentNotReadyError(DomainError):
    status_code = 409
    detail = "Document is not ready yet."


class HighlightNotFoundError(DomainError):
    status_code = 404
    detail = "Highlight not found."
