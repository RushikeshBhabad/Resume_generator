"""
Node 7: Iterative Resume Evaluation (LLM-Powered) with ADAPTIVE PAGE OPTIMIZATION

Evaluates the resume on multiple criteria and triggers improvements if needed.
Implements:
- Soft one-page constraint (page count as penalty, not failure)
- Score monotonicity enforcement (scores must not decrease)
- Adaptive page pressure updates
- Intelligent iteration control
"""
import re
import json
from typing import Dict, List, Tuple

from ..models import WorkflowState, ResumeScore, EvaluationResult, ResumeData
from ..utils.helpers import get_page_count
from ..utils.llm_client import call_llm


LLM_REVIEW_PROMPT = """You are an expert resume reviewer implementing ADAPTIVE QUALITY ASSESSMENT.

TARGET ROLE: {target_role}
CURRENT PAGE COUNT: {page_count}
CURRENT PAGE PRESSURE: {page_pressure:.2f}

LATEX RESUME CODE:
{latex_code}

🎯 EVALUATION DIRECTIVE:
You are evaluating for QUALITY, not just page count.
One page is preferred, but two pages are acceptable if the content is high-quality and justified.

Evaluate the resume on these criteria:

1. **Role Alignment (0-30):** How well does the content match the target role?
   - Are skills relevant to {target_role}?
   - Are experiences aligned with career goals?
   - Are keywords present that recruiters look for?

2. **Clarity & Impact (0-25):** Are bullet points strong?
   - Do bullets start with strong action verbs?
   - Are achievements quantified with metrics?
   - Is each bullet point clear and impactful?
   - Does each bullet preserve FULL meaning (not over-compressed)?

3. **ATS Optimization (0-20):** Is the resume ATS-friendly?
   - Are relevant technical keywords present?
   - Is the formatting machine-readable?
   - Are important skills highlighted?

4. **Formatting & Density (0-15):** Is the layout optimal?
   - Is information dense but readable?
   - Is spacing appropriate?
   - Are sections well-organized?

5. **Grammar & Safety (0-10):** Any issues?
   - Spelling and grammar correct?
   - No dangerous LaTeX commands?
   - Professional language throughout?

📏 PAGE COUNT ASSESSMENT:
- 1 page with high score (≥90): Excellent
- 1 page with medium score (80-89): Good, minor improvements possible
- 2 pages with high score (≥92): Acceptable IF content justifies length
- 2 pages with lower score: Needs compression

RESPOND WITH ONLY A JSON OBJECT (no markdown, no explanation):
{{
    "role_alignment": <score 0-30>,
    "clarity_impact": <score 0-25>,
    "ats_optimization": <score 0-20>,
    "formatting_density": <score 0-15>,
    "grammar_safety": <score 0-10>,
    "needs_improvement": <true/false>,
    "two_pages_justified": <true/false if page_count > 1>,
    "issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1", "suggestion2"],
    "bullet_quality_notes": "Assessment of bullet point quality - are they preserving full information?",
    "improvement_instructions": "If needs_improvement is true, specific instructions for regeneration"
}}
"""


def llm_review_resume(latex_code: str, target_role: str, page_count: int, page_pressure: float = 0.4) -> Dict:
    """Use LLM to review the generated resume with adaptive awareness."""
    try:
        response = call_llm(
            system_prompt="You are a professional resume reviewer. Output ONLY valid JSON. Evaluate quality holistically - page count is important but not the only factor.",
            user_prompt=LLM_REVIEW_PROMPT.format(
                target_role=target_role,
                latex_code=latex_code[:8000],  # Limit size for LLM
                page_count=page_count,
                page_pressure=page_pressure
            ),
            temperature=0
        )
        
        # Parse JSON response
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1] if "\n" in response else response[3:]
            if response.endswith("```"):
                response = response[:-3]
        
        # Find JSON object
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group(0))
        
        return json.loads(response)
        
    except Exception as e:
        print(f"LLM review failed: {e}")
        return None


