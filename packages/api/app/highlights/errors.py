from app.shared.domain_error import DomainError


class DocumentNotReadyError(DomainError):
    status_code = 409
    detail = "Document is not ready yet."


class HighlightNotFoundError(DomainError):
    status_code = 404
    detail = "Highlight not found."


class HighlightTypeMismatchError(DomainError):
    status_code = 400
    detail = "Highlight type does not match target node content type."


class NodeNotFoundError(DomainError):
    status_code = 400
    detail = "Target node not found in document."
