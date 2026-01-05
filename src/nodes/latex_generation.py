"""
Node 5: LaTeX Resume Generation (LLM-Powered with ADAPTIVE PAGE PRESSURE)

Uses LLM to intelligently generate clean, compilable LaTeX code.
Implements:
- Pressure-aware spacing and layout adjustments
- Adaptive compression for one-page targeting
- Strict LaTeX safety rules
"""
import os
import re
import json
from typing import Optional
from pathlib import Path

from ..models import WorkflowState, ResumeData
from ..utils.helpers import escape_latex, sanitize_latex
from ..utils.llm_client import call_llm


LATEX_GENERATION_PROMPT = """You are an expert LaTeX resume writer implementing STRICT STRUCTURAL CONSISTENCY.

🎯 CORE DIRECTIVE:
Generate a COMPLETE, COMPILABLE LaTeX resume with CONSISTENT STRUCTURE across ALL sections.
One page is the goal for ≈95% of resumes, but quality > page count.

🧱 STRICT STRUCTURE ENFORCEMENT (NON-NEGOTIABLE):
"If two sections look different structurally, the resume is wrong."

TARGET ROLE: {target_role}
PAGE PRESSURE: {page_pressure:.2f} (Range: 0.3-0.9)
COMPRESSION LEVEL: {compression_level}

RESUME DATA:
{resume_data}

=== 📐 CANONICAL ENTRY LAYOUT (MANDATORY FOR ALL SECTIONS) ===

ALL entries in Education, Experience, Projects, Extracurricular MUST follow this EXACT pattern:

\\textbf{{Title / Organization}} \\hfill Location
\\textit{{Role / Degree}} \\hfill Date Range
\\begin{{itemize}}[leftmargin=*, itemsep=2pt, topsep=2pt]
  \\item Bullet point
  \\item Bullet point
\\end{{itemize}}

🛑 FORBIDDEN LAYOUT PATTERNS:
- Do NOT mix tabular with \\hfill
- Do NOT use raw line breaks for alignment
- Do NOT change indentation per section
- Do NOT use \\resumeSubheading for some and raw LaTeX for others

=== 📌 EDUCATION SECTION RULES ===

Education entries MUST follow hierarchy:
1. Institution (bold) \\hfill Location
2. Degree / Certificate (italic) \\hfill Date Range
3. Academic metrics as single-line bullets ONLY

✅ CORRECT EDUCATION FORMAT:
\\textbf{{University Name}} \\hfill City, State
\\textit{{B.S. Computer Science, GPA: 3.8}} \\hfill Aug 2020 -- May 2024

❌ FORBIDDEN in Education:
- Multiple GPA bullets
- Percentile bullets spanning lines
- Overcrowding with school-level detail
- More than 1-2 bullets per education item
- School education (SSC/HSC) = 1 line max, NO bullets

=== 📌 EXPERIENCE SECTION RULES ===

\\textbf{{Company Name}} \\hfill Location
\\textit{{Job Title}} \\hfill Start Date -- End Date
\\begin{{itemize}}[leftmargin=*, itemsep=2pt, topsep=2pt]
  \\item Impact-driven bullet with metric
  \\item Technical achievement bullet
\\end{{itemize}}

=== 📌 PROJECT SECTION RULES ===

Each project MUST be structured as:

\\textbf{{Project Name}} \\hfill Date Range
\\begin{{itemize}}[leftmargin=*, itemsep=2pt, topsep=2pt]
  \\item Impact-driven bullet
  \\item Tech + outcome bullet
\\end{{itemize}}

❌ FORBIDDEN in Projects:
- Inline descriptions after project name
- More than 2 bullets unless justified
- Long project titles causing wraps
- Tech stack in title (put in bullets instead)

=== 📌 TECHNICAL SKILLS FORMATTING (NO BULLETS) ===

Skills MUST be written as inline categories, NOT bullets:

\\textbf{{Languages:}} Python, JavaScript, C++, Java \\\\
\\textbf{{Frameworks:}} Node.js, Express, React, Flask \\\\
\\textbf{{Tools:}} Git, Docker, AWS, PostgreSQL

❌ Do NOT use itemize for skills
❌ Do NOT allow skill lines to wrap unnecessarily
✅ Compact, single-line per category

=== 📌 BULLET INDENTATION & WRAPPING RULES ===

For ALL itemize blocks, ENFORCE:
- leftmargin=*
- itemsep=2pt
- topsep=2pt

Bullets MUST align vertically across the ENTIRE resume.
Wrapped lines MUST align under bullet text (not under bullet symbol).

=== ADAPTIVE SPACING BASED ON PAGE PRESSURE ===

{spacing_instructions}

=== BULLET WRITING RULES (CRITICAL) ===

Every bullet MUST:
- Start with strong action verb: Built, Led, Designed, Optimized, Implemented
- Include impact/metric when available
- Pattern: "[Verb] [what] achieving/using [result/tech]"
- PRESERVE FULL MEANING from the original data

🛑 FORBIDDEN:
- Do NOT shorten bullets by removing meaning
- Do NOT delete metrics to save space
- Do NOT replace specifics with generic wording

=== LATEX ESCAPING ===
- & → \\&, % → \\%, $ → \\$, # → \\#, _ → \\_
- C++ → C\\texttt{{++}}

=== PREAMBLE TEMPLATE ===

%-------------------------
% Resume in LaTeX - STRICT STRUCTURE
%-------------------------

\\documentclass[letterpaper,{font_size}pt]{{article}}

\\usepackage{{latexsym}}
\\usepackage[empty]{{fullpage}}
\\usepackage{{titlesec}}
\\usepackage{{marvosym}}
\\usepackage[usenames,dvipsnames]{{color}}
\\usepackage{{verbatim}}
\\usepackage{{enumitem}}
\\usepackage[hidelinks]{{hyperref}}
\\usepackage{{fancyhdr}}
\\usepackage{{tabularx}}

\\pagestyle{{fancy}}
\\fancyhf{{}}
\\fancyfoot{{}}
\\renewcommand{{\\headrulewidth}}{{0pt}}
\\renewcommand{{\\footrulewidth}}{{0pt}}

% ADAPTIVE MARGINS
\\addtolength{{\\oddsidemargin}}{{{margin_adjust}}}
\\addtolength{{\\evensidemargin}}{{{margin_adjust}}}
\\addtolength{{\\textwidth}}{{{text_width_adjust}}}
\\addtolength{{\\topmargin}}{{{top_margin_adjust}}}
\\addtolength{{\\textheight}}{{{text_height_adjust}}}

\\setlength{{\\footskip}}{{4pt}}
\\urlstyle{{same}}
\\raggedbottom
\\raggedright
\\setlength{{\\tabcolsep}}{{0in}}

% Section formatting
\\titleformat{{\\section}}{{
  \\vspace{{{section_vspace}}}\\scshape\\raggedright\\large
}}{{}}{{0em}}{{}}[\\color{{black}}\\titlerule \\vspace{{{section_vspace}}}]

\\begin{{document}}

% === HEADER ===
\\begin{{center}}
    {{\\Huge\\scshape Name}} \\\\ \\vspace{{1pt}}
    \\small Location $|$ Phone $|$ \\href{{mailto:email}}{{email}} \\\\
    \\href{{linkedin}}{{linkedin}} $|$ \\href{{github}}{{github}}
\\end{{center}}

% === EDUCATION ===
\\section{{Education}}
% Use: \\textbf{{Institution}} \\hfill Location
%      \\textit{{Degree}} \\hfill Dates

% === EXPERIENCE ===
\\section{{Experience}}
% Use canonical layout with itemize[leftmargin=*, itemsep=2pt, topsep=2pt]

% === PROJECTS ===
\\section{{Projects}}
% Use canonical layout

% === TECHNICAL SKILLS ===
\\section{{Technical Skills}}
% Use inline format: \\textbf{{Category:}} item1, item2, item3 \\\\

\\end{{document}}

=== 🧠 CONSISTENCY VERIFICATION (INTERNAL CHECK) ===

After generating LaTeX, VERIFY:
1. Every section uses the SAME alignment logic
2. Every entry has IDENTICAL indentation rules
3. No section visually "floats" differently
4. Skills use inline format, NOT bullets
5. All itemize blocks have [leftmargin=*, itemsep=2pt, topsep=2pt]

If inconsistency is detected: REGENERATE the section.

=== OUTPUT RULES ===
- Output ONLY the complete LaTeX code
- NO markdown blocks, NO explanations
- Start with %-------------------------
- End with \\end{{document}}
- VERIFY: Content preserves ALL information from source data
"""


