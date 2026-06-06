import hashlib

def generate_line_hashes(pages_lines: dict) -> dict:
    """
    Takes the output of pdf_parser (dict of pages to lines).
    Generates SHA-256 hash for each line.
    Stores the hashes in a structured JSON dict format:
    {
      "page_1": {
        "line_1": "hash",
        "line_2": "hash"
      }
    }
    """
    hash_map = {}
    for page_key, lines in pages_lines.items():
        page_hash_map = {}
        for idx, line in enumerate(lines):
            line_key = f"line_{idx+1}"
            sha256 = hashlib.sha256()
            sha256.update(line.encode('utf-8'))
            page_hash_map[line_key] = sha256.hexdigest()
        hash_map[page_key] = page_hash_map

    return hash_map
