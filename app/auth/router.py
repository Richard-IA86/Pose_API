from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth import schemas, utils
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


# ---------------------------------------------------------------------------
# Dependency: get current user from Bearer token
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = utils.decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = utils.get_user_by_username(db, username)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def get_current_superuser(current_user=Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user account."""
    if utils.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    if utils.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = utils.create_user(db, payload.username, payload.email, payload.password, payload.full_name)
    return user


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and receive an access + refresh token pair."""
    user = utils.authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    access_token = utils.create_access_token({"sub": user.username})
    refresh_token, expires_at = utils.create_refresh_token({"sub": user.username})
    utils.store_refresh_token(db, user.id, refresh_token, expires_at)

    return schemas.TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=schemas.AccessTokenResponse)
def refresh_token(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = utils.decode_token(payload.refresh_token)
        if token_data.get("type") != "refresh":
            raise credentials_exception
        username: str | None = token_data.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    rt = utils.get_refresh_token(db, payload.refresh_token)
    if rt is None or rt.revoked or rt.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise credentials_exception

    user = utils.get_user_by_username(db, username)
    if user is None or not user.is_active:
        raise credentials_exception

    access_token = utils.create_access_token({"sub": user.username})
    return schemas.AccessTokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    """Revoke the provided refresh token."""
    utils.revoke_refresh_token(db, payload.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Revoke all refresh tokens for the current user."""
    utils.revoke_all_user_tokens(db, current_user.id)


@router.get("/me", response_model=schemas.UserRead)
def me(current_user=Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user