def get_adaptive_spacing_config(page_pressure: float) -> dict:
    """
    Get LaTeX spacing configuration based on page pressure.
    
    Higher pressure = tighter spacing for one-page fit.
    """
    if page_pressure < 0.45:
        # Light pressure - comfortable spacing
        return {
            'font_size': '11',
            'margin_adjust': '-0.55in',
            'text_width_adjust': '1.1in',
            'top_margin_adjust': '-0.5in',
            'text_height_adjust': '1.0in',
            'section_vspace': '-5pt',
            'item_vspace': '-2pt',
            'subheading_vspace': '-2pt',
            'subheading_after_vspace': '-7pt',
            'project_vspace': '-7pt',
            'item_sep': '-1pt',
            'list_end_vspace': '-5pt',
            'bullet_item_sep': '-2pt',
            'bullet_list_end_vspace': '-5pt',
        }
    elif page_pressure < 0.6:
        # Medium pressure - compact spacing
        return {
            'font_size': '10',
            'margin_adjust': '-0.6in',
            'text_width_adjust': '1.2in',
            'top_margin_adjust': '-0.55in',
            'text_height_adjust': '1.1in',
            'section_vspace': '-6pt',
            'item_vspace': '-3pt',
            'subheading_vspace': '-3pt',
            'subheading_after_vspace': '-8pt',
            'project_vspace': '-8pt',
            'item_sep': '-2pt',
            'list_end_vspace': '-5pt',
            'bullet_item_sep': '-2pt',
            'bullet_list_end_vspace': '-6pt',
        }
    elif page_pressure < 0.8:
        # Aggressive pressure - tight spacing
        return {
            'font_size': '10',
            'margin_adjust': '-0.65in',
            'text_width_adjust': '1.3in',
            'top_margin_adjust': '-0.6in',
            'text_height_adjust': '1.2in',
            'section_vspace': '-6pt',
            'item_vspace': '-3pt',
            'subheading_vspace': '-3pt',
            'subheading_after_vspace': '-8pt',
            'project_vspace': '-8pt',
            'item_sep': '-2pt',
            'list_end_vspace': '-5pt',
            'bullet_item_sep': '-3pt',
            'bullet_list_end_vspace': '-6pt',
        }
    else:
        # MAXIMUM pressure - ULTRA-TIGHT spacing
        return {
            'font_size': '10',
            'margin_adjust': '-0.7in',
            'text_width_adjust': '1.4in',
            'top_margin_adjust': '-0.65in',
            'text_height_adjust': '1.3in',
            'section_vspace': '-7pt',
            'item_vspace': '-3pt',
            'subheading_vspace': '-4pt',
            'subheading_after_vspace': '-9pt',
            'project_vspace': '-9pt',
            'item_sep': '-3pt',
            'list_end_vspace': '-6pt',
            'bullet_item_sep': '-3pt',
            'bullet_list_end_vspace': '-7pt',
        }


