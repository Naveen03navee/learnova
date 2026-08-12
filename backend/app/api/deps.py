from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.supabase import get_supabase_client
from app.core.database import get_db
from app.models.workspace import Profile
import uuid

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> str:
    """
    Validates the Supabase JWT, ensures the user exists in the profiles table, 
    and returns the authenticated user ID.
    """
    token = credentials.credentials
    supabase = get_supabase_client()
    try:
        # Validate token against Supabase Auth
        response = supabase.auth.get_user(token)
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
