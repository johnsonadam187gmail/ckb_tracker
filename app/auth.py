import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

# Load environment variables from .env file
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Generate a new secret key if not found
    import secrets

    SECRET_KEY = secrets.token_urlsafe(32)
    with open(".env", "a") as f:
        f.write(f"\nSECRET_KEY={SECRET_KEY}\n")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 5

# Password hashing context
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)


def create_teacher_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT for a teacher with a given expiry."""
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY is not set")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_teacher_token(token: str) -> Optional[dict]:
    """Verifies and decodes a teacher's JWT."""
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY is not set")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def extend_teacher_token(token: str) -> str:
    """Extends a teacher's JWT session by creating a new token."""
    payload = verify_teacher_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token for extension.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Remove old expiration time to replace it
    payload.pop("exp", None)
    return create_teacher_token(payload)
