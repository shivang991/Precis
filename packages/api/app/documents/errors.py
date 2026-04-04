from app.shared.exceptions import DomainError


class DocumentNotFoundError(DomainError):
    status_code = 404
    detail = "Document not found."


class DocumentNotProcessedError(DomainError):
    status_code = 409
    detail = "Document not yet processed."


class InvalidFileTypeError(DomainError):
    status_code = 400
    detail = "Only PDF files are accepted."


class FileTooLargeError(DomainError):
    status_code = 413
    detail = "File exceeds size limit."
