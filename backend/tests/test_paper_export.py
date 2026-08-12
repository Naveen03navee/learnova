import unittest
import sys
import os
from uuid import uuid4

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.paper import QuestionPaper, PaperStatus, QuestionPaperItem
from app.services.export.docx_exporter import export_question_paper_docx
from app.services.export.answer_key_exporter import export_answer_key_docx

class TestPaperExport(unittest.TestCase):
    def setUp(self):
        self.draft_paper = QuestionPaper(
            id=uuid4(),
            title="Test Paper",
            status=PaperStatus.DRAFT,
            items=[]
        )
        
        self.approved_paper = QuestionPaper(
            id=uuid4(),
            title="Approved Paper",
            status=PaperStatus.APPROVED,
            items=[
                QuestionPaperItem(
                    id=uuid4(),
                    paper_id=uuid4(),
                    question_id=uuid4(),
                    section_name="Section A",
                    order_index=1,
                    question_text_snapshot="What is 2+2?",
                    content_snapshot={"options": [{"id": "A", "text": "3"}, {"id": "B", "text": "4"}], "correct_answer": "B", "explanation": "Math"},
                    marks_snapshot=2
                )
            ]
        )

    def test_export_draft_rejected(self):
        with self.assertRaisesRegex(ValueError, "Only APPROVED papers can be exported."):
            export_question_paper_docx(self.draft_paper)
            
        with self.assertRaisesRegex(ValueError, "Only APPROVED papers can be exported."):
            export_answer_key_docx(self.draft_paper)

    def test_export_approved_success(self):
        # Should not raise
        qp_buffer = export_question_paper_docx(self.approved_paper)
        ak_buffer = export_answer_key_docx(self.approved_paper)
        
        self.assertIsNotNone(qp_buffer)
        self.assertIsNotNone(ak_buffer)
        
        # Ensure there is content in the buffers
        self.assertGreater(qp_buffer.getbuffer().nbytes, 0)
        self.assertGreater(ak_buffer.getbuffer().nbytes, 0)

if __name__ == '__main__':
    unittest.main()
