import unittest
import sys
import os
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from app.api.routers import papers
from app.core.database import get_db
from app.models.paper import QuestionPaper, QuestionPaperItem, PaperStatus

app = FastAPI()
app.include_router(papers.router)

class TestPaperApproval(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('app.api.routers.papers.AsyncSession')
    def test_approve_paper_structural_validation_failure(self, mock_session_cls):
        mock_db = AsyncMock()
        
        # Setup Paper that violates structural validation (e.g., missing correct answer in MCQ)
        mock_paper = MagicMock(spec=QuestionPaper)
        mock_paper.access = None
        mock_paper.id = uuid4()
        mock_paper.status = PaperStatus.DRAFT
        mock_paper.config = {
            "sections": [
                {
                    "name": "Section A",
                    "question_type": "MCQ",
                    "difficulty": "Easy",
                    "count": 1,
                    "marks_per_question": 1
                }
            ]
        }
        
        mock_item = MagicMock(spec=QuestionPaperItem)
        mock_item.section_name = "Section A"
        mock_item.marks_override = None
        mock_item.marks_snapshot = 1
        # Invalid MCQ content: wrong correct_answer
        mock_item.content_snapshot = {
            "options": [{"id": "A", "text": "Option A"}, {"id": "B", "text": "Option B"}],
            "correct_answer": "C"
        }
        
        mock_paper.items = [mock_item]
        
        user_id = str(uuid4())
        mock_paper.subject_id = uuid4()
        mock_paper.exam_id = uuid4()
        
        class MockExam:
            id = mock_paper.exam_id
            created_by = None
            
        async def mock_get(model, id):
            if model.__name__ == 'Exam': return MockExam()
            return None
        mock_db.get = AsyncMock(side_effect=mock_get)
        
        async def mock_execute(stmt):
            stmt_str = str(stmt).lower()
            mock_res = MagicMock()
            if "subjects.created_by" in stmt_str:
                import uuid
                mock_res.scalar_one_or_none.return_value = uuid.UUID(user_id)
            elif "question_papers.exam_id" in stmt_str and "question_papers.id" not in stmt_str:
                mock_res.scalar_one_or_none.return_value = mock_paper.exam_id
            elif "sharepermission" in stmt_str:
                mock_res.scalar_one_or_none.return_value = None
            else:
                mock_res.scalar_one_or_none.return_value = mock_paper
            return mock_res
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        async def override_get_db():
            yield mock_db
            
        async def override_get_current_user():
            return user_id
            
        app.dependency_overrides[get_db] = override_get_db
        from app.api.deps import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user
            
        app.dependency_overrides[get_db] = override_get_db
        
        response = self.client.post(f"/api/v1/papers/{mock_paper.id}/approve", json={"override_ai_check": False})
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Structural validation failed", response.json()["detail"]["message"])
        self.assertIn("does not match any option", response.json()["detail"]["errors"][0])
        
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    @patch('app.api.routers.papers.AsyncSession')
    def test_approve_paper_quality_report_stale(self, mock_session_cls):
        mock_db = AsyncMock()
        
        mock_paper = MagicMock(spec=QuestionPaper)
        mock_paper.access = None
        mock_paper.id = uuid4()
        mock_paper.status = PaperStatus.DRAFT
        mock_paper.config = {"sections": []}
        mock_paper.items = []
        mock_paper.quality_report_stale = True # Stale
        
        user_id = str(uuid4())
        mock_paper.subject_id = uuid4()
        mock_paper.exam_id = uuid4()
        
        class MockExam:
            id = mock_paper.exam_id
            created_by = None
            
        async def mock_get(model, id):
            if model.__name__ == 'Exam': return MockExam()
            return None
        mock_db.get = AsyncMock(side_effect=mock_get)
        
        async def mock_execute(stmt):
            stmt_str = str(stmt).lower()
            mock_res = MagicMock()
            if "subjects.created_by" in stmt_str:
                import uuid
                mock_res.scalar_one_or_none.return_value = uuid.UUID(user_id)
            elif "question_papers.exam_id" in stmt_str and "question_papers.id" not in stmt_str:
                mock_res.scalar_one_or_none.return_value = mock_paper.exam_id
            elif "sharepermission" in stmt_str:
                mock_res.scalar_one_or_none.return_value = None
            else:
                mock_res.scalar_one_or_none.return_value = mock_paper
            return mock_res
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        async def override_get_db():
            yield mock_db
            
        async def override_get_current_user():
            return user_id
            
        app.dependency_overrides[get_db] = override_get_db
        from app.api.deps import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user
            
        app.dependency_overrides[get_db] = override_get_db
        
        response = self.client.post(f"/api/v1/papers/{mock_paper.id}/approve", json={"override_ai_check": False})
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "AI Quality Check is stale. Please re-run the check before approving.")
        
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    @patch('app.api.routers.papers.AsyncSession')
    def test_approve_paper_quality_status_fail_without_override(self, mock_session_cls):
        mock_db = AsyncMock()
        
        mock_paper = MagicMock(spec=QuestionPaper)
        mock_paper.access = None
        mock_paper.id = uuid4()
        mock_paper.status = PaperStatus.DRAFT
        mock_paper.config = {"sections": []}
        mock_paper.items = []
        mock_paper.quality_report_stale = False
        mock_paper.quality_status = "FAIL"
        
        user_id = str(uuid4())
        mock_paper.subject_id = uuid4()
        mock_paper.exam_id = uuid4()
        
        class MockExam:
            id = mock_paper.exam_id
            created_by = None
            
        async def mock_get(model, id):
            if model.__name__ == 'Exam': return MockExam()
            return None
        mock_db.get = AsyncMock(side_effect=mock_get)
        
        async def mock_execute(stmt):
            stmt_str = str(stmt).lower()
            mock_res = MagicMock()
            if "subjects.created_by" in stmt_str:
                import uuid
                mock_res.scalar_one_or_none.return_value = uuid.UUID(user_id)
            elif "question_papers.exam_id" in stmt_str and "question_papers.id" not in stmt_str:
                mock_res.scalar_one_or_none.return_value = mock_paper.exam_id
            elif "sharepermission" in stmt_str:
                mock_res.scalar_one_or_none.return_value = None
            else:
                mock_res.scalar_one_or_none.return_value = mock_paper
            return mock_res
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        async def override_get_db():
            yield mock_db
            
        async def override_get_current_user():
            return user_id
            
        app.dependency_overrides[get_db] = override_get_db
        from app.api.deps import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user
            
        app.dependency_overrides[get_db] = override_get_db
        
        response = self.client.post(f"/api/v1/papers/{mock_paper.id}/approve", json={"override_ai_check": False})
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Explicit override required", response.json()["detail"])
        
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    @patch('app.api.routers.papers.AsyncSession')
    def test_approve_paper_quality_status_fail_with_override(self, mock_session_cls):
        mock_db = AsyncMock()
        
        mock_paper = MagicMock(spec=QuestionPaper)
        mock_paper.access = None
        mock_paper.id = uuid4()
        mock_paper.exam_id = uuid4()
        mock_paper.subject_id = uuid4()
        mock_paper.title = "Title"
        mock_paper.status = PaperStatus.DRAFT
        mock_paper.config = {"sections": []}
        mock_paper.items = []
        mock_paper.quality_report_stale = False
        mock_paper.quality_status = "FAIL"
        mock_paper.quality_report = {}
        
        user_id = str(uuid4())
        
        class MockExam:
            id = mock_paper.exam_id
            created_by = None
            
        async def mock_get(model, id):
            if model.__name__ == 'Exam': return MockExam()
            return None
        mock_db.get = AsyncMock(side_effect=mock_get)
        
        def mock_execute(stmt, *args, **kwargs):
            stmt_str = str(stmt).lower()
            mock_res = MagicMock()
            if "subjects.created_by" in stmt_str:
                import uuid
                mock_res.scalar_one_or_none.return_value = uuid.UUID(user_id)
            elif "question_papers.exam_id" in stmt_str and "question_papers.id" not in stmt_str:
                mock_res.scalar_one_or_none.return_value = mock_paper.exam_id
            elif "sharepermission" in stmt_str:
                mock_res.scalar_one_or_none.return_value = None
            else:
                mock_res.scalar_one_or_none.return_value = mock_paper
                mock_res.scalar_one.return_value = mock_paper
            return mock_res
            
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        async def override_get_db():
            yield mock_db
            
        async def override_get_current_user():
            return user_id
            
        app.dependency_overrides[get_db] = override_get_db
        from app.api.deps import get_current_user
        app.dependency_overrides[get_current_user] = override_get_current_user
            
        app.dependency_overrides[get_db] = override_get_db
        
        response = self.client.post(f"/api/v1/papers/{mock_paper.id}/approve", json={"override_ai_check": True})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_paper.status, PaperStatus.APPROVED)
        mock_db.commit.assert_called_once()
        
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

if __name__ == '__main__':
    unittest.main()