def check_grammar(text: str) -> List[str]:
    """
    Check for grammar and spelling errors.
    
    Returns list of errors found.
    """
    errors = []
    
    try:
        import language_tool_python
        tool = language_tool_python.LanguageTool('en-US')
        matches = tool.check(text)
        
        for match in matches[:10]:  # Limit to 10 errors
            errors.append(f"{match.ruleId}: {match.message}")
        
        tool.close()
    except Exception as e:
        # If language_tool is not available, do basic checks
        pass
    
    return errors


def evaluate_bullet_strength(bullets: List[str]) -> Tuple[int, List[str]]:
    """
    Evaluate the strength of bullet points.
    
    Returns (score out of 10, list of issues)
    """
    if not bullets:
        return 5, ["No bullet points found"]
    
    issues = []
    score = 10
    
    # Strong action verbs
    strong_verbs = [
        'developed', 'designed', 'implemented', 'built', 'created',
        'optimized', 'improved', 'reduced', 'increased', 'achieved',
        'led', 'managed', 'launched', 'deployed', 'engineered',
        'architected', 'automated', 'streamlined', 'accelerated'
    ]
    
    # Weak phrases
    weak_phrases = [
        'worked on', 'helped with', 'responsible for', 'assisted',
        'participated', 'involved in', 'dealt with'
    ]
    
    for bullet in bullets:
        lower_bullet = bullet.lower()
        
        # Check for weak phrases
        for phrase in weak_phrases:
            if phrase in lower_bullet:
                issues.append(f"Weak phrase '{phrase}' in: {bullet[:50]}...")
                score -= 1
        
        # Check for action verb at start
        first_word = bullet.split()[0].lower() if bullet.split() else ""
        if first_word not in strong_verbs and not any(v in first_word for v in strong_verbs):
            if not any(char.isdigit() for char in first_word):  # Allow numbers at start
                issues.append(f"Missing strong action verb at start: {bullet[:50]}...")
                score -= 0.5
        
        # Check for quantification
        if not re.search(r'\d+', bullet):
            issues.append(f"No quantification in: {bullet[:50]}...")
            score -= 0.5
    
    return max(0, min(10, int(score))), issues


def evaluate_ats_keywords(resume_data: ResumeData, target_role: str) -> Tuple[int, List[str]]:
    """
    Evaluate ATS keyword optimization.
    
    Returns (score out of 20, list of suggestions)
    """
    suggestions = []
    score = 15  # Start with base score
    
    # Common keywords by role type
    role_keywords = {
        'software': ['python', 'java', 'javascript', 'react', 'node', 'sql', 'git', 'agile', 'api', 'rest'],
        'data': ['python', 'sql', 'machine learning', 'pandas', 'numpy', 'visualization', 'statistics', 'analytics'],
        'machine learning': ['python', 'tensorflow', 'pytorch', 'deep learning', 'nlp', 'computer vision', 'neural network'],
        'frontend': ['javascript', 'react', 'vue', 'angular', 'css', 'html', 'typescript', 'responsive'],
        'backend': ['python', 'java', 'node', 'api', 'database', 'sql', 'microservices', 'rest'],
        'devops': ['docker', 'kubernetes', 'aws', 'ci/cd', 'jenkins', 'terraform', 'linux', 'automation'],
    }
    
    # Determine role category
    role_lower = target_role.lower()
    relevant_keywords = []
    
    for category, keywords in role_keywords.items():
        if category in role_lower:
            relevant_keywords.extend(keywords)
    
    if not relevant_keywords:
        relevant_keywords = role_keywords.get('software', [])
    
    # Check for keywords in skills
    all_skills = []
    if resume_data.skills:
        all_skills.extend(resume_data.skills.languages)
        all_skills.extend(resume_data.skills.frameworks)
        all_skills.extend(resume_data.skills.tools)
        all_skills.extend(resume_data.skills.databases)
        all_skills.extend(resume_data.skills.cloud)
    
    skills_lower = [s.lower() for s in all_skills]
    
    missing_keywords = []
    for keyword in relevant_keywords:
        if keyword not in skills_lower and keyword not in ' '.join(skills_lower):
            missing_keywords.append(keyword)
    
    if missing_keywords:
        suggestions.append(f"Consider adding relevant keywords: {', '.join(missing_keywords[:5])}")
        score -= len(missing_keywords) // 2
    
    return max(0, min(20, score)), suggestions


