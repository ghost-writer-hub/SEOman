"""
Authentication endpoints.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.core.security import create_access_token
from app.models.tenant import Tenant
from app.models.user import UserRole, UserStatus
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Authenticate user and return access token."""
    user_service = UserService(db)
    
    user = await user_service.authenticate(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )
    
    await user_service.update_last_login(user.id)
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Register a new user and optionally create a tenant."""
    user_service = UserService(db)
    
    # Check if email exists
    existing_user = await user_service.get_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    tenant_id = None
    role = UserRole.READ_ONLY
    
    # Create tenant if name provided
    if request.tenant_name:
        slug = request.tenant_name.lower().replace(" ", "-")
        
        # Check slug uniqueness
        from app.services.tenant_service import TenantService
        tenant_service = TenantService(db)
        existing_tenant = await tenant_service.get_by_slug(slug)
        if existing_tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name already taken",
            )
        
        from app.schemas.tenant import TenantCreate
        tenant = await tenant_service.create(TenantCreate(
            name=request.tenant_name,
            slug=slug,
        ))
        tenant_id = tenant.id
        role = UserRole.TENANT_ADMIN
    
    # Create user
    user = await user_service.create(
        email=request.email,
        password=request.password,
        name=request.name,
        tenant_id=tenant_id,
        role=role,
    )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user)
