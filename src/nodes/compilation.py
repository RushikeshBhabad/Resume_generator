"""
Node 6: LaTeX Compilation

Compiles LaTeX to PDF using FREE tools only:
- pdflatex (local)
- Docker with blang/latex
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Optional

from ..models import WorkflowState
from ..utils.helpers import compile_latex, ensure_directory


def check_pdflatex_available() -> bool:
    """Check if pdflatex is available on the system."""
    try:
        result = subprocess.run(
            ['pdflatex', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def check_docker_available() -> bool:
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ['docker', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def compile_with_pdflatex(tex_path: str, output_dir: str) -> Tuple[bool, str, Optional[str]]:
    """
    Compile LaTeX using local pdflatex.
    
    Args:
        tex_path: Path to .tex file
        output_dir: Output directory for PDF
        
    Returns:
        Tuple of (success, message, pdf_path)
    """
    try:
        ensure_directory(output_dir)
        
        # Run pdflatex twice for proper references
        for i in range(2):
            result = subprocess.run(
                [
                    'pdflatex',
                    '-interaction=nonstopmode',
                    '-halt-on-error',
                    '-output-directory', output_dir,
                    tex_path
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.path.dirname(tex_path) or '.'
            )
        
        # Check if PDF was created
        tex_name = Path(tex_path).stem
        pdf_path = os.path.join(output_dir, f"{tex_name}.pdf")
        
        if os.path.exists(pdf_path):
            # Clean up auxiliary files
            for ext in ['.aux', '.log', '.out']:
                aux_file = os.path.join(output_dir, f"{tex_name}{ext}")
                if os.path.exists(aux_file):
                    try:
                        os.remove(aux_file)
                    except:
                        pass
            
            return True, "Compilation successful", pdf_path
        else:
            error_msg = result.stderr or result.stdout
            return False, f"Compilation failed: {error_msg[:500]}", None
            
    except subprocess.TimeoutExpired:
        return False, "Compilation timed out (60s limit)", None
    except FileNotFoundError:
        return False, "pdflatex not found. Install with: sudo apt install texlive-latex-base", None
    except Exception as e:
        return False, f"Compilation error: {str(e)}", None


def compile_with_docker(tex_path: str, output_dir: str) -> Tuple[bool, str, Optional[str]]:
    """
    Compile LaTeX using Docker (blang/latex image).
    
    Args:
        tex_path: Path to .tex file
        output_dir: Output directory for PDF
        
    Returns:
        Tuple of (success, message, pdf_path)
    """
    try:
        ensure_directory(output_dir)
        
        # Get absolute paths
        tex_path = os.path.abspath(tex_path)
        output_dir = os.path.abspath(output_dir)
        tex_dir = os.path.dirname(tex_path)
        tex_name = Path(tex_path).name
        
        # Run pdflatex in Docker container
        result = subprocess.run(
            [
                'docker', 'run', '--rm',
                '-v', f'{tex_dir}:/data',
                '-v', f'{output_dir}:/output',
                '-w', '/data',
                'blang/latex',
                'pdflatex',
                '-interaction=nonstopmode',
                '-output-directory=/output',
                tex_name
            ],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Run twice for references
        subprocess.run(
            [
                'docker', 'run', '--rm',
                '-v', f'{tex_dir}:/data',
                '-v', f'{output_dir}:/output',
                '-w', '/data',
                'blang/latex',
                'pdflatex',
                '-interaction=nonstopmode',
                '-output-directory=/output',
                tex_name
            ],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Check if PDF was created
        pdf_name = Path(tex_path).stem + ".pdf"
        pdf_path = os.path.join(output_dir, pdf_name)
        
        if os.path.exists(pdf_path):
            return True, "Compilation successful (Docker)", pdf_path
        else:
            return False, f"Docker compilation failed: {result.stderr[:500]}", None
            
    except subprocess.TimeoutExpired:
        return False, "Docker compilation timed out", None
    except FileNotFoundError:
        return False, "Docker not found. Install with: sudo apt install docker.io", None
    except Exception as e:
        return False, f"Docker compilation error: {str(e)}", None


def compile_resume(state: WorkflowState) -> WorkflowState:
    """
    Main compilation node - compiles LaTeX to PDF.
    
    This is LangGraph Node 6: LaTeX Compilation
    """
    if not state.latex_code:
        state.error = "No LaTeX code to compile"
        return state
    
    try:
        # Create output directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_dir = os.path.join(base_dir, "output")
        ensure_directory(output_dir)
        
        # Write LaTeX to file
        tex_path = os.path.join(output_dir, "resume.tex")
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(state.latex_code)
        
        # Try pdflatex first, then Docker
        success = False
        message = ""
        pdf_path = None
        
        if check_pdflatex_available():
            success, message, pdf_path = compile_with_pdflatex(tex_path, output_dir)
        elif check_docker_available():
            success, message, pdf_path = compile_with_docker(tex_path, output_dir)
        else:
            state.error = (
                "No LaTeX compiler available. Please install one:\n"
                "  Option 1: sudo apt install texlive-latex-base texlive-latex-recommended texlive-fonts-extra\n"
                "  Option 2: sudo apt install docker.io && docker pull blang/latex"
            )
            state.compilation_success = False
            return state
        
        state.compilation_success = success
        state.pdf_path = pdf_path
        
        if not success:
            state.compilation_error = message
        
        state.current_node = "compilation_complete"
        
    except Exception as e:
        state.error = f"Compilation error: {str(e)}"
        state.compilation_success = False
    
    return state
