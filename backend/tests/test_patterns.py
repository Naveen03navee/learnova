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
        self.exam_id = str(uuid4())
        self.subject_id = str(uuid4())
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

    def tearDown(self):
        app.dependency_overrides = {}

    @patch('app.api.routers.patterns.aiofiles.open')
    @patch('app.api.routers.patterns.BackgroundTasks.add_task')
    def test_pattern_upload_valid(self, mock_add_task, mock_aiofiles):
        # Setup mock db to say exam and subject exist
        mock_execute = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = True # Exam/Subject exist
        mock_execute.return_value = mock_result
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        mock_aiofiles.return_value.__aenter__.return_value.write = AsyncMock()
        
        files = {"file": ("test.pdf", io.BytesIO(b"Valid PDF"), "application/pdf")}
        data = {"exam_id": self.exam_id, "subject_id": self.subject_id, "year": "2024"}
        
        response = self.client.post("/api/v1/patterns/upload", files=files, data=data)
        
        self.assertEqual(response.status_code, 201)
        res_data = response.json()
        self.assertEqual(res_data["status"], "UPLOADED")
        mock_add_task.assert_called_once()
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        
    def test_pattern_upload_empty(self):
        files = {"file": ("test.pdf", io.BytesIO(b""), "application/pdf")}
        data = {"exam_id": self.exam_id, "subject_id": self.subject_id}
        
        response = self.client.post("/api/v1/patterns/upload", files=files, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.json()["detail"].lower())
        
    def test_pattern_upload_no_filename(self):
        files = {"file": ("", io.BytesIO(b"Data"), "application/pdf")}
        data = {"exam_id": self.exam_id, "subject_id": self.subject_id}
        
        response = self.client.post("/api/v1/patterns/upload", files=files, data=data)
        self.assertEqual(response.status_code, 422)

class TestPatternAnalysisService(unittest.TestCase):
    @patch('app.services.pattern_analysis.asyncio.to_thread')
    @patch('app.services.pattern_analysis.aiofiles.open')
    @patch('app.services.ai.manager.ai_manager.generate')
    def test_analysis_math_inconsistency(self, mock_generate, mock_open, mock_to_thread):
        mock_open.return_value.__aenter__.return_value.read = AsyncMock(return_value=b"PDF bytes")
        
        mock_to_thread.return_value = asyncio.Future()
        mock_to_thread.return_value.set_result(("Text", False))
        
        class MockParsed:
            def __init__(self):
                self.parsed_output = type('PatternAnalysisData', (), {
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
        
        mock_generate.return_value = asyncio.Future()
        mock_generate.return_value.set_result(MockParsed())
        
        from app.services.pattern_analysis import analyze_pattern, validate_math
        
        # 60 qs * 2 marks = 120, but total_marks = 60. Should fail math.
        self.assertFalse(validate_math(MockParsed().parsed_output))

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