def get_spacing_instructions(page_pressure: float) -> str:
    """Get human-readable spacing instructions for the LLM."""
    if page_pressure < 0.45:
        return """
LIGHT COMPRESSION MODE:
- Use comfortable spacing between sections
- Standard margins and font size (11pt)
- Full bullet points with complete details
- Include all optional sections if data exists
- MAX 4 bullets per experience/project
"""
    elif page_pressure < 0.6:
        return """
MEDIUM COMPRESSION MODE:
- Use compact spacing (-5pt to -6pt between sections)
- Slightly tighter margins, 10pt font
- Concise bullets (15-18 words, one line)
- MAX 3 bullets per experience, MAX 2-3 per project
- Reduce optional sections
"""
    elif page_pressure < 0.8:
        return """
AGGRESSIVE COMPRESSION MODE:
- Maximum space efficiency (-6pt to -8pt spacing)
- Tight margins and 10pt font
- Ultra-concise bullets (15 words max, one line STRICT)
- MAX 2 bullets per experience, MAX 2 per project
- REMOVE optional sections (achievements, certifications)
- Compress dates: "Aug 2023 - Dec 2024" → "Aug 2023 - Dec 2024"
"""
    else:
        return """
☢️ MAXIMUM COMPRESSION MODE - NUCLEAR OPTION:
- ULTRA-TIGHT spacing (-7pt to -9pt)
- Tightest margins possible, 10pt font
- Bullets MUST be under 15 words
- MAX 2 bullets per experience
- MAX 2 bullets per project
- MAX 2-3 experiences total
- MAX 2-3 projects total
- REMOVE ALL: achievements, certifications, extracurricular
- Education: degree, school, GPA, dates ONLY
- Fix ALL spacing issues in text
- EVERY bullet MUST have a metric/number
"""


