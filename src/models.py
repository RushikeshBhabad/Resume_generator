"""
Pydantic models for structured resume data.
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import date


class PersonalInfo(BaseModel):
    """Personal contact information."""
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""
    location: str = ""


class Education(BaseModel):
    """Educational qualification."""
    institution: str
    degree: str
    field_of_study: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""
    coursework: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)


class Experience(BaseModel):
    """Work experience entry."""
    company: str
    title: str
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    is_current: bool = False
    bullets: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class Project(BaseModel):
    """Project entry."""
    name: str
    description: str = ""
    url: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class Certification(BaseModel):
    """Certification entry."""
    name: str
    issuer: str = ""
    date: str = ""
    url: str = ""
    credential_id: str = ""


class Achievement(BaseModel):
    """Achievement entry."""
    title: str
    description: str = ""
    date: str = ""


class Extracurricular(BaseModel):
    """Extracurricular activity."""
    organization: str
    role: str = ""
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: List[str] = Field(default_factory=list)


class Skills(BaseModel):
    """Technical and soft skills."""
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    cloud: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    other: List[str] = Field(default_factory=list)


class ResumeData(BaseModel):
    """Complete structured resume data."""
    personal: PersonalInfo = Field(default_factory=PersonalInfo)
    education: List[Education] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    certifications: List[Certification] = Field(default_factory=list)
    achievements: List[Achievement] = Field(default_factory=list)
    extracurricular: List[Extracurricular] = Field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResumeData":
        """Create from dictionary."""
        return cls.model_validate(data)


class ResumeScore(BaseModel):
    """Resume quality score."""
    role_alignment: int = Field(default=0, ge=0, le=30)
    clarity_impact: int = Field(default=0, ge=0, le=25)
    ats_optimization: int = Field(default=0, ge=0, le=20)
    formatting_density: int = Field(default=0, ge=0, le=15)
    grammar_safety: int = Field(default=0, ge=0, le=10)
    
    @property
    def total(self) -> int:
        return (
            self.role_alignment + 
            self.clarity_impact + 
            self.ats_optimization + 
            self.formatting_density + 
            self.grammar_safety
        )
    
    @property
    def passed(self) -> bool:
        return self.total >= 90


class EvaluationResult(BaseModel):
    """Resume evaluation result."""
    score: ResumeScore = Field(default_factory=ResumeScore)
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    page_count: int = 1
    grammar_errors: List[str] = Field(default_factory=list)
    passed: bool = False


class WorkflowState(BaseModel):
    """LangGraph workflow state."""
    # Input
    raw_input: str = ""
    input_type: str = ""  # pdf, image, video, url, text
    file_path: Optional[str] = None
    
    # Extracted data
    extracted_text: str = ""
    resume_data: Optional[ResumeData] = None
    
    # Target role
    target_role: str = ""
    role_confirmed: bool = False
    
    # Generated content
    optimized_data: Optional[ResumeData] = None
    latex_code: str = ""
    
    # Compilation
    pdf_path: Optional[str] = None
    compilation_success: bool = False
    compilation_error: str = ""
    
    # Evaluation
    evaluation: Optional[EvaluationResult] = None
    iteration_count: int = 0
    max_iterations: int = 5
    
    # Adaptive Page Pressure Optimization
    page_pressure: float = 0.55  # Range [0.3, 0.95] - controls compression aggressiveness (START HIGHER)
    previous_score: int = 0  # Track previous score for monotonicity
    score_history: List[int] = Field(default_factory=list)  # Full score history
    compression_attempts: int = 0  # Track compression attempts at current level
    last_successful_data: Optional[ResumeData] = None  # Rollback point
    last_successful_latex: str = ""  # Rollback LaTeX
    
    # Line-Aware Layout Optimization
    estimated_lines: int = 0  # Current estimated line count
    line_budget: Dict[str, int] = Field(default_factory=lambda: {
        'education': 5,      # 4-5 lines
        'experience': 13,    # 12-14 lines
        'projects': 13,      # 12-14 lines
        'skills': 5,         # 4-5 lines
        'extracurricular': 3,  # 3-4 lines
        'optional': 4,       # certifications, achievements combined
    })
    target_total_lines: int = 48  # Target 46-50 lines
    escalation_level: int = 0  # 0=rewrite, 1=reduce bullets, 2=reduce items, 3=trim sections
    
    # Status
    current_node: str = ""
    error: Optional[str] = None
    completed: bool = False
    
    class Config:
        arbitrary_types_allowed = True
    
    def update_page_pressure(self, page_count: int) -> None:
        """
        Update page_pressure based on compilation result.
        
        If pages > 1: increase pressure by 0.20 (AGGRESSIVE)
        If pages == 1: decrease pressure by 0.05 (SLOW)
        Clamp between [0.4, 0.95]
        """
        if page_count > 1:
            self.page_pressure = min(0.95, self.page_pressure + 0.20)  # Faster ramp-up
        else:
            self.page_pressure = max(0.4, self.page_pressure - 0.05)  # Slower cool-down
    
    def get_compression_level(self) -> str:
        """
        Get current compression level based on page_pressure.
        
        Returns: 'light', 'medium', 'aggressive', or 'maximum'
        """
        if self.page_pressure < 0.45:
            return 'light'
        elif self.page_pressure < 0.6:
            return 'medium'
        elif self.page_pressure < 0.8:
            return 'aggressive'
        else:
            return 'maximum'  # Nuclear option
    
    def calculate_page_penalty(self, page_count: int) -> int:
        """
        Calculate score penalty based on page count (soft constraint).
        
        Returns:
            0 for 1 page
            -5 to -8 for 2 pages
            -15+ for 3+ pages
        """
        if page_count == 1:
            return 0
        elif page_count == 2:
            return -6  # Middle of -5 to -8 range
        else:
            return -15 - (page_count - 3) * 5
    
    def check_score_regression(self, new_score: int) -> bool:
        """
        Check if new score represents a regression.
        
        Returns True if score dropped (regression occurred).
        """
        if self.previous_score == 0:
            return False
        return new_score < self.previous_score
    
    def save_checkpoint(self) -> None:
        """Save current successful state as rollback point."""
        if self.optimized_data:
            self.last_successful_data = self.optimized_data.model_copy(deep=True)
        self.last_successful_latex = self.latex_code
    
    def rollback(self) -> bool:
        """
        Rollback to last successful checkpoint.
        
        Returns True if rollback was successful.
        """
        if self.last_successful_data:
            self.optimized_data = self.last_successful_data
            self.latex_code = self.last_successful_latex
            return True
        return False
    
    def escalate_compression(self) -> str:
        """
        Escalate compression strategy when page overflow persists.
        
        Escalation order:
        0 → Rewrite bullets (make them shorter and better)
        1 → Reduce bullets per item
        2 → Reduce number of items (projects/roles)
        3 → Trim optional sections
        
        Returns description of current escalation level.
        """
        self.escalation_level = min(3, self.escalation_level + 1)
        
        levels = {
            0: 'REWRITE: Shorten and improve bullets',
            1: 'REDUCE_BULLETS: Cut bullets per item',
            2: 'REDUCE_ITEMS: Remove weakest projects/roles',
            3: 'TRIM_SECTIONS: Remove optional sections'
        }
        return levels.get(self.escalation_level, 'MAXIMUM')
    
    def get_escalation_action(self) -> str:
        """
        Get the current escalation action type.
        
        Returns: 'rewrite', 'reduce_bullets', 'reduce_items', or 'trim_sections'
        """
        actions = ['rewrite', 'reduce_bullets', 'reduce_items', 'trim_sections']
        return actions[min(self.escalation_level, 3)]
    
    def is_over_line_budget(self) -> bool:
        """
        Check if estimated lines exceed target.
        """
        return self.estimated_lines > self.target_total_lines
