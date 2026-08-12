import re

def clean_text(text: str) -> str:
    """
    Normalizes whitespace, removes obvious extraction artifacts, 
    but preserves structural numbering (1., (a), etc.) which is 
    critical for question papers.
    """
    if not text:
        return ""
    
    # 1. Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 2. Remove invisible characters (excluding newlines and tabs)
    # Using a simple printable regex approach, but keeping unicode letters
    # Actually, it's safer to just remove specific bad control chars to avoid breaking unicode math
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # 3. Collapse multiple blank lines into a single blank line
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 4. Collapse excessive horizontal whitespace (spaces/tabs) into single space
    # but don't mess with leading spaces which might be indentation for code/lists
    # We'll just replace 3+ spaces with a single space except at the start of a line
    text = re.sub(r'(?<!^)[ \t]{3,}', ' ', text, flags=re.MULTILINE)
    
    # 5. Remove trailing whitespace on each line
    text = re.sub(r'[ \t]+\n', '\n', text)
    
    return text.strip()
