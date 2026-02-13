"""
Security module for PEI Agentic Platform.
Handles JWT token generation/validation, password hashing, and user authentication.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

from .config import get_settings

# ============================================================================
# CONSTANTS & CONFIGURATION
# ============================================================================

# Password hashing context with bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

# HTTP Bearer scheme for FastAPI security
security = HTTPBearer()

# ============================================================================
# ENUMS: USER ROLES
# ============================================================================


class UserRole(str, Enum):
    """
    User roles in the PEI system.
    
    Roles:
    - PM: Project Manager - Full system access, approves planning decisions
    - COORDINATOR: OPU Coordinator - Manages crews and monitors inactivity
    - TECNICO: Technician - Executes OTs, reports progress
    """

    PM = "PM"
    COORDINATOR = "COORDINATOR"
    TECNICO = "TECNICO"


# ============================================================================
# PYDANTIC MODELS: USER SCHEMAS
# ============================================================================


class User(BaseModel):
    """
    Base user model for API responses.
    
    Attributes:
        id: Unique user identifier
        username: Login username
        email: User email address
        full_name: User's full name
        role: User role (PM, COORDINATOR, TECNICO)
        active: Whether user account is active
    """

    id: str
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole
    active: bool = True

    class Config:
        """Pydantic configuration"""
        from_attributes = True


class UserInDB(User):
    """User model with hashed password (internal use only)."""

    hashed_password: str


class UserCreate(BaseModel):
    """User creation request model."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None
    role: UserRole = UserRole.TECNICO


class UserUpdate(BaseModel):
    """User update request model."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    active: Optional[bool] = None


# ============================================================================
# JWT TOKEN MODELS
# ============================================================================


class TokenData(BaseModel):
    """JWT token payload data."""

    sub: str  # Subject (username)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at time
    role: UserRole  # User role
    user_id: str  # User ID


class TokenResponse(BaseModel):
    """Token response for authentication."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until expiration


class TokenRefreshRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str


# ============================================================================
# PASSWORD HASHING FUNCTIONS
# ============================================================================


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        str: Hashed password (bcrypt format)
        
    Example:
        >>> hashed = hash_password("mypassword123")
        >>> hashed.startswith("$2b$")
        True
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database
        
    Returns:
        bool: True if password matches, False otherwise
        
    Example:
        >>> hashed = hash_password("mypassword123")
        >>> verify_password("mypassword123", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT TOKEN FUNCTIONS
# ============================================================================


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary of claims to include in token
              Should include: sub (username), role, user_id
        expires_delta: Custom expiration time. If None, uses default from settings
        
    Returns:
        str: Encoded JWT token
        
    Raises:
        ValueError: If required fields are missing from data
        
    Example:
        >>> token = create_access_token(
        ...     data={"sub": "john", "role": "PM", "user_id": "123"},
        ...     expires_delta=timedelta(hours=24)
        ... )
        >>> len(token) > 0
        True
    """
    settings = get_settings()
    
    # Copy data to avoid modifying original
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Add standard JWT claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
    })
    
    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        TokenData: Decoded token data
        
    Raises:
        HTTPException (401): If token is invalid, expired, or malformed
        
    Example:
        >>> token = create_access_token({"sub": "john", "role": "PM", "user_id": "123"})
        >>> data = decode_token(token)
        >>> data.sub
        'john'
    """
    settings = get_settings()
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        
        # Extract subject (username)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        # Extract user_id
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        
        # Extract role
        role_str: str = payload.get("role")
        if role_str is None:
            raise credentials_exception
        
        # Convert role string to enum
        try:
            role = UserRole(role_str)
        except ValueError:
            raise credentials_exception
        
        # Extract timestamps
        exp = payload.get("exp")
        iat = payload.get("iat")
        
        if exp is None or iat is None:
            raise credentials_exception
        
        # Convert timestamps to datetime
        token_data = TokenData(
            sub=username,
            exp=datetime.fromtimestamp(exp),
            iat=datetime.fromtimestamp(iat),
            role=role,
            user_id=user_id,
        )
        
    except JWTError:
        raise credentials_exception
    
    return token_data


# ============================================================================
# FASTAPI DEPENDENCIES
# ============================================================================


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """
    FastAPI dependency to validate and extract current user from JWT token.
    
    Usage in route handlers:
        @router.get("/protected")
        async def protected_route(current_user: TokenData = Depends(get_current_user)):
            return {"message": f"Hello {current_user.sub}"}
    
    Args:
        credentials: HTTP Bearer credentials from request header
        
    Returns:
        TokenData: Decoded token data with user information
        
    Raises:
        HTTPException (401): If token is invalid or missing
        
    Example:
        >>> # In a route handler:
        >>> async def get_profile(current_user: TokenData = Depends(get_current_user)):
        ...     return {"username": current_user.sub, "role": current_user.role}
    """
    token = credentials.credentials
    return decode_token(token)


async def get_current_user_required_role(
    required_role: UserRole,
) -> callable:
    """
    Create a dependency that checks for a specific user role.
    
    Usage in route handlers:
        @router.delete("/users/{user_id}")
        async def delete_user(
            user_id: str,
            current_user: TokenData = Depends(
                get_current_user_required_role(UserRole.PM)
            ),
        ):
            # Only PMs can delete users
            return {"message": "User deleted"}
    
    Args:
        required_role: The role required to access the route
        
    Returns:
        callable: A dependency function that validates the role
        
    Raises:
        HTTPException (403): If user doesn't have the required role
    """

    async def role_checker(
        current_user: TokenData = Depends(get_current_user),
    ) -> TokenData:
        """Check if user has the required role."""
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User must have {required_role} role to access this resource",
            )
        return current_user

    return role_checker


