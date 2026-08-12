import io

def extract_txt(file_bytes: bytes) -> str:
    """
    Extracts text from a plain text file.
    Tries utf-8 first, falls back to other common encodings, 
    and uses 'replace' to gracefully handle malformed bytes without crashing.
    """
    try:
        return file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return file_bytes.decode('latin-1')
        except UnicodeDecodeError:
            # Fallback that guarantees no crash, replacing invalid chars
            return file_bytes.decode('utf-8', errors='replace')
