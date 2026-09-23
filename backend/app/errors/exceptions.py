from typing import Any, Dict, Optional
from fastapi import Request
from fastapi.responses import JSONResponse

class AppError(Exception):
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}

class ValidationError(AppError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=400, code="VALIDATION_ERROR", details=details)

class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized access", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=401, code="UNAUTHORIZED", details=details)

class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden resource access", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=403, code="FORBIDDEN", details=details)

class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=404, code="NOT_FOUND", details=details)

class ConflictError(AppError):
    def __init__(self, message: str = "Resource state conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=409, code="CONFLICT", details=details)

class UnprocessableError(AppError):
    def __init__(self, message: str = "Unprocessable entity state", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=422, code="UNPROCESSABLE_ENTITY", details=details)

class DependencyError(AppError):
    def __init__(self, message: str = "External dependency failure", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=502, code="DEPENDENCY_FAILURE", details=details)

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "UNKNOWN")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "correlation_id": correlation_id,
            }
        },
    )
