from app.shared.domain_error import DomainError


class GoogleAuthError(DomainError):
    status_code = 400
    detail = "Google authentication failed."
