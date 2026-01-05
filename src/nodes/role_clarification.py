"""
Node 3: Target Role Clarification

Asks the user for the target job role and stores it for content optimization.
"""
from ..models import WorkflowState


# Common role categories for suggestions
ROLE_SUGGESTIONS = {
    "software_engineering": [
        "Software Engineer",
        "Software Engineer Intern",
        "Frontend Developer",
        "Backend Developer",
        "Full Stack Developer",
        "Mobile Developer",
        "DevOps Engineer",
        "Site Reliability Engineer",
    ],
    "data_science": [
        "Data Scientist",
        "Data Analyst",
        "Business Analyst",
        "Data Engineer",
        "Analytics Engineer",
    ],
    "machine_learning": [
        "Machine Learning Engineer",
        "ML Engineer Intern",
        "AI Engineer",
        "GenAI Engineer",
        "NLP Engineer",
        "Computer Vision Engineer",
        "Research Scientist",
    ],
    "product": [
        "Product Manager",
        "Technical Product Manager",
        "Program Manager",
    ],
    "security": [
        "Security Engineer",
        "Cybersecurity Analyst",
        "Penetration Tester",
    ],
}


def get_role_suggestions() -> list:
    """Get flat list of all role suggestions."""
    roles = []
    for category in ROLE_SUGGESTIONS.values():
        roles.extend(category)
    return roles


def clarify_role(state: WorkflowState) -> WorkflowState:
    """
    Role clarification node - this is handled by the Streamlit UI.
    The state.target_role should be set by the UI before this node runs.
    
    This is LangGraph Node 3: Target Role Clarification
    """
    if not state.target_role:
        # This will be handled by the Streamlit UI
        state.current_node = "awaiting_role"
        return state
    
    state.role_confirmed = True
    state.current_node = "role_confirmed"
    
    return state


def should_wait_for_role(state: WorkflowState) -> bool:
    """Check if we need to wait for role input."""
    return not state.role_confirmed and not state.target_role
