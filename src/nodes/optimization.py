"""
Node 4: Resume Content Optimization

Optimizes resume content for the target role with ADAPTIVE PAGE PRESSURE:
- Soft one-page constraint (≈95% one-page target)
- Adaptive compression based on page_pressure [0.3, 0.9]
- Score monotonicity enforcement
- Intelligent bullet rewriting
- Strong action verbs and quantified impact
- Role-aligned keywords and ATS optimization
"""
import json
import re
from typing import Dict, Any, List

from ..models import WorkflowState, ResumeData
from ..utils.llm_client import call_llm
from .adaptive_optimizer import (
    adaptive_optimize_content,
    apply_incremental_compression,
    get_compression_level,
    COMPRESSION_BEHAVIOR_TEMPLATES,
)


# Action verbs categorized by impact type
ACTION_VERBS = {
    "leadership": ["Led", "Directed", "Managed", "Orchestrated", "Spearheaded", "Oversaw"],
    "creation": ["Developed", "Designed", "Created", "Built", "Engineered", "Architected"],
    "improvement": ["Optimized", "Enhanced", "Improved", "Streamlined", "Accelerated", "Refined"],
    "achievement": ["Achieved", "Delivered", "Exceeded", "Accomplished", "Attained", "Surpassed"],
    "analysis": ["Analyzed", "Evaluated", "Assessed", "Investigated", "Researched", "Identified"],
    "collaboration": ["Collaborated", "Partnered", "Coordinated", "Facilitated", "Mentored"],
    "implementation": ["Implemented", "Deployed", "Executed", "Integrated", "Launched", "Established"],
}

# Weak phrases to avoid
WEAK_PHRASES = [
    "worked on",
    "helped with",
    "responsible for",
    "assisted with",
    "was involved in",
    "participated in",
    "dealt with",
    "handled",
]


OPTIMIZATION_PROMPT = """You are an ULTRA-AGGRESSIVE resume optimization AI with LINE-AWARE layout intelligence.

🚨 CRITICAL DIRECTIVE 🚨
This resume MUST fit on ONE PAGE. You must be AWARE of approximate line usage.

📏 LINE BUDGET AWARENESS:
- 1 resume line ≈ 90 characters
- Target total: 46-50 lines
- YOU MUST internally estimate line usage and REBALANCE content

TARGET ROLE: {target_role}
PAGE PRESSURE: {page_pressure:.2f} (Range: 0.4-0.95, higher = EXTREME compression)
COMPRESSION LEVEL: {compression_level}
ESCALATION ACTION: {escalation_action}
ESTIMATED LINES: {estimated_lines} (target: 48)

CURRENT RESUME DATA:
{resume_data}

{compression_behavior}

=== 📏 SECTION LINE BUDGETS (ENFORCE THESE) ===

| Section          | Target Lines | Notes                           |
|------------------|--------------|----------------------------------|
| Education        | 4-5 lines    | Degree + GPA + 1 line max       |
| Experience       | 12-14 lines  | 2-3 roles × 2-3 bullets each    |
| Projects         | 12-14 lines  | 3-4 projects × 2 bullets each   |
| Skills           | 4-5 lines    | Compact, 1 line per category    |
| Extracurricular  | 3-4 lines    | Optional, cut if over budget    |
| Optional (certs) | ≤4 lines     | Inline list or REMOVE           |

⚠️ If total estimated lines > 50: YOU MUST cut content aggressively.

=== 🧩 STRUCTURAL COMPRESSION (MANDATORY) ===

When estimated lines exceed budget, apply IN ORDER:

**STEP 1 - REWRITE (escalation=0):**
- Shorten bullets to 15-18 words max (fits one line)
- Remove filler words: "in order to", "responsible for"
- Combine related information

**STEP 2 - REDUCE BULLETS (escalation=1):**
- MAX 2-3 bullets per experience
- MAX 2 bullets per project
- Keep ONLY highest-impact bullets

**STEP 3 - REDUCE ITEMS (escalation=2):**
- Keep only 2-3 strongest experiences
- Keep only 3 best projects
- Remove or merge weaker items

**STEP 4 - TRIM SECTIONS (escalation=3):**
- REMOVE achievements section
- REMOVE certifications OR make inline
- REMOVE extracurricular if weak

=== 🧠 HEADER & TITLE COMPRESSION ===

- Section headers: Single line only
- Project titles: Inline format preferred
  ✅ "Project Name | React, Node.js, MongoDB"
  ❌ Multi-line descriptions

- Compress dates: "Aug 2023 - Dec 2024" not "August 2023 - December 2024"

=== ✨ BULLET SURGERY RULES ===

Every bullet MUST fit ONE LINE (≈90 chars):
- Pattern: "[Verb] [What] + [Tech/How] + [Impact]"
- MAX 15-18 words per bullet
- EVERY bullet MUST have a NUMBER or METRIC

**BULLET TRANSFORMATION EXAMPLES:**
❌ "Worked on developing a machine learning model that was used for predicting customer churn with 85% accuracy" (22 words)
✅ "Built ML churn prediction model achieving 85% accuracy using XGBoost" (11 words)

❌ "Was responsible for creating REST APIs using Node.js and Express framework for the backend"
✅ "Developed RESTful APIs using Node.js/Express serving 10K+ daily requests"

=== 🔧 SPACING & FORMATTING FIXES ===

**FIX THESE ISSUES:**
- Add hyphens: "LLMdriven" → "LLM-driven"
- Compact tech stacks: "Node.js and Express Essentials" → "Node.js, Express"
- Remove redundant titles from certifications

=== 📊 QUANTIFICATION REQUIREMENTS ===

**EVERY BULLET NEEDS A METRIC:**
- No metric? ADD one: "50+ users", "3x faster", "40% reduction"
- If truly no metric possible: "production-ready", "enterprise-grade"

=== 🧠 INTERNAL EDITOR PRINCIPLE ===

"If it doesn't earn its line, it doesn't stay."

Ask yourself for each bullet:
- Does this add unique value?
- Is this already covered elsewhere?
- Would a recruiter care about this?
- Can I say this in fewer words?

=== 🛑 ABSOLUTE RULES ===

FORBIDDEN to:
- Output bullets >90 characters (they waste a line)
- Keep bullets without metrics
- Keep weak phrases ("responsible for", "worked on", "helped with")
- Keep sections that push resume past 50 lines

=== OUTPUT FORMAT ===
Return the COMPLETE optimized resume data in the EXACT same JSON structure.
Output ONLY valid JSON, no explanations or markdown.
Ensure ALL text has proper spacing - NO concatenated words like "LLMdriven".
"""