def get_compression_level(page_pressure: float) -> str:
    """Get compression level string."""
    if page_pressure < 0.45:
        return 'light'
    elif page_pressure < 0.6:
        return 'medium'
    elif page_pressure < 0.8:
        return 'aggressive'
    else:
        return 'maximum'


def generate_latex_with_llm(resume_data: ResumeData, target_role: str, page_pressure: float = 0.4) -> str:
    """Use LLM to intelligently generate LaTeX code with adaptive spacing."""
    
    # Get spacing configuration based on pressure
    spacing_config = get_adaptive_spacing_config(page_pressure)
    spacing_instructions = get_spacing_instructions(page_pressure)
    compression_level = get_compression_level(page_pressure)
    
    # Convert resume data to readable format for LLM
    data_json = json.dumps(resume_data.to_dict(), indent=2)
    
    # Build prompt with adaptive parameters
    prompt = LATEX_GENERATION_PROMPT.format(
        target_role=target_role,
        page_pressure=page_pressure,
        compression_level=compression_level.upper(),
        resume_data=data_json,
        spacing_instructions=spacing_instructions,
        **spacing_config
    )
    
    # Call LLM to generate LaTeX
    response = call_llm(
        system_prompt="You are an expert LaTeX resume generator. Output ONLY valid, compilable LaTeX code. No explanations, no markdown. PRESERVE all information from the source data.",
        user_prompt=prompt,
        temperature=0
    )
    
    # Clean up the response
    latex_code = response.strip()
    
    # Remove any markdown code blocks if present
    if latex_code.startswith("```"):
        # Find the end of opening block
        first_newline = latex_code.find("\n")
        if first_newline != -1:
            latex_code = latex_code[first_newline+1:]
        # Remove closing ```
        if latex_code.endswith("```"):
            latex_code = latex_code[:-3]
        latex_code = latex_code.strip()
    
    # Ensure it starts with the document
    if not latex_code.startswith("%") and not latex_code.startswith("\\"):
        # Try to find the start of LaTeX
        doc_start = latex_code.find("\\documentclass")
        if doc_start != -1:
            latex_code = latex_code[doc_start:]
    
    return latex_code


