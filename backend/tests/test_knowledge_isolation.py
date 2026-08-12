import unittest
import sys
import os
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from app.api.routers import folders
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.knowledge import Folder

app = FastAPI()
app.include_router(folders.router)

class TestKnowledgeIsolation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        
    def test_breadcrumb_path_isolation(self):
        exam_id = uuid4()
        subject_id = uuid4()
        
        # Corrupt parent
        exam_2 = uuid4()
        
        child_folder = Folder(id=uuid4(), name="child", normalized_name="child", exam_id=exam_id, subject_id=subject_id, parent_id=uuid4())
        parent_folder = Folder(id=child_folder.parent_id, name="parent", normalized_name="parent", exam_id=exam_2, subject_id=subject_id)
        
        mock_db = AsyncMock()
        
        # Mock db.get to return child then parent
        async def mock_get(model, id):
            if id == child_folder.id:
                return child_folder
            elif id == parent_folder.id:
                return parent_folder
            return None
            
        mock_db.get = mock_get
        
        async def override_get_db(): yield mock_db
        async def override_get_current_user(): return str(uuid4())
        
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        response = self.client.get(f"/api/v1/folders/{child_folder.id}/path")
        
        self.assertEqual(response.status_code, 403)
        self.assertIn("Corrupted folder hierarchy context", response.json()["detail"])

