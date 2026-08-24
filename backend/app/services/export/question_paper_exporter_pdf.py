import io
from fpdf import FPDF
from app.models.paper import QuestionPaper, PaperStatus

def _clean_text(text: str) -> str:
    if not text:
        return ""
    replacements = {
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "--",
        "\u2026": "...",
        "\u00a0": " ",
        "\u2264": "<=", "\u2265": ">=",
        "\u2260": "!=", "\u00b1": "+/-",
        "\u00d7": "*", "\u00f7": "/",
        "\u03bc": "u", "\u03a9": "Ohm",
        "\u03c0": "pi", "\u03b8": "theta",
        "\u03bb": "lambda", "\u03b1": "alpha", "\u03b2": "beta", "\u03b3": "gamma"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")

def export_question_paper_pdf(paper: QuestionPaper) -> io.BytesIO:
    if paper.status != PaperStatus.APPROVED:
        raise ValueError("Only APPROVED papers can be exported.")
        
    pdf = FPDF()
    pdf.add_page()
    
    # Fonts
    pdf.set_font("Helvetica", "B", 16)
    
    # Title
    title = _clean_text(paper.title)
    try:
        pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align='C')
    except:
        pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(5)
    
    # Sort items by order_index
    items = sorted(paper.items, key=lambda x: x.order_index)
    
    # Group by section
    sections = {}
    for item in items:
        if item.section_name not in sections:
            sections[item.section_name] = []
        sections[item.section_name].append(item)
        
    question_number = 1
    
    for section_name, section_items in sections.items():
        pdf.set_font("Helvetica", "B", 14)
        s_name = _clean_text(section_name)
        try:
            pdf.cell(0, 10, s_name, new_x="LMARGIN", new_y="NEXT")
        except:
            pdf.cell(0, 10, s_name, ln=True)
        pdf.ln(2)
        
        for item in section_items:
            marks = item.marks_override if item.marks_override is not None else item.marks_snapshot
            question_text = _clean_text(item.question_text_snapshot)
            options = item.content_snapshot.get("options", [])
            
            pdf.set_font("Helvetica", "B", 12)
            try:
                pdf.cell(10, 6, f"{question_number}.", new_x="RIGHT")
            except:
                pdf.cell(10, 6, f"{question_number}.")
                
            pdf.set_font("Helvetica", "", 12)
            pdf.multi_cell(0, 6, question_text)
            
            if options:
                pdf.ln(2)
                for opt in options:
                    opt_id = _clean_text(str(opt.get('id', '')))
                    opt_text = _clean_text(str(opt.get('text', '')))
                    pdf.set_font("Helvetica", "", 11)
                    pdf.set_x(pdf.l_margin + 10)
                    pdf.multi_cell(0, 5, f"{opt_id}. {opt_text}")
            
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_x(pdf.l_margin)
            try:
                pdf.cell(0, 6, f"[{marks} Marks]", new_x="LMARGIN", new_y="NEXT", align="R")
            except:
                pdf.cell(0, 6, f"[{marks} Marks]", ln=True, align="R")
                
            pdf.ln(4)
            question_number += 1
            
    buffer = io.BytesIO()
    try:
        buffer.write(pdf.output())
    except TypeError:
        buffer.write(pdf.output(dest='S').encode('latin1'))
    
    buffer.seek(0)
    return buffer