def generate_header(personal) -> str:
    """Generate LaTeX header with personal info."""
    lines = []
    
    # Name
    name = escape_latex(personal.name) if personal.name else "Your Name"
    lines.append(f"\\begin{{center}}")
    lines.append(f"    {{\\Huge\\scshape {name}}} \\\\ \\vspace{{1pt}}")
    
    # Contact line
    contact_parts = []
    
    if personal.location:
        contact_parts.append(escape_latex(personal.location))
    
    if personal.phone:
        contact_parts.append(escape_latex(personal.phone))
    
    if personal.email:
        email = escape_latex(personal.email)
        contact_parts.append(f"\\href{{mailto:{personal.email}}}{{{email}}}")
    
    if contact_parts:
        lines.append(f"    \\small {' $|$ '.join(contact_parts)} \\\\")
    
    # Links line
    link_parts = []
    
    if personal.linkedin:
        linkedin_clean = personal.linkedin.replace("https://", "").replace("http://", "")
        link_parts.append(f"\\href{{{personal.linkedin}}}{{\\underline{{{escape_latex(linkedin_clean)}}}}}")
    
    if personal.github:
        github_clean = personal.github.replace("https://", "").replace("http://", "")
        link_parts.append(f"\\href{{{personal.github}}}{{\\underline{{{escape_latex(github_clean)}}}}}")
    
    if personal.portfolio:
        portfolio_clean = personal.portfolio.replace("https://", "").replace("http://", "")
        link_parts.append(f"\\href{{{personal.portfolio}}}{{\\underline{{{escape_latex(portfolio_clean)}}}}}")
    
    if link_parts:
        lines.append(f"    \\small {' $|$ '.join(link_parts)}")
    
    lines.append(f"\\end{{center}}")
    
    return "\n".join(lines)


def generate_education(education_list) -> str:
    """Generate LaTeX education section with CANONICAL LAYOUT."""
    if not education_list:
        return ""
    
    lines = ["\\section{Education}"]
    
    for i, edu in enumerate(education_list):
        institution = escape_latex(edu.institution)
        degree = escape_latex(edu.degree)
        field = escape_latex(edu.field_of_study) if edu.field_of_study else ""
        
        if field:
            degree_line = f"{degree} in {field}"
        else:
            degree_line = degree
        
        # Add GPA to degree line if available (keeps education compact)
        if edu.gpa:
            degree_line += f", GPA: {escape_latex(edu.gpa)}"
        
        dates = ""
        if edu.start_date or edu.end_date:
            start = escape_latex(edu.start_date) if edu.start_date else ""
            end = escape_latex(edu.end_date) if edu.end_date else ""
            dates = f"{start} -- {end}" if start and end else (start or end)
        
        location = escape_latex(edu.location) if hasattr(edu, 'location') and edu.location else ""
        
        # CANONICAL LAYOUT: \textbf{Institution} \hfill Location
        #                   \textit{Degree} \hfill Dates
        if location:
            lines.append(f"\\textbf{{{institution}}} \\hfill {location} \\\\")
        else:
            lines.append(f"\\textbf{{{institution}}} \\\\")
        
        lines.append(f"\\textit{{{degree_line}}} \\hfill {dates}")
        
        # Only add bullets for notable achievements (coursework, honors) - MAX 1-2
        notable_items = []
        if edu.coursework and len(edu.coursework) > 0:
            coursework = ", ".join([escape_latex(c) for c in edu.coursework[:5]])  # Max 5 courses
            notable_items.append(f"Relevant Coursework: {coursework}")
        
        if edu.achievements and len(edu.achievements) > 0:
            for ach in edu.achievements[:1]:  # Max 1 achievement
                notable_items.append(escape_latex(ach))
        
        if notable_items:
            lines.append("\\begin{itemize}[leftmargin=*, itemsep=2pt, topsep=2pt]")
            for item in notable_items[:2]:  # MAX 2 bullets per education
                lines.append(f"  \\item {item}")
            lines.append("\\end{itemize}")
        
        # Add spacing between education entries
        if i < len(education_list) - 1:
            lines.append("\\vspace{4pt}")
    
    return "\n".join(lines)


