import unittest
import sys
import os
import asyncio
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from app.api.routers import generation
from app.core.database import get_db
from app.models.generation import GeneratedQuestion, ApprovalStatus, GenerationSession
from app.models.question import Question

app = FastAPI()
app.include_router(generation.router)

class TestQuestionApprovalTransaction(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('app.api.routers.generation.AsyncSession')
    def test_approval_transaction_rollback_on_failure(self, mock_session_cls):
        # We will override get_db to return a mock session that fails on commit
        mock_db = AsyncMock()
        
        # Setup mock data for the query
        # result = await db.execute(...) -> row
        mock_result = MagicMock()
        mock_gen_question = MagicMock()
        mock_gen_question.id = uuid4()
        mock_gen_question.approval_status = ApprovalStatus.PENDING
        mock_gen_question.question_text = "Test Question"
        mock_gen_question.content = {}
        mock_gen_question.source_resource_ids = []
        mock_gen_question.source_chunk_ids = []
        mock_gen_question.embedding = [0.1] * 384
        
        mock_session = MagicMock()
        mock_session.id = uuid4()
        mock_session.exam_id = uuid4()
        mock_session.subject_id = uuid4()
        mock_session.folder_id = uuid4()
        mock_session.question_type = "MCQ"
        mock_session.difficulty = "Easy"
        mock_session.marks = 1
        
        user_id = str(uuid4())
        mock_exam = MagicMock()
        mock_exam.id = mock_session.exam_id
        mock_result.first.return_value = (mock_gen_question, mock_session, mock_exam)
        
        class MockExamObj:
            id = mock_session.exam_id
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
            elif "select subject.exam_id" in stmt_str:
                mock_res.scalar_one_or_none.return_value = mock_session.exam_id
            elif "sharepermission" in stmt_str:
                mock_res.scalar_one_or_none.return_value = None
            else:
                return mock_result
            return mock_res
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        # Make db.commit raise an exception to trigger the rollback
        mock_db.commit.side_effect = Exception("DB Connection Lost")
        
        async def override_get_db():
            yield mock_db
            
        async def override_get_current_user():
            return user_id
            
        app.dependency_overrides[get_db] = override_get_db
        from app.api.deps import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        response = self.client.post(f"/api/v1/generation/questions/{mock_gen_question.id}/approve")
        
        # Verify 500 status code
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to approve question: DB Connection Lost", response.json()["detail"])
        
        # Verify rollback was called
        mock_db.rollback.assert_called_once()
        
        # Clean up
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    @patch('app.api.routers.generation.AsyncSession')
    def test_approval_transaction_success(self, mock_session_cls):
        mock_db = AsyncMock()
        
        mock_result = MagicMock()
        mock_gen_question = MagicMock()
        mock_gen_question.id = uuid4()
        mock_gen_question.approval_status = ApprovalStatus.PENDING
        mock_gen_question.question_text = "Test Question"
        mock_gen_question.content = {}
        mock_gen_question.source_resource_ids = []
        mock_gen_question.source_chunk_ids = []
        mock_gen_question.embedding = [0.1] * 384
        
        mock_session = MagicMock()
        mock_session.id = uuid4()
        mock_session.exam_id = uuid4()
        mock_session.subject_id = uuid4()
        mock_session.folder_id = uuid4()
        mock_session.question_type = "MCQ"
        mock_session.difficulty = "Easy"
        mock_session.marks = 1
        
        user_id = str(uuid4())
        mock_exam = MagicMock()
        mock_exam.id = mock_session.exam_id
        mock_result.first.return_value = (mock_gen_question, mock_session, mock_exam)
        
        class MockExamObj:
            id = mock_session.exam_id
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
            elif "select subject.exam_id" in stmt_str:
                mock_res.scalar_one_or_none.return_value = mock_session.exam_id
            elif "sharepermission" in stmt_str:
                mock_res.scalar_one_or_none.return_value = None
            else:
                return mock_result
            return mock_res
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        # commit succeeds
        mock_db.commit.return_value = None
        
        async def override_get_db():
            yield mock_db
            
        async def override_get_current_user():
            return user_id
            
        app.dependency_overrides[get_db] = override_get_db
        from app.api.deps import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        response = self.client.post(f"/api/v1/generation/questions/{mock_gen_question.id}/approve")
        
        # Verify 200 status code
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        
        # Verify commit was called, and status was changed
        mock_db.commit.assert_called_once()
        self.assertEqual(mock_gen_question.approval_status, ApprovalStatus.APPROVED)
        mock_db.add.assert_called_once()
        
        added_obj = mock_db.add.call_args[0][0]
        self.assertIsInstance(added_obj, Question)
        self.assertEqual(added_obj.generated_question_id, mock_gen_question.id)
        
        # Clean up
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

if __name__ == '__main__':
    unittest.main()




