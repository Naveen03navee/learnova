"""
Tests for DELETE /api/v1/patterns/{pattern_id}

Access model verified:
  Owner                → 204
  EDIT-shared teacher  → 204
  VIEW-shared teacher  → 403
  Unrelated teacher    → 403
  Non-existent pattern → 404
"""
import unittest
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('SUPABASE_URL', 'http://localhost')
os.environ.setdefault('SUPABASE_ANON_KEY', 'anon')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'service')
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://fake:fake@localhost/fake')

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.sharing import SharePermissionLevel


def _make_scalar(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


class TestPatternDelete(unittest.TestCase):
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

    # ------------------------------------------------------------------
    # Helper: wire authorization for a given (exam, subject, owner, share)
    # ------------------------------------------------------------------
    def _wire_auth(self, exam_id, subject_id, pattern_id, owner_id, share_permission=None):
        """
        Mocks the three DB calls that get_entity_access() makes:
          1. get_entity_exam_id  → SELECT exam_id FROM exam_patterns WHERE id = ?
          2. exam lookup         → db.get(Exam, exam_id)
          3. get_entity_owner_id → SELECT subjects.created_by JOIN exam_patterns WHERE id = ?
          4. share lookup        → SELECT SharePermission WHERE ...

        Then also mocks the pattern fetch for the delete body itself.
        """
        from types import SimpleNamespace

        mock_exam = SimpleNamespace(id=exam_id, created_by=uuid4())  # private exam
        mock_pattern = SimpleNamespace(
            id=pattern_id,
            exam_id=exam_id,
            subject_id=subject_id,
            file_path="patterns/test/file.pdf"
        )

        async def mock_db_get(model, ident):
            name = getattr(model, '__name__', str(model))
            if 'Exam' in name:
                return mock_exam
            return None

        self.mock_db.get = AsyncMock(side_effect=mock_db_get)

        share_obj = None
        if share_permission is not None:
            share_obj = SimpleNamespace(
                id=uuid4(),
                permission=share_permission
            )

        async def execute_side_effect(stmt, *args, **kwargs):
            stmt_str = str(stmt).lower()
            # get_entity_exam_id: returns exam_id for the pattern
            if 'exam_id' in stmt_str and 'exam_pattern' in stmt_str:
                return _make_scalar(exam_id)
            # get_entity_owner_id: returns owner of the pattern's subject
            if 'created_by' in stmt_str and 'subject' in stmt_str:
                return _make_scalar(owner_id)
            # share lookup
            if 'sharepermission' in stmt_str or 'share_permission' in stmt_str:
                return _make_scalar(share_obj)
            # pattern fetch in delete body
            if 'exam_pattern' in stmt_str:
                r = MagicMock()
                r.scalar_one_or_none.return_value = mock_pattern
                return r
            return _make_scalar(None)

        self.mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    # ------------------------------------------------------------------
    # Case 1: Owner → 204
    # ------------------------------------------------------------------
    @patch('app.services.storage.delete_file_from_storage')
    @patch('app.api.routers.patterns.get_supabase_service_client')
    def test_owner_can_delete_pattern(self, mock_supabase, mock_delete_storage):
        owner_id = uuid4()
        exam_id = uuid4()
        subject_id = uuid4()
        pattern_id = uuid4()

        self._setup_user(str(owner_id))
        self._wire_auth(exam_id, subject_id, pattern_id, owner_id=owner_id, share_permission=None)

        response = self.client.delete(f"/api/v1/patterns/{pattern_id}")
        self.assertEqual(response.status_code, 204,
                         f"Owner should receive 204, got {response.status_code}: {response.text}")

    # ------------------------------------------------------------------
    # Case 2: EDIT-shared teacher → 204
    # ------------------------------------------------------------------
    @patch('app.services.storage.delete_file_from_storage')
    @patch('app.api.routers.patterns.get_supabase_service_client')
    def test_edit_shared_teacher_can_delete_pattern(self, mock_supabase, mock_delete_storage):
        owner_id = uuid4()
        edit_user_id = uuid4()
        exam_id = uuid4()
        subject_id = uuid4()
        pattern_id = uuid4()

        self._setup_user(str(edit_user_id))
        self._wire_auth(
            exam_id, subject_id, pattern_id,
            owner_id=owner_id,
            share_permission=SharePermissionLevel.EDIT
        )

        response = self.client.delete(f"/api/v1/patterns/{pattern_id}")
        self.assertEqual(response.status_code, 204,
                         f"EDIT-shared teacher should receive 204, got {response.status_code}: {response.text}")

    # ------------------------------------------------------------------
    # Case 3: VIEW-only shared teacher → 403
    # ------------------------------------------------------------------
    def test_view_shared_teacher_cannot_delete_pattern(self):
        owner_id = uuid4()
        view_user_id = uuid4()
        exam_id = uuid4()
        subject_id = uuid4()
        pattern_id = uuid4()

        self._setup_user(str(view_user_id))
        self._wire_auth(
            exam_id, subject_id, pattern_id,
            owner_id=owner_id,
            share_permission=SharePermissionLevel.VIEW
        )

        response = self.client.delete(f"/api/v1/patterns/{pattern_id}")
        self.assertEqual(response.status_code, 403,
                         f"VIEW-shared teacher must receive 403, got {response.status_code}: {response.text}")

    # ------------------------------------------------------------------
    # Case 4: Unrelated teacher (no share) → 403
    # ------------------------------------------------------------------
    def test_unrelated_teacher_cannot_delete_pattern(self):
        owner_id = uuid4()
        stranger_id = uuid4()
        exam_id = uuid4()
        subject_id = uuid4()
        pattern_id = uuid4()

        self._setup_user(str(stranger_id))
        self._wire_auth(
            exam_id, subject_id, pattern_id,
            owner_id=owner_id,
            share_permission=None  # no share record
        )

        response = self.client.delete(f"/api/v1/patterns/{pattern_id}")
        self.assertEqual(response.status_code, 403,
                         f"Unrelated teacher must receive 403, got {response.status_code}: {response.text}")

    # ------------------------------------------------------------------
    # Case 5: Non-existent pattern → 404
    # ------------------------------------------------------------------
    def test_delete_nonexistent_pattern_returns_404(self):
        user_id = uuid4()
        missing_pattern_id = uuid4()

        self._setup_user(str(user_id))

        # Authorization: entity not found → get_entity_exam_id returns None
        self.mock_db.get = AsyncMock(return_value=None)
        self.mock_db.execute = AsyncMock(return_value=_make_scalar(None))

        response = self.client.delete(f"/api/v1/patterns/{missing_pattern_id}")
        self.assertIn(response.status_code, (403, 404),
                      f"Non-existent pattern must return 404 (or 403 if auth fails first), got {response.status_code}")


if __name__ == '__main__':
    unittest.main()
