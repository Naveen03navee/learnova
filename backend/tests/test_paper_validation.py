import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from uuid import uuid4

from app.models.paper import QuestionPaper, QuestionPaperItem, PaperStatus
from app.services.paper.validator import validate_structural_integrity

class TestPaperValidation(unittest.TestCase):
    def setUp(self):
        self.valid_paper = QuestionPaper(
            id=uuid4(),
            title="Valid Paper",
            status=PaperStatus.DRAFT,
            config={
                "title": "Valid Paper",
                "exam_id": str(uuid4()),
                "subject_id": str(uuid4()),
                "sections": [
                    {
                        "name": "Section A",
                        "question_type": "MCQ",
                        "difficulty": "Medium",
                        "count": 2,
                        "marks_per_question": 1
                    }
                ]
            },
            items=[
                QuestionPaperItem(
                    id=uuid4(),
                    paper_id=uuid4(),
                    question_id=uuid4(),
                    section_name="Section A",
                    order_index=1,
                    question_text_snapshot="Q1",
                    content_snapshot={"options": [{"id": "A", "text": "1"}, {"id": "B", "text": "2"}], "correct_answer": "B"},
                    marks_snapshot=1,
                    marks_override=None
                ),
                QuestionPaperItem(
                    id=uuid4(),
                    paper_id=uuid4(),
                    question_id=uuid4(),
                    section_name="Section A",
                    order_index=2,
                    question_text_snapshot="Q2",
                    content_snapshot={"options": [{"id": "A", "text": "1"}, {"id": "B", "text": "2"}], "correct_answer": "A"},
                    marks_snapshot=1,
                    marks_override=None
                )
            ]
        )

    def test_valid_paper_passes(self):
        errors = validate_structural_integrity(self.valid_paper)
        self.assertEqual(len(errors), 0)

    def test_invalid_count_fails(self):
        # Remove one item
        self.valid_paper.items.pop()
        errors = validate_structural_integrity(self.valid_paper)
        self.assertIn("Section 'Section A' expects 2 questions, found 1.", errors)

    def test_invalid_marks_fails(self):
        # Change marks
        self.valid_paper.items[0].marks_override = 2
        errors = validate_structural_integrity(self.valid_paper)
        self.assertIn("Section 'Section A' Question 1: expected 1 marks, found 2.", errors)

    def test_invalid_mcq_fails(self):
        # Change answer to something invalid
        self.valid_paper.items[0].content_snapshot["correct_answer"] = "C"
        errors = validate_structural_integrity(self.valid_paper)
        self.assertTrue(any("does not match any option" in e for e in errors))
        
    def test_missing_options_fails(self):
        # Remove options
        self.valid_paper.items[0].content_snapshot["options"] = []
        errors = validate_structural_integrity(self.valid_paper)
        self.assertTrue(any("MCQ requires at least 2 options" in e for e in errors))

if __name__ == '__main__':
    unittest.main()




