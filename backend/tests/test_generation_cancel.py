import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.generation import GenerationSession, GenerationStatus
from app.models.sharing import SharePermissionLevel
from app.services.generation.orchestrator import _cancelled_sessions

MOCK_SESSION_ID = uuid4()
MOCK_EXAM_ID = uuid4()
MOCK_SUBJECT_ID = uuid4()
MOCK_OWNER_ID = uuid4()
MOCK_UNRELATED_USER_ID = uuid4()

def get_mock_session(status=GenerationStatus.PENDING):
    return GenerationSession(
        id=MOCK_SESSION_ID,
        exam_id=MOCK_EXAM_ID,
        subject_id=MOCK_SUBJECT_ID,
        folder_id=uuid4(),
        topic="Math",
        question_type="multiple_choice",
        difficulty="medium",
        marks=1,
        requested_count=5,
        status=status
    )

@pytest.fixture(autouse=True)
def setup_teardown():
    _cancelled_sessions.clear()
    app.dependency_overrides.clear()
    yield
    _cancelled_sessions.clear()
    app.dependency_overrides.clear()

def override_get_current_user(user_id):
    def _override():
        return str(user_id)
    return _override

def test_cancel_generation_owner():
    app.dependency_overrides[get_current_user] = override_get_current_user(MOCK_OWNER_ID)
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = get_mock_session()
    mock_db.execute.return_value = mock_result
    
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    with patch("app.core.authorization.require_edit_access", new_callable=AsyncMock) as mock_require_edit:
        mock_require_edit.return_value = True
        
        client = TestClient(app)
        response = client.post(
            f"/api/v1/generation/{MOCK_SESSION_ID}/cancel"
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert MOCK_SESSION_ID in _cancelled_sessions

def test_cancel_generation_already_completed():
    app.dependency_overrides[get_current_user] = override_get_current_user(MOCK_OWNER_ID)
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = get_mock_session(status=GenerationStatus.COMPLETED)
    mock_db.execute.return_value = mock_result
    
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    with patch("app.core.authorization.require_edit_access", new_callable=AsyncMock) as mock_require_edit:
        mock_require_edit.return_value = True
        
        client = TestClient(app)
        response = client.post(
            f"/api/v1/generation/{MOCK_SESSION_ID}/cancel"
        )
        
        assert response.status_code == 409
        assert "already completed" in response.json()["detail"]
        assert MOCK_SESSION_ID not in _cancelled_sessions

def test_cancel_generation_unauthorized():
    app.dependency_overrides[get_current_user] = override_get_current_user(MOCK_UNRELATED_USER_ID)
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = get_mock_session()
    mock_db.execute.return_value = mock_result
    
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    from fastapi import HTTPException
    with patch("app.core.authorization.require_edit_access", new_callable=AsyncMock) as mock_require_edit:
        mock_require_edit.side_effect = HTTPException(status_code=403, detail="Not authorized")
        
        client = TestClient(app)
        response = client.post(
            f"/api/v1/generation/{MOCK_SESSION_ID}/cancel"
        )
        
        assert response.status_code == 403
        assert MOCK_SESSION_ID not in _cancelled_sessions

def test_cancel_generation_not_found():
    app.dependency_overrides[get_current_user] = override_get_current_user(MOCK_OWNER_ID)
    
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    response = client.post(
        f"/api/v1/generation/{MOCK_SESSION_ID}/cancel"
    )
    
    assert response.status_code == 404
    assert MOCK_SESSION_ID not in _cancelled_sessions
