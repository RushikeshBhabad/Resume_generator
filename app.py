"""
Streamlit Frontend for Resume Generator

A beautiful, user-friendly interface for the LangGraph resume generator.
"""
import os
import sys
import json
import tempfile
from pathlib import Path

import streamlit as st

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.workflow import ResumeGenerator
from src.models import WorkflowState, ResumeData
from src.nodes.role_clarification import get_role_suggestions
from src.nodes.compilation import check_pdflatex_available, check_docker_available

# Page config
st.set_page_config(
    page_title="AI Resume Generator",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        text-align: center;
    }
    .score-number {
        font-size: 3rem;
        font-weight: 700;
    }
    .score-label {
        font-size: 1rem;
        opacity: 0.9;
    }
    .status-success {
        color: #10b981;
        font-weight: 600;
    }
    .status-error {
        color: #ef4444;
        font-weight: 600;
    }
    .status-warning {
        color: #f59e0b;
        font-weight: 600;
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea, #764ba2);
    }
</style>
""", unsafe_allow_html=True)


def check_system_requirements():
    """Check if system requirements are met."""
    requirements = {
        "GROQ_API_KEY": bool(os.getenv("GROQ_API_KEY")),
        "LaTeX Compiler": check_pdflatex_available() or check_docker_available(),
    }
    return requirements


def display_system_status():
    """Display system requirements status in sidebar."""
    st.sidebar.header("System Status")
    
    requirements = check_system_requirements()
    
    for req, status in requirements.items():
        if status:
            st.sidebar.success(f"✅ {req}")
        else:
            st.sidebar.error(f"❌ {req}")
    
    if not requirements["GROQ_API_KEY"]:
        st.sidebar.warning(
            "Set GROQ_API_KEY in .env file.\n"
            "Get free key: https://console.groq.com/keys"
        )
    
    if not requirements["LaTeX Compiler"]:
        st.sidebar.warning(
            "Install LaTeX:\n"
            "`sudo apt install texlive-latex-base`"
        )


def display_score_card(score):
    """Display the resume score in a nice card."""
    total = score.total
    
    if total >= 90:
        color = "#10b981"
        status = "Excellent"
    elif total >= 70:
        color = "#f59e0b"
        status = "Good"
    else:
        color = "#ef4444"
        status = "Needs Work"
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Role Alignment", f"{score.role_alignment}/30")
    with col2:
        st.metric("Clarity & Impact", f"{score.clarity_impact}/25")
    with col3:
        st.metric("ATS Optimization", f"{score.ats_optimization}/20")
    with col4:
        st.metric("Formatting", f"{score.formatting_density}/15")
    with col5:
        st.metric("Grammar", f"{score.grammar_safety}/10")
    
    st.markdown(f"""
    <div style="text-align: center; margin: 1rem 0;">
        <span style="font-size: 3rem; font-weight: 700; color: {color};">{total}/100</span>
        <br>
        <span style="font-size: 1.2rem; color: {color};">{status}</span>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown('<h1 class="main-header">📄 AI Resume Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Generate ATS-optimized, one-page LaTeX resumes powered by LangGraph</p>', unsafe_allow_html=True)
    
    # Sidebar
    display_system_status()
    
    st.sidebar.markdown("---")
    st.sidebar.header("About")
    st.sidebar.info(
        "This tool uses LangGraph to orchestrate:\n"
        "1. File ingestion (PDF, Image, Video, URL)\n"
        "2. Data structuring\n"
        "3. Content optimization\n"
        "4. LaTeX generation\n"
        "5. PDF compilation\n"
        "6. Quality evaluation"
    )
    
    # Initialize session state
    if 'state' not in st.session_state:
        st.session_state.state = None
    if 'generator' not in st.session_state:
        st.session_state.generator = ResumeGenerator()
    if 'step' not in st.session_state:
        st.session_state.step = 1
    
    # Main content
    tabs = st.tabs(["📤 Upload", "🎯 Configure", "📊 Results"])
    
    # Tab 1: Upload
    with tabs[0]:
        st.header("Step 1: Provide Your Information")
        
        input_method = st.radio(
            "Choose input method:",
            ["Upload File", "Paste Text", "Enter URL"],
            horizontal=True
        )
        
        file_path = None
        raw_text = None
        url = None
        
        if input_method == "Upload File":
            uploaded_file = st.file_uploader(
                "Upload your resume or portfolio",
                type=['pdf', 'jpg', 'jpeg', 'png', 'txt', 'mp4', 'avi', 'mov'],
                help="Supported: PDF, Images (JPG/PNG), Video, Text files"
            )
            
            if uploaded_file:
                # Save uploaded file
                upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, uploaded_file.name)
                
                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                
                st.success(f"Uploaded: {uploaded_file.name}")
        
        elif input_method == "Paste Text":
            raw_text = st.text_area(
                "Paste your resume content or raw information",
                height=300,
                placeholder="Paste your resume text, LinkedIn summary, project descriptions, etc."
            )
        
        else:  # URL
            url = st.text_input(
                "Enter URL",
                placeholder="https://github.com/username or https://linkedin.com/in/username"
            )
            
            if url:
                st.info("Supported URLs: GitHub profiles, LinkedIn (limited), Portfolio websites")
        
        # Process button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            process_btn = st.button(
                "🔍 Extract & Analyze",
                type="primary",
                use_container_width=True,
                disabled=not (file_path or raw_text or url)
            )
        
        if process_btn:
            with st.spinner("Extracting and structuring your information..."):
                try:
                    state = st.session_state.generator.process_input(
                        file_path=file_path,
                        raw_text=raw_text,
                        url=url
                    )
                    
                    if state.error:
                        st.error(f"Error: {state.error}")
                    else:
                        st.session_state.state = state
                        st.session_state.step = 2
                        st.success("✅ Information extracted successfully!")
                        
                        # Show extracted data summary
                        if state.resume_data:
                            with st.expander("📋 Extracted Data Preview", expanded=True):
                                data = state.resume_data.to_dict()
                                
                                cols = st.columns(4)
                                with cols[0]:
                                    st.metric("Education", len(data.get('education', [])))
                                with cols[1]:
                                    st.metric("Experience", len(data.get('experience', [])))
                                with cols[2]:
                                    st.metric("Projects", len(data.get('projects', [])))
                                with cols[3]:
                                    skills_count = sum(len(v) for v in data.get('skills', {}).values() if isinstance(v, list))
                                    st.metric("Skills", skills_count)
                                
                                st.json(data)
                        
                        st.info("👉 Go to the **Configure** tab to select your target role")
                        
                except Exception as e:
                    st.error(f"Error processing input: {str(e)}")
    
    # Tab 2: Configure
    with tabs[1]:
        st.header("Step 2: Select Target Role")
        
        if st.session_state.state is None or st.session_state.state.resume_data is None:
            st.warning("⚠️ Please upload and extract your information first")
        else:
            # Role selection
            role_suggestions = get_role_suggestions()
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                target_role = st.selectbox(
                    "Select your target role:",
                    options=[""] + role_suggestions,
                    index=0
                )
            
            with col2:
                custom_role = st.text_input(
                    "Or enter a custom role:",
                    placeholder="e.g., GenAI Engineer"
                )
            
            final_role = custom_role if custom_role else target_role
            
            if final_role:
                st.success(f"Target role: **{final_role}**")
            
            st.markdown("---")
            
            # Generation options
            st.subheader("Options")
            
            col1, col2 = st.columns(2)
            with col1:
                max_iterations = st.slider(
                    "Max optimization iterations",
                    min_value=1,
                    max_value=5,
                    value=3,
                    help="More iterations = better quality but slower"
                )
            
            with col2:
                one_page_strict = st.checkbox(
                    "Strictly enforce one page",
                    value=True,
                    help="Will reduce content if needed"
                )
            
            # Generate button
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                generate_btn = st.button(
                    "🚀 Generate Resume",
                    type="primary",
                    use_container_width=True,
                    disabled=not final_role
                )
            
            if generate_btn and final_role:
                progress_bar = st.progress(0)
                status_text = st.empty()
                status_detail = st.empty()
                
                try:
                    state = st.session_state.state
                    state.max_iterations = max_iterations
                    
                    # Step 1: Optimization
                    status_text.markdown("### 🔧 Optimizing Content...")
                    status_detail.info("🤖 AI is aggressively compressing your resume for one-page perfection. This may take 30-60 seconds...")
                    progress_bar.progress(20)
                    
                    from src.nodes import optimize_content
                    state.target_role = final_role
                    state.role_confirmed = True
                    state = optimize_content(state)
                    
                    if state.error:
                        st.error(f"Optimization error: {state.error}")
                        return
                    
                    # Step 2: LaTeX Generation
                    status_text.markdown("### 📝 Generating LaTeX Resume...")
                    status_detail.info("🤖 AI is intelligently crafting your professional LaTeX resume. Please wait 30-60 seconds...")
                    progress_bar.progress(40)
                    
                    from src.nodes import generate_latex
                    state = generate_latex(state)
                    
                    if state.error:
                        st.error(f"LaTeX generation error: {state.error}")
                        return
                    
                    # Step 3: Compilation
                    status_text.markdown("### ⚙️ Compiling PDF...")
                    status_detail.info("📄 Converting LaTeX to PDF using pdflatex compiler...")
                    progress_bar.progress(60)
                    
                    from src.nodes import compile_resume
                    state = compile_resume(state)
                    
                    if not state.compilation_success:
                        st.error(f"Compilation error: {state.compilation_error}")
                        # Still show LaTeX code
                        with st.expander("📄 LaTeX Code (compilation failed)"):
                            st.code(state.latex_code, language="latex")
                        return
                    
                    # Step 4: Evaluation
                    status_text.markdown("### 📊 Evaluating Quality...")
                    status_detail.info("🔍 AI is reviewing your resume for ATS optimization, clarity, and impact...")
                    progress_bar.progress(80)
                    
                    from src.nodes import evaluate_resume, should_continue_loop
                    state = evaluate_resume(state)
                    
                    # Iterative improvement if needed
                    while should_continue_loop(state) and state.iteration_count < max_iterations:
                        status_text.markdown(f"### 🔄 Refining Resume (Iteration {state.iteration_count}/{max_iterations})...")
                        status_detail.info("🤖 AI detected improvements needed. Regenerating for better quality...")
                        state = generate_latex(state)
                        state = compile_resume(state)
                        state = evaluate_resume(state)
                    
                    progress_bar.progress(100)
                    status_text.markdown("### ✅ Resume Generated Successfully!")
                    status_detail.success("Your one-page professional resume is ready for download.")
                    
                    st.session_state.state = state
                    st.session_state.step = 3
                    
                    st.success("🎉 Resume generated! Go to the **Results** tab to view and download.")
                    
                except Exception as e:
                    st.error(f"Error generating resume: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    
    # Tab 3: Results
    with tabs[2]:
        st.header("Step 3: Your Resume")
        
        state = st.session_state.state
        
        if state is None or not state.latex_code:
            st.warning("⚠️ No resume generated yet. Complete steps 1 and 2 first.")
        else:
            # Score display
            if state.evaluation and state.evaluation.score:
                st.subheader("📊 Resume Quality Score")
                display_score_card(state.evaluation.score)
                
                if state.evaluation.passed:
                    st.success("✅ Resume meets quality standards!")
                else:
                    st.warning("⚠️ Resume could be improved. See suggestions below.")
                
                # Issues and suggestions
                col1, col2 = st.columns(2)
                
                with col1:
                    if state.evaluation.issues:
                        with st.expander("🔍 Issues Found", expanded=False):
                            for issue in state.evaluation.issues[:10]:
                                st.write(f"• {issue}")
                
                with col2:
                    if state.evaluation.suggestions:
                        with st.expander("💡 Suggestions", expanded=False):
                            for suggestion in state.evaluation.suggestions[:10]:
                                st.write(f"• {suggestion}")
            
            st.markdown("---")
            
            # Download buttons
            st.subheader("📥 Download")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if state.pdf_path and os.path.exists(state.pdf_path):
                    with open(state.pdf_path, 'rb') as f:
                        st.download_button(
                            label="📄 Download PDF",
                            data=f.read(),
                            file_name="resume.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.button("📄 PDF Not Available", disabled=True, use_container_width=True)
            
            with col2:
                st.download_button(
                    label="📝 Download LaTeX",
                    data=state.latex_code,
                    file_name="resume.tex",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col3:
                if state.optimized_data or state.resume_data:
                    data = (state.optimized_data or state.resume_data).to_dict()
                    st.download_button(
                        label="📊 Download JSON",
                        data=json.dumps(data, indent=2),
                        file_name="resume_data.json",
                        mime="application/json",
                        use_container_width=True
                    )
            
            st.markdown("---")
            
            # Preview sections
            col1, col2 = st.columns(2)
            
            with col1:
                with st.expander("📄 LaTeX Source Code", expanded=False):
                    st.code(state.latex_code, language="latex")
            
            with col2:
                with st.expander("📊 Structured Data", expanded=False):
                    if state.optimized_data:
                        st.json(state.optimized_data.to_dict())
                    elif state.resume_data:
                        st.json(state.resume_data.to_dict())
            
            # PDF preview (if available)
            if state.pdf_path and os.path.exists(state.pdf_path):
                st.subheader("👁️ PDF Preview")
                st.info("Download the PDF to view the full resume. PDF preview in browser may be limited.")
                
                # Try to embed PDF
                try:
                    with open(state.pdf_path, 'rb') as f:
                        pdf_bytes = f.read()
                    
                    import base64
                    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    
                    st.markdown(
                        f'<iframe src="data:application/pdf;base64,{pdf_base64}" '
                        f'width="100%" height="800" type="application/pdf"></iframe>',
                        unsafe_allow_html=True
                    )
                except Exception as e:
                    st.warning(f"Could not preview PDF: {str(e)}")


if __name__ == "__main__":
    main()
