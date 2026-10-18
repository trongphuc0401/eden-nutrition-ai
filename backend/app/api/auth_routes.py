from __future__ import annotations

from typing import Any

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import SessionLocal
from app.models.user import User


router = APIRouter(prefix="/v1/auth", tags=["auth"])

# Used when Google sign-in is not configured on a local machine, so the
# report flow stays usable without OAuth credentials. Never active in production.
LOCAL_DEV_USER = {"id": "local-dev", "email": None, "name": "Local developer", "avatar_url": None}

oauth = OAuth()
if settings.google_auth_enabled:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def _user_payload(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.display_name,
        "avatar_url": user.avatar_url,
    }


def current_user(request: Request) -> dict[str, Any] | None:
    session_user = request.session.get("user")
    if session_user:
        return session_user
    if not settings.google_auth_enabled and not settings.is_production:
        return LOCAL_DEV_USER
    return None


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthenticated", "message": "Vui lòng đăng nhập bằng Google để tiếp tục."},
        )
    return user


def _upsert_google_user(userinfo: dict[str, Any]) -> dict[str, Any]:
    sub = userinfo["sub"]
    email = userinfo.get("email") if userinfo.get("email_verified") else None
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.google_sub == sub))
        if user is None and email:
            user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email)
            db.add(user)
        user.google_sub = sub
        user.display_name = userinfo.get("name")
        user.avatar_url = userinfo.get("picture")
        if email:
            user.email = email
        db.flush()
        return _user_payload(user)


@router.get("/configuration")
def auth_configuration() -> dict[str, bool | str]:
    """Expose only public readiness, never OAuth secrets."""
    ready = settings.google_auth_enabled
    return {
        "google_enabled": ready,
        "redirect_uri": settings.google_redirect_uri,
        "message": "Google OAuth is ready." if ready else "Google OAuth needs GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and SESSION_SECRET.",
    }


@router.get("/google/login")
async def google_login(request: Request):
    if not settings.google_auth_enabled:
        raise HTTPException(status_code=503, detail="Google OAuth chưa được cấu hình.")
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request) -> RedirectResponse:
    if not settings.google_auth_enabled:
        raise HTTPException(status_code=503, detail="Google OAuth chưa được cấu hình.")
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        return RedirectResponse(f"{settings.frontend_url}/?auth_error=oauth", status_code=302)
    userinfo = token.get("userinfo") or {}
    if not userinfo.get("sub"):
        return RedirectResponse(f"{settings.frontend_url}/?auth_error=userinfo", status_code=302)
    try:
        user = _upsert_google_user(userinfo)
    except SQLAlchemyError:
        return RedirectResponse(f"{settings.frontend_url}/?auth_error=database", status_code=302)
    request.session.clear()
    request.session["user"] = user
    return RedirectResponse(f"{settings.frontend_url}/", status_code=302)


@router.get("/me")
def me(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return {"user": user, "google_enabled": settings.google_auth_enabled}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
