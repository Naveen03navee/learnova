import unittest
import sys
import os
import io
import asyncio
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from app.main import app
from app.core.database import get_db
from app.models.pattern import ExamPattern, PatternStatus

class TestPatternsAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.exam_id = uuid4()
        self.subject_id = uuid4()
        self.user_id = uuid4()
        self.mock_db = AsyncMock()
        
        def mock_add(obj):
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = uuid4()
            if hasattr(obj, 'created_at') and obj.created_at is None:
                from datetime import datetime
                obj.created_at = datetime.utcnow()
            if hasattr(obj, 'updated_at') and obj.updated_at is None:
                from datetime import datetime
                obj.updated_at = datetime.utcnow()
                
        self.mock_db.add.side_effect = mock_add
        
        async def override_get_db():
            yield self.mock_db
            
        app.dependency_overrides[get_db] = override_get_db
        
        from app.api.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: str(self.user_id)

    def tearDown(self):
        app.dependency_overrides = {}

    @patch('app.api.routers.patterns.upload_file_to_storage')
    @patch('app.api.routers.patterns.BackgroundTasks.add_task')
    def test_pattern_upload_valid(self, mock_add_task, mock_upload):
        exam_id = self.exam_id
        subject_id = self.subject_id
        user_id = self.user_id

        from types import SimpleNamespace
        mock_exam = SimpleNamespace(id=exam_id, created_by=None)
        mock_subject = SimpleNamespace(id=subject_id, exam_id=exam_id, created_by=user_id)

        async def mock_db_get(model, ident):
            name = getattr(model, '__name__', '')
            if name == 'Exam':
                return mock_exam
            if name == 'Subject':
                return mock_subject
            return None

        self.mock_db.get = AsyncMock(side_effect=mock_db_get)

        def make_scalar_result(value):
            r = MagicMock()
            r.scalar_one_or_none.return_value = value
            return r

        async def execute_side_effect(stmt, *args, **kwargs):
            stmt_str = str(stmt).lower()
            # get_entity_exam_id: SELECT subjects.exam_id WHERE subjects.id = ?
            if 'exam_id' in stmt_str and 'subject' in stmt_str:
                return make_scalar_result(exam_id)
            # get_entity_owner_id: SELECT subjects.created_by ...
            if 'created_by' in stmt_str and 'subject' in stmt_str:
                return make_scalar_result(user_id)
            # SharePermission lookup or anything else -> no share record
            return make_scalar_result(None)

        self.mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        files = {"file": ("test.pdf", io.BytesIO(b"Valid PDF"), "application/pdf")}
        data = {"exam_id": str(self.exam_id), "subject_id": str(self.subject_id), "year": "2024"}

        response = self.client.post("/api/v1/patterns/upload", files=files, data=data)

        self.assertEqual(response.status_code, 201)
        res_data = response.json()
        self.assertEqual(res_data["status"], "UPLOADED")
        mock_add_task.assert_called_once()
        mock_upload.assert_called_once()
        
    def test_pattern_upload_empty(self):
        files = {"file": ("test.pdf", io.BytesIO(b""), "application/pdf")}
        data = {"exam_id": str(self.exam_id), "subject_id": str(self.subject_id)}
        
        response = self.client.post("/api/v1/patterns/upload", files=files, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.json()["detail"].lower())
        
    def test_pattern_upload_no_filename(self):
        # FastAPI/Starlette multipart validation rejects empty filename with 422
        # before the router body executes (router would return 400).
        # Both are valid rejections of an invalid request.
        files = {"file": ("", io.BytesIO(b"Data"), "application/pdf")}
        data = {"exam_id": str(self.exam_id), "subject_id": str(self.subject_id)}

        response = self.client.post("/api/v1/patterns/upload", files=files, data=data)
        self.assertIn(response.status_code, (400, 422))

class TestPatternAnalysisService(unittest.TestCase):
    def test_analysis_math_inconsistency(self):
        from app.services.pattern_analysis import validate_math

        # Section says 60 qs x 2 marks/q = 120, but total_marks field = 60.
        # validate_math must detect this inconsistency and return False.
        parsed_output = type('PatternAnalysisData', (), {
            'exam': 'KCET',
            'subject': 'Physics',
            'total_marks': 60,
            'question_count': 60,
            'sections': [
                type('Section', (), {'question_count': 60, 'marks_per_question': 2, 'total_marks': 60})
            ],
            'difficulty_distribution': {'easy': 0.3, 'medium': 0.5, 'hard': 0.2},
            'topic_weight': {'Thermodynamics': 1.0}
        })()

        self.assertFalse(validate_math(parsed_output))

    def test_analysis_math_valid(self):
        from app.services.pattern_analysis import validate_math
        parsed_output = type('PatternAnalysisData', (), {
            'exam': 'KCET',
            'subject': 'Physics',
            'total_marks': 60,
            'question_count': 60,
            'sections': [
                type('Section', (), {'question_count': 60, 'marks_per_question': 1, 'total_marks': 60})
            ],
            'difficulty_distribution': {'easy': 0.3, 'medium': 0.5, 'hard': 0.2},
            'topic_weight': {'Thermodynamics': 1.0}
        })()
        
        self.assertTrue(validate_math(parsed_output))

if __name__ == '__main__':
    unittest.main()




