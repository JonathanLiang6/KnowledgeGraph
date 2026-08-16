"""
API 认证工具 (v4.1 安全加固)

- API_AUTH_TOKEN 为空时认证关闭（本地开发模式）
- 支持 Authorization: Bearer <token> 或 X-API-Token 请求头
- 使用 secrets.compare_digest 防时序攻击
"""
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

# 无需认证的公开路径（健康检查）
PUBLIC_PATHS = {"/health"}

# 认证未启用/未通过时的统一响应
_UNAUTHORIZED = JSONResponse(
    status_code=401,
    content={"detail": "未授权：缺少或无效的 API Token（Authorization: Bearer <token> 或 X-API-Token 头）"},
)


def extract_api_token(request: Request) -> str:
    """从请求头提取 API Token（Bearer 优先，其次 X-API-Token）"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return request.headers.get("X-API-Token", "").strip()


def is_auth_enabled(expected_token: str) -> bool:
    """认证是否启用（token 已配置）"""
    return bool(expected_token)


def verify_request_auth(request: Request, expected_token: str) -> bool:
    """校验请求是否携带正确的 API Token"""
    if not expected_token:
        return True
    provided = extract_api_token(request)
    if not provided:
        return False
    return secrets.compare_digest(provided, expected_token)


def auth_middleware_check(request: Request, expected_token: str):
    """
    中间件用认证检查。

    Returns:
        None（放行）或 JSONResponse(401)（拒绝）
    """
    if not expected_token or request.url.path in PUBLIC_PATHS:
        return None
    if not verify_request_auth(request, expected_token):
        return _UNAUTHORIZED
    return None
