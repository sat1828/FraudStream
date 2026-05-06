"""JWT Authentication with rate limiting and audit logging."""

from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.core.redis_client import redis_client
from app.models.user import AuditLog, User

logger = structlog.get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


async def check_login_rate_limit(ip_address: str) -> bool:
    """Check if login attempts from this IP exceed the rate limit."""
    key = f"login_rl:{ip_address}"
    current = await redis_client.incr(key, ttl=settings.LOGIN_RATE_LIMIT_WINDOW)
    if current > settings.LOGIN_RATE_LIMIT_ATTEMPTS:
        logger.warning(
            "Login rate limit exceeded",
            ip_address=ip_address,
            attempts=current,
        )
        return False
    return True


async def record_audit_event(
    db: AsyncSession,
    user_id: Optional[str],
    action: str,
    resource: str,
    resource_id: str,
    details: dict,
    ip_address: str,
) -> None:
    """Record an audit log entry."""
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
        )
        db.add(audit_entry)
        await db.commit()
    except Exception as e:
        logger.error("Failed to record audit event", error=str(e))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user
