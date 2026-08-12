import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

from app.models.paper import QuestionPaper, PaperStatus
from app.api.routers.papers import approve_paper
from app.schemas.paper import ApprovePaperRequest

class TestQualityStateTransitions(unittest.IsolatedAsyncioTestCase):
    async def test_approve_with_stale_report_fails(self):
        paper_id = uuid4()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        
        paper = QuestionPaper(id=paper_id, status=PaperStatus.DRAFT, config={"sections":[]}, quality_report_stale=True, quality_status="PASS")
        mock_result.scalar_one_or_none.return_value = paper
        mock_db.execute.return_value = mock_result
        
        req = ApprovePaperRequest(override_ai_check=False)
        
        with patch('app.services.paper.validator.validate_structural_integrity', return_value=[]):
            with self.assertRaises(Exception) as context:
                await approve_paper(paper_id, req, mock_db)
                
            self.assertIn("AI Quality Check is stale", str(context.exception))

    async def test_approve_fail_without_override_fails(self):
        paper_id = uuid4()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        
        paper = QuestionPaper(id=paper_id, status=PaperStatus.DRAFT, config={"sections":[]}, quality_report_stale=False, quality_status="FAIL")
        mock_result.scalar_one_or_none.return_value = paper
        mock_db.execute.return_value = mock_result
        
        req = ApprovePaperRequest(override_ai_check=False)
        
        with patch('app.services.paper.validator.validate_structural_integrity', return_value=[]):
            with self.assertRaises(Exception) as context:
                await approve_paper(paper_id, req, mock_db)
                
            self.assertIn("Explicit override required", str(context.exception))
            
    async def test_approve_fail_with_override_passes(self):
        paper_id = uuid4()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_result = MagicMock()
        
        paper = QuestionPaper(id=paper_id, status=PaperStatus.DRAFT, config={"sections":[]}, quality_report_stale=False, quality_status="FAIL")
        mock_result.scalar_one_or_none.return_value = paper
        mock_result.scalar_one.return_value = paper
        mock_db.execute.return_value = mock_result
        
        req = ApprovePaperRequest(override_ai_check=True)
        
        with patch('app.services.paper.validator.validate_structural_integrity', return_value=[]):
            res = await approve_paper(paper_id, req, mock_db)
            self.assertEqual(res.status, PaperStatus.APPROVED)

if __name__ == '__main__':
    unittest.main()
