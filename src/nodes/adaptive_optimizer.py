"""
Adaptive Page Optimization Module

Implements intelligent, pressure-aware resume compression:
- Soft one-page constraint (≈95% one-page target)
- Adaptive page pressure model [0.3, 0.9]
- Score monotonicity enforcement
- Intelligent bullet rewriting and merging
- Quality-preserving compression strategies
- LINE-AWARE layout optimization (1 line ≈ 90 chars, target 46-50 lines)
"""
import re
import json
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from ..models import WorkflowState, ResumeData
from ..utils.llm_client import call_llm


# ============================================================================
# LINE BUDGET CONSTANTS (1 line ≈ 90 characters)
# ============================================================================

CHARS_PER_LINE = 90
TARGET_TOTAL_LINES = 48  # Target 46-50 lines for one page

# Soft targets for section line allocation
SECTION_LINE_BUDGETS = {
    'header': 4,           # Name, contact info
    'education': 5,        # 4-5 lines
    'experience': 13,      # 12-14 lines
    'projects': 13,        # 12-14 lines
    'skills': 5,           # 4-5 lines
    'extracurricular': 3,  # 3-4 lines
    'optional': 4,         # certifications, achievements combined
}

# Maximum items per section at each escalation level
ESCALATION_LIMITS = {
    # escalation_level: {section: (max_items, max_bullets_per_item)}
    0: {'experience': (4, 4), 'projects': (4, 3), 'education': (2, 3)},  # Rewrite only
    1: {'experience': (3, 3), 'projects': (3, 2), 'education': (2, 2)},  # Reduce bullets
    2: {'experience': (2, 2), 'projects': (3, 2), 'education': (2, 1)},  # Reduce items
    3: {'experience': (2, 2), 'projects': (2, 2), 'education': (1, 0)},  # Trim sections
}


# ============================================================================
# LINE ESTIMATION FUNCTIONS
# ============================================================================

