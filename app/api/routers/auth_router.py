"""
Authentication Router Module

Handles user registration, login, password reset, and account status.
Follows Single Responsibility Principle - focuses only on authentication.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.utils.logger import setup_logger
from app.utils.mongo_handler import mongo_handler
from app.api.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.api.schemas import (
    UserCreate,
    Token,
    User,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetResponse,
    AccountStatus,
    QuotaInfo,
)
from app.api.app_config import get_config

logger = setup_logger()
config = get_config()

# Will be injected by the main app
account_lockout_service = None
password_reset_service = None
quota_service = None

router = APIRouter(prefix="/auth", tags=["Authentication"])


def init_auth_services(lockout_service, reset_service, quota_svc):
    """Initialize services - called from main app"""
    global account_lockout_service, password_reset_service, quota_service
    account_lockout_service = lockout_service
    password_reset_service = reset_service
    quota_service = quota_svc


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """
    Register a new user.
    
    - **username**: Unique username
    - **email**: User email address
    - **password**: Password (will be hashed)
    """
    existing_user = await mongo_handler.get_user(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    hashed_password = get_password_hash(user.password)
    await mongo_handler.create_user({
        "email": user.email,
        "username": user.username,
        "password_hash": hashed_password,
        "roles": user.roles,
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    })

    logger.info(f"User registered: {user.username}")
    return {"message": "User created successfully"}


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login with username and password.
    
    Returns JWT access token for authenticated requests.
    
    **Security:**
    - Locks account after 5 failed attempts
    - Lock expires in 24 hours
    """
    # Check if account is locked
    is_locked = await account_lockout_service.is_account_locked(form_data.username)
    if is_locked:
        logger.warning(f"Login attempt to locked account: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked due to too many failed attempts. Try again in {config.security.lockout_duration_hours} hours.",
        )

    user = await mongo_handler.get_user(form_data.username)

    if not user or not verify_password(form_data.password, user["password_hash"]):
        # Record failed attempt
        await account_lockout_service.record_failed_attempt(form_data.username)
        logger.warning(f"Failed login attempt: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Reset failed attempts on successful login
    await account_lockout_service.reset_failed_attempts(form_data.username)
    logger.info(f"User logged in: {form_data.username}")

    token = create_access_token(
        data={"sub": user["username"], "roles": user["roles"], 
              "email": user["email"], "tier": user.get("tier", "free")}
    )

    return {"access_token": token, "token_type": "bearer"}


@router.post("/request-reset", response_model=PasswordResetResponse)
async def request_password_reset(req: PasswordResetRequest):
    """
    Request password reset.
    
    Sends reset email to user with token valid for 24 hours.
    
    **Security:**
    - Does not reveal if user exists
    - Email must match registered email
    """
    user = await mongo_handler.get_user(req.username)
    if not user:
        # Security: don't reveal if user exists
        logger.warning(f"Password reset requested for non-existent user: {req.username}")
        return PasswordResetResponse(
            success=True,
            message="If the account exists, a reset link has been sent to the email."
        )

    if user.get("email") != req.email:
        # Email mismatch
        logger.warning(f"Email mismatch for password reset: {req.username}")
        return PasswordResetResponse(
            success=True,
            message="If the account exists, a reset link has been sent to the email."
        )

    # Send reset email
    success, message = await password_reset_service.request_password_reset(req.username, req.email)
    return PasswordResetResponse(success=success, message=message)


@router.post("/confirm-reset", response_model=PasswordResetResponse)
async def confirm_password_reset(req: PasswordResetConfirm):
    """
    Confirm password reset with token and new password.
    
    **Steps:**
    1. Validates reset token (must be valid and not expired)
    2. Hashes new password
    3. Updates password in database
    4. Invalidates token
    """
    # Validate token
    valid, msg = await password_reset_service.validate_reset_token(req.username, req.token)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    # Hash new password
    hashed_password = get_password_hash(req.new_password)

    # Complete reset (token is deleted here)
    success, message = await password_reset_service.complete_password_reset(
        req.username, req.token, hashed_password
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    logger.info(f"Password reset completed for user: {req.username}")
    return PasswordResetResponse(success=True, message="Password reset successfully!")


@router.get("/account-status", response_model=AccountStatus)
async def get_account_status(current_user: dict = Depends(get_current_user)):
    """
    Get account status including tier, quota, and lockout status.
    
    **Returns:**
    - Account information (username, email, is_active)
    - Lock status
    - Current tier (free/premium)
    - Quota information (usage, limit, remaining, reset time)
    """
    username = current_user["username"]
    
    # Get quota info
    can_analyze, quota_info = await quota_service.can_perform_analysis(username)
    
    # Check if locked
    is_locked = await account_lockout_service.is_account_locked(username)

    return AccountStatus(
        username=username,
        email=current_user["email"],
        is_active=current_user["is_active"],
        is_locked=is_locked,
        tier=current_user.get("tier", "free"),
        quota=QuotaInfo(**quota_info),
        roles=current_user["roles"],
    )


@router.get("/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return current_user
