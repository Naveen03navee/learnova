import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

from app.models.generation import GenerationSession, GenerationStatus
from app.services.generation.orchestrator import process_generation_session
from app.core.config import settings

class TestGenerationFailures(unittest.IsolatedAsyncioTestCase):
    
    @patch('app.services.generation.orchestrator.retrieve_chunks')
    @patch('app.services.generation.orchestrator.build_bounded_context')
    @patch('app.services.generation.orchestrator.ai_manager')
    @patch('app.services.generation.orchestrator.AsyncSessionLocal')
    @patch('app.services.generation.orchestrator._publish_event')
    async def test_ai_provider_failure_recovery(self, mock_publish, mock_db, mock_ai, mock_context, mock_retrieve):
        session_id = uuid4()
        
        mock_db_instance = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        
        db_session_obj = GenerationSession(
            id=session_id,
            exam_id=uuid4(),
            subject_id=uuid4(),
            folder_id=uuid4(),
            requested_count=2,
            topic="Test",
            difficulty="Easy",
            question_type="MCQ",
            status=GenerationStatus.PENDING,
            invalid_count=0,
            valid_count=0,
            repair_count=0,
            duplicate_count=0
        )
        from app.models.workspace import Exam, Subject
        exam = Exam(id=uuid4(), name="Test Exam")
        subject = Subject(id=uuid4(), name="Test Subject")
        
        mock_result = MagicMock()
        mock_result.first.return_value = (db_session_obj, exam, subject)
        mock_db_instance.execute.return_value = mock_result
        
        mock_retrieve.return_value = MagicMock(results=["chunk1"])
        mock_context.return_value = ("context", {"source1": {"resource_id": uuid4(), "chunk_id": uuid4()}})
        
        # Simulate AI throwing an exception
        mock_ai.generate = AsyncMock(side_effect=Exception("API limit reached"))
        
        # Should gracefully fail all attempts and eventually mark session as FAILED
        # Max repairs = 3, so 4 attempts total.
        original_max = settings.GENERATION_MAX_REPAIR_ATTEMPTS
        settings.GENERATION_MAX_REPAIR_ATTEMPTS = 3
        
        try:
            await process_generation_session(session_id)
            
            # The AI provider threw exceptions 4 times for the first batch,
            # then it moves to supplementary batch until global limit is reached or it hits max supp batches.
            # Regardless, the session should not crash the worker and should eventually save.
            self.assertEqual(db_session_obj.status, GenerationStatus.FAILED)
            self.assertEqual(db_session_obj.valid_count, 0)
        finally:
            settings.GENERATION_MAX_REPAIR_ATTEMPTS = original_max

    @patch('app.services.generation.orchestrator.retrieve_chunks')
    @patch('app.services.generation.orchestrator.build_bounded_context')
    @patch('app.services.generation.orchestrator.ai_manager')
    @patch('app.services.generation.orchestrator.validate_question_logic')
    @patch('app.services.generation.orchestrator.check_duplicate')
    @patch('app.services.generation.orchestrator.generate_question_embedding')
    @patch('app.services.generation.orchestrator.AsyncSessionLocal')
    @patch('app.services.generation.orchestrator._publish_event')
    async def test_database_commit_failure_rollback(self, mock_publish, mock_db, mock_emb, mock_dup, mock_val, mock_ai, mock_context, mock_retrieve):
        session_id = uuid4()
        
        mock_db_instance = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        
        db_session_obj = GenerationSession(
            id=session_id,
            exam_id=uuid4(),
            subject_id=uuid4(),
            folder_id=uuid4(),
            requested_count=1,
            topic="Test",
            difficulty="Easy",
            question_type="MCQ",
            status=GenerationStatus.PENDING,
            invalid_count=0,
            valid_count=0,
            repair_count=0,
            duplicate_count=0
        )
        from app.models.workspace import Exam, Subject
        exam = Exam(id=uuid4(), name="Test Exam")
        subject = Subject(id=uuid4(), name="Test Subject")
        
        mock_result = MagicMock()
        mock_result.first.return_value = (db_session_obj, exam, subject)
        mock_result.scalar_one_or_none.return_value = db_session_obj
        mock_db_instance.execute.return_value = mock_result
        
        mock_retrieve.return_value = MagicMock(results=["chunk1"])
        mock_context.return_value = ("context", {"source1": {"resource_id": uuid4(), "chunk_id": uuid4()}})
        
        # Valid AI response
        mock_ai_response = MagicMock()
        mock_ai_response.parsed_output.questions = [MagicMock(question_text="Q1", source_citations=["source1"], model_dump=lambda: {})]
        mock_ai_response.provider_name = "test"
        mock_ai.generate = AsyncMock(return_value=mock_ai_response)
        
        mock_val.return_value = None
        mock_dup.return_value = False
        mock_emb.return_value = [0.1] * 384
        
        # Make db.commit() fail exactly once during question save
        commit_calls = [0]
        async def mock_commit():
            commit_calls[0] += 1
            if commit_calls[0] == 4: # First few commits are for status updates
                raise Exception("DB lock timeout")
            return None
            
        mock_db_instance.commit = AsyncMock(side_effect=mock_commit)
        
        await process_generation_session(session_id)
        
        # If rollback works, the inner exception loop catches it, rolls back, and retries.
        mock_db_instance.rollback.assert_called()

if __name__ == '__main__':
    unittest.main()




