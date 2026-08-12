import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

from app.models.generation import GenerationSession, GenerationStatus
from app.services.generation.orchestrator import process_generation_session
from app.core.config import settings

class TestGenerationOrchestrator(unittest.IsolatedAsyncioTestCase):
    @patch('app.services.generation.orchestrator.retrieve_chunks')
    @patch('app.services.generation.orchestrator.build_bounded_context')
    @patch('app.services.generation.orchestrator.ai_manager')
    @patch('app.services.generation.orchestrator.validate_question_logic')
    @patch('app.services.generation.orchestrator.check_duplicate')
    @patch('app.services.generation.orchestrator.AsyncSessionLocal')
    @patch('app.services.generation.orchestrator._publish_event')
    async def test_repair_limits_prevent_infinite_loops(self, mock_publish, mock_db, mock_duplicate, mock_validate, mock_ai, mock_context, mock_retrieve):
        session_id = uuid4()
        
        # Setup mocks
        mock_session = MagicMock()
        mock_db_instance = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        
        db_session_obj = GenerationSession(
            id=session_id,
            exam_id=uuid4(),
            subject_id=uuid4(),
            folder_id=uuid4(),
            requested_count=5,
            topic="Test",
            difficulty="Easy",
            question_type="MCQ",
            status=GenerationStatus.PENDING,
            invalid_count=0,
            valid_count=0,
            repair_count=0,
            duplicate_count=0
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = db_session_obj
        mock_db_instance.execute.return_value = mock_result
        
        mock_retrieve.return_value = MagicMock(results=["chunk1"])
        mock_context.return_value = ("context", {"source1": {"resource_id": uuid4(), "chunk_id": uuid4()}})
        
        # AI returns 1 question per attempt
        mock_ai_response = MagicMock()
        mock_ai_response.parsed_output.questions = [MagicMock(question_text="Q1", source_citations=["source1"], model_dump=lambda: {})]
        mock_ai_response.provider_name = "test"
        mock_ai.generate = AsyncMock(return_value=mock_ai_response)
        
        # Make all questions structurally invalid to force repairs
        mock_validate.return_value = "Missing options"
        
        # Set limits low for testing
        original_max = settings.GENERATION_MAX_REPAIR_ATTEMPTS
        original_total = settings.GENERATION_MAX_TOTAL_LLM_CALLS
        settings.GENERATION_MAX_REPAIR_ATTEMPTS = 3
        settings.GENERATION_MAX_TOTAL_LLM_CALLS = 10
        
        try:
            await process_generation_session(session_id)
            
            # The target for the batch is 5, but we only generate 1 invalid question each time.
            # Max repair attempts is 3 per batch (4 total attempts per batch).
            # It will fail 4 times in batch 1, 4 times in supp batch 2, 2 times in supp batch 3
            # before hitting the global limit of 10.
            self.assertEqual(mock_ai.generate.call_count, 10)
            self.assertEqual(db_session_obj.invalid_count, 10)
            self.assertEqual(db_session_obj.valid_count, 0)
        finally:
            settings.GENERATION_MAX_REPAIR_ATTEMPTS = original_max
            settings.GENERATION_MAX_TOTAL_LLM_CALLS = original_total

if __name__ == '__main__':
    unittest.main()
