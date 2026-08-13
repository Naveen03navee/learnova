"""
Tests for DELETE /api/v1/subjects/{subject_id}/resources

Cases verified:
  Zero resources          → 200, {"deleted": 0}
  One resource            → 200, {"deleted": 1}
  Multiple resources      → 200, {"deleted": N}
  Unauthorized teacher    → 403
  VIEW-only shared        → 403
  Owner deletion          → 200
"""
import unittest
import sys
import os
from uuid import uuid4, UUID

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('SUPABASE_URL', 'http://localhost')
os.environ.setdefault('SUPABASE_ANON_KEY', 'anon')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'service')
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://fake:fake@localhost/fake')

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.sharing import SharePermissionLevel


def _make_scalar(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


class TestBulkResourceDelete(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.mock_db = AsyncMock()
        self.mock_db.add = MagicMock()

        async def override_get_db():
            yield self.mock_db

        app.dependency_overrides[get_db] = override_get_db

    def tearDown(self):
        app.dependency_overrides = {}

    def _setup_user(self, user_id: str):
        async def override_get_current_user():
            return user_id
        app.dependency_overrides[get_current_user] = override_get_current_user

    def _wire_subject_auth(self, subject_id, owner_id, share_permission=None, rowcount=0):
        """
        Wires the mock DB for the bulk-delete endpoint:
          1. db.get(Subject, subject_id)           — for the existence check
          2. get_entity_exam_id(subject)            — returns exam_id
          3. db.get(Exam, exam_id)                  — exam object
          4. get_entity_owner_id(subject)           — returns owner_id
          5. share lookup                           — returns share or None
          6. bulk DELETE execution                  — rowcount
        """
        from types import SimpleNamespace

        exam_id = uuid4()
        mock_exam = SimpleNamespace(id=exam_id, created_by=uuid4())  # private exam
        mock_subject = SimpleNamespace(
            id=subject_id,
            exam_id=exam_id,
            created_by=owner_id,
            name="Physics",
            normalized_name="physics"
        )

        async def mock_db_get(model, ident):
            name = getattr(model, '__name__', str(model))
            if 'Exam' in name:
                return mock_exam
            if 'Subject' in name:
                return mock_subject
            return None

        self.mock_db.get = AsyncMock(side_effect=mock_db_get)

        share_obj = None
        if share_permission is not None:
            share_obj = SimpleNamespace(
                id=uuid4(),
                permission=share_permission
            )

        # Mock the bulk DELETE result with the specified rowcount
        bulk_delete_result = MagicMock()
        bulk_delete_result.rowcount = rowcount

        async def execute_side_effect(stmt, *args, **kwargs):
            stmt_str = str(stmt).lower()
            # get_entity_exam_id for subject: SELECT subjects.exam_id WHERE subjects.id = ?
            if 'exam_id' in stmt_str and 'subject' in stmt_str:
                return _make_scalar(exam_id)
            # get_entity_owner_id: SELECT subjects.created_by WHERE subjects.id = ?
            if 'created_by' in stmt_str and 'subject' in stmt_str:
                return _make_scalar(owner_id)
            # share lookup
            if 'sharepermission' in stmt_str or 'share_permission' in stmt_str:
                return _make_scalar(share_obj)
            # bulk DELETE statement
            if 'delete' in stmt_str and 'resource' in stmt_str:
                return bulk_delete_result
            return _make_scalar(None)

        self.mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    # ------------------------------------------------------------------
    # Case 1: Owner deletes — zero resources
    # ------------------------------------------------------------------
    def test_owner_delete_zero_resources(self):
        owner_id = uuid4()
        subject_id = uuid4()
        self._setup_user(str(owner_id))
        self._wire_subject_auth(subject_id, owner_id=owner_id, rowcount=0)

        response = self.client.delete(f"/api/v1/subjects/{subject_id}/resources")
        self.assertEqual(response.status_code, 200,
                         f"Expected 200, got {response.status_code}: {response.text}")
        self.assertEqual(response.json()["deleted"], 0)

    # ------------------------------------------------------------------
    # Case 2: Owner deletes — one resource
    # ------------------------------------------------------------------
    def test_owner_delete_one_resource(self):
        owner_id = uuid4()
        subject_id = uuid4()
        self._setup_user(str(owner_id))
        self._wire_subject_auth(subject_id, owner_id=owner_id, rowcount=1)

        response = self.client.delete(f"/api/v1/subjects/{subject_id}/resources")
        self.assertEqual(response.status_code, 200,
                         f"Expected 200, got {response.status_code}: {response.text}")
        self.assertEqual(response.json()["deleted"], 1)

    # ------------------------------------------------------------------
    # Case 3: Owner deletes — multiple resources
    # ------------------------------------------------------------------
    def test_owner_delete_multiple_resources(self):
        owner_id = uuid4()
        subject_id = uuid4()
        self._setup_user(str(owner_id))
        self._wire_subject_auth(subject_id, owner_id=owner_id, rowcount=7)

        response = self.client.delete(f"/api/v1/subjects/{subject_id}/resources")
        self.assertEqual(response.status_code, 200,
                         f"Expected 200, got {response.status_code}: {response.text}")
        self.assertEqual(response.json()["deleted"], 7)

    # ------------------------------------------------------------------
    # Case 4: Unauthorized teacher (no share at all) → 403
    # ------------------------------------------------------------------
    def test_unauthorized_teacher_cannot_bulk_delete(self):
        owner_id = uuid4()
        stranger_id = uuid4()
        subject_id = uuid4()

        self._setup_user(str(stranger_id))
        self._wire_subject_auth(subject_id, owner_id=owner_id, share_permission=None, rowcount=0)

        response = self.client.delete(f"/api/v1/subjects/{subject_id}/resources")
        self.assertEqual(response.status_code, 403,
                         f"Stranger must get 403, got {response.status_code}: {response.text}")

    # ------------------------------------------------------------------
    # Case 5: VIEW-only shared teacher → 403
    # ------------------------------------------------------------------
    def test_view_shared_teacher_cannot_bulk_delete(self):
        owner_id = uuid4()
        viewer_id = uuid4()
        subject_id = uuid4()

        self._setup_user(str(viewer_id))
        self._wire_subject_auth(
            subject_id, owner_id=owner_id,
            share_permission=SharePermissionLevel.VIEW,
            rowcount=0
        )

        response = self.client.delete(f"/api/v1/subjects/{subject_id}/resources")
        self.assertEqual(response.status_code, 403,
                         f"VIEW-only shared user must get 403, got {response.status_code}: {response.text}")

    # ------------------------------------------------------------------
    # Case 6: EDIT-shared teacher → 200 (per approved access model)
    # ------------------------------------------------------------------
    def test_edit_shared_teacher_can_bulk_delete(self):
        owner_id = uuid4()
        edit_user_id = uuid4()
        subject_id = uuid4()

        self._setup_user(str(edit_user_id))
        self._wire_subject_auth(
            subject_id, owner_id=owner_id,
            share_permission=SharePermissionLevel.EDIT,
            rowcount=3
        )

        response = self.client.delete(f"/api/v1/subjects/{subject_id}/resources")
        self.assertEqual(response.status_code, 200,
                         f"EDIT-shared teacher should get 200, got {response.status_code}: {response.text}")
        self.assertEqual(response.json()["deleted"], 3)

    # ------------------------------------------------------------------
    # Case 7: Subject not found → 404
    # ------------------------------------------------------------------
    def test_bulk_delete_missing_subject_returns_404(self):
        user_id = uuid4()
        missing_id = uuid4()
        self._setup_user(str(user_id))

        self.mock_db.get = AsyncMock(return_value=None)
        self.mock_db.execute = AsyncMock(return_value=_make_scalar(None))

        response = self.client.delete(f"/api/v1/subjects/{missing_id}/resources")
        self.assertEqual(response.status_code, 404,
                         f"Missing subject must return 404, got {response.status_code}: {response.text}")


if __name__ == '__main__':
    unittest.main()
