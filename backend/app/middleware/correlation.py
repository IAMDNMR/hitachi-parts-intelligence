import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

CORRELATION_HEADER = "X-Correlation-ID"

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(CORRELATION_HEADER)
        if not correlation_id:
            correlation_id = f"corr-{uuid.uuid4()}"
        
        request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response
