import asyncio
from app.core.database import engine

async def test():
    try:
        async with engine.begin() as conn:
            print("SQLAlchemy Success!")
    except Exception as e:
        print(f"SQLAlchemy Error: {type(e).__name__} - {e}")

if __name__ == "__main__":
    asyncio.run(test())
