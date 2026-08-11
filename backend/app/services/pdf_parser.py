import os
import logging
import io
from typing import List, Dict, Any

# Configure logger
logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    logger.error("PyMuPDF is not installed. PDF text extraction will fail.")

try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    logger.warning("pytesseract or PIL is not installed. OCR fallback will be disabled.")

def extract_text_from_pdf(file_path: str, use_ocr: bool = False) -> List[Dict[str, Any]]:
    """
    Extracts text from a PDF file page-by-page.
    
    Args:
        file_path: Path to the PDF file.
        use_ocr: If True, falls back to OCR for pages with low text density.
        
    Returns:
        A list of dictionaries, each containing:
            - page_number: 1-indexed page number
            - text: extracted text content of the page
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at: {file_path}")

    pages_data = []
    
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logger.error(f"Failed to open PDF file {file_path}: {e}")
        raise e

    try:
        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc[page_idx]
        
            # 1. Native text extraction
            try:
                text = page.get_text()
            except Exception as e:
                logger.warning(f"Native text extraction failed on page {page_num}: {e}")
                text = ""
            
            text = text.strip()
        
        # 2. Trigger OCR if requested and native text is sparse
        # We consider text sparse if it's less than 80 characters
            if use_ocr and len(text) < 80:
                if HAS_OCR:
                    try:
                        logger.info(f"Running OCR fallback on page {page_num}...")
                    # Render page to an image
                        pix = page.get_pixmap(dpi=150)
                        img_data = pix.tobytes("png")
                        image = Image.open(io.BytesIO(img_data))
                    
                    # Run OCR
                        ocr_text = pytesseract.image_to_string(image).strip()
                    
                        if len(ocr_text) > len(text):
                            text = ocr_text
                            logger.info(f"OCR successfully extracted {len(text)} characters on page {page_num}.")
                    except Exception as ocr_err:
                        logger.warning(f"OCR fallback failed on page {page_num}: {ocr_err}")
                else:
                    logger.warning(f"OCR requested for page {page_num} but OCR packages are not available.")
                
            pages_data.append({"page_number": page_num, "text": text})
    finally:
        doc.close()
    return pages_data
