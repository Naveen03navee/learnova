import unittest
import sys
import os
import io
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from app.api.routers import resources
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.knowledge import Resource
from app.models.workspace import Subject

app = FastAPI()
app.include_router(resources.router)

class TestUploadValidation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.exam_id = uuid4()
        self.subject_id = uuid4()

    def _mock_db_with_subject(self):
        mock_db = AsyncMock()
        mock_subject = MagicMock(spec=Subject)
        mock_subject.exam_id = self.exam_id
        mock_db.get.return_value = mock_subject
        return mock_db

    @patch('app.api.deps.get_current_user')
    def test_upload_empty_filename(self, mock_get_user):
        mock_get_user.return_value = str(uuid4())
        mock_db = self._mock_db_with_subject()
        
        async def override_get_db(): yield mock_db
        async def override_get_current_user(): return str(uuid4())
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        # Upload an empty filename
        response = self.client.post(
            "/api/v1/resources",
            data={"exam_id": str(self.exam_id), "subject_id": str(self.subject_id)},
            files={"file": ("", b"Some content", "text/plain")}
        )
        
        self.assertIn(response.status_code, [400, 422])
        if response.status_code == 400:
            self.assertIn("Empty filename", response.json()["detail"])
        app.dependency_overrides.pop(get_db, None)

    @patch('app.api.deps.get_current_user')
    def test_upload_unsupported_file_type(self, mock_get_user):
        mock_get_user.return_value = str(uuid4())
        mock_db = self._mock_db_with_subject()
        
        async def override_get_db(): yield mock_db
        async def override_get_current_user(): return str(uuid4())
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        response = self.client.post(
            "/api/v1/resources",
            data={"exam_id": str(self.exam_id), "subject_id": str(self.subject_id)},
            files={"file": ("test.exe", b"executable content", "application/x-msdownload")}
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file type", response.json()["detail"])
        app.dependency_overrides.pop(get_db, None)

    @patch('app.api.deps.get_current_user')
    def test_upload_empty_file_content(self, mock_get_user):
        mock_get_user.return_value = str(uuid4())
        mock_db = self._mock_db_with_subject()
        
        async def override_get_db(): yield mock_db
        async def override_get_current_user(): return str(uuid4())
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        response = self.client.post(
            "/api/v1/resources",
            data={"exam_id": str(self.exam_id), "subject_id": str(self.subject_id)},
            files={"file": ("test.txt", b"", "text/plain")}
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("File is empty", response.json()["detail"])
        app.dependency_overrides.pop(get_db, None)

    @patch('app.api.deps.get_current_user')
    @patch('app.api.routers.resources.settings')
    def test_upload_file_too_large(self, mock_settings, mock_get_user):
        mock_settings.MAX_RESOURCE_FILE_SIZE_MB = 1 # 1 MB limit
        mock_get_user.return_value = str(uuid4())
        mock_db = self._mock_db_with_subject()
        
        async def override_get_db(): yield mock_db
        async def override_get_current_user(): return str(uuid4())
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        large_content = b"0" * (1 * 1024 * 1024 + 1) # 1 byte over 1MB
        
        response = self.client.post(
            "/api/v1/resources",
            data={"exam_id": str(self.exam_id), "subject_id": str(self.subject_id)},
            files={"file": ("large.txt", large_content, "text/plain")}
        )
        
        self.assertEqual(response.status_code, 413)
        self.assertIn("File exceeds maximum size", response.json()["detail"])
        app.dependency_overrides.pop(get_db, None)

if __name__ == '__main__':
    unittest.main()




