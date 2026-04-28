import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .logger import RequestContext, api_logger


class RequestLogMiddleware(BaseHTTPMiddleware):
    """请求日志中间件 - 记录每个请求的详细信息"""

    async def dispatch(self, request: Request, call_next):
        # 生成请求 ID
        request_id = str(uuid.uuid4())[:8]
        RequestContext.set_request_id(request_id)

        # 获取开始时间
        start_time = time.time()

        # 记录请求开始
        api_logger.info(
            f"Request started",
            extra={
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                }
            }
        )

        # 设置 user_id 到上下文（如果已认证）
        # 这个需要在路由处理时由 auth 依赖项设置

        try:
            response = await call_next(request)

            # 计算耗时
            duration = time.time() - start_time

            # 记录请求完成
            api_logger.info(
                f"Request completed",
                extra={
                    "extra_data": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": round(duration * 1000, 2),
                    }
                }
            )

            # 在响应头中添加 request_id
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration = time.time() - start_time

            api_logger.error(
                f"Request failed",
                extra={
                    "extra_data": {
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(duration * 1000, 2),
                        "error": str(e),
                    }
                }
            )
            raise

        finally:
            RequestContext.clear()
