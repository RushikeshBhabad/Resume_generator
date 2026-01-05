"""LangGraph nodes package with ADAPTIVE PAGE OPTIMIZATION and LINE-AWARE LAYOUT."""
from .ingestion import ingest_file
from .structuring import structure_data
from .role_clarification import clarify_role, get_role_suggestions, should_wait_for_role
from .optimization import optimize_content
from .latex_generation import generate_latex
from .compilation import compile_resume, check_pdflatex_available, check_docker_available
from .evaluation import evaluate_resume, should_continue_loop, apply_line_aware_reduction
from .adaptive_optimizer import (
    adaptive_optimize_content,
    apply_incremental_compression,
    compress_resume_data,
    rewrite_bullets_with_llm,
    assess_bullet_quality,
    rank_bullets_by_impact,
    get_compression_level,
    verify_compression_quality,
    # Line estimation functions
    estimate_text_lines,
    estimate_bullet_lines,
    estimate_section_lines,
    estimate_resume_lines,
    get_line_overflow,
    identify_sections_to_compress,
    get_structural_reduction_plan,
    # Constants
    CHARS_PER_LINE,
    TARGET_TOTAL_LINES,
    SECTION_LINE_BUDGETS,
    ESCALATION_LIMITS,
)

__all__ = [
    # Core nodes
    'ingest_file',
    'structure_data',
    'clarify_role',
    'get_role_suggestions',
    'should_wait_for_role',
    'optimize_content',
    'generate_latex',
    'compile_resume',
    'check_pdflatex_available',
    'check_docker_available',
    'evaluate_resume',
    'should_continue_loop',
    'apply_line_aware_reduction',
    # Adaptive optimization
    'adaptive_optimize_content',
    'apply_incremental_compression',
    'compress_resume_data',
    'rewrite_bullets_with_llm',
    'assess_bullet_quality',
    'rank_bullets_by_impact',
    'get_compression_level',
    'verify_compression_quality',
    # Line-aware layout
    'estimate_text_lines',
    'estimate_bullet_lines',
    'estimate_section_lines',
    'estimate_resume_lines',
    'get_line_overflow',
    'identify_sections_to_compress',
    'get_structural_reduction_plan',
    'CHARS_PER_LINE',
    'TARGET_TOTAL_LINES',
    'SECTION_LINE_BUDGETS',
    'ESCALATION_LIMITS',
]
