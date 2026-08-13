from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.supabase import get_supabase_client
from app.core.database import get_db
from app.models.workspace import Profile
import uuid
from typing import Optional

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> str:
    """
    Validates the Supabase JWT, ensures the user exists in the profiles table, 
    and returns the authenticated user ID.
    """
    auth_token = credentials.credentials if credentials else token
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    supabase = get_supabase_client()
    try:
        # Validate token against Supabase Auth
        response = supabase.auth.get_user(auth_token)
        user = response.user
        if not user:
            raise ValueError("Invalid user")
            
        # Ensure user exists in profiles table
        user_uuid = uuid.UUID(user.id)
        profile = await db.get(Profile, user_uuid)
        if not profile:
            new_profile = Profile(
                id=user_uuid,
                email=user.email or f"{user.id}@unknown.com"
            )
            db.add(new_profile)
            try:
                await db.commit()
            except Exception:
                await db.rollback()
                
        return user.id
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