def estimate_text_lines(text: str) -> int:
    """Estimate how many resume lines a text string will occupy."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / CHARS_PER_LINE))


def estimate_bullet_lines(bullets: List[str]) -> int:
    """Estimate total lines for a list of bullets."""
    if not bullets:
        return 0
    total = 0
    for bullet in bullets:
        # Each bullet takes at least 1 line, plus overflow
        total += estimate_text_lines(bullet)
    return total


def estimate_section_lines(section_name: str, data: Any) -> int:
    """
    Estimate lines for a specific section.
    
    Returns estimated line count for the section.
    """
    if not data:
        return 0
    
    lines = 1  # Section header
    
    if section_name == 'education':
        for edu in data if isinstance(data, list) else [data]:
            # Institution + Degree line
            lines += 1
            # GPA/dates line
            if hasattr(edu, 'gpa') and edu.gpa:
                lines += 1
            # Coursework
            if hasattr(edu, 'coursework') and edu.coursework:
                coursework_text = ', '.join(edu.coursework)
                lines += estimate_text_lines(coursework_text)
            # Achievements
            if hasattr(edu, 'achievements') and edu.achievements:
                lines += estimate_bullet_lines(edu.achievements)
    
    elif section_name == 'experience':
        for exp in data if isinstance(data, list) else [data]:
            # Title + Company line
            lines += 1
            # Dates/location line (sometimes merged)
            lines += 1
            # Bullets
            if hasattr(exp, 'bullets') and exp.bullets:
                lines += estimate_bullet_lines(exp.bullets)
    
    elif section_name == 'projects':
        for proj in data if isinstance(data, list) else [data]:
            # Project name + tech stack line
            lines += 1
            # Bullets
            if hasattr(proj, 'bullets') and proj.bullets:
                lines += estimate_bullet_lines(proj.bullets)
    
    elif section_name == 'skills':
        if hasattr(data, 'languages') or isinstance(data, dict):
            # Each skill category is typically 1 line
            skill_categories = ['languages', 'frameworks', 'tools', 'databases', 'cloud', 'other']
            for cat in skill_categories:
                cat_data = getattr(data, cat, None) if hasattr(data, cat) else data.get(cat)
                if cat_data:
                    skill_text = ', '.join(cat_data) if isinstance(cat_data, list) else str(cat_data)
                    lines += estimate_text_lines(f"{cat}: {skill_text}")
    
    elif section_name == 'extracurricular':
        for ext in data if isinstance(data, list) else [data]:
            lines += 1  # Org + role
            if hasattr(ext, 'bullets') and ext.bullets:
                lines += estimate_bullet_lines(ext.bullets)
    
    elif section_name == 'certifications':
        # Typically 1 line per cert, or inline list
        lines += len(data) if isinstance(data, list) else 1
    
    elif section_name == 'achievements':
        lines += len(data) if isinstance(data, list) else 1
    
    return lines


def estimate_resume_lines(resume_data: ResumeData) -> Dict[str, int]:
    """
    Estimate total lines for entire resume, broken down by section.
    
    Returns dict with section names as keys and line counts as values.
    """
    line_counts = {
        'header': 4,  # Name + contact info
        'education': estimate_section_lines('education', resume_data.education),
        'experience': estimate_section_lines('experience', resume_data.experience),
        'projects': estimate_section_lines('projects', resume_data.projects),
        'skills': estimate_section_lines('skills', resume_data.skills),
        'extracurricular': estimate_section_lines('extracurricular', resume_data.extracurricular),
        'certifications': estimate_section_lines('certifications', resume_data.certifications),
        'achievements': estimate_section_lines('achievements', resume_data.achievements),
    }
    
    line_counts['total'] = sum(line_counts.values())
    return line_counts


def get_line_overflow(resume_data: ResumeData) -> int:
    """
    Calculate how many lines over budget the resume is.
    
    Returns positive number if over budget, negative if under.
    """
    line_counts = estimate_resume_lines(resume_data)
    return line_counts['total'] - TARGET_TOTAL_LINES


def identify_sections_to_compress(resume_data: ResumeData) -> List[Tuple[str, int, int]]:
    """
    Identify which sections are over their line budgets.
    
    Returns list of (section_name, current_lines, budget) tuples,
    sorted by how much over budget they are (descending).
    """
    line_counts = estimate_resume_lines(resume_data)
    over_budget = []
    
    for section, budget in SECTION_LINE_BUDGETS.items():
        current = line_counts.get(section, 0)
        if current > budget:
            over_budget.append((section, current, budget))
    
    # Sort by overflow amount (most over budget first)
    over_budget.sort(key=lambda x: x[1] - x[2], reverse=True)
    return over_budget


def get_structural_reduction_plan(resume_data: ResumeData, escalation_level: int) -> Dict[str, Any]:
    """
    Create a plan for structural reduction based on escalation level.
    
    Returns dict with reduction instructions per section.
    """
    limits = ESCALATION_LIMITS.get(escalation_level, ESCALATION_LIMITS[3])
    line_counts = estimate_resume_lines(resume_data)
    overflow = line_counts['total'] - TARGET_TOTAL_LINES
    
    plan = {
        'overflow_lines': overflow,
        'escalation_level': escalation_level,
        'actions': []
    }
    
    if overflow <= 0:
        return plan
    
    # Priority order for reduction
    if escalation_level >= 3:
        # TRIM SECTIONS: Remove optional sections entirely
        if resume_data.achievements:
            plan['actions'].append(('remove_section', 'achievements', 'Remove achievements section'))
        if resume_data.certifications:
            plan['actions'].append(('remove_section', 'certifications', 'Remove certifications section'))
        if resume_data.extracurricular:
            plan['actions'].append(('remove_section', 'extracurricular', 'Remove extracurricular section'))
    
    if escalation_level >= 2:
        # REDUCE ITEMS: Remove weakest projects/experiences
        exp_limit = limits['experience'][0]
        if len(resume_data.experience) > exp_limit:
            plan['actions'].append(('reduce_items', 'experience', f'Keep only top {exp_limit} experiences'))
        
        proj_limit = limits['projects'][0]
        if len(resume_data.projects) > proj_limit:
            plan['actions'].append(('reduce_items', 'projects', f'Keep only top {proj_limit} projects'))
    
    if escalation_level >= 1:
        # REDUCE BULLETS: Cut bullets per item
        exp_bullets = limits['experience'][1]
        plan['actions'].append(('reduce_bullets', 'experience', f'Max {exp_bullets} bullets per experience'))
        
        proj_bullets = limits['projects'][1]
        plan['actions'].append(('reduce_bullets', 'projects', f'Max {proj_bullets} bullets per project'))
    
    # Always: REWRITE bullets to be shorter
    plan['actions'].append(('rewrite', 'all', 'Shorten all bullets to 15-18 words max'))
    
    return plan


# ============================================================================
# BULLET QUALITY CONSTANTS
# ============================================================================

STRONG_ACTION_VERBS = [
    "Developed", "Designed", "Implemented", "Built", "Created", "Engineered",
    "Architected", "Optimized", "Enhanced", "Improved", "Streamlined", "Accelerated",
    "Led", "Managed", "Directed", "Orchestrated", "Spearheaded", "Coordinated",
    "Achieved", "Delivered", "Exceeded", "Accomplished", "Launched", "Deployed",
    "Automated", "Integrated", "Scaled", "Reduced", "Increased", "Transformed",
    "Analyzed", "Evaluated", "Researched", "Identified", "Established", "Pioneered",
]

WEAK_PHRASES_TO_REMOVE = [
    "worked on", "helped with", "responsible for", "assisted with",
    "was involved in", "participated in", "dealt with", "handled",
    "with the help of", "in order to", "various features",
    "different aspects", "multiple tasks", "several projects",
]

FILLER_PHRASES = [
    "in order to", "so that", "with the goal of", "for the purpose of",
    "as well as", "in addition to", "on a daily basis", "at the end of the day",
]


# ============================================================================
# BULLET REWRITING PROMPTS
# ============================================================================

BULLET_REWRITE_PROMPT = """You are an expert resume bullet point optimizer. Your task is to rewrite bullet points to be more concise, impactful, and ATS-optimized while preserving ALL original information.

