import io
import fitz # PyMuPDF
import pytesseract
from PIL import Image
import os
import logging

logger = logging.getLogger(__name__)

# Allow overriding Tesseract command path via environment variable if it's not in PATH
if os.getenv("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")
elif os.path.exists(r"C:\Users\navee\scoop\apps\tesseract\current\tesseract.exe"):
    pytesseract.pytesseract.tesseract_cmd = r"C:\Users\navee\scoop\apps\tesseract\current\tesseract.exe"
    os.environ["TESSDATA_PREFIX"] = r"C:\Users\navee\scoop\apps\tesseract\current\tessdata"

def extract_pdf_ocr(file_bytes: bytes) -> str:
    """
    Extracts text from scanned/image PDFs.
    Attempts local Tesseract OCR first, then seamlessly falls back to Gemini Vision OCR.
    """
    # 1. Try local Tesseract OCR
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = []
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img)
            if text.strip():
                full_text.append(text)
                
        doc.close()
        extracted = "\n\n".join(full_text)
        if extracted.strip():
            return extracted
    except Exception as e:
        logger.warning(f"Local Tesseract OCR unavailable or failed: {e}. Trying Gemini Vision OCR.")

    # 2. Gemini Multimodal AI Vision OCR fallback (serverless & works in cloud without local binaries)
    try:
        from google import genai
        from google.genai import types
        from app.core.config import settings
        
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if api_key:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"),
                    "Extract all text, questions, options, mathematical equations, and structural contents from this scanned document verbatim. Do not summarize or alter the text."
                ]
            )
            if response.text and response.text.strip():
                logger.info("Successfully extracted text using Gemini Vision OCR.")
                return response.text
    except Exception as gemini_err:
        logger.error(f"Gemini Vision OCR failed: {gemini_err}")

    return ""


