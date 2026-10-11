"""
Audit logging middleware — writes AuditLog records for mutating requests.
"""

from __future__ import annotations
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("audit")


class AuditMiddleware(BaseHTTPMiddleware):
    TRACKED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method in self.TRACKED_METHODS:
            logger.info(
                "AUDIT | %s %s | status=%d | ip=%s",
                request.method,
                request.url.path,
                response.status_code,
                request.client.host if request.client else "unknown",
            )
        return response