COMPRESSION LEVEL: {compression_level}
TARGET ROLE: {target_role}

ORIGINAL BULLETS:
{bullets}

=== BULLET REWRITING RULES ===

1. **STRUCTURE (MANDATORY):**
   Each bullet MUST follow: <Action Verb> + <What You Did> + <How/Tech> + <Impact/Metric>
   If a component is missing in original, DO NOT hallucinate - just compress without it.

2. **VERB REPLACEMENT:**
   Replace weak verbs → strong verbs:
   ❌ worked on → ✅ developed/built/designed
   ❌ helped build → ✅ co-developed/contributed to
   ❌ involved in → ✅ participated/collaborated
   ❌ responsible for → ✅ managed/led/owned

3. **FILLER REMOVAL:**
   Remove these phrases completely:
   - "with the help of" → remove
   - "in order to" → remove  
   - "responsible for" → remove
   - "various features" → be specific

4. **SENTENCE → PHRASE CONVERSION:**
   ❌ "Developed a backend system that was used to handle user authentication"
   ✅ "Developed JWT-based authentication system for secure user access"

5. **INTELLIGENT MERGING (if compression_level >= medium):**
   ❌ "Built REST APIs using Node.js" + "Integrated MongoDB for data storage"
   ✅ "Built RESTful APIs using Node.js with MongoDB-backed persistence"

6. **ONE-LINE TARGET:**
   - Prefer bullets that are 18-22 words max
   - Multi-line only if impact justifies it

7. **PRESERVE (CRITICAL):**
   - ALL technical keywords and tools
   - ALL metrics and numbers
   - ALL quantified achievements
   - ATS-relevant terms

{compression_instructions}

=== OUTPUT FORMAT ===
Return a JSON array of rewritten bullets. Each bullet should be a string.
Output ONLY valid JSON array, no explanations.

Example output:
["Bullet 1 rewritten", "Bullet 2 rewritten", "Bullet 3 rewritten"]
"""

COMPRESSION_INSTRUCTIONS = {
    'light': """
=== LIGHT COMPRESSION (page_pressure < 0.45) ===
- Focus on wording refinement only
- Merge bullets semantically where obvious
- Remove redundancy
- Improve information density
- NO content removal
- Keep all bullets, just make them tighter
- MAX 4 bullets per experience/project
""",
    'medium': """