async def get_current_admin_user(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """
    FastAPI dependency that requires PM (admin) role.
    
    Usage in route handlers:
        @router.delete("/users/{user_id}")
        async def delete_user(
            user_id: str,
            current_user: TokenData = Depends(get_current_admin_user),
        ):
            # Only PMs can access this
            return {"message": "User deleted"}
    
    Args:
        current_user: Current user from get_current_user dependency
        
    Returns:
        TokenData: Current user token data
        
    Raises:
        HTTPException (403): If user is not a PM
    """
    if current_user.role != UserRole.PM:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only PMs can access this resource",
        )
    return current_user


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def verify_user_credentials(
    username: str,
    password: str,
    hashed_password_from_db: str,
) -> bool:
    """
    Verify user credentials during login.
    
    Args:
        username: Username (for logging/audit purposes)
        password: Plain text password provided by user
        hashed_password_from_db: Hashed password from database
        
    Returns:
        bool: True if credentials are valid
        
    Example:
        >>> # During login:
        >>> user = db.get_user_by_username("john")
        >>> if verify_user_credentials("john", "password123", user.hashed_password):
        ...     # Login successful
        ...     token = create_access_token({"sub": user.username, ...})
    """
    return verify_password(password, hashed_password_from_db)


def get_token_expiration_seconds(token: str) -> int:
    """
    Get the number of seconds until a token expires.
    
    Args:
        token: JWT token string
        
    Returns:
        int: Seconds until expiration (negative if expired)
        
    Raises:
        HTTPException (401): If token is invalid
        
    Example:
        >>> token = create_access_token({"sub": "john"})
        >>> seconds = get_token_expiration_seconds(token)
        >>> seconds > 0
        True
    """
    token_data = decode_token(token)
    now = datetime.utcnow()
    expires_in = (token_data.exp - now).total_seconds()
    return int(expires_in)


def create_login_response(
    user: User,
    expires_delta: Optional[timedelta] = None,
) -> TokenResponse:
    """
    Create a complete login response with token.
    
    Args:
        user: Authenticated user object
        expires_delta: Custom token expiration time
        
    Returns:
        TokenResponse: Token and metadata
        
    Example:
        >>> user = User(id="1", username="john", email="john@example.com", role=UserRole.PM)
        >>> response = create_login_response(user)
        >>> response.token_type
        'bearer'
    """
    # Create token
    token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role,
            "user_id": user.id,
        },
        expires_delta=expires_delta,
    )
    
    # Calculate expiration time
    settings = get_settings()
    if expires_delta:
        expires_in = int(expires_delta.total_seconds())
    else:
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
    )