def generate_experience(experience_list) -> str:
    """Generate LaTeX experience section with CANONICAL LAYOUT."""
    if not experience_list:
        return ""
    
    lines = ["\\section{Experience}"]
    
    for i, exp in enumerate(experience_list):
        company = escape_latex(exp.company)
        title = escape_latex(exp.title)
        location = escape_latex(exp.location) if exp.location else ""
        
        dates = ""
        if exp.start_date or exp.end_date:
            start = escape_latex(exp.start_date) if exp.start_date else ""
            end = "Present" if exp.is_current else (escape_latex(exp.end_date) if exp.end_date else "")
            dates = f"{start} -- {end}" if start else end
        
        # CANONICAL LAYOUT: \textbf{Company} \hfill Location
        #                   \textit{Title} \hfill Dates
        if location:
            lines.append(f"\\textbf{{{company}}} \\hfill {location} \\\\")
        else:
            lines.append(f"\\textbf{{{company}}} \\\\")
        
        lines.append(f"\\textit{{{title}}} \\hfill {dates}")
        
        if exp.bullets:
            lines.append("\\begin{itemize}[leftmargin=*, itemsep=2pt, topsep=2pt]")
            for bullet in exp.bullets:
                bullet_text = escape_latex(bullet)
                lines.append(f"  \\item {bullet_text}")
            lines.append("\\end{itemize}")
        
        # Add spacing between experience entries
        if i < len(experience_list) - 1:
            lines.append("\\vspace{4pt}")
    
    return "\n".join(lines)


def generate_projects(projects_list) -> str:
    """Generate LaTeX projects section with CANONICAL LAYOUT."""
    if not projects_list:
        return ""
    
    lines = ["\\section{Projects}"]
    
    for i, proj in enumerate(projects_list):
        name = escape_latex(proj.name)
        
        dates = ""
        if proj.start_date or proj.end_date:
            start = escape_latex(proj.start_date) if proj.start_date else ""
            end = escape_latex(proj.end_date) if proj.end_date else ""
            dates = f"{start} -- {end}" if start and end else (start or end)
        
        # CANONICAL LAYOUT: \textbf{Project Name} \hfill Date Range
        lines.append(f"\\textbf{{{name}}} \\hfill {dates}")
        
        if proj.bullets:
            lines.append("\\begin{itemize}[leftmargin=*, itemsep=2pt, topsep=2pt]")
            for bullet in proj.bullets:
                bullet_text = escape_latex(bullet)
                lines.append(f"  \\item {bullet_text}")
            lines.append("\\end{itemize}")
        
        # Add spacing between project entries
        if i < len(projects_list) - 1:
            lines.append("\\vspace{4pt}")
    
    return "\n".join(lines)


def generate_skills(skills) -> str:
    """Generate LaTeX technical skills section with INLINE FORMAT (no bullets)."""
    lines = ["\\section{Technical Skills}"]
    
    skill_lines = []
    
    if skills.languages:
        langs = ", ".join([escape_latex(s) for s in skills.languages])
        skill_lines.append(f"\\textbf{{Languages:}} {langs}")
    
    if skills.frameworks:
        frameworks = ", ".join([escape_latex(s) for s in skills.frameworks])
        skill_lines.append(f"\\textbf{{Frameworks:}} {frameworks}")
    
    if skills.tools:
        tools = ", ".join([escape_latex(s) for s in skills.tools])
        skill_lines.append(f"\\textbf{{Developer Tools:}} {tools}")
    
    if skills.databases:
        dbs = ", ".join([escape_latex(s) for s in skills.databases])
        skill_lines.append(f"\\textbf{{Databases:}} {dbs}")
    
    if skills.cloud:
        cloud = ", ".join([escape_latex(s) for s in skills.cloud])
        skill_lines.append(f"\\textbf{{Cloud/DevOps:}} {cloud}")
    
    if skills.other:
        other = ", ".join([escape_latex(s) for s in skills.other])
        skill_lines.append(f"\\textbf{{Other:}} {other}")
    
    # Join with \\ for line breaks, no bullets
    lines.append(" \\\\\n".join(skill_lines))
    
    return "\n".join(lines)


