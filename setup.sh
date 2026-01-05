#!/bin/bash

# =============================================================================
# Resume Generator Setup Script
# =============================================================================
# This script sets up the complete environment for the LangGraph Resume Generator
# =============================================================================

set -e  # Exit on error

echo "=========================================="
echo "  AI Resume Generator - Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    print_warning "This script is designed for Linux. Some commands may not work on other systems."
fi

# Step 1: Check Python version
echo ""
echo "Step 1: Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_status "Python $PYTHON_VERSION found"
    
    # Check if version is 3.10+
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        print_error "Python 3.10+ required. Please upgrade Python."
        exit 1
    fi
else
    print_error "Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Step 2: Create virtual environment
echo ""
echo "Step 2: Creating virtual environment..."
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists. Skipping creation."
else
    python3 -m venv venv
    print_status "Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate
print_status "Virtual environment activated"

# Step 3: Upgrade pip
echo ""
echo "Step 3: Upgrading pip..."
pip install --upgrade pip --quiet
print_status "pip upgraded"

# Step 4: Install Python dependencies
echo ""
echo "Step 4: Installing Python dependencies..."
pip install -r requirements.txt --quiet
print_status "Python dependencies installed"

# Step 5: Install system dependencies
echo ""
echo "Step 5: Installing system dependencies..."

# Check if running with sudo capabilities
if [ "$EUID" -ne 0 ]; then
    print_warning "Not running as root. System packages will require sudo."
    SUDO="sudo"
else
    SUDO=""
fi

# Tesseract OCR
echo "  Installing Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    print_status "Tesseract already installed"
else
    $SUDO apt-get update -qq
    $SUDO apt-get install -y tesseract-ocr -qq
    print_status "Tesseract installed"
fi

# FFmpeg
echo "  Installing FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    print_status "FFmpeg already installed"
else
    $SUDO apt-get install -y ffmpeg -qq
    print_status "FFmpeg installed"
fi

# poppler-utils (for pdfinfo)
echo "  Installing poppler-utils..."
if command -v pdfinfo &> /dev/null; then
    print_status "poppler-utils already installed"
else
    $SUDO apt-get install -y poppler-utils -qq
    print_status "poppler-utils installed"
fi

# Step 6: Install LaTeX
echo ""
echo "Step 6: Installing LaTeX compiler..."
if command -v pdflatex &> /dev/null; then
    print_status "LaTeX already installed"
else
    echo "  This may take a few minutes..."
    $SUDO apt-get install -y texlive-latex-base texlive-latex-recommended texlive-fonts-extra -qq
    print_status "LaTeX installed"
fi

# Step 7: Setup environment file
echo ""
echo "Step 7: Setting up environment file..."
if [ -f ".env" ]; then
    print_warning ".env file already exists. Please verify GROQ_API_KEY is set."
else
    cp .env.example .env
    print_status ".env file created from template"
    print_warning "Please edit .env and add your GROQ_API_KEY"
    echo ""
    echo "  Get your FREE API key from: https://console.groq.com/keys"
fi

# Step 8: Create directories
echo ""
echo "Step 8: Creating directories..."
mkdir -p uploads output
touch uploads/.gitkeep output/.gitkeep
print_status "Directories created"

# Step 9: Verify installation
echo ""
echo "Step 9: Verifying installation..."

# Check Python packages
python3 -c "import langgraph; print('  LangGraph:', langgraph.__version__)" 2>/dev/null || print_warning "LangGraph not found"
python3 -c "import streamlit; print('  Streamlit:', streamlit.__version__)" 2>/dev/null || print_warning "Streamlit not found"
python3 -c "import pdfplumber; print('  pdfplumber: OK')" 2>/dev/null || print_warning "pdfplumber not found"
python3 -c "import pytesseract; print('  pytesseract: OK')" 2>/dev/null || print_warning "pytesseract not found"

# Check system tools
echo ""
echo "  System tools:"
tesseract --version 2>/dev/null | head -1 || print_warning "Tesseract not found"
ffmpeg -version 2>/dev/null | head -1 || print_warning "FFmpeg not found"
pdflatex --version 2>/dev/null | head -1 || print_warning "pdflatex not found"

# Final message
echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env file and add your GROQ_API_KEY"
echo "     Get free key: https://console.groq.com/keys"
echo ""
echo "  2. Activate virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  3. Run the application:"
echo "     streamlit run app.py"
echo ""
echo "=========================================="
