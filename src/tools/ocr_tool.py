"""
OCR Tool for PDF Document Ingestion
"""
import pdfplumber

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts raw text from a provided PDF file path.
    Args:
        pdf_path (str): The local path to the KYC/financial PDF document.
    Returns:
        str: Extracted text or an error message.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        if not text.strip():
            return "Error: No text found in the PDF. It might be a scanned image-only file."
            
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"