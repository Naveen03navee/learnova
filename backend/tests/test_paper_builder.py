import unittest
import sys
import os
import asyncio
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.paper.schemas import PaperBlueprint, PaperSectionBlueprint
from app.services.paper.builder import build_question_paper, select_diverse_questions, select_single_replacement
from app.models.question import Question

class TestPaperBuilder(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.exam_id = uuid4()
        self.subject_id = uuid4()
        
    async def test_build_question_paper_success(self):
        mock_db = AsyncMock()
        
        # We need 2 Easy MCQs and 1 Hard SAQ
        q1 = MagicMock(spec=Question); q1.id = uuid4(); q1.question_text = "q1"; q1.marks = 1; q1.embedding = [1,0,0]
        q2 = MagicMock(spec=Question); q2.id = uuid4(); q2.question_text = "q2"; q2.marks = 1; q2.embedding = [0,1,0]
        q3 = MagicMock(spec=Question); q3.id = uuid4(); q3.question_text = "q3"; q3.marks = 1; q3.embedding = [0.5,0.5,0]
        q_saq = MagicMock(spec=Question); q_saq.id = uuid4(); q_saq.question_text = "saq"; q_saq.marks = 5; q_saq.embedding = [0,0,1]
        
        call_count = [0]
        def mock_execute(query):
            mock_res = MagicMock()
            if call_count[0] == 0:
                mock_res.scalars().all.return_value = [q1, q2, q3]
            else:
                mock_res.scalars().all.return_value = [q_saq]
            call_count[0] += 1
            return mock_res
            
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        blueprint = PaperBlueprint(
            title="Midterm",
            exam_id=self.exam_id,
            subject_id=self.subject_id,
            sections=[
                PaperSectionBlueprint(name="Section A", question_type="MCQ", difficulty="Easy", count=2, marks_per_question=1),
                PaperSectionBlueprint(name="Section B", question_type="SAQ", difficulty="Hard", count=1, marks_per_question=5)
            ]
        )
        
        paper = await build_question_paper(mock_db, blueprint)
        
        self.assertEqual(paper.title, "Midterm")
        self.assertEqual(paper.status, "DRAFT")
        mock_db.add.assert_called()
        self.assertEqual(mock_db.add.call_count, 1 + 3) # 1 paper + 3 items
        mock_db.commit.assert_called_once()
        
    async def test_build_question_paper_insufficient_inventory(self):
        mock_db = AsyncMock()
        
        # Only 1 MCQ available, but 2 requested
        q1 = MagicMock(spec=Question); q1.id = uuid4(); q1.question_text = "q1"; q1.marks = 1; q1.embedding = [1,0,0]
        
        def mock_execute(query):
            mock_res = MagicMock()
            mock_res.scalars().all.return_value = [q1]
            return mock_res
            
        mock_db.execute = AsyncMock(side_effect=mock_execute)
        
        blueprint = PaperBlueprint(
            title="Midterm",
            exam_id=self.exam_id,
            subject_id=self.subject_id,
            sections=[
                PaperSectionBlueprint(name="Section A", question_type="MCQ", difficulty="Easy", count=2, marks_per_question=1)
            ]
        )
        
        with self.assertRaises(ValueError) as context:
            await build_question_paper(mock_db, blueprint)
            
        self.assertIn("Insufficient questions for Section A", str(context.exception))
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_mmr_semantic_diversity(self):
        # We have 4 candidates.
        # q1 and q2 are identical. q3 is orthogonal. q4 is somewhat in between.
        # If we pick 2, MMR should pick q1 (or q2) and q3, but never q1 and q2 together.
        q1 = MagicMock(spec=Question); q1.id = 1; q1.embedding = [1, 0, 0]
        q2 = MagicMock(spec=Question); q2.id = 2; q2.embedding = [1, 0, 0]
        q3 = MagicMock(spec=Question); q3.id = 3; q3.embedding = [0, 1, 0]
        q4 = MagicMock(spec=Question); q4.id = 4; q4.embedding = [0.707, 0.707, 0]
        
        candidates = [q1, q2, q3, q4]
        
        with patch('app.services.paper.builder.random.randint', return_value=0):
            # first_idx = 0 -> picks q1
            selected = select_diverse_questions(candidates, count=2)
            
            self.assertEqual(len(selected), 2)
            self.assertEqual(selected[0].id, 1)
            # Second choice MUST be q3 because it is orthogonal (max distance)
            self.assertEqual(selected[1].id, 3)

    def test_mmr_auto_replace_selection(self):
        q1 = MagicMock(spec=Question); q1.id = 1; q1.embedding = [1, 0, 0]
        q2 = MagicMock(spec=Question); q2.id = 2; q2.embedding = [0, 1, 0]
        
        # existing questions in paper are identical to q1
        existing_embs = [np.array([1, 0, 0])]
        
        candidates = [q1, q2]
        
        # Should pick q2 because it's further from existing_embs
        best = select_single_replacement(candidates, existing_embs)
        
        self.assertEqual(best.id, 2)

if __name__ == '__main__':
    unittest.main()
