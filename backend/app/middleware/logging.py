import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from app.core.logging import get_logger, request_id_ctx

logger = get_logger("app.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        
        start_time = time.perf_counter()
        
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            response.headers["X-Request-ID"] = request_id
            
            # Avoid overly verbose logging on static/health checks unless error
            if path in ("/api/v1/health", "/docs", "/openapi.json") and response.status_code < 400:
                pass
            else:
                logger.info(
                    f"{method} {path} - {response.status_code} ({duration_ms}ms)",
                    extra={
                        "http_method": method,
                        "http_path": path,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                        "client_ip": client_ip,
                        "request_id": request_id,
                    }
                )
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Unhandled exception during {method} {path}: {str(exc)}",
                exc_info=True,
                extra={
                    "http_method": method,
                    "http_path": path,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    "request_id": request_id,
                }
            )
            raise exc
        finally:
            request_id_ctx.reset(token)
