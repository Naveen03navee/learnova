import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.paper import QuestionPaper, PaperStatus
from app.api.routers.papers import approve_paper, auto_replace_item, swap_item, reorder_items
from app.schemas.paper import ApprovePaperRequest, SwapItemRequest, ReorderItemRequest

class TestPaperStateMachine(unittest.IsolatedAsyncioTestCase):
    async def test_approve_valid_transition(self):
        paper_id = uuid4()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_result = MagicMock()
        
        paper = QuestionPaper(id=paper_id, status=PaperStatus.DRAFT, config={"sections":[]}, quality_report_stale=False, quality_status="PASS")
        mock_result.scalar_one_or_none.return_value = paper
        mock_result.scalar_one.return_value = paper
        mock_db.execute.return_value = mock_result
        
        req = ApprovePaperRequest()
        with patch('app.services.paper.validator.validate_structural_integrity', return_value=[]):
            res = await approve_paper(paper_id, req, mock_db)
            self.assertEqual(res.status, PaperStatus.APPROVED)

    async def test_approve_already_approved_fails(self):
        paper_id = uuid4()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        
        paper = QuestionPaper(id=paper_id, status=PaperStatus.APPROVED, config={"sections":[]})
        mock_result.scalar_one_or_none.return_value = paper
        mock_db.execute.return_value = mock_result
        
        req = ApprovePaperRequest()
        with self.assertRaises(Exception) as context:
            await approve_paper(paper_id, req, mock_db)
        self.assertIn("already PaperStatus.APPROVED", str(context.exception))

    async def test_approve_published_fails(self):
        paper_id = uuid4()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        
        paper = QuestionPaper(id=paper_id, status=PaperStatus.PUBLISHED, config={"sections":[]})
        mock_result.scalar_one_or_none.return_value = paper
        mock_db.execute.return_value = mock_result
        
        req = ApprovePaperRequest()
        with self.assertRaises(Exception) as context:
            await approve_paper(paper_id, req, mock_db)
        self.assertIn("already PaperStatus.PUBLISHED", str(context.exception))

    async def test_mutation_on_approved_fails(self):
        paper_id = uuid4()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        
        paper = QuestionPaper(id=paper_id, status=PaperStatus.APPROVED)
        mock_result.scalar_one_or_none.return_value = paper
        mock_db.execute.return_value = mock_result
        
        # Test auto_replace
        with self.assertRaises(Exception) as context:
            await auto_replace_item(paper_id, uuid4(), mock_db)
        self.assertIn("not in DRAFT status", str(context.exception))
        
        # Test swap
        req = SwapItemRequest(new_question_id=uuid4())
        with self.assertRaises(Exception) as context:
            await swap_item(paper_id, uuid4(), req, mock_db)
        self.assertIn("not in DRAFT status", str(context.exception))

        # Test reorder
        req2 = [ReorderItemRequest(item_id=uuid4(), new_index=1)]
        with self.assertRaises(Exception) as context:
            await reorder_items(paper_id, req2, mock_db)
        self.assertIn("Only DRAFT papers can be modified", str(context.exception))

if __name__ == '__main__':
    unittest.main()
