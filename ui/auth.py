from __future__ import annotations
import hmac
from fastapi import Request, HTTPException
from config import settings


def resolve_identity(request: Request) -> dict:
    if not settings.require_auth:
        return {"id": "anonymous", "method": "open", "display": "Anonymous"}

    api_key = (
        request.query_params.get("apikey")
        or request.headers.get("x-api-key")
        or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    )
    if api_key and settings.dashboard_api_key:
        if hmac.compare_digest(api_key, settings.dashboard_api_key):
            return {"id": "api-client", "method": "api-key", "display": "API Client"}

    if settings.trust_npm_headers:
        npm_user = request.headers.get("x-auth-user")
        if npm_user:
            return {"id": npm_user, "method": "npm-header", "display": npm_user}

    if settings.trust_forwarded_user:
        fwd_user = request.headers.get("x-forwarded-user") or request.headers.get("remote-user")
        if fwd_user:
            return {"id": fwd_user, "method": "forwarded-user", "display": fwd_user}

    sso_cookie = request.cookies.get(settings.sso_cookie_name)
    if sso_cookie:
        return {"id": "sso-user", "method": "sso-cookie", "display": "SSO User"}

    raise HTTPException(status_code=401, detail="Authentication required")


def require_auth(request: Request) -> dict:
    return resolve_identity(request)
