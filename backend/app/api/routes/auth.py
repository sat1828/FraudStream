"""Authentication routes with rate limiting and audit logging."""

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    check_login_rate_limit,
    create_access_token,
    get_current_user,
    hash_password,
    record_audit_event,
    verify_password,
)
from app.models.user import User
from app.schemas.schemas import LoginRequest, TokenResponse, UserResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT token with rate limiting."""
    client_ip = request.client.host if request.client else "unknown"

    allowed = await check_login_rate_limit(client_ip)
    if not allowed:
        await record_audit_event(
            db=db,
            user_id=None,
            action="LOGIN_RATE_LIMITED",
            resource="auth",
            resource_id=credentials.email,
            details={"ip_address": client_ip},
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        await record_audit_event(
            db=db,
            user_id=None,
            action="LOGIN_FAILED",
            resource="auth",
            resource_id=credentials.email,
            details={"ip_address": client_ip, "reason": "invalid_credentials"},
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        await record_audit_event(
            db=db,
            user_id=str(user.id),
            action="LOGIN_DISABLED_ACCOUNT",
            resource="auth",
            resource_id=credentials.email,
            details={"ip_address": client_ip},
            ip_address=client_ip,
        )
        raise HTTPException(status_code=400, detail="Account is disabled")

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token({"sub": user.email, "user_id": str(user.id)})

    await record_audit_event(
        db=db,
        user_id=str(user.id),
        action="LOGIN_SUCCESS",
        resource="auth",
        resource_id=credentials.email,
        details={"ip_address": client_ip},
        ip_address=client_ip,
    )

    logger.info("User logged in", email=user.email, ip_address=client_ip)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return UserResponse.model_validate(current_user)


@router.post("/seed-admin", include_in_schema=False)
async def seed_admin(db: AsyncSession = Depends(get_db)):
    """
    Idempotent admin user seed — reads credentials from environment variables.
    Only works if ADMIN_PASSWORD is set. No external access control — use in trusted environments only.
    """
    admin_email = settings.ADMIN_EMAIL
    admin_password = getattr(settings, "ADMIN_PASSWORD", None)

    if not admin_password or admin_password.startswith("CHANGE_ME"):
        return {"status": "skipped", "reason": "ADMIN_PASSWORD env var not set or using default"}

    result = await db.execute(select(User).where(User.email == admin_email))
    if result.scalar_one_or_none():
        return {"status": "already_exists", "email": admin_email}

    admin = User(
        email=admin_email,
        hashed_password=hash_password(admin_password),
        full_name="UPI Admin",
        is_superuser=True,
        is_active=True,
    )
    db.add(admin)
    await db.commit()
    logger.info("Admin user seeded from environment", email=admin_email)
    return {"status": "created", "email": admin_email}
