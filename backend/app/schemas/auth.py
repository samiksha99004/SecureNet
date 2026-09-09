"""
SecureNet Backend — Authentication Schemas

Pydantic models for auth request/response validation.
These match the frontend TypeScript interfaces exactly.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
from app.models.user import UserRole, AccountStatus, AuthProvider


# ── User Schema ───────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """User data returned to frontend"""
    id: str
    email: str
    fullName: str = Field(..., alias="full_name")
    role: UserRole
    accountStatus: AccountStatus = Field(..., alias="account_status")
    authProvider: AuthProvider = Field(..., alias="auth_provider")
    createdAt: datetime = Field(..., alias="created_at")
    lastLoginAt: Optional[datetime] = Field(None, alias="last_login_at")
    avatarUrl: Optional[str] = Field(None, alias="avatar_url")
    
    class Config:
        from_attributes = True
        populate_by_name = True


# ── Auth Requests ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Login credentials"""
    email: EmailStr
    password: str = Field(..., min_length=1)


class SignupRequest(BaseModel):
    """User registration data"""
    fullName: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirmPassword: str = Field(..., min_length=8)
    
    @validator('confirmPassword')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class OtpVerifyRequest(BaseModel):
    """OTP verification"""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class OtpResendRequest(BaseModel):
    """Request OTP resend"""
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    """Change password for authenticated user"""
    currentPassword: str = Field(..., min_length=1)
    newPassword: str = Field(..., min_length=8)
    confirmNewPassword: str = Field(..., min_length=8)
    
    @validator('confirmNewPassword')
    def passwords_match(cls, v, values):
        if 'newPassword' in values and v != values['newPassword']:
            raise ValueError('Passwords do not match')
        return v


class ForgotPasswordRequest(BaseModel):
    """Request password reset"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password with token"""
    token: str
    newPassword: str = Field(..., min_length=8)
    confirmNewPassword: str = Field(..., min_length=8)
    
    @validator('confirmNewPassword')
    def passwords_match(cls, v, values):
        if 'newPassword' in values and v != values['newPassword']:
            raise ValueError('Passwords do not match')
        return v


# ── Auth Responses ────────────────────────────────────────────────────────────

class AuthTokens(BaseModel):
    """JWT tokens"""
    accessToken: str
    refreshToken: str
    expiresIn: int  # seconds


class AuthResponse(BaseModel):
    """Successful authentication response"""
    user: UserResponse
    tokens: AuthTokens


class OtpVerifyResponse(BaseModel):
    """OTP verification result"""
    verified: bool
    authResponse: Optional[AuthResponse] = None