def evaluate_formatting(latex_code: str) -> Tuple[int, List[str]]:
    """
    Evaluate formatting and density.
    
    Returns (score out of 15, list of issues)
    """
    issues = []
    score = 15
    
    # Check for excessive spacing
    if latex_code.count('\n\n\n') > 3:
        issues.append("Excessive vertical spacing detected")
        score -= 2
    
    # Check for section balance
    sections = ['Education', 'Experience', 'Projects', 'Technical Skills']
    missing_sections = []
    
    for section in sections:
        if f"\\section{{{section}}}" not in latex_code:
            missing_sections.append(section)
    
    if missing_sections:
        issues.append(f"Missing mandatory sections: {', '.join(missing_sections)}")
        score -= len(missing_sections) * 2
    
    return max(0, min(15, score)), issues


def evaluate_role_alignment(resume_data: ResumeData, target_role: str) -> Tuple[int, List[str]]:
    """
    Evaluate how well the resume aligns with the target role.
    
    Returns (score out of 30, list of suggestions)
    """
    suggestions = []
    score = 25  # Start with good base score
    
    # Check if experience is relevant
    if resume_data.experience:
        role_words = target_role.lower().split()
        relevant_exp = 0
        
        for exp in resume_data.experience:
            title_lower = exp.title.lower()
            bullets_text = ' '.join(exp.bullets).lower()
            
            if any(word in title_lower or word in bullets_text for word in role_words):
                relevant_exp += 1
        
        if relevant_exp == 0:
            suggestions.append("No experience directly matches target role")
            score -= 5
    
    # Check projects alignment
    if resume_data.projects:
        relevant_proj = 0
        role_words = target_role.lower().split()
        
        for proj in resume_data.projects:
            tech_text = ' '.join(proj.technologies).lower()
            bullets_text = ' '.join(proj.bullets).lower()
            
            if any(word in tech_text or word in bullets_text for word in role_words):
                relevant_proj += 1
        
        if relevant_proj == 0:
            suggestions.append("Consider highlighting projects relevant to target role")
            score -= 3
    
    return max(0, min(30, score)), suggestions