=== MEDIUM COMPRESSION (0.45 ≤ page_pressure < 0.6) ===
- Cap bullets: Experience max 3, Projects max 2-3
- Shorten bullets to fit ONE LINE (15-18 words max)
- Convert sentences → phrases aggressively
- Merge related bullets
- Remove redundant information
- Remove achievements section if not exceptional
- Keep all high-impact content
""",
    'aggressive': """
=== AGGRESSIVE COMPRESSION (0.6 ≤ page_pressure < 0.8) ===
- Keep only TOP 2 bullets per experience
- Keep only TOP 2 bullets per project
- MAX 3 experiences, MAX 3-4 projects
- Remove weakest bullets (no metrics, generic)
- Remove optional sections (certifications, achievements)
- Maximum density, minimum fluff
- EVERY bullet must have a metric
""",
    'maximum': """
=== MAXIMUM COMPRESSION (page_pressure ≥ 0.8) - NUCLEAR OPTION ===
- Keep only TOP 2 bullets per experience (STRICT)
- Keep only TOP 2 bullets per project (STRICT)
- MAX 2-3 experiences only
- MAX 2-3 projects only
- REMOVE: achievements, certifications, extracurricular unless exceptional
- Education: ONLY degree, school, GPA, dates - NO bullets
- Skills: MAX 5 items per category
- Bullets MUST be under 15 words
- EVERY bullet MUST have a number/metric
- If no metric, REMOVE the bullet
"""
}


# ============================================================================
# BULLET QUALITY SCORING
# ============================================================================

@dataclass
class BulletQuality:
    """Quality assessment for a bullet point."""
    text: str
    has_action_verb: bool
    has_quantification: bool
    has_technical_terms: bool
    word_count: int
    impact_score: float  # 0-10 scale
    issues: List[str]
    
    @property
    def is_high_quality(self) -> bool:
        return self.impact_score >= 7 and not self.issues


def assess_bullet_quality(bullet: str) -> BulletQuality:
    """
    Assess the quality of a single bullet point.
    
    Returns BulletQuality with detailed analysis.
    """
    issues = []
    impact_score = 10.0
    
    words = bullet.split()
    word_count = len(words)
    
    # Check for action verb at start
    first_word = words[0] if words else ""
    has_action_verb = any(
        first_word.lower() == verb.lower() or first_word.lower().startswith(verb.lower()[:4])
        for verb in STRONG_ACTION_VERBS
    )
    
    if not has_action_verb:
        issues.append("Missing strong action verb at start")
        impact_score -= 1.5
    
    # Check for weak phrases
    lower_bullet = bullet.lower()
    for phrase in WEAK_PHRASES_TO_REMOVE:
        if phrase in lower_bullet:
            issues.append(f"Contains weak phrase: '{phrase}'")
            impact_score -= 1.0
    
    # Check for quantification
    has_quantification = bool(re.search(r'\d+', bullet))
    has_percentage = bool(re.search(r'\d+%', bullet))
    
    if not has_quantification:
        issues.append("No quantification (numbers/metrics)")
        impact_score -= 1.0
    elif has_percentage:
        impact_score += 0.5  # Bonus for percentage metrics
    
    # Check for technical terms (simple heuristic)
    tech_patterns = [
        r'\b(API|REST|GraphQL|SQL|NoSQL|ML|AI|NLP|AWS|GCP|Azure|Docker|K8s|CI/CD)\b',
        r'\b(Python|Java|JavaScript|TypeScript|React|Node|Go|Rust|C\+\+)\b',
        r'\b(TensorFlow|PyTorch|Pandas|NumPy|Kubernetes|Redis|MongoDB)\b',
    ]
    has_technical_terms = any(re.search(p, bullet, re.IGNORECASE) for p in tech_patterns)
    
    if has_technical_terms:
        impact_score += 0.5  # Bonus for technical keywords
    
    # Check length
    if word_count > 25:
        issues.append("Bullet too long (>25 words)")
        impact_score -= 0.5
    elif word_count < 5:
        issues.append("Bullet too short (<5 words)")
        impact_score -= 1.0
    
    # Check for filler phrases
    for filler in FILLER_PHRASES:
        if filler in lower_bullet:
            issues.append(f"Contains filler: '{filler}'")
            impact_score -= 0.5
    
    return BulletQuality(
        text=bullet,
        has_action_verb=has_action_verb,
        has_quantification=has_quantification,
        has_technical_terms=has_technical_terms,
        word_count=word_count,
        impact_score=max(0, min(10, impact_score)),
        issues=issues
    )


def rank_bullets_by_impact(bullets: List[str]) -> List[Tuple[str, float]]:
    """
    Rank bullets by impact score.
    
    Returns list of (bullet, score) tuples sorted by score descending.
    """
    scored = [(b, assess_bullet_quality(b).impact_score) for b in bullets]
    return sorted(scored, key=lambda x: x[1], reverse=True)


# ============================================================================
# ADAPTIVE COMPRESSION ENGINE
# ============================================================================

def get_compression_instructions(page_pressure: float) -> str:
    """Get compression instructions based on page pressure level."""
    if page_pressure < 0.45:
        return COMPRESSION_INSTRUCTIONS['light']
    elif page_pressure < 0.6:
        return COMPRESSION_INSTRUCTIONS['medium']
    elif page_pressure < 0.8:
        return COMPRESSION_INSTRUCTIONS['aggressive']
    else:
        return COMPRESSION_INSTRUCTIONS['maximum']


def get_compression_level(page_pressure: float) -> str:
    """Get compression level string based on page pressure."""
    if page_pressure < 0.45:
        return 'light'
    elif page_pressure < 0.6:
        return 'medium'
    elif page_pressure < 0.8:
        return 'aggressive'
    else:
        return 'maximum'


def rewrite_bullets_with_llm(
    bullets: List[str],
    target_role: str,
    page_pressure: float
) -> List[str]:
    """
    Use LLM to rewrite bullets with compression awareness.
    
    Args:
        bullets: List of original bullet points
        target_role: Target job role for optimization
        page_pressure: Current page pressure [0.3, 0.9]
        
    Returns:
        List of rewritten bullet points
    """
    if not bullets:
        return []
    
    compression_level = get_compression_level(page_pressure)
    compression_instructions = get_compression_instructions(page_pressure)
    
    prompt = BULLET_REWRITE_PROMPT.format(
        compression_level=compression_level.upper(),
        target_role=target_role,
        bullets=json.dumps(bullets, indent=2),
        compression_instructions=compression_instructions
    )
    
    try:
        response = call_llm(
            system_prompt="You are an expert resume optimizer. Output ONLY valid JSON array.",
            user_prompt=prompt,
            temperature=0
        )
        
        # Parse response
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1] if "\n" in response else response[3:]
            if response.endswith("```"):
                response = response[:-3]
        
        # Find JSON array
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            rewritten = json.loads(json_match.group(0))
            if isinstance(rewritten, list) and all(isinstance(b, str) for b in rewritten):
                return rewritten
        
        return bullets  # Return original if parsing fails
        
    except Exception as e:
        print(f"Bullet rewriting failed: {e}")
        return bullets


def apply_bullet_limits(
    bullets: List[str],
    max_bullets: int,
    page_pressure: float
) -> List[str]:
    """
    Apply bullet count limits based on compression level.
    
    Keeps highest-impact bullets when reducing.
    """
    if len(bullets) <= max_bullets:
        return bullets
    
    # Rank by impact and keep top ones
    ranked = rank_bullets_by_impact(bullets)
    return [b for b, _ in ranked[:max_bullets]]


def compress_resume_data(
    resume_data: ResumeData,
    target_role: str,
    page_pressure: float
) -> ResumeData:
    """
    Apply pressure-aware compression to resume data.
    
    Args:
        resume_data: Original resume data
        target_role: Target job role
        page_pressure: Current page pressure [0.3, 0.9]
        
    Returns:
        Compressed ResumeData
    """
    data_dict = resume_data.to_dict()
    compression_level = get_compression_level(page_pressure)
    
    # Determine limits based on compression level
    if compression_level == 'light':
        exp_bullet_limit = 5
        proj_bullet_limit = 4
        exp_limit = None  # No limit
        proj_limit = None
    elif compression_level == 'medium':
        exp_bullet_limit = 3
        proj_bullet_limit = 3
        exp_limit = 4
        proj_limit = 4
    else:  # aggressive
        exp_bullet_limit = 2
        proj_bullet_limit = 2
        exp_limit = 3
        proj_limit = 3
    
    # Process experience bullets
    if data_dict.get('experience'):
        experiences = data_dict['experience']
        
        # Limit number of experiences if aggressive
        if exp_limit and len(experiences) > exp_limit:
            experiences = experiences[:exp_limit]
        
        for exp in experiences:
            if exp.get('bullets'):
                # Rewrite bullets
                exp['bullets'] = rewrite_bullets_with_llm(
                    exp['bullets'],
                    target_role,
                    page_pressure
                )
                # Apply limits
                exp['bullets'] = apply_bullet_limits(
                    exp['bullets'],
                    exp_bullet_limit,
                    page_pressure
                )
        
        data_dict['experience'] = experiences
    
    # Process project bullets
    if data_dict.get('projects'):
        projects = data_dict['projects']
        
        # Limit number of projects if aggressive
        if proj_limit and len(projects) > proj_limit:
            projects = projects[:proj_limit]
        
        for proj in projects:
            if proj.get('bullets'):
                # Rewrite bullets
                proj['bullets'] = rewrite_bullets_with_llm(
                    proj['bullets'],
                    target_role,
                    page_pressure
                )
                # Apply limits
                proj['bullets'] = apply_bullet_limits(
                    proj['bullets'],
                    proj_bullet_limit,
                    page_pressure
                )
        
        data_dict['projects'] = projects
    
    # Handle optional sections in aggressive mode
    if compression_level == 'aggressive':
        # Reduce achievements to max 2
        if data_dict.get('achievements') and len(data_dict['achievements']) > 2:
            data_dict['achievements'] = data_dict['achievements'][:2]
        
        # Reduce certifications to max 2
        if data_dict.get('certifications') and len(data_dict['certifications']) > 2:
            data_dict['certifications'] = data_dict['certifications'][:2]
        
        # Reduce extracurricular to max 2
        if data_dict.get('extracurricular') and len(data_dict['extracurricular']) > 2:
            data_dict['extracurricular'] = data_dict['extracurricular'][:2]
    
    return ResumeData.from_dict(data_dict)


# ============================================================================
# QUALITY VERIFICATION
# ============================================================================

def verify_compression_quality(
    original_bullets: List[str],
    compressed_bullets: List[str]
) -> Tuple[bool, List[str]]:
    """
    Verify that compression maintained or improved quality.
    
    Returns:
        (is_acceptable, issues) tuple
    """
    issues = []
    
    # Calculate original quality
    original_scores = [assess_bullet_quality(b).impact_score for b in original_bullets]
    original_avg = sum(original_scores) / len(original_scores) if original_scores else 0
    
    # Calculate compressed quality
    compressed_scores = [assess_bullet_quality(b).impact_score for b in compressed_bullets]
    compressed_avg = sum(compressed_scores) / len(compressed_scores) if compressed_scores else 0
    
    # Check if quality dropped significantly
    if compressed_avg < original_avg - 1.0:
        issues.append(f"Quality dropped: {original_avg:.1f} → {compressed_avg:.1f}")
    
    # Check if technical keywords were preserved
    original_text = ' '.join(original_bullets).lower()
    compressed_text = ' '.join(compressed_bullets).lower()
    
    tech_keywords = re.findall(r'\b[A-Z][a-zA-Z]*(?:\+\+|#)?\b', ' '.join(original_bullets))
    for keyword in tech_keywords:
        if keyword.lower() in original_text and keyword.lower() not in compressed_text:
            issues.append(f"Lost technical keyword: {keyword}")
    
    # Check if metrics were preserved
    original_numbers = re.findall(r'\d+%?', ' '.join(original_bullets))
    compressed_numbers = re.findall(r'\d+%?', ' '.join(compressed_bullets))
    
    if len(compressed_numbers) < len(original_numbers) * 0.7:  # Allow some loss
        issues.append("Significant metric loss detected")
    
    is_acceptable = len(issues) == 0
    return is_acceptable, issues


# ============================================================================
# MAIN ADAPTIVE OPTIMIZATION FUNCTION
# ============================================================================

ADAPTIVE_OPTIMIZATION_PROMPT = """You are an elite resume optimization AI implementing SOFT ONE-PAGE OPTIMIZATION.

