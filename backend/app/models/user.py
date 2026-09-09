"""
SecureNet Backend — User Model
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from app.db.base import Base


class AuthProvider(str, enum.Enum):
    """Authentication provider types"""
    LOCAL = "local"
    GOOGLE = "google"


class AccountStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class UserRole(str, enum.Enum):
    """User roles for authorization"""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.VIEWER)
    account_status = Column(SQLEnum(AccountStatus), nullable=False, default=AccountStatus.PENDING_VERIFICATION)
    auth_provider = Column(SQLEnum(AuthProvider), nullable=False, default=AuthProvider.LOCAL)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    # Optional profile fields
    avatar_url = Column(String(512), nullable=True)
    
    # Security
    failed_login_attempts = Column(String, nullable=False, default="0")
    locked_until = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User {self.email}>"
