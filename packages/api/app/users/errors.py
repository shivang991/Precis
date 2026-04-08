from app.shared.exceptions import DomainError


class GoogleAuthError(DomainError):
    status_code = 400
    detail = "Google authentication failed."
