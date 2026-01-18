from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from app.api.schemas import TokenData
from app.utils.mongo_handler import mongo_handler

# --- Configuration ---
try:
    SECRET_KEY = os.environ["JWT_SECRET_KEY"]
except KeyError:
    raise RuntimeError("JWT_SECRET_KEY is not set in the environment.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# --- JWT Creation ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Token Verification and User Retrieval ---
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        email: str = payload.get("email")
        roles: List[str] = payload.get("roles", [])

        if not username or not email:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Fetch user from DB
    user = await mongo_handler.get_user(username=username)

    if user is None or not user.get("is_active"):
        raise credentials_exception

    # Return normalized user object
    return {
        "username": user["username"],
        "email": user["email"],
        "roles": user["roles"],
        "is_active": user["is_active"]
    }


# --- Role-Based Dependency ---
def require_role(required_role: str):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if required_role not in current_user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user does not have adequate privileges",
            )
        return current_user
    return role_checker
