import io
import fitz # PyMuPDF
import pytesseract
from PIL import Image
import os

# Allow overriding Tesseract command path via environment variable if it's not in PATH
if os.getenv("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")
elif os.path.exists(r"C:\Users\navee\scoop\apps\tesseract\current\tesseract.exe"):
    pytesseract.pytesseract.tesseract_cmd = r"C:\Users\navee\scoop\apps\tesseract\current\tesseract.exe"
    os.environ["TESSDATA_PREFIX"] = r"C:\Users\navee\scoop\apps\tesseract\current\tessdata"

def extract_pdf_ocr(file_bytes: bytes) -> str:
    """
    Renders PDF pages as images and extracts text using Tesseract OCR.
    Safely falls back to empty string if Tesseract is not installed on the system.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = []
        
        # Increase zoom for better OCR quality (roughly 300 DPI)
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert PyMuPDF pixmap to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Run OCR
            try:
                text = pytesseract.image_to_string(img)
                if text.strip():
                    full_text.append(text)
            except Exception:
                continue
                
        doc.close()
        return "\n\n".join(full_text)
    except Exception:
        return ""