def reduce_content_if_needed(state: WorkflowState) -> WorkflowState:
    """
    Apply ULTRA-AGGRESSIVE content reduction based on page_pressure.
    
    Priority order:
    1. Bullet rewriting & tightening (handled by optimizer)
    2. Bullet merging (handled by optimizer)
    3. Bullet count reduction
    4. Optional section removal
    5. Experience/project count reduction
    
    For intern/entry-level: ONE PAGE IS MANDATORY.
    """
    if not state.evaluation or state.evaluation.page_count <= 1:
        return state
    
    resume_data = state.optimized_data or state.resume_data
    if not resume_data:
        return state
    
    # Save checkpoint before modifications
    state.save_checkpoint()
    
    # Create a copy for modifications
    data_dict = resume_data.to_dict()
    
    # Get compression level based on current page pressure
    compression_level = state.get_compression_level()
    
    print(f"🔧 Applying {compression_level.upper()} compression (pressure: {state.page_pressure:.2f})")
    
    if compression_level == 'light':
        # Light compression: minimal changes
        if data_dict.get('experience'):
            for exp in data_dict['experience']:
                if len(exp.get('bullets', [])) > 4:
                    exp['bullets'] = exp['bullets'][:4]
        
        if data_dict.get('projects'):
            for proj in data_dict['projects']:
                if len(proj.get('bullets', [])) > 3:
                    proj['bullets'] = proj['bullets'][:3]
    
    elif compression_level == 'medium':
        # Medium compression: cap bullets per item
        if data_dict.get('experience'):
            for exp in data_dict['experience']:
                if len(exp.get('bullets', [])) > 3:
                    exp['bullets'] = exp['bullets'][:3]
        
        if data_dict.get('projects'):
            for proj in data_dict['projects']:
                if len(proj.get('bullets', [])) > 2:
                    proj['bullets'] = proj['bullets'][:2]
        
        # Reduce optional sections
        if data_dict.get('achievements'):
            data_dict['achievements'] = data_dict['achievements'][:1]
        
        if data_dict.get('certifications') and len(data_dict['certifications']) > 2:
            data_dict['certifications'] = data_dict['certifications'][:2]
    
    elif compression_level == 'aggressive':
        # Aggressive compression: remove more content
        
        # Cap experience bullets to 2
        if data_dict.get('experience'):
            if len(data_dict['experience']) > 3:
                data_dict['experience'] = data_dict['experience'][:3]
            for exp in data_dict['experience']:
                if len(exp.get('bullets', [])) > 2:
                    exp['bullets'] = exp['bullets'][:2]
        
        # Cap projects to 3, bullets to 2
        if data_dict.get('projects'):
            if len(data_dict['projects']) > 3:
                data_dict['projects'] = data_dict['projects'][:3]
            for proj in data_dict['projects']:
                if len(proj.get('bullets', [])) > 2:
                    proj['bullets'] = proj['bullets'][:2]
        
        # Remove optional sections
        data_dict['achievements'] = []
        if data_dict.get('certifications') and len(data_dict['certifications']) > 2:
            data_dict['certifications'] = data_dict['certifications'][:2]
        
        # Reduce extracurricular
        if data_dict.get('extracurricular') and len(data_dict['extracurricular']) > 1:
            data_dict['extracurricular'] = data_dict['extracurricular'][:1]
    
    else:  # maximum compression - NUCLEAR OPTION
        print("☢️ MAXIMUM COMPRESSION MODE - NUCLEAR OPTION")
        
        # Cap experience to 2-3, bullets to 2
        if data_dict.get('experience'):
            if len(data_dict['experience']) > 2:
                data_dict['experience'] = data_dict['experience'][:2]
            for exp in data_dict['experience']:
                if len(exp.get('bullets', [])) > 2:
                    exp['bullets'] = exp['bullets'][:2]
        
        # Cap projects to 2-3, bullets to 2
        if data_dict.get('projects'):
            if len(data_dict['projects']) > 3:
                data_dict['projects'] = data_dict['projects'][:3]
            for proj in data_dict['projects']:
                if len(proj.get('bullets', [])) > 2:
                    proj['bullets'] = proj['bullets'][:2]
        
        # Remove ALL optional sections
        data_dict['achievements'] = []
        data_dict['certifications'] = []
        data_dict['extracurricular'] = []
        
        # Remove education bullets
        if data_dict.get('education'):
            for edu in data_dict['education']:
                edu['achievements'] = []
                edu['coursework'] = edu.get('coursework', [])[:3] if edu.get('coursework') else []
    
    # Update state
    state.optimized_data = ResumeData.from_dict(data_dict)
    state.compression_attempts += 1
    
    return state


