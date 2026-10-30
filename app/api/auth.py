from fastapi import APIRouter, HTTPException, status
from app.core.security import create_access_token, verify_admin_credentials
from app.schemas.comment import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/v1/admin/auth", tags=["Admin authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    if not verify_admin_credentials(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(payload.username))
