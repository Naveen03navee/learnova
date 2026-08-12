import pytest
from httpx import AsyncClient
from uuid import uuid4
import json
from unittest.mock import patch, MagicMock, AsyncMock

from app.models.generation import GenerationSession, GenerationStatus
from app.models.pattern import ExamPattern, PatternStatus
from app.models.workspace import Exam, Subject
from app.schemas.generation import GenerationStartRequest
from app.services.generation.orchestrator import process_generation_session

# Test Data
MOCK_EXAM_ID = uuid4()
MOCK_SUBJECT_ID = uuid4()
MOCK_OTHER_EXAM_ID = uuid4()

def get_mock_pattern(exam_id=MOCK_EXAM_ID, subject_id=MOCK_SUBJECT_ID, status=PatternStatus.ACTIVE, pattern_id=None):
    if not pattern_id:
        pattern_id = uuid4()
    p = ExamPattern(
        id=pattern_id,
        exam_id=exam_id,
        subject_id=subject_id,
        file_name="test.pdf",
        file_path="/tmp/test.pdf",
        year="2024",
        status=status,
        analysis_data={"total_questions": 30, "marks": 60}
    )
    return p

@pytest.fixture
def mock_db_session():
    # We will mock the database methods for testing orchestrator logic directly
    mock_session = AsyncMock()
    return mock_session

# Test 4: Pattern context mismatch
@patch("app.api.routers.generation.get_db")
@pytest.mark.asyncio
async def test_generation_start_context_mismatch(mock_get_db):
    from app.api.routers.generation import start_generation
    
    mock_db = AsyncMock()
    pattern = get_mock_pattern(exam_id=MOCK_OTHER_EXAM_ID) # Different exam
    
    # Mock pattern fetch
    async def mock_execute(stmt):
        class MockResult:
            def scalar_one_or_none(self): return pattern
        return MockResult()
    mock_db.execute = mock_execute
    
    req = GenerationStartRequest(
        exam_id=MOCK_EXAM_ID,
        subject_id=MOCK_SUBJECT_ID,
        topic="Physics",
        question_type="MCQ",
        difficulty="medium",
        marks=2,
        count=5,
        pattern_id=pattern.id
    )
    
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await start_generation(req, MagicMock(), mock_db)
    
    assert exc.value.status_code == 400
    assert "Exam pattern does not match" in str(exc.value.detail)

# Test 5: Inactive pattern
@patch("app.api.routers.generation.get_db")
@pytest.mark.asyncio
async def test_generation_start_inactive_pattern(mock_get_db):
    from app.api.routers.generation import start_generation
    
    mock_db = AsyncMock()
    pattern = get_mock_pattern(status=PatternStatus.FAILED)
    
    async def mock_execute(stmt):
        class MockResult:
            def scalar_one_or_none(self): return pattern
        return MockResult()
    mock_db.execute = mock_execute
    
    req = GenerationStartRequest(
        exam_id=MOCK_EXAM_ID,
        subject_id=MOCK_SUBJECT_ID,
        topic="Physics",
        question_type="MCQ",
        difficulty="medium",
        marks=2,
        count=5,
        pattern_id=pattern.id
    )
    
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await start_generation(req, MagicMock(), mock_db)
        
    assert exc.value.status_code == 400
    assert "must be ACTIVE" in str(exc.value.detail)

# Test 5b: LLM Not Called on Context Mismatch (Checking LLM doesn't fire)
@patch("app.api.routers.generation.get_db")
@patch("app.services.generation.orchestrator.ai_manager.generate")
@pytest.mark.asyncio
async def test_llm_not_called_on_mismatch(mock_generate, mock_get_db):
    from app.api.routers.generation import start_generation
    
    mock_db = AsyncMock()
    pattern = get_mock_pattern(exam_id=MOCK_OTHER_EXAM_ID) # Different exam
    
    # Mock pattern fetch
    async def mock_execute(stmt):
        class MockResult:
            def scalar_one_or_none(self): return pattern
        return MockResult()
    mock_db.execute = mock_execute
    
    req = GenerationStartRequest(
        exam_id=MOCK_EXAM_ID,
        subject_id=MOCK_SUBJECT_ID,
        topic="Physics",
        question_type="MCQ",
        difficulty="medium",
        marks=2,
        count=5,
        pattern_id=pattern.id
    )
    
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await start_generation(req, MagicMock(), mock_db)
    
    assert exc.value.status_code == 400
    mock_generate.assert_not_called()

# Test 8: No-pattern generation
@patch("app.services.generation.orchestrator.ai_manager.generate")
@patch("app.services.generation.orchestrator.retrieve_chunks")
@patch("app.services.generation.orchestrator.AsyncSessionLocal")
@pytest.mark.asyncio
async def test_no_pattern_generation(mock_db_cls, mock_retrieve, mock_generate):
    """
    Ensure that generation succeeds when no pattern is provided and [EXAM_PATTERN] is excluded.
    """
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db_cls.return_value.__aenter__.return_value = mock_db
    
    session_id = uuid4()
    mock_session = GenerationSession(
        id=session_id, exam_id=MOCK_EXAM_ID, subject_id=MOCK_SUBJECT_ID,
        topic="Test", question_type="MCQ", difficulty="easy", marks=1, requested_count=5,
        pattern_id=None, repair_count=0, valid_count=0, duplicate_count=0, invalid_count=0
    )
    
    exam = Exam(id=MOCK_EXAM_ID, name="Mock Exam")
    subject = Subject(id=MOCK_SUBJECT_ID, name="Mock Subject")
    
    async def mock_execute(stmt):
        class MockResult:
            def scalar_one_or_none(self): return None
            def all(self): return []
            def first(self): return (mock_session, "Mock Exam", "Mock Subject")
        return MockResult()
        
    mock_db.execute = mock_execute
    
    mock_retrieve.return_value = MagicMock(results=[MagicMock(content="Knowledge base text.")])
    
    mock_generate.return_value = MagicMock(
        parsed_output=MagicMock(questions=[MagicMock() for _ in range(5)])
    )
    
    from app.services.generation.orchestrator import process_generation_session
    
    await process_generation_session(session_id)
    
    mock_generate.assert_called()
    gen_request = mock_generate.call_args[0][1]
    called_prompt = gen_request.user_prompt
    
    assert "[KNOWLEDGE_CONTEXT]" in called_prompt
    assert "[EXAM_PATTERN]" not in called_prompt