def generate_extracurricular(extracurricular_list) -> str:
    """Generate LaTeX extracurricular section with CANONICAL LAYOUT."""
    if not extracurricular_list:
        return ""
    
    lines = ["\\section{Extracurricular Activities}"]
    
    for i, extra in enumerate(extracurricular_list):
        org = escape_latex(extra.organization)
        role = escape_latex(extra.role) if extra.role else ""
        
        dates = ""
        if extra.start_date or extra.end_date:
            start = escape_latex(extra.start_date) if extra.start_date else ""
            end = escape_latex(extra.end_date) if extra.end_date else ""
            dates = f"{start} -- {end}" if start and end else (start or end)
        
        # CANONICAL LAYOUT: \textbf{Organization} \hfill Dates
        #                   \textit{Role}
        lines.append(f"\\textbf{{{org}}} \\hfill {dates}")
        if role:
            lines.append(f"\\textit{{{role}}}")
        
        if extra.bullets:
            lines.append("\\begin{itemize}[leftmargin=*, itemsep=2pt, topsep=2pt]")
            for bullet in extra.bullets:
                bullet_text = escape_latex(bullet)
                lines.append(f"  \\item {bullet_text}")
            lines.append("\\end{itemize}")
        
        # Add spacing between entries
        if i < len(extracurricular_list) - 1:
            lines.append("\\vspace{4pt}")
    
    return "\n".join(lines)


def generate_certifications(certifications_list) -> str:
    """Generate LaTeX certifications section with INLINE FORMAT (compact)."""
    if not certifications_list:
        return ""
    
    lines = ["\\section{Certifications}"]
    
    # Format certifications as inline list for compactness
    cert_items = []
    for cert in certifications_list:
        name = escape_latex(cert.name)
        issuer = escape_latex(cert.issuer) if cert.issuer else ""
        if issuer:
            cert_items.append(f"{name} ({issuer})")
        else:
            cert_items.append(name)
    
    # Join as comma-separated inline list
    lines.append(", ".join(cert_items))
    
    return "\n".join(lines)


def generate_achievements(achievements_list) -> str:
    """Generate LaTeX achievements section with INLINE FORMAT (compact)."""
    if not achievements_list:
        return ""
    
    lines = ["\\section{Achievements}"]
    
    # Format achievements as compact list
    for ach in achievements_list:
        title = escape_latex(ach.title)
        desc = escape_latex(ach.description) if ach.description else ""
        date = escape_latex(ach.date) if ach.date else ""
        
        if desc:
            lines.append(f"\\textbf{{{title}}} -- {desc} \\hfill {date}")
        else:
            lines.append(f"\\textbf{{{title}}} \\hfill {date}")
    
    return "\n".join(lines)


def get_latex_preamble(page_pressure: float = 0.4) -> str:
    """Get the LaTeX document preamble with adaptive spacing."""
    config = get_adaptive_spacing_config(page_pressure)
    
    return r"""%-------------------------
% Resume in LaTeX - ADAPTIVE LAYOUT
% Author: Resume Generator AI
% License: MIT
%-------------------------

\documentclass[letterpaper,""" + config['font_size'] + r"""pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage{tabularx}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Adaptive margins
\addtolength{\oddsidemargin}{""" + config['margin_adjust'] + r"""}
\addtolength{\evensidemargin}{""" + config['margin_adjust'] + r"""}
\addtolength{\textwidth}{""" + config['text_width_adjust'] + r"""}
\addtolength{\topmargin}{""" + config['top_margin_adjust'] + r"""}
\addtolength{\textheight}{""" + config['text_height_adjust'] + r"""}

% Fix footskip warning
\setlength{\footskip}{4pt}

\urlstyle{same}

\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Section formatting
\titleformat{\section}{
  \vspace{""" + config['section_vspace'] + r"""}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{""" + config['section_vspace'] + r"""}]

% Bullet label for nested lists
\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

%-------------------------------------------
"""


