import fitz # PyMuPDF
from .ocr import extract_pdf_ocr
import logging

logger = logging.getLogger(__name__)

# Minimum characters per page to consider normal extraction "successful"
# If the average characters per page is lower than this, we suspect it's a scanned PDF
MIN_CHARS_PER_PAGE_THRESHOLD = 50

def extract_pdf(file_bytes: bytes) -> tuple[str, bool]:
    """
    Extracts text from a PDF. 
    First tries normal text extraction. If text is too sparse, falls back to OCR.
    Returns a tuple of (extracted_text, used_ocr)
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    
    pages_text = []
    total_chars = 0
    total_pages = len(doc)
    
    if total_pages == 0:
        return "", False
        
    for page in doc:
        text = page.get_text()
        pages_text.append(text)
        total_chars += len(text.strip())
        
    doc.close()
    
    avg_chars_per_page = total_chars / total_pages if total_pages > 0 else 0
    
    if avg_chars_per_page < MIN_CHARS_PER_PAGE_THRESHOLD:
        logger.info(f"PDF extraction yielded only {avg_chars_per_page:.1f} chars/page. Falling back to OCR.")
        ocr_text = extract_pdf_ocr(file_bytes)
        return ocr_text, True
        
    return "\n\n".join(pages_text), False
