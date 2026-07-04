"""Custom exception classes and handlers."""

from fastapi import HTTPException, status


class DocumentNotFoundError(HTTPException):
    def __init__(self, document_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id '{document_id}' not found",
        )


class DocumentProcessingError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document processing failed: {detail}",
        )


class InvalidFileTypeError(HTTPException):
    def __init__(self, file_type: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file_type}' is not supported",
        )


class FileTooLargeError(HTTPException):
    def __init__(self, max_size_mb: int):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {max_size_mb}MB",
        )


class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class TemplateNotFoundError(HTTPException):
    def __init__(self, template_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id '{template_id}' not found",
        )


class WebhookDeliveryError(Exception):
    def __init__(self, url: str, status_code: int, detail: str):
        self.url = url
        self.status_code = status_code
        super().__init__(f"Webhook delivery to {url} failed ({status_code}): {detail}")


class ExtractionError(Exception):
    def __init__(self, detail: str):
        super().__init__(f"Extraction failed: {detail}")


class OCRError(Exception):
    def __init__(self, detail: str):
        super().__init__(f"OCR failed: {detail}")
