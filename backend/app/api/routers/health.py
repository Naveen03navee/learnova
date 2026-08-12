from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(prefix="/api/v1", tags=["health"])

@router.get("/health", status_code=status.HTTP_200_OK)
async def liveness_check():
    """Basic liveness probe. Indicates the application is running."""
    return {"status": "alive"}

@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness probe. Verifies dependencies like PostgreSQL are reachable."""
    try:
        # Check database connection
        await db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )

    # Note: If Redis is strictly required for the app to serve any traffic, check it here.
    # We will assume DB is the primary critical dependency.
    return {"status": "ready"}
