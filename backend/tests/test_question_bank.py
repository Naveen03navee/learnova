import unittest
import sys
import os
import asyncio
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from app.api.routers import questions
from app.core.database import get_db
from app.models.question import Question

app = FastAPI()
app.include_router(questions.router)

class TestQuestionBankUpdates(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('app.services.generation.deduplicator.generate_question_embedding', new_callable=AsyncMock)
    @patch('app.api.routers.questions.AsyncSession')
    def test_question_update_regenerates_embedding(self, mock_session_cls, mock_gen_embed):
        mock_db = AsyncMock()
        
        # Setup existing question
        mock_question = MagicMock()
        mock_question.access = None
        mock_question.id = uuid4()
        mock_question.generated_question_id = uuid4()
        mock_question.exam_id = uuid4()
        mock_question.subject_id = uuid4()
        mock_question.folder_id = uuid4()
        mock_question.question_type = "MCQ"
        mock_question.difficulty = "Easy"
        mock_question.marks = 1
        mock_question.question_text = "Old Text"
        mock_question.content = {}
        mock_question.source_citation = "Book"
        mock_question.embedding = [0.1] * 384
        
        user_id = str(uuid4())
        class MockExamObj:
            id = mock_question.exam_id
            created_by = None
        async def mock_get(model, id):
            if model.__name__ == 'Exam': return MockExamObj()
            return None
        mock_db.get = AsyncMock(side_effect=mock_get)
        
        async def mock_execute(stmt, *args, **kwargs):
            stmt_str = str(stmt).lower()
            mock_res = MagicMock()
            if "subjects.created_by" in stmt_str:
                import uuid
                mock_res.scalar_one_or_none.return_value = uuid.UUID(user_id)
            elif "questions.subject_id" in stmt_str and "questions.id" not in stmt_str:
                mock_res.scalar_one_or_none.return_value = mock_question.subject_id
            elif "questions.exam_id" in stmt_str and "questions.id" not in stmt_str:
                mock_res.scalar_one_or_none.return_value = mock_question.exam_id
            elif "sharepermission" in stmt_str:
                mock_res.scalar_one_or_none.return_value = None
            else:
                mock_res.scalar_one_or_none.return_value = mock_question
            return mock_res
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        # Mock new embedding
        new_embedding = [0.9] * 384
        mock_gen_embed.return_value = new_embedding
        
        async def override_get_db():
            yield mock_db
            
        async def override_get_current_user():
            return user_id
            
        app.dependency_overrides[get_db] = override_get_db
        from app.api.deps import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        # Update text
        payload = {
            "question_text": "New Text completely changed"
        }
        
        response = self.client.put(f"/api/v1/questions/{mock_question.id}", json=payload)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify generate_question_embedding was called
        mock_gen_embed.assert_called_once_with("New Text completely changed")
        
        # Verify question object was updated
        self.assertEqual(mock_question.question_text, "New Text completely changed")
        self.assertEqual(mock_question.embedding, new_embedding)
        
        # Verify commit
        mock_db.commit.assert_called_once()
        
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        
    @patch('app.services.generation.deduplicator.generate_question_embedding', new_callable=AsyncMock)
    @patch('app.api.routers.questions.AsyncSession')
    def test_question_update_skips_embedding_if_text_unchanged(self, mock_session_cls, mock_gen_embed):
        mock_db = AsyncMock()
        
        # Setup existing question
        mock_question = MagicMock()
        mock_question.access = None
        mock_question.id = uuid4()
        mock_question.generated_question_id = uuid4()
        mock_question.exam_id = uuid4()
        mock_question.subject_id = uuid4()
        mock_question.folder_id = uuid4()
        mock_question.question_type = "MCQ"
        mock_question.difficulty = "Easy"
        mock_question.marks = 1
        mock_question.question_text = "Old Text"
        mock_question.content = {}
        mock_question.source_citation = "Book"
        mock_question.embedding = [0.1] * 384
        
        user_id = str(uuid4())
        class MockExamObj:
            id = mock_question.exam_id
            created_by = None
        async def mock_get(model, id):
            if model.__name__ == 'Exam': return MockExamObj()
            return None
        mock_db.get = AsyncMock(side_effect=mock_get)
        
        async def mock_execute(stmt, *args, **kwargs):
            stmt_str = str(stmt).lower()
            mock_res = MagicMock()
            if "subjects.created_by" in stmt_str:
                import uuid
                mock_res.scalar_one_or_none.return_value = uuid.UUID(user_id)
            elif "questions.subject_id" in stmt_str and "questions.id" not in stmt_str:
                mock_res.scalar_one_or_none.return_value = mock_question.subject_id
            elif "questions.exam_id" in stmt_str and "questions.id" not in stmt_str:
                mock_res.scalar_one_or_none.return_value = mock_question.exam_id
            elif "sharepermission" in stmt_str:
                mock_res.scalar_one_or_none.return_value = None
            else:
                mock_res.scalar_one_or_none.return_value = mock_question
            return mock_res
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        async def override_get_db():
            yield mock_db
            
        async def override_get_current_user():
            return user_id
            
        app.dependency_overrides[get_db] = override_get_db
        from app.api.deps import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        # Update just difficulty
        payload = {
            "difficulty": "Hard"
        }
        
        response = self.client.put(f"/api/v1/questions/{mock_question.id}", json=payload)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify embedding was NOT regenerated
        mock_gen_embed.assert_not_called()
        self.assertEqual(mock_question.difficulty, "Hard")
        
        mock_db.commit.assert_called_once()
        
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

if __name__ == '__main__':
    unittest.main()