🎯 CORE DIRECTIVE:
Your primary goal is to produce a high-quality, ATS-optimized resume that fits on one page in MOST cases (≈95%).
One-page is a strong preference, not an absolute rule.

TARGET ROLE: {target_role}
CURRENT PAGE PRESSURE: {page_pressure:.2f} (Range: 0.3-0.9)
COMPRESSION LEVEL: {compression_level}

CURRENT RESUME DATA:
{resume_data}

{compression_behavior}

=== BULLET REWRITING PRINCIPLES (MANDATORY) ===

Every bullet point MUST follow this structure:
<Action Verb> + <What You Did> + <How/Tech> + <Impact/Metric>

1️⃣ REPLACE WEAK VERBS:
   ❌ worked on, helped build, involved in
   ✅ designed, implemented, optimized, automated, reduced, scaled

2️⃣ REMOVE FILLER PHRASES:
   ❌ "with the help of", "in order to", "responsible for", "various features"

3️⃣ CONVERT SENTENCES → PHRASES:
   ❌ "Developed a backend system that was used to handle user authentication and authorization."
   ✅ "Developed JWT-based authentication system for secure user access."

4️⃣ MERGE BULLETS INTELLIGENTLY:
   ❌ "Built REST APIs using Node.js" + "Integrated MongoDB for data storage"
   ✅ "Built RESTful APIs using Node.js with MongoDB-backed persistence."

