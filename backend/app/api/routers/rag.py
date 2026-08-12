from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.rag import RetrievalRequest, RetrievalResponse
from app.services.rag import retrieve_chunks

router = APIRouter(prefix="/api/v1/retrieval", tags=["Retrieval"])
logger = logging.getLogger(__name__)

@router.post("/search", response_model=RetrievalResponse)
async def search_knowledge(
    request: RetrievalRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    try:
        response = await retrieve_chunks(db, request)
        return response
    except ValueError as e:
        # Hierarchy validation failure
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Vector search failed.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred during retrieval search.")
