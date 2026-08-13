import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

from app.models.paper import QuestionPaper, PaperStatus
from app.api.routers.papers import approve_paper
from app.schemas.paper import ApprovePaperRequest


class TestQualityStateTransitions(unittest.IsolatedAsyncioTestCase):
    async def test_approve_with_stale_report_fails(self):
        paper_id = uuid4()
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_paper = MagicMock()
        mock_paper.access = None
        mock_paper.status = PaperStatus.DRAFT
        mock_paper.config = {"sections": []}
        mock_paper.quality_report_stale = True
        mock_paper.quality_status = "PASS"
        user_id = str(uuid4())

        class MockExam:
            id = uuid4()
            created_by = None

        async def mock_get(model, id):
            if model.__name__ == "Exam":
                return MockExam()
            return None

        mock_db.get = AsyncMock(side_effect=mock_get)

        async def mock_execute(stmt, *args, **kwargs):
            stmt_str = str(stmt).lower()
            mock_res = MagicMock()
            if "subjects.created_by" in stmt_str:
                import uuid

                mock_res.scalar_one_or_none.return_value = uuid.UUID(user_id)
            elif (
                "question_papers.exam_id" in stmt_str
                and "question_papers.id" not in stmt_str
            ):
                mock_res.scalar_one_or_none.return_value = uuid4()
            elif "sharepermission" in stmt_str:
                mock_res.scalar_one_or_none.return_value = None
            else:
                mock_res.scalar_one_or_none.return_value = mock_paper
            return mock_res

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        req = ApprovePaperRequest(override_ai_check=False)

        with patch(
            "app.services.paper.validator.validate_structural_integrity",
            return_value=[],
        ):
            with self.assertRaises(Exception) as context:
                await approve_paper(paper_id, req, mock_db, user_id)

            self.assertIn("AI Quality Check is stale", str(context.exception))

    async def test_approve_fail_without_override_fails(self):
        paper_id = uuid4()
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_paper = MagicMock()
        mock_paper.access = None
        mock_paper.status = PaperStatus.DRAFT
        mock_paper.config = {"sections": []}
        mock_paper.quality_report_stale = False
        mock_paper.quality_status = "FAIL"
        user_id = str(uuid4())

        class MockExam:
            id = uuid4()
            created_by = None

        async def mock_get(model, id):
            if model.__name__ == "Exam":
                return MockExam()
            return None

        mock_db.get = AsyncMock(side_effect=mock_get)

        async def mock_execute(stmt, *args, **kwargs):
            stmt_str = str(stmt).lower()
            mock_res = MagicMock()
            if "subjects.created_by" in stmt_str:
                import uuid

                mock_res.scalar_one_or_none.return_value = uuid.UUID(user_id)
            elif (
                "question_papers.exam_id" in stmt_str
                and "question_papers.id" not in stmt_str
            ):
                mock_res.scalar_one_or_none.return_value = uuid4()
            elif "sharepermission" in stmt_str:
                mock_res.scalar_one_or_none.return_value = None
            else:
                mock_res.scalar_one_or_none.return_value = mock_paper
            return mock_res

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        req = ApprovePaperRequest(override_ai_check=False)

        with patch(
            "app.services.paper.validator.validate_structural_integrity",
            return_value=[],
        ):
            with self.assertRaises(Exception) as context:
                await approve_paper(paper_id, req, mock_db, user_id)

            self.assertIn("Explicit override required", str(context.exception))

    async def test_approve_fail_with_override_passes(self):
        paper_id = uuid4()
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_paper = MagicMock()
        mock_paper.access = None
        mock_paper.status = PaperStatus.DRAFT
        mock_paper.config = {"sections": []}
        mock_paper.quality_report_stale = False
        mock_paper.quality_status = "FAIL"
        user_id = str(uuid4())

        class MockExam:
            id = uuid4()
            created_by = None

        async def mock_get(model, id):
            if model.__name__ == "Exam":
                return MockExam()
            return None

        mock_db.get = AsyncMock(side_effect=mock_get)

        async def mock_execute(stmt, *args, **kwargs):
            stmt_str = str(stmt).lower()
            mock_res = MagicMock()
            if "subjects.created_by" in stmt_str:
                import uuid

                mock_res.scalar_one_or_none.return_value = uuid.UUID(user_id)
            elif (
                "question_papers.exam_id" in stmt_str
                and "question_papers.id" not in stmt_str
            ):
                mock_res.scalar_one_or_none.return_value = uuid4()
            elif "sharepermission" in stmt_str:
                mock_res.scalar_one_or_none.return_value = None
            else:
                mock_res.scalar_one_or_none.return_value = mock_paper
                mock_res.scalar_one.return_value = mock_paper
            return mock_res

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        req = ApprovePaperRequest(override_ai_check=True)

        with patch(
            "app.services.paper.validator.validate_structural_integrity",
            return_value=[],
        ):
            res = await approve_paper(paper_id, req, mock_db, user_id)
            self.assertEqual(res.status, PaperStatus.APPROVED)


if __name__ == "__main__":
    unittest.main()