5️⃣ ONE-LINE BULLET RULE:
   - Prefer bullets that fit in one LaTeX line
   - Max ~18-22 words per bullet
   - Multi-line only if impact justifies it

=== ATS DENSITY REQUIREMENTS ===
When shortening bullets:
- PRESERVE technical keywords
- PRESERVE tools & technologies
- PRESERVE metrics and numbers
- Do NOT compress away ATS-relevant terms

=== QUALITY GOLDEN RULE ===
"If a bullet gets shorter but weaker, the optimization failed."

Each bullet MUST represent the FULL information from the original - never lose meaning!

=== OUTPUT FORMAT ===
Return the COMPLETE optimized resume data in the EXACT same JSON structure.
Output ONLY valid JSON, no explanations or markdown.
"""

COMPRESSION_BEHAVIOR_TEMPLATES = {
    'light': """
🧩 LIGHT COMPRESSION (page_pressure < 0.45):
- Focus on wording refinement
- Merge bullets semantically
- Remove redundancy
- Improve information density
- MAX 4 bullets per experience/project
- NO content removal - just tighten wording
""",
    'medium': """
🧩 MEDIUM COMPRESSION (0.45 ≤ page_pressure < 0.6):
- Cap bullets per item:
  • Experience: max 3 bullets each
  • Projects: max 2-3 bullets each
