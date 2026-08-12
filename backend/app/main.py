from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import exams, subjects, folders, resources, rag, generation, questions, papers, health, metrics, patterns
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.request_context import set_request_id
import uuid

setup_logging()
logger = get_logger(__name__)

from contextlib import asynccontextmanager
from app.core.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Application starting up...")
    
    # Clean up stuck sessions from a previous server restart
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.generation import GenerationSession, GenerationStatus
        from sqlalchemy.future import select
        from sqlalchemy import update
        
        stuck_statuses = [
            GenerationStatus.PENDING,
            GenerationStatus.RETRIEVING,
            GenerationStatus.GENERATING,
            GenerationStatus.VALIDATING,
            GenerationStatus.DEDUPLICATING,
            GenerationStatus.SAVING,
        ]
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                update(GenerationSession)
                .where(GenerationSession.status.in_(stuck_statuses))
                .values(status=GenerationStatus.FAILED)
                .returning(GenerationSession.id)
            )
            stuck_ids = result.scalars().all()
            await db.commit()
            if stuck_ids:
                logger.warning(f"Marked {len(stuck_ids)} stuck generation session(s) as FAILED on startup.")
                # Notify any waiting SSE clients
                from app.services.generation.events import event_bus
                from app.schemas.generation import GenerationEvent
                for sid in stuck_ids:
                    failed_event = GenerationEvent(
                        session_id=sid,
                        status=GenerationStatus.FAILED,
                        message="Generation session was interrupted by a server restart.",
                        progress=0,
                    )
                    await event_bus.publish(failed_event)
    except Exception as e:
        logger.error(f"Failed to clean up stuck sessions on startup: {e}")
    
    yield
    # Shutdown actions
    logger.info("Application shutting down, disposing database connections...")
    await engine.dispose()
    logger.info("Database connections disposed.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    req_id = str(uuid.uuid4())
    set_request_id(req_id)
    response = await call_next(request)
    return response

# CORS
# Milestone 1: CORS must not use unrestricted * when credentials are enabled.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(exams.router)
app.include_router(subjects.router)
app.include_router(folders.router)
app.include_router(resources.router)
app.include_router(rag.router)
app.include_router(generation.router)
app.include_router(questions.router)
app.include_router(papers.router)
app.include_router(patterns.router)
app.include_router(health.router)
app.include_router(metrics.router)


