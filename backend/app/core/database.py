from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# asyncpg URL format required by SQLAlchemy async
# IMPORTANT FOR RENDER / SUPABASE:
# Render instances are IPv4-only and cannot reach Supabase direct IPv6 hostnames (db.xxx.supabase.co).
# You MUST use the Supabase Connection Pooler URL from your Supabase Dashboard:
# Example: postgresql://postgres.ref:password@aws-0-region.pooler.supabase.com:6543/postgres

db_url = settings.DATABASE_URL
if db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Configure connect_args for SSL if on remote cloud DBs
connect_args = {}
if "supabase" in db_url or "render" in db_url or "aws" in db_url:
    connect_args["ssl"] = "require"

engine = create_async_engine(
    db_url,
    echo=False,
    connect_args=connect_args,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
