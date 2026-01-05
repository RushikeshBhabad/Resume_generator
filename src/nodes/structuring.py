"""
Node 2: Information Structuring & Storage

Extracts structured data from raw text and stores it in a strict JSON schema.
Uses LLM for intelligent extraction while maintaining factual accuracy.
"""
import json
import re
from typing import Dict, Any, Optional

from ..models import (
    WorkflowState, 
    ResumeData, 
    PersonalInfo, 
    Education, 
    Experience,
    Project,
    Skills,
    Certification,
    Achievement,
    Extracurricular
)
from ..utils.llm_client import call_llm
from ..utils.helpers import normalize_date, format_phone


EXTRACTION_PROMPT = """You are an expert resume data extractor. Extract ALL information from the provided text and structure it into the exact JSON schema below.

RULES:
1. Extract ONLY factual information present in the text
2. Do NOT hallucinate or fabricate any data
3. Preserve all dates, metrics, URLs, and specific details
4. Normalize job titles and skill names to standard formats
5. Maintain chronological order (most recent first)
6. If a field has no data, use empty string "" or empty array []

OUTPUT SCHEMA (respond with ONLY valid JSON, no markdown):
{
  "personal": {
    "name": "",
    "email": "",
    "phone": "",
    "linkedin": "",
    "github": "",
    "portfolio": "",
    "location": ""
  },
  "education": [
    {
      "institution": "",
      "degree": "",
      "field_of_study": "",
      "start_date": "",
      "end_date": "",
      "gpa": "",
      "coursework": [],
      "achievements": []
    }
  ],
  "experience": [
    {
      "company": "",
      "title": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "is_current": false,
      "bullets": [],
      "technologies": []
    }
  ],
  "projects": [
    {
      "name": "",
      "description": "",
      "url": "",
      "start_date": "",
      "end_date": "",
      "bullets": [],
      "technologies": []
    }
  ],
  "skills": {
    "languages": [],
    "frameworks": [],
    "tools": [],
    "databases": [],
    "cloud": [],
    "soft_skills": [],
    "other": []
  },
  "certifications": [
    {
      "name": "",
      "issuer": "",
      "date": "",
      "url": "",
      "credential_id": ""
    }
  ],
  "achievements": [
    {
      "title": "",
      "description": "",
      "date": ""
    }
  ],
  "extracurricular": [
    {
      "organization": "",
      "role": "",
      "description": "",
      "start_date": "",
      "end_date": "",
      "bullets": []
    }
  ]
}

TEXT TO EXTRACT FROM:
"""


def parse_llm_json(response: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    # Remove markdown code blocks if present
    response = response.strip()
    
    # Try to find JSON in code blocks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if json_match:
        response = json_match.group(1)
    
    # Try to find raw JSON object
    json_obj_match = re.search(r'\{[\s\S]*\}', response)
    if json_obj_match:
        response = json_obj_match.group(0)
    
    return json.loads(response)


def normalize_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and clean extracted data."""
    
    # Normalize personal info
    if 'personal' in data:
        personal = data['personal']
        if personal.get('phone'):
            personal['phone'] = format_phone(personal['phone'])
    
    # Normalize dates in education
    if 'education' in data:
        for edu in data['education']:
            if edu.get('start_date'):
                edu['start_date'] = normalize_date(edu['start_date'])
            if edu.get('end_date'):
                edu['end_date'] = normalize_date(edu['end_date'])
    
    # Normalize dates in experience
    if 'experience' in data:
        for exp in data['experience']:
            if exp.get('start_date'):
                exp['start_date'] = normalize_date(exp['start_date'])
            if exp.get('end_date'):
                exp['end_date'] = normalize_date(exp['end_date'])
            # Handle current positions
            if exp.get('is_current') or exp.get('end_date', '').lower() in ['present', 'current']:
                exp['end_date'] = 'Present'
                exp['is_current'] = True
    
    # Normalize dates in projects
    if 'projects' in data:
        for proj in data['projects']:
            if proj.get('start_date'):
                proj['start_date'] = normalize_date(proj['start_date'])
            if proj.get('end_date'):
                proj['end_date'] = normalize_date(proj['end_date'])
    
    # Normalize dates in extracurricular
    if 'extracurricular' in data:
        for extra in data['extracurricular']:
            if extra.get('start_date'):
                extra['start_date'] = normalize_date(extra['start_date'])
            if extra.get('end_date'):
                extra['end_date'] = normalize_date(extra['end_date'])
    
    # Remove duplicates from skills
    if 'skills' in data:
        skills = data['skills']
        for key in skills:
            if isinstance(skills[key], list):
                skills[key] = list(dict.fromkeys(skills[key]))  # Preserve order
    
    return data


def structure_data(state: WorkflowState) -> WorkflowState:
    """
    Main structuring node - extracts structured data from raw text.
    
    This is LangGraph Node 2: Information Structuring & Storage
    """
    if not state.extracted_text:
        state.error = "No extracted text to structure"
        return state
    
    try:
        # Call LLM for intelligent extraction
        response = call_llm(
            system_prompt="You are a precise data extraction assistant. Output ONLY valid JSON.",
            user_prompt=f"{EXTRACTION_PROMPT}\n\n{state.extracted_text}"
        )
        
        # Parse the JSON response
        extracted_data = parse_llm_json(response)
        
        # Normalize the data
        normalized_data = normalize_extracted_data(extracted_data)
        
        # Create ResumeData object
        state.resume_data = ResumeData.from_dict(normalized_data)
        state.current_node = "structuring_complete"
        
    except json.JSONDecodeError as e:
        state.error = f"Failed to parse LLM response as JSON: {str(e)}"
    except Exception as e:
        state.error = f"Structuring error: {str(e)}"
    
    return state