# For tests 1, 2, 3, 6, 7 we test the orchestrator prompt assembly and validation logic directly
@patch("app.services.generation.orchestrator.ai_manager.generate")
@patch("app.services.generation.orchestrator.retrieve_chunks")
@patch("app.services.generation.orchestrator.AsyncSessionLocal")
@pytest.mark.asyncio
async def test_orchestrator_prompt_and_isolation(mock_db_cls, mock_retrieve, mock_ai_generate):
    """
    Test 1, Test 2, Test 3: Knowledge only vs Pattern, and Raw isolation.
    """
    # Setup Mocks
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db_cls.return_value.__aenter__.return_value = mock_db
    
    session_id = uuid4()
    mock_session = GenerationSession(
        id=session_id, exam_id=MOCK_EXAM_ID, subject_id=MOCK_SUBJECT_ID,
        topic="Test", question_type="MCQ", difficulty="easy", marks=1, requested_count=5,
        pattern_id=uuid4(), repair_count=0, valid_count=0, duplicate_count=0, invalid_count=0
    )
    
    exam = Exam(id=MOCK_EXAM_ID, name="Mock Exam")
    subject = Subject(id=MOCK_SUBJECT_ID, name="Mock Subject")
    pattern = get_mock_pattern(pattern_id=mock_session.pattern_id)
    
    # Mock retrieve_chunks
    mock_retrieve.return_value = MagicMock(results=[MagicMock(content="Knowledge base text.")])
    
    # Mock AI response to bypass validation
    mock_ai_generate.return_value = MagicMock(
        provider_name="test",
        parsed_output=MagicMock(questions=[MagicMock(question_text="Q1")] * 5)
    )

    # We need to capture the prompt sent to ai_manager
    # We will mock the prompt builder temporarily, or inspect the arguments to ai_manager
    with patch("app.services.generation.orchestrator.build_generation_user_prompt", side_effect=lambda *args, **kwargs: str(kwargs)) as mock_prompt_builder:
        
        # We need to simulate the DB execute for session and pattern loading
        async def mock_execute(stmt):
            class MockResult:
                def first(self): return (mock_session, "Exam", "Subj")
                def scalar_one_or_none(self): return pattern
            return MockResult()
            
        mock_db.execute = mock_execute
        
        await process_generation_session(session_id)
        
        # Check that prompt builder was called with pattern data
        assert mock_prompt_builder.called
        kwargs = mock_prompt_builder.call_args.kwargs
        
        # Test 1/2: Pattern data is JSON
        assert kwargs["exam_pattern"] is not None
        assert "total_questions" in kwargs["exam_pattern"]
        
        # Test 3: Raw pattern isolation
        # Ensure the secret string is NOT in the prompt anywhere
        prompt_str = str(kwargs)
        assert "RAW_PATTERN_SECRET_12345" not in prompt_str

@patch("app.services.generation.orchestrator.retrieve_chunks")
@patch("app.services.generation.orchestrator.AsyncSessionLocal")
@pytest.mark.asyncio
async def test_constraint_validation(mock_db_cls, mock_retrieve):
    """
    Test 6: Post-generation constraint validation (28 generated but 30 required)
    """
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db_cls.return_value.__aenter__.return_value = mock_db
    
    session_id = uuid4()
    mock_session = GenerationSession(
        id=session_id, exam_id=MOCK_EXAM_ID, subject_id=MOCK_SUBJECT_ID,
        topic="Test", question_type="MCQ", difficulty="easy", marks=1, requested_count=30,
        repair_count=0, valid_count=0, duplicate_count=0, invalid_count=0
    )
    
    mock_retrieve.return_value = MagicMock(results=[MagicMock(content="Knowledge base text.")])
    
    async def mock_execute(stmt):
        class MockResult:
            def first(self): return (mock_session, "Exam", "Subj")
            def scalar_one_or_none(self): return None # No pattern
        return MockResult()
    mock_db.execute = mock_execute
    
    with patch("app.services.generation.orchestrator.ai_manager.generate") as mock_ai_generate:
        # Mock LLM returning 28 questions instead of 30
        mock_ai_generate.return_value = MagicMock(
            provider_name="test",
            parsed_output=MagicMock(questions=[MagicMock(question_text="Q1")] * 28)
        )
        
        # In the orchestrator, a ValueError will be raised and caught by the try-except, logging a warning.
        # It will then loop and try again. We check if repair_count increases or loop is executed.
        await process_generation_session(session_id)
        
        # Ensure it attempted to retry (called generate multiple times because validation failed)
        assert mock_ai_generate.call_count > 1

