import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock

from app.models.generation import GenerationSession, GenerationStatus
from app.services.generation.orchestrator import process_generation_session

@pytest.mark.asyncio
@pytest.mark.parametrize("req_count", [5, 10, 20, 40])
@patch('app.services.generation.orchestrator.settings.GENERATION_MAX_TOTAL_LLM_CALLS', 100)
@patch('app.services.generation.orchestrator.generate_question_embedding')
@patch('app.services.generation.orchestrator.retrieve_chunks')
@patch('app.services.generation.orchestrator.build_bounded_context')
@patch('app.services.generation.orchestrator.ai_manager')
@patch('app.services.generation.orchestrator.validate_question_logic')
@patch('app.services.generation.orchestrator.check_duplicate')
@patch('app.services.generation.orchestrator.AsyncSessionLocal')
@patch('app.services.generation.orchestrator._publish_event')
async def test_requested_count_is_preserved_through_generation(
    mock_publish, mock_db, mock_duplicate, mock_validate, mock_ai, mock_context, mock_retrieve, mock_embedding, req_count
):
    import random
    def mock_embedding_side_effect(*args, **kwargs):
        return [random.random() for _ in range(768)]
    mock_embedding.side_effect = mock_embedding_side_effect
    session_id = uuid4()
    
    # Setup mocks
    mock_db_instance = AsyncMock()
    mock_db.return_value.__aenter__.return_value = mock_db_instance
    
    db_session_obj = GenerationSession(
        id=session_id,
        exam_id=uuid4(),
        subject_id=uuid4(),
        folder_id=uuid4(),
        requested_count=req_count,
        topic="Test",
        difficulty="Easy",
        question_type="MCQ",
        status=GenerationStatus.PENDING,
        invalid_count=0,
        valid_count=0,
        repair_count=0,
        duplicate_count=0
    )
    
    # Mock the query result to return our session
    mock_result = MagicMock()
    mock_result.first.return_value = (db_session_obj, "Exam", "Subject")
    mock_db_instance.execute.return_value = mock_result
    
    mock_retrieve.return_value = MagicMock(results=["chunk1"])
    mock_context.return_value = ("context", {"source1": {"resource_id": uuid4(), "chunk_id": uuid4()}})
    
    # Simulate a scenario where 2 questions are invalid on first pass, so repair loop runs
    # AI returns the batch size.
    async def mock_ai_generate(*args, **kwargs):
        import re
        gen_req = args[1]
        match = re.search(r"Number of questions: (\d+)", gen_req.user_prompt)
        count = int(match.group(1)) if match else 5
        res = MagicMock()
        parsed = MagicMock()
        parsed.questions = [
            MagicMock(
                question_text=f"q_{uuid4()}_{i}",
                options=[],
                correct_answer="A",
                explanation="exp",
                difficulty="Easy",
                tags=[]
            ) for i in range(count)
        ]
        res.parsed_output = parsed
        res.provider_name = "mock"
        return res
        
    mock_ai.generate.side_effect = mock_ai_generate
    
    # First pass: some valid, some invalid. Second pass: all valid.
    call_counts = {'val': 0}
    def mock_validate_logic(*args, **kwargs):
        call_counts['val'] += 1
        # if this is the first batch and it's validating the first 2 questions, fail them
        if call_counts['val'] <= 2:
            return "Bad"
        return None
        
    mock_validate.side_effect = mock_validate_logic
    mock_duplicate.return_value = False
    
    await process_generation_session(session_id)
    
    # The crucial invariant: requested_count MUST remain exactly what was requested.
    assert db_session_obj.requested_count == req_count
    
    # Repair count should reflect the 1 repair attempt
    assert db_session_obj.repair_count == 1
    
    # Status should be COMPLETED
    assert db_session_obj.status == GenerationStatus.COMPLETED
    
    # Total valid generated should equal requested_count
    assert db_session_obj.valid_count == req_count





