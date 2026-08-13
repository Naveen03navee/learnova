import unittest
import sys
import os
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.core.database import get_db
from app.models.sharing import SharePermission, SharePermissionLevel
from app.api.deps import get_current_user

class TestAuthorizationAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_db = AsyncMock()
        
        def mock_add(obj):
            if hasattr(obj, 'id') and getattr(obj, 'id', None) is None:
                obj.id = uuid4()
                
        self.mock_db.add.side_effect = mock_add
        
        async def override_get_db():
            yield self.mock_db
            
        app.dependency_overrides[get_db] = override_get_db

    def tearDown(self):
        app.dependency_overrides = {}

    def test_idor_exam_access_denied(self):
        # We mock the get_current_user to return a specific ID
        user_2_id = str(uuid4())
        
        async def override_get_current_user():
            return user_2_id
            
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        # We mock db.execute to return an empty list for exams (because the user owns none)
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = []
        self.mock_db.execute.return_value = mock_result
        
        response = self.client.get("/api/v1/exams")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_shared_exam_access_granted(self):
        user_2_id = str(uuid4())
        
        async def override_get_current_user():
            return user_2_id
            
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        # We mock the exam result to return a shared exam
        class MockExam:
            def __init__(self):
                self.id = uuid4()
                self.name = "Shared Exam"
                self.exam_type = "Competitive"
                self.description = "Test"
                self.is_college = False
                from datetime import datetime
                self.created_at = datetime.utcnow()
                self.updated_at = datetime.utcnow()
                
        mock_exam = MockExam()
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = [mock_exam]
        
        # We also need to mock get_entity_access call which is inside the endpoint
        with patch('app.api.routers.exams.get_entity_access', new_callable=AsyncMock) as mock_get_access:
            mock_get_access.return_value = {"level": "VIEW", "is_shared": True, "is_global": False}
            self.mock_db.execute.return_value = mock_result
            
            response = self.client.get("/api/v1/exams")
            self.assertEqual(response.status_code, 200)
            exams = response.json()
            self.assertEqual(len(exams), 1)
            self.assertEqual(exams[0]["access"]["level"], "VIEW")
            self.assertEqual(exams[0]["access"]["is_shared"], True)

    def test_revoke_share_access_denied_not_owner(self):
        user_id = str(uuid4())
        
        async def override_get_current_user():
            return user_id
            
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        # Mock share lookup to return a share owned by someone else
        class MockShare:
            def __init__(self):
                self.id = uuid4()
                self.entity_type = "exam"
                self.entity_id = uuid4()
                
        mock_share = MockShare()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_share
        
        # Mock require_owner_access to raise HTTPException (403)
        with patch('app.api.routers.shares.require_owner_access', new_callable=AsyncMock) as mock_require_owner:
            from fastapi import HTTPException
            mock_require_owner.side_effect = HTTPException(status_code=403, detail="Not authorized")
            
            self.mock_db.execute.return_value = mock_result
            
            response = self.client.delete(f"/api/v1/shares/{mock_share.id}")
            self.assertEqual(response.status_code, 403)

if __name__ == '__main__':
    unittest.main()




