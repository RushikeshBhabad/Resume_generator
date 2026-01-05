# 📄 AI Resume Generator

An end-to-end **LangGraph-powered resume generator** that creates ATS-optimized, one-page LaTeX resumes from any input format.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- **Multi-format Input Support**
  - 📄 PDF documents
  - 🖼️ Images (JPG, PNG) with OCR
  - 🎥 Video files (frame extraction + OCR)
  - 🔗 URLs (GitHub, LinkedIn, portfolio websites)
  - 📝 Plain text

- **Intelligent Processing**
  - LangGraph workflow orchestration
  - LLM-powered data extraction
  - Content optimization with strong action verbs
  - ATS keyword alignment

- **🆕 Adaptive Page Optimization**
  - Soft one-page constraint (≈95% one-page target)
  - Intelligent page pressure model [0.3, 0.9]
  - Score monotonicity enforcement (quality never decreases)
  - Adaptive compression levels (light → medium → aggressive)
  - Bullet rewriting with full information preservation

- **Professional Output**
  - Clean, compilable LaTeX code
  - Pressure-aware spacing and margins
  - Quality scoring with page penalty model
  - Iterative improvement loop

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 ADAPTIVE LangGraph Workflow                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │  Ingest  │ → │Structure │ → │ Optimize │ → │  LaTeX   │    │
│  │   File   │   │   Data   │   │(Adaptive)│   │(Pressure)│    │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘    │
│                                                    │           │
│                                                    ▼           │
│  ┌──────────┐   ┌──────────┐                ┌──────────┐      │
│  │  Output  │ ← │ Evaluate │ ← ─ ─ ─ ─ ─ ─ ┤ Compile  │      │
│  │   PDF    │   │(Monotonic│    (iterate)   │   PDF    │      │
│  └──────────┘   │ Scoring) │                └──────────┘      │
│                 └──────────┘                                   │
│                      │                                         │
│                      ▼                                         │
│            ┌─────────────────┐                                 │
│            │ Update Pressure │                                 │
│            │ [0.3 ─────→ 0.9]│                                 │
│            └─────────────────┘                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 🎯 Adaptive Iteration Strategy

```
Generate → Compile → Measure → Score
        ↓
   If pages > 1:
      Increase page_pressure (+0.15)
      Apply adaptive compression
      Re-optimize wording
      Re-score (must not drop)
      Loop
   Else:
      Decrease page_pressure (-0.1)
```

## 🚀 Quick Start

### 1. Clone & Setup

```bash
# Clone the repository
cd ResumeGenerator

# Run the setup script
chmod +x setup.sh
./setup.sh
```

### 2. Configure API Key

Get your **FREE** Groq API key from: https://console.groq.com/keys

```bash
# Edit .env file
nano .env

# Add your API key
GROQ_API_KEY=your_key_here
```

### 3. Run the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Start Streamlit
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## 📦 Manual Installation

If you prefer manual installation:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Install system dependencies (Ubuntu/Debian)
sudo apt install tesseract-ocr ffmpeg poppler-utils
sudo apt install texlive-latex-base texlive-latex-recommended texlive-fonts-extra

# Copy environment file
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

## 🎯 Usage

### Web Interface (Streamlit)

1. **Upload Tab**: Upload your resume/portfolio (PDF, image, video, or URL)
2. **Configure Tab**: Select your target job role
3. **Results Tab**: Download your optimized PDF resume

### Programmatic Usage

```python
from src.workflow import ResumeGenerator

# Initialize generator
generator = ResumeGenerator()

# Process input
state = generator.process_input(file_path="path/to/resume.pdf")

# Generate resume for target role
state = generator.generate_resume(state, target_role="Software Engineer")

# Access outputs
print(f"PDF: {state.pdf_path}")
print(f"Score: {state.evaluation.score.total}/100")
print(state.latex_code)
```

## 📊 Quality Scoring

Resumes are scored on a 100-point scale:

| Criteria | Weight | Description |
|----------|--------|-------------|
| Role Alignment | 30 | How well content matches target role |
| Clarity & Impact | 25 | Strong action verbs, quantified results |
| ATS Optimization | 20 | Relevant keywords for applicant tracking |
| Formatting | 15 | Clean layout, proper density |
| Grammar & Safety | 10 | Error-free, safe LaTeX |

### Page Penalty Model (Soft Constraint)

| Pages | Penalty | Notes |
|-------|---------|-------|
| 1 | 0 | Optimal |
| 2 | -5 to -8 | Acceptable if justified |
| 3+ | -15+ | Needs significant reduction |

**Passing score: ≥90/100** (adjusted for page penalty)

### 🆕 Adaptive Compression Levels

| Pressure | Level | Behavior |
|----------|-------|----------|
| < 0.5 | Light | Wording refinement, semantic merging, no content removal |
| 0.5 - 0.7 | Medium | Cap bullets (3 per item), one-line bullets, phrase conversion |
| ≥ 0.7 | Aggressive | Top 2-3 bullets only, remove optional sections, max density |

## 🔧 Configuration

### LLM Settings

The system uses Groq's free API with these models:

- `llama-3.3-70b-versatile` (default, best quality)
- `llama-3.1-8b-instant` (faster)
- `mixtral-8x7b-32768` (good balance)

### LaTeX Compilation

Supports two compilation methods:

1. **Local pdflatex** (recommended)
   ```bash
   sudo apt install texlive-latex-base texlive-latex-recommended texlive-fonts-extra
   ```

2. **Docker** (isolated)
   ```bash
   sudo apt install docker.io
   docker pull blang/latex
   ```

## 📁 Project Structure

```
ResumeGenerator/
├── app.py                 # Streamlit frontend
├── setup.sh              # Setup script
├── requirements.txt      # Python dependencies
├── .env.example          # Environment template
├── src/
│   ├── __init__.py
│   ├── models.py         # Pydantic data models
│   ├── workflow.py       # LangGraph workflow
│   ├── nodes/
│   │   ├── ingestion.py      # Node 1: File ingestion
│   │   ├── structuring.py    # Node 2: Data structuring
│   │   ├── role_clarification.py  # Node 3: Role input
│   │   ├── optimization.py   # Node 4: Content optimization
│   │   ├── latex_generation.py    # Node 5: LaTeX generation
│   │   ├── compilation.py    # Node 6: PDF compilation
│   │   └── evaluation.py     # Node 7: Quality evaluation
│   └── utils/
│       ├── helpers.py        # Utility functions
│       └── llm_client.py     # LLM configuration
├── templates/
│   └── sample_resume.tex # Sample LaTeX template
├── uploads/              # Uploaded files
└── output/               # Generated resumes
```

## 🔒 Security

- LaTeX special characters are escaped
- Dangerous LaTeX commands (`\write18`, `\input`, etc.) are blocked
- No personal data logging
- URL validation before scraping
- No fabrication of achievements

## 🐛 Troubleshooting

### "GROQ_API_KEY not found"
```bash
# Make sure .env file exists and contains your key
cat .env
# Should show: GROQ_API_KEY=gsk_...
```

### "pdflatex not found"
```bash
# Install LaTeX
sudo apt install texlive-latex-base texlive-latex-recommended texlive-fonts-extra

# Verify
pdflatex --version
```

### "Tesseract not found"
```bash
# Install Tesseract OCR
sudo apt install tesseract-ocr

# Verify
tesseract --version
```

### Compilation errors
Check the LaTeX output in the Results tab. Common issues:
- Special characters not escaped (handled automatically)
- Missing packages (the template uses standard packages)

## 📄 License

MIT License - feel free to use and modify for your projects.

## 🙏 Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- [Groq](https://groq.com/) for fast, free LLM inference
- [Streamlit](https://streamlit.io/) for the beautiful UI
- Jake's Resume template for LaTeX inspiration

---

**Made with ❤️ for job seekers everywhere**
