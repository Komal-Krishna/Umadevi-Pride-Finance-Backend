from fastapi import APIRouter, HTTPException, status
from app.models.base import LoginRequest, LoginResponse
from app.core.auth import auth_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest):
    """Authenticate user with password and return JWT token"""
    try:
        response = await auth_manager.authenticate_user(login_request)
        
        if not response:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
