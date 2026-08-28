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
    # 1. Try local Tesseract OCR if available
    import shutil
    tess_cmd = pytesseract.pytesseract.tesseract_cmd
    tess_exists = False
    
    if os.path.exists(tess_cmd):
        tess_exists = True
    elif shutil.which(tess_cmd):
        tess_exists = True
        
    if tess_exists:
        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                full_text = []
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    try:
                        text = pytesseract.image_to_string(img)
                        if text.strip():
                            full_text.append(text)
                    finally:
                        # Explicitly free memory for large image objects
                        del img
                        del pix
                        page = None
                        
                extracted = "\n\n".join(full_text)
                if extracted.strip():
                    return extracted
        except Exception as e:
            logger.warning(f"Local Tesseract OCR failed: {e}. Trying Gemini Vision OCR.")
    else:
        logger.info("Tesseract not found. Skipping local OCR and using Gemini Vision OCR directly.")

    # 2. Gemini Multimodal AI Vision OCR fallback (serverless & works in cloud without local binaries)
    try:
        from google import genai
        from google.genai import types
        from app.core.config import settings
        import time
        
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if api_key:
            client = genai.Client(api_key=api_key)
            contents = [
                types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"),
                "Extract all text, questions, options, mathematical equations, and structural contents from this scanned document verbatim. Do not summarize or alter the text."
            ]
            
            # Retry logic with fallback models
            models_to_try = ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
            last_err = None
            
            for model_name in models_to_try:
                for attempt in range(3):
                    try:
                        logger.info(f"Attempting Gemini OCR with model {model_name} (Attempt {attempt+1}/3)")
                        response = client.models.generate_content(
                            model=model_name,
                            contents=contents
                        )
                        if response.text and response.text.strip():
                            logger.info(f"Successfully extracted text using Gemini Vision OCR ({model_name}).")
                            return response.text
                        break # If response is empty but successful, don't retry same model
                    except Exception as gemini_err:
                        last_err = gemini_err
                        err_str = str(gemini_err).lower()
                        if "503" in err_str or "unavailable" in err_str or "429" in err_str:
                            logger.warning(f"Model {model_name} overloaded (503/429). Retrying in {2 ** attempt}s...")
                            time.sleep(2 ** attempt)
                        else:
                            # Not a transient error, break inner loop to try next model
                            break
            
            logger.error(f"Gemini Vision OCR failed after all retries/models. Last error: {last_err}")
    except Exception as general_err:
        logger.error(f"Failed to initialize Gemini for OCR: {general_err}")

    return ""


