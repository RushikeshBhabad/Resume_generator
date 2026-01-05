"""
Utility functions for LaTeX safety, text processing, and file handling.
"""
import re
import os
import subprocess
from typing import Optional, Tuple
from pathlib import Path


# LaTeX special characters that need escaping
LATEX_SPECIAL_CHARS = {
    '&': r'\&',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\textasciicircum{}',
}

# Common text replacements for LaTeX
LATEX_TEXT_REPLACEMENTS = {
    'C++': r'C\texttt{++}',
    'C#': r'C\#',
}

# Spacing fixes for common concatenation errors
SPACING_FIXES = {
    'LLMdriven': 'LLM-driven',
    'LLMpowered': 'LLM-powered',
    'LLMbased': 'LLM-based',
    'AIdriven': 'AI-driven',
    'AIpowered': 'AI-powered',
    'AIbased': 'AI-based',
    'MLdriven': 'ML-driven',
    'MLpowered': 'ML-powered',
    'MLbased': 'ML-based',
    'Node.jsand': 'Node.js and',
    'Expressand': 'Express and',
    'Reactand': 'React and',
    'Pythonand': 'Python and',
    'andExpress': 'and Express',
    'andNode': 'and Node',
    'andReact': 'and React',
    'andPython': 'and Python',
    'usingNode': 'using Node',
    'usingReact': 'using React',
    'usingPython': 'using Python',
    'withNode': 'with Node',
    'withReact': 'with React',
    'withPython': 'with Python',
    'inNode': 'in Node',
    'inReact': 'in React',
    'inPython': 'in Python',
}

# Dangerous LaTeX commands to block
DANGEROUS_COMMANDS = [
    r'\\write18',
    r'\\input',
    r'\\include',
    r'\\openout',
    r'\\immediate',
    r'\\newwrite',
    r'\\closeout',
    r'\\read',
    r'\\catcode',
]


def fix_text_spacing(text: str) -> str:
    """
    Fix common spacing issues in text.
    
    Args:
        text: Text with potential spacing issues
        
    Returns:
        Text with fixed spacing
    """
    if not text:
        return ""
    
    result = text
    
    # Apply known fixes
    for wrong, correct in SPACING_FIXES.items():
        result = result.replace(wrong, correct)
    
    # Fix camelCase-like concatenations (e.g., "Node.jsExpress" → "Node.js Express")
    # Pattern: lowercase followed by uppercase without space
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', result)
    
    # Fix missing space after periods in tech terms (but not decimals)
    # e.g., "Node.jsand" should be "Node.js and"
    result = re.sub(r'(\.[a-z]+)([a-z]{3,})', r'\1 \2', result, flags=re.IGNORECASE)
    
    return result


def escape_latex(text: str) -> str:
    """
    Escape LaTeX special characters in text.
    Also fixes common spacing issues before escaping.
    
    Args:
        text: Raw text to escape
        
    Returns:
        Text with fixed spacing and escaped LaTeX special characters
    """
    if not text:
        return ""
    
    # FIRST: Fix spacing issues (LLMdriven -> LLM-driven, etc.)
    result = fix_text_spacing(text)
    
    # Then handle common text replacements (like C++)
    for original, replacement in LATEX_TEXT_REPLACEMENTS.items():
        result = result.replace(original, replacement)
    
    # Escape special characters
    for char, escaped in LATEX_SPECIAL_CHARS.items():
        result = result.replace(char, escaped)
    
    return result


def sanitize_latex(latex_code: str) -> Tuple[str, bool]:
    """
    Sanitize LaTeX code by removing dangerous commands.
    
    Args:
        latex_code: Raw LaTeX code
        
    Returns:
        Tuple of (sanitized code, is_safe flag)
    """
    is_safe = True
    sanitized = latex_code
    
    for dangerous in DANGEROUS_COMMANDS:
        if re.search(dangerous, sanitized, re.IGNORECASE):
            is_safe = False
            sanitized = re.sub(dangerous, '', sanitized, flags=re.IGNORECASE)
    
    # Remove any Unicode characters that might cause issues
    sanitized = sanitized.encode('ascii', 'ignore').decode('ascii')
    
    return sanitized, is_safe


def validate_url(url: str) -> bool:
    """
    Validate a URL format.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL format
    """
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return url_pattern.match(url) is not None


def get_file_type(file_path: str) -> str:
    """
    Determine file type from extension.
    
    Args:
        file_path: Path to file
        
    Returns:
        File type string (pdf, image, video, text, unknown)
    """
    ext = Path(file_path).suffix.lower()
    
    if ext == '.pdf':
        return 'pdf'
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
        return 'image'
    elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
        return 'video'
    elif ext in ['.txt', '.md', '.json', '.yaml', '.yml']:
        return 'text'
    else:
        return 'unknown'


def get_page_count(pdf_path: str) -> int:
    """
    Get page count of a PDF file using PyPDF2.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Number of pages
    """
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception as e:
        # Fallback to pdfinfo if available
        try:
            result = subprocess.run(
                ['pdfinfo', pdf_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        except:
            pass
    return 1


def compile_latex(tex_path: str, output_dir: str) -> Tuple[bool, str, Optional[str]]:
    """
    Compile LaTeX file to PDF using pdflatex.
    
    Args:
        tex_path: Path to .tex file
        output_dir: Output directory for PDF
        
    Returns:
        Tuple of (success, message, pdf_path)
    """
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Run pdflatex twice for proper references
        for _ in range(2):
            result = subprocess.run(
                [
                    'pdflatex',
                    '-interaction=nonstopmode',
                    '-output-directory', output_dir,
                    tex_path
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
        
        # Check if PDF was created
        tex_name = Path(tex_path).stem
        pdf_path = os.path.join(output_dir, f"{tex_name}.pdf")
        
        if os.path.exists(pdf_path):
            return True, "Compilation successful", pdf_path
        else:
            return False, f"Compilation failed: {result.stderr}", None
            
    except subprocess.TimeoutExpired:
        return False, "Compilation timed out", None
    except FileNotFoundError:
        return False, "pdflatex not found. Please install texlive-latex-base", None
    except Exception as e:
        return False, f"Compilation error: {str(e)}", None


def clean_text(text: str) -> str:
    """
    Clean extracted text by removing extra whitespace and normalizing.
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove non-printable characters
    text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def normalize_date(date_str: str) -> str:
    """
    Normalize date string to consistent format.
    
    Args:
        date_str: Raw date string
        
    Returns:
        Normalized date string (Month Year format)
    """
    from dateutil import parser
    
    if not date_str:
        return ""
    
    # Handle common patterns
    date_str = date_str.strip().lower()
    
    if date_str in ['present', 'current', 'now', 'ongoing']:
        return 'Present'
    
    try:
        parsed = parser.parse(date_str, fuzzy=True)
        return parsed.strftime('%B %Y')
    except:
        return date_str.title()


def format_phone(phone: str) -> str:
    """
    Format phone number consistently.
    
    Args:
        phone: Raw phone number
        
    Returns:
        Formatted phone number
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Format based on length
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        return phone


def ensure_directory(path: str) -> None:
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)
