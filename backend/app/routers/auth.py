from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.auth import authenticate_user, create_access_token, get_current_user
from app.database import get_db
from app.models import User
from app.permissions import user_permission_codes
from app.schemas import LoginRequest, Token, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post("/login", response_model=Token)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, payload.username, payload.password)
    ip = _client_ip(request)
    if not user:
        record_audit(
            db,
            username=payload.username or "",
            action="login",
            resource="auth",
            detail={"reason": "invalid_credentials"},
            ip=ip,
            success=False,
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject=user.username)
    record_audit(
        db,
        username=user.username,
        action="login",
        resource="auth",
        resource_id=user.id,
        detail={"role": user.role},
        ip=ip,
        success=True,
        commit=True,
    )
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        permissions=sorted(user_permission_codes(db, current_user)),
    )
