"""
Custom application exception hierarchy.

Defines domain-specific exceptions that decouple the service layer
from FastAPI's HTTPException. Services raise these exceptions,
and a global handler in main.py converts them to JSON responses.

This allows services to be tested independently of the web framework
and potentially reused in CLI tools, Celery workers, etc.
"""


class AppError(Exception):
    """Base exception for all application-level errors.

    Attributes:
        status_code: HTTP status code to return to the client.
        detail: Human-readable error message.
    """

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    detail = "Resource not found"


class ConflictError(AppError):
    """Raised when an action conflicts with existing state.

    Examples: duplicate email registration, active job already exists.
    """

    status_code = 409
    detail = "Resource conflict"


class AuthenticationError(AppError):
    """Raised when credentials are invalid or session has expired."""

    status_code = 401
    detail = "Authentication failed"


class ForbiddenError(AppError):
    """Raised when the user lacks permission for the requested action."""

    status_code = 403
    detail = "Permission denied"


class ValidationError(AppError):
    """Raised when input data fails domain-level validation.

    Note: This is for business-rule validation, not Pydantic schema
    validation (which is handled automatically by FastAPI).
    """

    status_code = 400
    detail = "Validation error"


class FileTooLargeError(AppError):
    """Raised when an uploaded file exceeds the size limit."""

    status_code = 413
    detail = "File too large"
