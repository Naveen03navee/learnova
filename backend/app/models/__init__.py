from app.core.database import Base
from app.models.workspace import Profile, Exam, Subject
from app.models.knowledge import Folder, Resource
from app.models.generation import GenerationSession, GeneratedQuestion
from app.models.question import Question
from app.models.paper import QuestionPaper, QuestionPaperItem
from app.models.pattern import ExamPattern
from app.models.pattern_chunk import PatternChunk
from app.models.history import ActivityLog
from app.models.sharing import SharePermission

# This file is imported by env.py so Alembic finds all models
