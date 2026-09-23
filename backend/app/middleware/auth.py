from typing import Optional, List
import jwt
from fastapi import Request, Header
from app.config import settings
from app.errors.exceptions import UnauthorizedError, ForbiddenError

class AuthUser:
    def __init__(self, user_id: str, role: str, dealer_id: Optional[str] = None):
        self.user_id = user_id
        self.role = role
        self.dealer_id = dealer_id

async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> AuthUser:
    if not authorization:
        # Default anonymous system user for open endpoints
        return AuthUser(user_id="ANONYMOUS", role="PUBLIC", dealer_id=None)
    
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return AuthUser(
            user_id=payload.get("sub", "UNKNOWN"),
            role=payload.get("role", "CUSTOMER"),
            dealer_id=payload.get("dealer_id")
        )
    except Exception as e:
        raise UnauthorizedError(f"Invalid or expired authentication token: {str(e)}")

def require_role(allowed_roles: List[str]):
    async def role_checker(user: AuthUser = get_current_user) -> AuthUser:
        if user.role not in allowed_roles and "ALL" not in allowed_roles:
            raise ForbiddenError(f"Role '{user.role}' is not authorized. Allowed: {allowed_roles}")
        return user
    return role_checker

def require_dealer_scope(dealer_id: str, user: AuthUser):
    if user.role == "SYSTEM_ADMIN" or user.role == "HCME_ADMIN":
        return True
    if user.dealer_id and user.dealer_id != dealer_id:
        raise ForbiddenError(f"Dealer scope violation: user associated with {user.dealer_id}, requested {dealer_id}")
    return True
