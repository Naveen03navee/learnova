import unittest
import sys
import os
import asyncio
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from app.api.routers import rag
from app.core.database import get_db
from app.api.deps import get_current_user

app = FastAPI()
app.include_router(rag.router)

class TestRAGIsolation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.exam_id = uuid4()
        self.subject_id = uuid4()
        self.folder_id = uuid4()
        self.other_exam_id = uuid4()
        self.other_subject_id = uuid4()

    @patch('app.services.rag.retriever.embedder.encode')
    def test_rag_hierarchy_validation_fails_on_mismatch(self, mock_encode):
        # We want to test that validate_hierarchy fails when Subject doesn't belong to Exam
        mock_encode.return_value = [[0.1] * 384]
        
        mock_db = AsyncMock()
        
        # When querying WorkspaceExam, we return an exam.
        # When querying WorkspaceSubject, we return None to simulate it not belonging to the Exam.
        def mock_execute(query):
            mock_res = MagicMock()
            query_str = str(query).lower()
            if "exam" in query_str and "subject" not in query_str and "folder" not in query_str:
                mock_exam = MagicMock()
                mock_res.scalar_one_or_none.return_value = mock_exam
            elif "subject" in query_str and "folder" not in query_str:
                mock_res.scalar_one_or_none.return_value = None
            return mock_res
            
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        async def override_get_db(): yield mock_db
        async def override_get_current_user(): return str(uuid4())
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        response = self.client.post(
            "/api/v1/retrieval/search",
            json={
                "query": "test query",
                "exam_id": str(self.exam_id),
                "subject_id": str(self.other_subject_id), # Mismatched subject
                "top_k": 5
            }
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("does not belong to Exam", response.json()["detail"])
        
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    @patch('app.services.rag.retriever.embedder.encode')
    def test_rag_retrieval_success(self, mock_encode):
        mock_encode.return_value = [[0.1] * 384]
        
        mock_db = AsyncMock()
        
        # Mock hierarchy validation passing
        def mock_execute(query):
            mock_res = MagicMock()
            # For hierarchy, just return a mock object
            query_str = str(query).lower()
            if "document_chunk" in query_str:
                # Return final query result
                mock_row = MagicMock()
                mock_row.chunk_id = uuid4()
                mock_row.resource_id = uuid4()
                mock_row.resource_name = "test.pdf"
                mock_row.folder_id = None
                mock_row.page_number = 1
                mock_row.chunk_index = 0
                mock_row.content = "Test content"
                mock_row.distance = 0.05
                mock_res.all.return_value = [mock_row]
            else:
                mock_res.scalar_one_or_none.return_value = MagicMock()
            return mock_res
            
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        async def override_get_db(): yield mock_db
        async def override_get_current_user(): return str(uuid4())
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        response = self.client.post(
            "/api/v1/retrieval/search",
            json={
                "query": "test query",
                "exam_id": str(self.exam_id),
                "subject_id": str(self.subject_id),
                "top_k": 5
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_results"], 1)
        self.assertEqual(data["results"][0]["content"], "Test content")
        self.assertEqual(data["results"][0]["similarity"], 0.95)
        
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

if __name__ == '__main__':
    unittest.main()