- Shorten bullets to ONE LINE (15-18 words max)
- Convert full sentences → concise phrases
- Merge related achievements
- Remove achievements section if not exceptional
""",
    'aggressive': """
🧩 AGGRESSIVE COMPRESSION (0.6 ≤ page_pressure < 0.8):
- Keep only TOP 2 bullets per experience
- Keep only TOP 2 bullets per project
- MAX 3 experiences, MAX 3-4 projects total
- Remove OPTIONAL sections (achievements, certifications)
- EVERY bullet must have a metric
- Maximum density mode
- Bullets under 15 words only
""",
    'maximum': """
🧩 MAXIMUM COMPRESSION (page_pressure ≥ 0.8) - NUCLEAR OPTION:
- MAX 2 bullets per experience (STRICT)
- MAX 2 bullets per project (STRICT)
- MAX 2-3 experiences total
- MAX 2-3 projects total
- REMOVE: achievements, certifications, extracurricular
- Education: degree, school, GPA, dates ONLY - NO bullets
- Skills: MAX 5 items per category
- Bullets MUST be under 15 words
- NO bullet without a number/metric
- Fix ALL spacing issues (no "LLMdriven" → "LLM-driven")
"""
}


def adaptive_optimize_content(state: WorkflowState) -> WorkflowState:
    """
    Main adaptive optimization function.
    
    Implements pressure-aware content optimization with:
    - Soft one-page constraint
    - Score monotonicity enforcement
    - Intelligent bullet rewriting
    - Quality preservation
    """
    if not state.resume_data:
        state.error = "No resume data to optimize"
        return state
    
    if not state.target_role:
        state.error = "No target role specified"
        return state
    
    try:
        # Get current compression level
        compression_level = get_compression_level(state.page_pressure)
        compression_behavior = COMPRESSION_BEHAVIOR_TEMPLATES[compression_level]
        
        # Convert resume data to JSON
        resume_json = json.dumps(state.resume_data.to_dict(), indent=2)
        
        # Build the optimization prompt
        prompt = ADAPTIVE_OPTIMIZATION_PROMPT.format(
            target_role=state.target_role,
            page_pressure=state.page_pressure,
            compression_level=compression_level.upper(),
            resume_data=resume_json,
            compression_behavior=compression_behavior
        )
        
        # Call LLM for optimization
        response = call_llm(
            system_prompt="You are a professional resume optimizer. Output ONLY valid JSON. Preserve ALL original information while making bullets more concise and impactful.",
            user_prompt=prompt
        )
        
        # Parse response
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1] if "\n" in response else response[3:]
            if response.endswith("```"):
                response = response[:-3]
        
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            optimized_data = json.loads(json_match.group(0))
        else:
            optimized_data = json.loads(response)
        
        # Normalize the data
        optimized_data = _normalize_optimized_data(optimized_data)
        
        # Create optimized ResumeData
        state.optimized_data = ResumeData.from_dict(optimized_data)
        state.current_node = "optimization_complete"
        
        print(f"📊 Adaptive optimization complete (pressure: {state.page_pressure:.2f}, level: {compression_level})")
        
    except json.JSONDecodeError as e:
        state.error = f"Failed to parse optimized data: {str(e)}"
    except Exception as e:
        state.error = f"Optimization error: {str(e)}"
    
    return state


def _normalize_optimized_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize LLM output to match expected Pydantic schema."""
    # Normalize skills
    if "skills" in data and isinstance(data["skills"], dict):
        skills = data["skills"]
        skill_fields = ["languages", "frameworks", "tools", "databases", "cloud", "soft_skills", "other"]
        for field in skill_fields:
            if field in skills:
                value = skills[field]
                if isinstance(value, str):
                    skills[field] = [s.strip() for s in value.split(",") if s.strip()]
                elif not isinstance(value, list):
                    skills[field] = []
    
    # Normalize certifications
    if "certifications" in data and isinstance(data["certifications"], list):
        normalized_certs = []
        for cert in data["certifications"]:
            if isinstance(cert, str):
                normalized_certs.append({"name": cert, "issuer": "", "date": ""})
            elif isinstance(cert, dict):
                if "name" not in cert:
                    cert["name"] = cert.get("title", "Certification")
                normalized_certs.append(cert)
        data["certifications"] = normalized_certs
    
    # Normalize achievements
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
    
    # Normalize extracurricular
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
    
    # Ensure bullets are lists
    for section in ["experience", "projects", "education"]:
        if section in data and isinstance(data[section], list):
            for item in data[section]:
                if isinstance(item, dict) and "bullets" in item:
                    if isinstance(item["bullets"], str):
                        item["bullets"] = [b.strip() for b in item["bullets"].split("\n") if b.strip()]
    
    return data


def apply_incremental_compression(state: WorkflowState) -> WorkflowState:
    """
    Apply incremental compression when pages > 1.
    
    This function is called during the iteration loop to progressively
    compress content while maintaining quality.
    """
    if not state.optimized_data:
        return state
    
    # First, save a checkpoint
    state.save_checkpoint()
    
    # Apply compression based on current pressure
    compressed_data = compress_resume_data(
        state.optimized_data,
        state.target_role,
        state.page_pressure
    )
    
    state.optimized_data = compressed_data
    state.compression_attempts += 1
    
    return state