def parse_llm_json(response: str) -> Dict[str, Any]:
    """Parse JSON from LLM response."""
    response = response.strip()
    
    # Remove markdown code blocks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
    if json_match:
        response = json_match.group(1)
    
    # Find JSON object
    json_obj_match = re.search(r'\{[\s\S]*\}', response)
    if json_obj_match:
        response = json_obj_match.group(0)
    
    return json.loads(response)


def normalize_optimized_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize LLM output to match expected Pydantic schema.
    Handles cases where LLM returns strings instead of lists/dicts.
    """
    # Normalize skills - convert comma-separated strings to lists
    if "skills" in data and isinstance(data["skills"], dict):
        skills = data["skills"]
        skill_fields = ["languages", "frameworks", "tools", "databases", "cloud", "soft_skills", "other"]
        for field in skill_fields:
            if field in skills:
                value = skills[field]
                if isinstance(value, str):
                    # Split comma-separated string into list
                    skills[field] = [s.strip() for s in value.split(",") if s.strip()]
                elif not isinstance(value, list):
                    skills[field] = []
    
    # Normalize certifications - convert strings to Certification dicts
    if "certifications" in data and isinstance(data["certifications"], list):
        normalized_certs = []
        for cert in data["certifications"]:
            if isinstance(cert, str):
                # Convert string to Certification dict
                normalized_certs.append({"name": cert, "issuer": "", "date": ""})
            elif isinstance(cert, dict):
                # Ensure required fields exist
                if "name" not in cert:
                    cert["name"] = cert.get("title", "Certification")
                normalized_certs.append(cert)
        data["certifications"] = normalized_certs
    
    # Normalize achievements - convert strings to Achievement dicts
    if "achievements" in data and isinstance(data["achievements"], list):
        normalized_achievements = []
        for ach in data["achievements"]:
            if isinstance(ach, str):
                normalized_achievements.append({"title": ach, "description": ""})
            elif isinstance(ach, dict):
                if "title" not in ach:
                    ach["title"] = ach.get("name", "Achievement")
                normalized_achievements.append(ach)
        data["achievements"] = normalized_achievements
    
    # Normalize extracurricular - convert strings to Extracurricular dicts
    if "extracurricular" in data and isinstance(data["extracurricular"], list):
        normalized_extra = []
        for item in data["extracurricular"]:
            if isinstance(item, str):
                normalized_extra.append({"organization": item, "role": "", "description": ""})
            elif isinstance(item, dict):
                if "organization" not in item:
                    item["organization"] = item.get("name", item.get("title", "Activity"))
                normalized_extra.append(item)
        data["extracurricular"] = normalized_extra
    
    # Ensure bullets are lists in experience/projects/education
    for section in ["experience", "projects", "education"]:
        if section in data and isinstance(data[section], list):
            for item in data[section]:
                if isinstance(item, dict) and "bullets" in item:
                    if isinstance(item["bullets"], str):
                        item["bullets"] = [b.strip() for b in item["bullets"].split("\n") if b.strip()]
    
    return data


def check_bullet_quality(bullet: str) -> Dict[str, Any]:
    """Check the quality of a bullet point."""
    issues = []
    
    # Check for weak phrases
    lower_bullet = bullet.lower()
    for phrase in WEAK_PHRASES:
        if phrase in lower_bullet:
            issues.append(f"Contains weak phrase: '{phrase}'")
    
    # Check for action verb at start
    first_word = bullet.split()[0] if bullet.split() else ""
    has_action_verb = any(
        first_word.lower() in [v.lower() for v in verbs]
        for verbs in ACTION_VERBS.values()
    )
    
    if not has_action_verb and first_word:
        issues.append("Does not start with strong action verb")
    
    # Check for quantification
    has_numbers = bool(re.search(r'\d+', bullet))
    has_percentage = bool(re.search(r'\d+%', bullet))
    
    return {
        "bullet": bullet,
        "has_action_verb": has_action_verb,
        "has_quantification": has_numbers or has_percentage,
        "issues": issues,
        "quality_score": 10 - len(issues) * 2 - (0 if has_action_verb else 2) - (0 if has_numbers else 1)
    }


def optimize_content(state: WorkflowState) -> WorkflowState:
    """
    Main optimization node - optimizes content for target role with ADAPTIVE PAGE PRESSURE.
    
    This is LangGraph Node 4: Resume Content Optimization
    
    Implements:
    - Soft one-page constraint (≈95% one-page target)
    - Adaptive compression based on page_pressure [0.3, 0.9]
    - Intelligent bullet rewriting with quality preservation
    - Score monotonicity enforcement
    """
    if not state.resume_data:
        state.error = "No resume data to optimize"
        return state
    
    if not state.target_role:
        state.error = "No target role specified"
        return state
    
    try:
        # Import line estimation functions
        from .adaptive_optimizer import estimate_resume_lines, get_structural_reduction_plan
        
        # Estimate current line usage
        line_counts = estimate_resume_lines(state.resume_data)
        estimated_lines = line_counts.get('total', 50)
        state.estimated_lines = estimated_lines
        
        # Get escalation action
        escalation_action = state.get_escalation_action() if hasattr(state, 'get_escalation_action') else 'rewrite'
        
        # Get structural reduction plan if over budget
        reduction_plan = get_structural_reduction_plan(state.resume_data, state.escalation_level if hasattr(state, 'escalation_level') else 0)
        
        # Get current compression level based on page pressure
        compression_level = get_compression_level(state.page_pressure)
        compression_behavior = COMPRESSION_BEHAVIOR_TEMPLATES.get(compression_level, COMPRESSION_BEHAVIOR_TEMPLATES['light'])
        
        # Add reduction plan info to compression behavior
        if reduction_plan.get('actions'):
            action_lines = [f"- {action[2]}" for action in reduction_plan['actions']]
            compression_behavior += f"\n\n=== 📋 STRUCTURAL REDUCTION PLAN (Lines over: {reduction_plan['overflow_lines']}) ===\n"
            compression_behavior += "\n".join(action_lines)
        
        # Convert resume data to JSON for LLM
        resume_json = json.dumps(state.resume_data.to_dict(), indent=2)
        
        print(f"📏 Line estimate: {estimated_lines} lines (target: 48, overflow: {reduction_plan['overflow_lines']})")
        
        # Build the adaptive optimization prompt
        prompt = OPTIMIZATION_PROMPT.format(
            target_role=state.target_role,
            page_pressure=state.page_pressure,
            compression_level=compression_level.upper(),
            escalation_action=escalation_action.upper(),
            estimated_lines=estimated_lines,
            resume_data=resume_json,
            compression_behavior=compression_behavior
        )
        
        # Call LLM for optimization
        response = call_llm(
            system_prompt="You are a professional resume optimizer. Output ONLY valid JSON. Preserve ALL original information while making bullets more concise and impactful. NEVER lose meaning or important details.",
            user_prompt=prompt
        )
        
        # Parse optimized data
        optimized_data = parse_llm_json(response)
        
        # Normalize the data to handle LLM output variations
        optimized_data = normalize_optimized_data(optimized_data)
        
        # Create optimized ResumeData
        state.optimized_data = ResumeData.from_dict(optimized_data)
        state.current_node = "optimization_complete"
        
        print(f"📊 Optimization complete (pressure: {state.page_pressure:.2f}, level: {compression_level})")
        
    except json.JSONDecodeError as e:
        state.error = f"Failed to parse optimized data: {str(e)}"
    except Exception as e:
        state.error = f"Optimization error: {str(e)}"
    
    return state
