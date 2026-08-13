from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import exams, subjects, folders, resources, rag, generation, questions, papers, health, metrics, patterns, shares
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
    logger.info("Application shutting down, closing AI provider clients...")
    try:
        from app.services.ai.manager import ai_manager
        await ai_manager.aclose_clients()
    except Exception as e:
        logger.error(f"Failed to close AI provider clients on shutdown: {e}")
    logger.info("Disposing database connections...")
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
    
    # Let FastAPI process the request with the real token
    response = await call_next(request)
    
    # Sanitize JWT tokens from query strings AFTER processing so they don't leak into Uvicorn access logs
    qs = request.scope.get("query_string", b"").decode("utf-8")
    if "token=" in qs:
        import re
        sanitized_qs = re.sub(r'token=[^&]+', 'token=***', qs)
        request.scope["query_string"] = sanitized_qs.encode("utf-8")
        
    return response

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Learnova API Service is running.",
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }

# CORS
cors_origins = settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else ["http://localhost:3000"]
if isinstance(cors_origins, str):
    cors_origins = [i.strip() for i in cors_origins.split(",") if i.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
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
app.include_router(shares.router)


