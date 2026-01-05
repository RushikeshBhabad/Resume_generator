"""
Node 1: File Ingestion & Normalization

Handles extraction of text from various input formats:
- PDF
- Images (JPG/PNG) via OCR
- Video (frames → OCR)
- URLs (portfolio/GitHub/LinkedIn scraping)
- Plain text
"""
import os
import re
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path

from ..models import WorkflowState
from ..utils.helpers import clean_text, get_file_type, validate_url


def extract_from_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    import pdfplumber
    
    text_parts = []
    
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    
    return "\n\n".join(text_parts)


def extract_from_image(file_path: str) -> str:
    """Extract text from image using OCR."""
    import pytesseract
    from PIL import Image
    
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image)
    
    return text


def extract_from_video(file_path: str, frame_interval: int = 30) -> str:
    """
    Extract text from video by sampling frames and running OCR.
    
    Args:
        file_path: Path to video file
        frame_interval: Extract every Nth frame
    """
    import cv2
    import pytesseract
    from PIL import Image
    import numpy as np
    
    cap = cv2.VideoCapture(file_path)
    texts = []
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            
            # OCR
            text = pytesseract.image_to_string(pil_image)
            if text.strip():
                texts.append(text.strip())
        
        frame_count += 1
    
    cap.release()
    
    # Remove duplicates while preserving order
    seen = set()
    unique_texts = []
    for text in texts:
        if text not in seen:
            seen.add(text)
            unique_texts.append(text)
    
    return "\n\n".join(unique_texts)


def extract_from_url(url: str) -> str:
    """
    Extract text from URL (portfolio, GitHub, LinkedIn).
    """
    import requests
    from bs4 import BeautifulSoup
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        
        # Handle GitHub profile
        if 'github.com' in url:
            return extract_github_info(soup, url)
        
        # Handle LinkedIn
        if 'linkedin.com' in url:
            return extract_linkedin_info(soup)
        
        # Generic portfolio extraction
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up excessive newlines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)
        
    except Exception as e:
        return f"Error extracting from URL: {str(e)}"


def extract_github_info(soup: Any, url: str) -> str:
    """Extract information from GitHub profile."""
    import requests
    
    info_parts = []
    
    # Try to extract username from URL
    match = re.search(r'github\.com/([^/]+)', url)
    if match:
        username = match.group(1)
        
        # Use GitHub API for public data
        try:
            api_response = requests.get(
                f'https://api.github.com/users/{username}',
                timeout=10
            )
            if api_response.ok:
                data = api_response.json()
                info_parts.append(f"GitHub Profile: {data.get('name', username)}")
                if data.get('bio'):
                    info_parts.append(f"Bio: {data['bio']}")
                if data.get('company'):
                    info_parts.append(f"Company: {data['company']}")
                if data.get('location'):
                    info_parts.append(f"Location: {data['location']}")
                if data.get('blog'):
                    info_parts.append(f"Website: {data['blog']}")
            
            # Get repositories
            repos_response = requests.get(
                f'https://api.github.com/users/{username}/repos?sort=updated&per_page=10',
                timeout=10
            )
            if repos_response.ok:
                repos = repos_response.json()
                info_parts.append("\nTop Repositories:")
                for repo in repos[:10]:
                    if not repo.get('fork'):
                        desc = repo.get('description', 'No description')
                        lang = repo.get('language', 'Unknown')
                        stars = repo.get('stargazers_count', 0)
                        info_parts.append(
                            f"- {repo['name']}: {desc} [{lang}] ({stars} stars)"
                        )
        except:
            pass
    
    # Fallback to page scraping
    if not info_parts:
        text = soup.get_text(separator='\n', strip=True)
        return text[:5000]  # Limit length
    
    return '\n'.join(info_parts)


def extract_linkedin_info(soup: Any) -> str:
    """Extract information from LinkedIn profile (limited due to auth)."""
    # Note: LinkedIn requires authentication for full profile access
    # This extracts what's publicly visible
    
    info_parts = []
    
    # Try to find name
    name_elem = soup.find('h1')
    if name_elem:
        info_parts.append(f"Name: {name_elem.get_text(strip=True)}")
    
    # Try to find headline
    headline = soup.find('div', class_=re.compile('headline'))
    if headline:
        info_parts.append(f"Headline: {headline.get_text(strip=True)}")
    
    # Get all text as fallback
    text = soup.get_text(separator='\n', strip=True)
    info_parts.append("\nProfile Content:")
    info_parts.append(text[:3000])
    
    return '\n'.join(info_parts)


def ingest_file(state: WorkflowState) -> WorkflowState:
    """
    Main ingestion node - extracts text from any input format.
    
    This is LangGraph Node 1: File Ingestion & Normalization
    """
    file_path = state.file_path
    input_type = state.input_type
    raw_input = state.raw_input
    
    extracted_text = ""
    
    try:
        if input_type == 'text' or (not file_path and raw_input):
            # Plain text input
            extracted_text = raw_input
            
        elif input_type == 'pdf':
            extracted_text = extract_from_pdf(file_path)
            
        elif input_type == 'image':
            extracted_text = extract_from_image(file_path)
            
        elif input_type == 'video':
            extracted_text = extract_from_video(file_path)
            
        elif input_type == 'url':
            if validate_url(raw_input):
                extracted_text = extract_from_url(raw_input)
            else:
                state.error = f"Invalid URL: {raw_input}"
                return state
                
        elif file_path:
            # Auto-detect type
            detected_type = get_file_type(file_path)
            
            if detected_type == 'pdf':
                extracted_text = extract_from_pdf(file_path)
            elif detected_type == 'image':
                extracted_text = extract_from_image(file_path)
            elif detected_type == 'video':
                extracted_text = extract_from_video(file_path)
            elif detected_type == 'text':
                with open(file_path, 'r', encoding='utf-8') as f:
                    extracted_text = f.read()
            else:
                state.error = f"Unsupported file type: {detected_type}"
                return state
        else:
            state.error = "No input provided"
            return state
        
        # Clean the extracted text
        state.extracted_text = clean_text(extracted_text)
        state.current_node = "ingestion_complete"
        
    except Exception as e:
        state.error = f"Ingestion error: {str(e)}"
    
    return state
