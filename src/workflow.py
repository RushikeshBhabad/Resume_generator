"""
LangGraph Workflow for Resume Generation with ADAPTIVE PAGE OPTIMIZATION

Orchestrates all nodes in a directed graph with:
- Soft one-page constraint (≈95% one-page target)
- Adaptive page pressure model [0.3, 0.9]
- Score monotonicity enforcement
- Intelligent iteration control
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END

from .models import WorkflowState
from .nodes import (
    ingest_file,
    structure_data,
    clarify_role,
    optimize_content,
    generate_latex,
    compile_resume,
    evaluate_resume,
    should_continue_loop,
)


def create_resume_workflow() -> StateGraph:
    """
    Create the LangGraph workflow for resume generation.
    
    Workflow:
    1. Ingest file → Extract text from any format
    2. Structure data → Parse into JSON schema
    3. Clarify role → Get target job role (handled by UI)
    4. Optimize content → Improve bullets, add keywords
    5. Generate LaTeX → Create resume document
    6. Compile → Convert to PDF
    7. Evaluate → Score and iterate if needed
    """
    
    # Create workflow with state schema
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("ingest", ingest_file)
    workflow.add_node("structure", structure_data)
    workflow.add_node("clarify_role", clarify_role)
    workflow.add_node("optimize", optimize_content)
    workflow.add_node("generate_latex", generate_latex)
    workflow.add_node("compile", compile_resume)
    workflow.add_node("evaluate", evaluate_resume)
    
    # Define routing logic
    def route_after_ingest(state: WorkflowState) -> Literal["structure", "error"]:
        if state.error:
            return "error"
        return "structure"
    
    def route_after_structure(state: WorkflowState) -> Literal["clarify_role", "error"]:
        if state.error:
            return "error"
        return "clarify_role"
    
    def route_after_role(state: WorkflowState) -> Literal["optimize", "wait_for_role"]:
        if not state.target_role:
            return "wait_for_role"
        return "optimize"
    
    def route_after_optimize(state: WorkflowState) -> Literal["generate_latex", "error"]:
        if state.error:
            return "error"
        return "generate_latex"
    
    def route_after_latex(state: WorkflowState) -> Literal["compile", "error"]:
        if state.error:
            return "error"
        return "compile"
    
    def route_after_compile(state: WorkflowState) -> Literal["evaluate", "error"]:
        if state.error or not state.compilation_success:
            return "error"
        return "evaluate"
    
    def route_after_evaluate(state: WorkflowState) -> Literal["generate_latex", "complete"]:
        if should_continue_loop(state):
            return "generate_latex"
        return "complete"
    
    # Set entry point
    workflow.set_entry_point("ingest")
    
    # Add edges with routing
    workflow.add_conditional_edges(
        "ingest",
        route_after_ingest,
        {
            "structure": "structure",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "structure",
        route_after_structure,
        {
            "clarify_role": "clarify_role",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "clarify_role",
        route_after_role,
        {
            "optimize": "optimize",
            "wait_for_role": END  # UI will resume
        }
    )
    
    workflow.add_conditional_edges(
        "optimize",
        route_after_optimize,
        {
            "generate_latex": "generate_latex",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "generate_latex",
        route_after_latex,
        {
            "compile": "compile",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "compile",
        route_after_compile,
        {
            "evaluate": "evaluate",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "generate_latex": "generate_latex",
            "complete": END
        }
    )
    
    return workflow


def compile_workflow():
    """Compile the workflow for execution."""
    workflow = create_resume_workflow()
    return workflow.compile()


class ResumeGenerator:
    """
    High-level interface for the resume generator.
    
    Usage:
        generator = ResumeGenerator()
        
        # Phase 1: Ingest and structure data
        state = generator.process_input(file_path="/path/to/resume.pdf")
        
        # Phase 2: Set role and generate
        state = generator.generate_resume(state, target_role="Software Engineer")
    """
    
    def __init__(self):
        self.workflow = compile_workflow()
    
    def process_input(
        self,
        file_path: str = None,
        raw_text: str = None,
        url: str = None,
        input_type: str = None
    ) -> WorkflowState:
        """
        Process input and extract structured data.
        
        Args:
            file_path: Path to file (PDF, image, video)
            raw_text: Plain text input
            url: URL to scrape (GitHub, LinkedIn, portfolio)
            input_type: Override input type detection
            
        Returns:
            WorkflowState with extracted and structured data
        """
        # Determine input type
        if input_type is None:
            if file_path:
                from .utils.helpers import get_file_type
                input_type = get_file_type(file_path)
            elif url:
                input_type = "url"
            else:
                input_type = "text"
        
        # Create initial state
        state = WorkflowState(
            file_path=file_path,
            raw_input=raw_text or url or "",
            input_type=input_type
        )
        
        # Run ingestion
        state = ingest_file(state)
        if state.error:
            return state
        
        # Run structuring
        state = structure_data(state)
        
        return state
    
    def generate_resume(
        self,
        state: WorkflowState,
        target_role: str
    ) -> WorkflowState:
        """
        Generate resume for a target role using ADAPTIVE PAGE OPTIMIZATION.
        
        Implements the intelligent iteration loop:
        Generate → Compile → Measure → Score
                ↓
           If pages > 1:
              Update page_pressure
              Apply adaptive compression
              Re-optimize wording
              Re-score (must not drop)
              Loop
        
        Args:
            state: State from process_input
            target_role: Target job role
            
        Returns:
            Final WorkflowState with PDF path and scores
        """
        # Set role
        state.target_role = target_role
        state.role_confirmed = True
        
        # Initialize adaptive optimization state
        state.page_pressure = 0.4  # Initial pressure
        state.previous_score = 0
        state.score_history = []
        state.compression_attempts = 0
        
        # Run initial optimization
        state = optimize_content(state)
        if state.error:
            return state
        
        # ADAPTIVE ITERATION LOOP
        # Key: Scoring happens every time, page count influences optimization pressure
        while state.iteration_count < state.max_iterations:
            # Generate LaTeX (pressure-aware)
            state = generate_latex(state)
            if state.error:
                return state
            
            # Compile to PDF
            state = compile_resume(state)
            if state.error or not state.compilation_success:
                return state
            
            # Evaluate (updates page_pressure, checks score monotonicity)
            state = evaluate_resume(state)
            
            # Check if we're done
            if state.completed or not should_continue_loop(state):
                break
            
            # If continuing, apply incremental optimization based on updated pressure
            # This re-runs optimization with the new pressure level
            if state.current_node == "needs_regeneration":
                # Re-optimize with updated pressure
                state = optimize_content(state)
                if state.error:
                    return state
        
        state.completed = True
        
        # Final status message
        if state.evaluation:
            page_count = state.evaluation.page_count
            score = state.evaluation.score.total if state.evaluation.score else 0
            penalty = state.calculate_page_penalty(page_count)
            print(f"\n🎯 FINAL RESULT:")
            print(f"   Pages: {page_count} | Score: {score} (penalty: {penalty})")
            print(f"   Pressure: {state.page_pressure:.2f} | Iterations: {state.iteration_count}")
            print(f"   Passed: {state.evaluation.passed}")
        
        return state
    
    def run_full_pipeline(
        self,
        file_path: str = None,
        raw_text: str = None,
        url: str = None,
        target_role: str = None
    ) -> WorkflowState:
        """
        Run the complete pipeline from input to PDF.
        
        Args:
            file_path: Path to input file
            raw_text: Plain text input
            url: URL to scrape
            target_role: Target job role
            
        Returns:
            Final WorkflowState
        """
        # Process input
        state = self.process_input(
            file_path=file_path,
            raw_text=raw_text,
            url=url
        )
        
        if state.error:
            return state
        
        # Generate resume
        if target_role:
            state = self.generate_resume(state, target_role)
        
        return state
