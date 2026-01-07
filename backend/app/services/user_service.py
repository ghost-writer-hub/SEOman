"""
User service for business logic.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole, UserStatus
from app.schemas.auth import RegisterRequest, UserUpdate


class UserService:
    """Service for user operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str, tenant_id: UUID | None = None) -> User | None:
        """Get user by email, optionally within a tenant."""
        query = select(User).where(User.email == email)
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_users(
        self,
        tenant_id: UUID | None = None,
        page: int = 1,
        per_page: int = 20,
        role: UserRole | None = None,
        status: UserStatus | None = None,
    ) -> tuple[list[User], int]:
        """List users with pagination and filters."""
        query = select(User)
        count_query = select(func.count(User.id))
        
        filters = []
        if tenant_id:
            filters.append(User.tenant_id == tenant_id)
        if role:
            filters.append(User.role == role)
        if status:
            filters.append(User.status == status)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        return list(users), total
    
    async def create(
        self,
        email: str,
        password: str,
        name: str,
        tenant_id: UUID | None = None,
        role: UserRole = UserRole.READ_ONLY,
    ) -> User:
        """Create a new user."""
        user = User(
            email=email,
            password_hash=hash_password(password),
            name=name,
            tenant_id=tenant_id,
            role=role,
            status=UserStatus.ACTIVE,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def authenticate(self, email: str, password: str) -> User | None:
        """Authenticate a user by email and password."""
        user = await self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
    
    async def update(self, user_id: UUID, data: UserUpdate) -> User | None:
        """Update a user."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            await self.db.flush()
    
    async def deactivate(self, user_id: UUID) -> bool:
        """Deactivate a user."""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        user.status = UserStatus.INACTIVE
        await self.db.flush()
        return True
