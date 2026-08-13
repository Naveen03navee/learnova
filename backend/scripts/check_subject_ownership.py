import asyncio
from sqlalchemy import select
from app.models.workspace import Subject
from app.core.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Subject).where(Subject.created_by == None))
        subjects = result.scalars().all()
        
        print(f"Found {len(subjects)} subjects with NULL created_by.")
        for s in subjects:
            print(f"- ID: {s.id}, Name: {s.name}, Exam_ID: {s.exam_id}")

if __name__ == "__main__":
    asyncio.run(main())