def evaluate_resume(state: WorkflowState) -> WorkflowState:
    """
    Main evaluation node with ADAPTIVE PAGE OPTIMIZATION.
    
    This is LangGraph Node 7: Iterative Resume Evaluation
    
    Implements:
    - Soft one-page constraint (page count as penalty, not failure)
    - Score monotonicity enforcement (scores must not decrease)
    - Adaptive page pressure updates
    - Intelligent iteration control
    """
    state.iteration_count += 1
    
    if not state.latex_code:
        state.error = "No LaTeX code to evaluate"
        return state
    
    resume_data = state.optimized_data or state.resume_data
    if not resume_data:
        state.error = "No resume data to evaluate"
        return state
    
    try:
        # Initialize evaluation result
        evaluation = EvaluationResult()
        score = ResumeScore()
        
        # Check page count
        if state.pdf_path:
            evaluation.page_count = get_page_count(state.pdf_path)
            
            # Update page pressure based on page count (ADAPTIVE LOGIC)
            state.update_page_pressure(evaluation.page_count)
            
            if evaluation.page_count > 1:
                evaluation.issues.append(f"Resume is {evaluation.page_count} pages (target: 1)")
        
        # Use LLM to review the resume (with page pressure awareness)
        llm_review = llm_review_resume(
            state.latex_code, 
            state.target_role or "Software Engineer",
            evaluation.page_count,
            state.page_pressure
        )
        
        if llm_review:
            # Use LLM scores
            score.role_alignment = min(30, max(0, llm_review.get('role_alignment', 25)))
            score.clarity_impact = min(25, max(0, llm_review.get('clarity_impact', 20)))
            score.ats_optimization = min(20, max(0, llm_review.get('ats_optimization', 15)))
            score.formatting_density = min(15, max(0, llm_review.get('formatting_density', 12)))
            score.grammar_safety = min(10, max(0, llm_review.get('grammar_safety', 8)))
            
            # Add LLM issues and suggestions
            if llm_review.get('issues'):
                evaluation.issues.extend(llm_review['issues'][:5])
            if llm_review.get('suggestions'):
                evaluation.suggestions.extend(llm_review['suggestions'][:5])
            
            # Check if LLM says we need improvement
            llm_needs_improvement = llm_review.get('needs_improvement', False)
            two_pages_justified = llm_review.get('two_pages_justified', False)
        else:
            # Fallback to rule-based evaluation
            text_content = re.sub(r'\\[a-zA-Z]+\{?', ' ', state.latex_code)
            text_content = re.sub(r'[{}\\]', ' ', text_content)
            evaluation.grammar_errors = check_grammar(text_content)
            
            grammar_score = 10 - len(evaluation.grammar_errors)
            score.grammar_safety = max(0, min(10, grammar_score))
            
            # Evaluate bullet strength
            all_bullets = []
            for exp in resume_data.experience:
                all_bullets.extend(exp.bullets)
            for proj in resume_data.projects:
                all_bullets.extend(proj.bullets)
            
            bullet_score, bullet_issues = evaluate_bullet_strength(all_bullets)
            score.clarity_impact = int(bullet_score * 2.5)
            evaluation.issues.extend(bullet_issues[:5])
            
            # Evaluate ATS optimization
            ats_score, ats_suggestions = evaluate_ats_keywords(resume_data, state.target_role)
            score.ats_optimization = ats_score
            evaluation.suggestions.extend(ats_suggestions)
            
            # Evaluate formatting
            format_score, format_issues = evaluate_formatting(state.latex_code)
            score.formatting_density = format_score
            evaluation.issues.extend(format_issues)
            
            # Evaluate role alignment
            align_score, align_suggestions = evaluate_role_alignment(resume_data, state.target_role)
            score.role_alignment = align_score
            evaluation.suggestions.extend(align_suggestions)
            
            llm_needs_improvement = False
            two_pages_justified = False
        
        # Calculate raw score
        raw_score = score.total
        
        # Apply PAGE PENALTY (soft constraint, not failure)
        page_penalty = state.calculate_page_penalty(evaluation.page_count)
        adjusted_score = raw_score + page_penalty
        
        # SCORE MONOTONICITY CHECK
        if state.check_score_regression(adjusted_score):
            print(f"⚠️ Score regression detected: {state.previous_score} → {adjusted_score}")
            
            # Try to rollback if possible
            if state.rollback():
                print("↩️ Rolled back to previous successful state")
                evaluation.issues.append("Compression caused score regression - rolled back")
                # Use previous score
                adjusted_score = state.previous_score
            else:
                # No rollback available, but note the issue
                evaluation.issues.append(f"Score dropped from {state.previous_score} to {adjusted_score}")
        
        # Update score history
        state.score_history.append(adjusted_score)
        state.previous_score = adjusted_score
        
        # Set final evaluation
        evaluation.score = score
        
        # LINE-AWARE ESCALATION LOGIC
        # If page_count > 1, escalate compression strategy progressively
        if evaluation.page_count > 1:
            from .adaptive_optimizer import estimate_resume_lines
            line_counts = estimate_resume_lines(resume_data)
            state.estimated_lines = line_counts.get('total', 50)
            
            # Escalate if still over budget
            if hasattr(state, 'escalation_level'):
                old_level = state.escalation_level
                escalation_desc = state.escalate_compression()
                print(f"📏 Lines: {state.estimated_lines} | Escalating: {old_level} → {state.escalation_level} ({escalation_desc})")
        
        # FINAL OUTPUT POLICY
        # Prefer one-page resumes whenever possible
        # Output two pages ONLY IF:
        # - page_pressure >= 0.85
        # - score >= 92
        # - mandatory sections would be harmed by further compression
        
        if evaluation.page_count == 1:
            # One page - check quality score
            evaluation.passed = adjusted_score >= 90
        elif evaluation.page_count == 2:
            # Two pages - only acceptable if highly justified
            if state.page_pressure >= 0.85 and adjusted_score >= 92 and two_pages_justified:
                evaluation.passed = True
                evaluation.issues.append("Two-page resume accepted (content richness justified)")
            else:
                evaluation.passed = False
                if adjusted_score >= 90:
                    evaluation.issues.append("Two-page resume needs more compression")
        else:
            # 3+ pages - definitely needs reduction
            evaluation.passed = False
            evaluation.issues.append(f"Resume is {evaluation.page_count} pages - must reduce to 1-2")
        
        state.evaluation = evaluation
        
        # Decide next action based on adaptive strategy
        if evaluation.page_count > 1 and state.iteration_count < state.max_iterations:
            # Need to compress more - apply LINE-AWARE reduction
            state = apply_line_aware_reduction(state)
            state.current_node = "needs_regeneration"
        elif (not evaluation.passed or llm_needs_improvement) and state.iteration_count < state.max_iterations:
            state.current_node = "needs_improvement"
        else:
            state.current_node = "evaluation_complete"
            state.completed = True
        
        # Print detailed status
        compression_level = state.get_compression_level()
        escalation_action = state.get_escalation_action() if hasattr(state, 'get_escalation_action') else 'rewrite'
        print(f"📊 Resume Score: {raw_score}/100 (adjusted: {adjusted_score}, penalty: {page_penalty})")
        print(f"📄 Pages: {evaluation.page_count} | Pressure: {state.page_pressure:.2f} ({compression_level})")
        print(f"📏 Est. Lines: {state.estimated_lines if hasattr(state, 'estimated_lines') else 'N/A'} | Escalation: {escalation_action}")
        print(f"✅ Passed: {evaluation.passed} | Iteration: {state.iteration_count}/{state.max_iterations}")
        
    except Exception as e:
        state.error = f"Evaluation error: {str(e)}"
    
    return state