def generate_template_based(resume_data: ResumeData, page_pressure: float = 0.4) -> str:
    """Generate LaTeX using template-based approach (fallback) with adaptive spacing."""
    sections = []
    
    # Preamble with adaptive spacing
    sections.append(get_latex_preamble(page_pressure))
    
    # Document start
    sections.append("\\begin{document}")
    sections.append("")
    
    # Header (personal info)
    sections.append(generate_header(resume_data.personal))
    sections.append("")
    
    # Education (MANDATORY)
    edu_section = generate_education(resume_data.education)
    if edu_section:
        sections.append(edu_section)
        sections.append("")
    
    # Experience (MANDATORY)
    exp_section = generate_experience(resume_data.experience)
    if exp_section:
        sections.append(exp_section)
        sections.append("")
    
    # Projects (MANDATORY)
    proj_section = generate_projects(resume_data.projects)
    if proj_section:
        sections.append(proj_section)
        sections.append("")
    
    # Technical Skills (MANDATORY)
    skills_section = generate_skills(resume_data.skills)
    if skills_section:
        sections.append(skills_section)
        sections.append("")
    
    # Extracurricular (MANDATORY)
    extra_section = generate_extracurricular(resume_data.extracurricular)
    if extra_section:
        sections.append(extra_section)
        sections.append("")
    
    # Optional sections - only include if not in aggressive compression
    compression_level = get_compression_level(page_pressure)
    
    # Certifications (OPTIONAL)
    if resume_data.certifications and compression_level != 'aggressive':
        cert_section = generate_certifications(resume_data.certifications)
        if cert_section:
            sections.append(cert_section)
            sections.append("")
    
    # Achievements (OPTIONAL)
    if resume_data.achievements and compression_level != 'aggressive':
        ach_section = generate_achievements(resume_data.achievements)
        if ach_section:
            sections.append(ach_section)
            sections.append("")
    
    # Document end
    sections.append("\\end{document}")
    
    return "\n".join(sections)


def generate_latex(state: WorkflowState) -> WorkflowState:
    """
    Main LaTeX generation node with ADAPTIVE PAGE PRESSURE.
    
    This is LangGraph Node 5: LaTeX Resume Generation
    
    Implements pressure-aware spacing and layout for optimal page fitting.
    """
    # Use optimized data if available, otherwise use original
    resume_data = state.optimized_data or state.resume_data
    
    if not resume_data:
        state.error = "No resume data to generate LaTeX from"
        return state
    
    try:
        # Save checkpoint before generation
        state.save_checkpoint()
        
        # Try LLM-based generation first (with page pressure)
        try:
            latex_code = generate_latex_with_llm(
                resume_data, 
                state.target_role or "Software Engineer",
                state.page_pressure
            )
            
            # Validate it looks like LaTeX
            if "\\documentclass" not in latex_code or "\\end{document}" not in latex_code:
                raise ValueError("LLM did not generate valid LaTeX structure")
                
        except Exception as llm_error:
            # Fallback to template-based generation with adaptive spacing
            print(f"LLM generation failed ({str(llm_error)}), using template-based approach")
            latex_code = generate_template_based(resume_data, state.page_pressure)
        
        # Sanitize the LaTeX code
        sanitized_code, is_safe = sanitize_latex(latex_code)
        
        if not is_safe:
            print("Warning: Unsafe LaTeX commands were detected and removed")
        
        state.latex_code = sanitized_code
        state.current_node = "latex_generated"
        
        compression_level = get_compression_level(state.page_pressure)
        print(f"📄 LaTeX generated (pressure: {state.page_pressure:.2f}, level: {compression_level})")
        
    except Exception as e:
        state.error = f"LaTeX generation error: {str(e)}"
    
    return state
