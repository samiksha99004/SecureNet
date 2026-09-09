"""
SecureNet Backend — Authentication Routes

Handles user registration, login, OTP verification, and token management.
"""

from datetime import datetime, timedelta
import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.base import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, validate_password_strength
from app.core.config import settings
from app.models.user import User, AccountStatus, AuthProvider
from app.models.otp import OTP
from app.schemas.auth import (
    LoginRequest,
    SignupRequest,
    OtpVerifyRequest,
    OtpResendRequest,
    ChangePasswordRequest,
    AuthResponse,
    AuthTokens,
    UserResponse,
    OtpVerifyResponse
)
from app.schemas.common import MessageResponse
from app.api.dependencies import get_current_user
from app.utils.email import send_otp_email
from app.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def create_auth_response(user: User) -> AuthResponse:
    """Create authentication response with tokens"""
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return AuthResponse(
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            account_status=user.account_status,
            auth_provider=user.auth_provider,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            avatar_url=user.avatar_url
        ),
        tokens=AuthTokens(
            accessToken=access_token,
            refreshToken=refresh_token,
            expiresIn=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    )


@router.post("/signup", response_model=MessageResponse)
async def signup(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    Sends OTP to email for verification.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password strength
    is_valid, error_msg = validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Create user
    user = User(
        email=request.email,
        full_name=request.fullName,
        password_hash=hash_password(request.password),
        account_status=AccountStatus.PENDING_VERIFICATION,
        auth_provider=AuthProvider.LOCAL
    )
    
    db.add(user)
    await db.commit()
    
    # Generate and store OTP
    otp_code = generate_otp(settings.OTP_LENGTH)
    otp = OTP(
        email=request.email,
        otp_code=otp_code
    )
    
    db.add(otp)
    await db.commit()
    
    # Send OTP email
    await send_otp_email(request.email, otp_code)
    
    logger.info(f"User registered: {request.email}")
    
    return MessageResponse(message="Registration successful. Please check your email for OTP.")


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user with email and password.
    Returns JWT tokens and user data.
    """
    # Find user
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check account status
    if user.account_status == AccountStatus.PENDING_VERIFICATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not verified. Please check your email for OTP."
        )
    
    if user.account_status == AccountStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended"
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    logger.info(f"User logged in: {user.email}")
    
    return create_auth_response(user)


@router.post("/otp/verify", response_model=OtpVerifyResponse)
async def verify_otp(
    request: OtpVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP code sent to user's email.
    Activates the account and returns auth tokens.
    """
    # Find most recent unused OTP for this email
    result = await db.execute(
        select(OTP)
        .where(and_(OTP.email == request.email, OTP.is_used == False))
        .order_by(OTP.created_at.desc())
    )
    otp = result.scalar_one_or_none()
    
    if not otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No OTP found for this email"
        )
    
    # Check if OTP is valid
    if not otp.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired or exceeded maximum attempts"
        )
    
    # Increment attempts
    otp.attempts += 1
    
    # Verify OTP code
    if otp.otp_code != request.otp:
        await db.commit()
        
        if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum OTP attempts exceeded. Please request a new OTP."
            )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP. {settings.OTP_MAX_ATTEMPTS - otp.attempts} attempts remaining."
        )
    
    # Mark OTP as used
    otp.is_used = True
    otp.used_at = datetime.utcnow()
    
    # Activate user account
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if user and user.account_status == AccountStatus.PENDING_VERIFICATION:
        user.account_status = AccountStatus.ACTIVE
        user.last_login_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(f"OTP verified for: {request.email}")
    
    # Return auth response if user exists
    if user:
        return OtpVerifyResponse(
            verified=True,
            authResponse=create_auth_response(user)
        )
    
    return OtpVerifyResponse(verified=True, authResponse=None)


@router.post("/otp/resend", response_model=MessageResponse)
async def resend_otp(
    request: OtpResendRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Resend OTP to user's email.
    Subject to cooldown period.
    """
    # Check for recent OTP
    result = await db.execute(
        select(OTP)
        .where(OTP.email == request.email)
        .order_by(OTP.created_at.desc())
    )
    last_otp = result.scalar_one_or_none()
    
    if last_otp:
        time_since_last = (datetime.utcnow() - last_otp.created_at).total_seconds()
        if time_since_last < settings.OTP_RESEND_COOLDOWN_SECONDS:
            remaining = int(settings.OTP_RESEND_COOLDOWN_SECONDS - time_since_last)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {remaining} seconds before requesting a new OTP"
            )
    
    # Generate new OTP
    otp_code = generate_otp(settings.OTP_LENGTH)
    otp = OTP(
        email=request.email,
        otp_code=otp_code
    )
    
    db.add(otp)
    await db.commit()
    
    # Send OTP email
    await send_otp_email(request.email, otp_code)
    
    logger.info(f"OTP resent to: {request.email}")
    
    return MessageResponse(message="OTP has been resent to your email")


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user (client-side token removal primarily).
    Server-side session invalidation could be added here.
    """
    logger.info(f"User logged out: {current_user.email}")
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's profile"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        account_status=current_user.account_status,
        auth_provider=current_user.auth_provider,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
        avatar_url=current_user.avatar_url
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change password for authenticated user"""
    
    # Only for local auth users
    if current_user.auth_provider != AuthProvider.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot change password for {current_user.auth_provider} authentication"
        )
    
    # Verify current password
    if not current_user.password_hash or not verify_password(request.currentPassword, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    is_valid, error_msg = validate_password_strength(request.newPassword)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Update password
    current_user.password_hash = hash_password(request.newPassword)
    current_user.updated_at = datetime.utcnow()
    await db.commit()
    
    logger.info(f"Password changed for: {current_user.email}")
    
    return MessageResponse(message="Password changed successfully")