def apply_line_aware_reduction(state: WorkflowState) -> WorkflowState:
    """
    Apply LINE-AWARE content reduction based on escalation level.
    
    ESCALATION ORDER (never skip directly to deletion):
    0 → Rewrite bullets (shorten to 15-18 words)
    1 → Reduce bullets per item
    2 → Reduce number of items (projects/roles)
    3 → Trim optional sections
    
    INTERNAL EDITOR PRINCIPLE: "If it doesn't earn its line, it doesn't stay."
    """
    if not state.evaluation or state.evaluation.page_count <= 1:
        return state
    
    resume_data = state.optimized_data or state.resume_data
    if not resume_data:
        return state
    
    from .adaptive_optimizer import estimate_resume_lines, ESCALATION_LIMITS
    
    # Save checkpoint before modifications
    state.save_checkpoint()
    
    # Create a copy for modifications
    data_dict = resume_data.to_dict()
    
    # Get escalation level
    escalation_level = state.escalation_level if hasattr(state, 'escalation_level') else 0
    limits = ESCALATION_LIMITS.get(escalation_level, ESCALATION_LIMITS[3])
    
    print(f"🔧 Applying LINE-AWARE reduction (escalation: {escalation_level})")
    
    # LEVEL 0: Rewrite only (handled by LLM in optimization.py)
    # Nothing structural to do here - just ensure content limits
    
    # LEVEL 1+: Reduce bullets per item
    if escalation_level >= 1:
        exp_limit = limits['experience'][1]
        if data_dict.get('experience'):
            for exp in data_dict['experience']:
                if len(exp.get('bullets', [])) > exp_limit:
                    exp['bullets'] = exp['bullets'][:exp_limit]
        
        proj_limit = limits['projects'][1]
        if data_dict.get('projects'):
            for proj in data_dict['projects']:
                if len(proj.get('bullets', [])) > proj_limit:
                    proj['bullets'] = proj['bullets'][:proj_limit]
    
    # LEVEL 2+: Reduce number of items
    if escalation_level >= 2:
        exp_count = limits['experience'][0]
        if data_dict.get('experience') and len(data_dict['experience']) > exp_count:
            print(f"  ↳ Reducing experiences: {len(data_dict['experience'])} → {exp_count}")
            data_dict['experience'] = data_dict['experience'][:exp_count]
        
        proj_count = limits['projects'][0]
        if data_dict.get('projects') and len(data_dict['projects']) > proj_count:
            print(f"  ↳ Reducing projects: {len(data_dict['projects'])} → {proj_count}")
            data_dict['projects'] = data_dict['projects'][:proj_count]
    
    # LEVEL 3: Trim optional sections
    if escalation_level >= 3:
        if data_dict.get('achievements'):
            print("  ↳ Removing achievements section")
            data_dict['achievements'] = []
        
        if data_dict.get('certifications'):
            print("  ↳ Removing certifications section")
            data_dict['certifications'] = []
        
        if data_dict.get('extracurricular'):
            print("  ↳ Removing extracurricular section")
            data_dict['extracurricular'] = []
        
        # Education: remove bullets/coursework
        if data_dict.get('education'):
            for edu in data_dict['education']:
                edu['achievements'] = []
                edu['coursework'] = []
    
    # Update state
    state.optimized_data = ResumeData.from_dict(data_dict)
    state.compression_attempts += 1
    
    # Re-estimate lines
    new_line_counts = estimate_resume_lines(state.optimized_data)
    state.estimated_lines = new_line_counts.get('total', 50)
    print(f"  ↳ New estimated lines: {state.estimated_lines}")
    
    return state


def should_continue_loop(state: WorkflowState) -> bool:
    """
    Check if we should continue the evaluation loop.
    
    ADAPTIVE ITERATION LOGIC:
    - Continue if pages > 1 and we haven't reached max iterations
    - Continue if score not passing and improvement possible
    - Stop if we've achieved one-page with good score
    - Stop if two-page is justified (high pressure + high score)
    """
    if state.error:
        return False
    
    if state.iteration_count >= state.max_iterations:
        print(f"🛑 Max iterations ({state.max_iterations}) reached")
        return False
    
    if state.evaluation and state.evaluation.passed:
        return False
    
    # Check for score regression pattern (stuck in loop)
    if len(state.score_history) >= 3:
        recent_scores = state.score_history[-3:]
        if all(s <= recent_scores[0] for s in recent_scores):
            print("⚠️ Score not improving - stopping iteration")
            return False
    
    # Continue if we need improvement
    return state.current_node in ["needs_regeneration", "needs_improvement"]
