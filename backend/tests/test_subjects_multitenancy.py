import unittest
import sys
import os

# Ensure required env vars exist for Settings during test import
os.environ.setdefault('SUPABASE_URL', 'http://localhost')
os.environ.setdefault('SUPABASE_ANON_KEY', 'anon')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'service')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')

# Avoid creating real SQLAlchemy async engine during test import
from unittest.mock import MagicMock
import sqlalchemy.ext.asyncio as _sa_asyncio
_sa_asyncio.create_async_engine = lambda *a, **k: MagicMock()
# leave async_sessionmaker alone to preserve typing/behaviour
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.core.database import get_db
from app.api.deps import get_current_user


class TestSubjectsMultitenancy(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_db = AsyncMock()

        # Make add a regular function (real AsyncSession.add is sync)
        def mock_add(obj):
            return None
        self.mock_db.add = mock_add

        # make commit an async mock and refresh set attributes when called
        async def mock_commit():
            return None
        async def mock_refresh(obj):
            from datetime import datetime
            if not getattr(obj, 'id', None):
                try:
                    obj.id = uuid4()
                except Exception:
                    pass
            if not getattr(obj, 'created_at', None):
                obj.created_at = datetime.utcnow()
            return None

        self.mock_db.commit = AsyncMock(side_effect=mock_commit)
        self.mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        # Default execute returns no rows
        default_result = MagicMock()
        default_result.scalar_one_or_none.return_value = None
        default_result.scalars.return_value.all.return_value = []
        self.mock_db.execute.return_value = default_result

        async def override_get_db():
            yield self.mock_db

        app.dependency_overrides[get_db] = override_get_db

    def tearDown(self):
        app.dependency_overrides = {}

    def test_teacher_a_create_subject_success(self):
        user_a = str(uuid4())
        exam_id = uuid4()

        async def override_get_current_user():
            return user_a

        app.dependency_overrides[get_current_user] = override_get_current_user

        # Mock exam exists and is global
        class MockExam:
            def __init__(self, id):
                self.id = id
                self.created_by = None

        self.mock_db.get.return_value = MockExam(exam_id)

        # No existing subject for this owner
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result

        payload = {"exam_id": str(exam_id), "name": "Physics"}
        response = self.client.post("/api/v1/subjects", json=payload)
        self.assertEqual(response.status_code, 201)

    def test_teacher_b_create_subject_success(self):
        user_b = str(uuid4())
        exam_id = uuid4()

        async def override_get_current_user():
            return user_b

        app.dependency_overrides[get_current_user] = override_get_current_user

        class MockExam:
            def __init__(self, id):
                self.id = id
                self.created_by = None

        self.mock_db.get.return_value = MockExam(exam_id)

        # No existing subject for this owner
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result

        payload = {"exam_id": str(exam_id), "name": "Physics"}
        response = self.client.post("/api/v1/subjects", json=payload)
        self.assertEqual(response.status_code, 201)

    def test_teacher_duplicate_rejected(self):
        user = str(uuid4())
        exam_id = uuid4()

        async def override_get_current_user():
            return user

        app.dependency_overrides[get_current_user] = override_get_current_user

        class MockExam:
            def __init__(self, id):
                self.id = id
                self.created_by = None

        self.mock_db.get.return_value = MockExam(exam_id)

        # Simulate existing subject for this owner
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = object()
        self.mock_db.execute.return_value = mock_result

        payload = {"exam_id": str(exam_id), "name": "Physics"}
        response = self.client.post("/api/v1/subjects", json=payload)
        self.assertEqual(response.status_code, 409)

    def test_cannot_modify_another_teachers_subject(self):
        user_a = str(uuid4())
        user_b = str(uuid4())
        subj_id = uuid4()

        async def override_get_current_user():
            return user_a

        app.dependency_overrides[get_current_user] = override_get_current_user

        # Subject owned by user_b
        class MockSubject:
            def __init__(self, id, owner):
                self.id = id
                self.created_by = owner
                self.exam_id = uuid4()
                self.name = "Physics"
                self.normalized_name = "physics"
                from datetime import datetime
                self.created_at = datetime.utcnow()

        self.mock_db.get.return_value = MockSubject(subj_id, uuid4())

        payload = {"name": "Physics"}
        response = self.client.put(f"/api/v1/subjects/{subj_id}", json=payload)
        self.assertEqual(response.status_code, 403)

    def test_shared_view_allows_read_but_not_edit(self):
        owner = uuid4()
        viewer = str(uuid4())
        subj_id = uuid4()

        async def override_get_current_user():
            return viewer

        app.dependency_overrides[get_current_user] = override_get_current_user

        class MockSubject:
            def __init__(self, id, owner):
                self.id = id
                self.created_by = owner
                self.exam_id = uuid4()
                self.name = "Physics"
                self.normalized_name = "physics"
                from datetime import datetime
                self.created_at = datetime.utcnow()
        self.mock_db.get.return_value = MockSubject(subj_id, owner)

        # Mock share permission: VIEW only
        mock_share = MagicMock()
        mock_share.permission = "VIEW"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_share
        self.mock_db.execute.return_value = mock_result

        # GET should succeed
        response = self.client.get(f"/api/v1/subjects/{subj_id}")
        self.assertEqual(response.status_code, 200)

        # PUT should be forbidden (VIEW cannot edit)
        payload = {"name": "Physics"}
        response = self.client.put(f"/api/v1/subjects/{subj_id}", json=payload)
        self.assertEqual(response.status_code, 403)


if __name__ == '__main__':
    unittest.main()




