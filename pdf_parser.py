import fitz

def extract_text_lines_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Accepts a decrypted PDF report (bytes).
    Extracts text page-wise from the PDF.
    Splits each page into individual lines.
    Returns a dict like: {"page_1": ["line 1", "line 2", ...], ...}
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        print(f"Error opening PDF bytes: {e}")
        return {}

    pages_lines = {}
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text("text")
        # Split and cleanly filter to normalize
        lines = [line.strip() for line in text.replace('\r', '').split('\n') if line.strip()]
        pages_lines[f"page_{i+1}"] = lines

    return pages_lines
