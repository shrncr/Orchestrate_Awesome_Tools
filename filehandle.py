from typing import Union
from io import BytesIO
import re
from ibm_watsonx_orchestrate.agent_builder.tools import tool
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

@tool
def create_pdf_from_text(title: str, content: str) -> bytes:
    """Creates a PDF file from markdown-formatted text and returns it as bytes.

    Args:
        title (str): The title of the PDF document.
        content (str): The main text content in markdown format to include in the PDF.
                      Supports: # headers, **bold**, *italic*, bullet lists, numbered lists, tables.

    Returns:
        bytes: The generated PDF file in bytes format.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Add the title
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 80, title)

    # Process markdown content
    y_position = height - 120
    left_margin = 72
    right_margin = width - 72
    max_width = right_margin - left_margin
    line_height = 14
    
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if we need a new page
        if y_position < 72:
            pdf.showPage()
            y_position = height - 72
        
        stripped = line.strip()
        
        # Handle markdown tables
        if '|' in stripped and stripped.startswith('|'):
            table_lines = []
            # Collect all table rows
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i])
                i += 1
            
            # Parse table
            if len(table_lines) >= 2:  # Need at least header and separator
                # Parse header
                header = [cell.strip() for cell in table_lines[0].split('|') if cell.strip()]
                
                # Skip separator line (the one with dashes)
                data_rows = []
                for row_line in table_lines[2:]:  # Skip header and separator
                    cells = [cell.strip() for cell in row_line.split('|') if cell.strip()]
                    if cells:
                        data_rows.append(cells)
                
                # Calculate column widths
                num_cols = len(header)
                col_width = max_width / num_cols
                
                # Draw table header
                pdf.setFont("Helvetica-Bold", 10)
                for col_idx, cell in enumerate(header):
                    x_pos = left_margin + (col_idx * col_width)
                    pdf.rect(x_pos, y_position - 12, col_width, 15)
                    # Wrap text if needed - inline wrapping for header
                    words = cell.split()
                    wrapped_lines = []
                    current_line = []
                    for word in words:
                        test_line = ' '.join(current_line + [word])
                        if pdf.stringWidth(test_line, "Helvetica-Bold", 10) <= col_width - 4:
                            current_line.append(word)
                        else:
                            if current_line:
                                wrapped_lines.append(' '.join(current_line))
                            current_line = [word]
                    if current_line:
                        wrapped_lines.append(' '.join(current_line))
                    
                    for wrap_idx, wrap_line in enumerate(wrapped_lines if wrapped_lines else [cell]):
                        pdf.drawString(x_pos + 2, y_position - 10 - (wrap_idx * 10), wrap_line)
                
                y_position -= 15
                
                # Draw data rows
                pdf.setFont("Helvetica", 10)
                for row in data_rows:
                    if y_position < 72:
                        pdf.showPage()
                        y_position = height - 72
                    
                    row_height = 12
                    for col_idx, cell in enumerate(row):
                        if col_idx >= num_cols:
                            break
                        x_pos = left_margin + (col_idx * col_width)
                        pdf.rect(x_pos, y_position - row_height, col_width, row_height + 3)
                        # Wrap text if needed - inline wrapping for data
                        words = cell.split()
                        wrapped_lines = []
                        current_line = []
                        for word in words:
                            test_line = ' '.join(current_line + [word])
                            if pdf.stringWidth(test_line, "Helvetica", 10) <= col_width - 4:
                                current_line.append(word)
                            else:
                                if current_line:
                                    wrapped_lines.append(' '.join(current_line))
                                current_line = [word]
                        if current_line:
                            wrapped_lines.append(' '.join(current_line))
                        
                        for wrap_idx, wrap_line in enumerate(wrapped_lines if wrapped_lines else [cell]):
                            pdf.drawString(x_pos + 2, y_position - 10 - (wrap_idx * 10), wrap_line)
                    
                    y_position -= row_height + 3
                
                y_position -= line_height
            continue
        
        # Handle headers with wrapping
        if stripped.startswith('### '):
            text = stripped[4:]
            # Wrap text inline
            words = text.split()
            wrapped_lines = []
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                if pdf.stringWidth(test_line, "Helvetica-Bold", 11) <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        wrapped_lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                wrapped_lines.append(' '.join(current_line))
            
            for wrap_line in (wrapped_lines if wrapped_lines else [text]):
                if y_position < 72:
                    pdf.showPage()
                    y_position = height - 72
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(left_margin, y_position, wrap_line)
                y_position -= line_height
                
        elif stripped.startswith('## '):
            text = stripped[3:]
            # Wrap text inline
            words = text.split()
            wrapped_lines = []
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                if pdf.stringWidth(test_line, "Helvetica-Bold", 13) <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        wrapped_lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                wrapped_lines.append(' '.join(current_line))
            
            for wrap_line in (wrapped_lines if wrapped_lines else [text]):
                if y_position < 72:
                    pdf.showPage()
                    y_position = height - 72
                pdf.setFont("Helvetica-Bold", 13)
                pdf.drawString(left_margin, y_position, wrap_line)
                y_position -= line_height + 2
                
        elif stripped.startswith('# '):
            text = stripped[2:]
            # Wrap text inline
            words = text.split()
            wrapped_lines = []
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                if pdf.stringWidth(test_line, "Helvetica-Bold", 15) <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        wrapped_lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                wrapped_lines.append(' '.join(current_line))
            
            for wrap_line in (wrapped_lines if wrapped_lines else [text]):
                if y_position < 72:
                    pdf.showPage()
                    y_position = height - 72
                pdf.setFont("Helvetica-Bold", 15)
                pdf.drawString(left_margin, y_position, wrap_line)
                y_position -= line_height + 4
        
        # Handle bullet lists with wrapping
        elif stripped.startswith('- ') or stripped.startswith('* '):
            text = stripped[2:]
            # Wrap text inline
            words = text.split()
            wrapped_lines = []
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                if pdf.stringWidth(test_line, "Helvetica", 11) <= max_width - 25:
                    current_line.append(word)
                else:
                    if current_line:
                        wrapped_lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                wrapped_lines.append(' '.join(current_line))
            
            for wrap_idx, wrap_line in enumerate(wrapped_lines if wrapped_lines else [text]):
                if y_position < 72:
                    pdf.showPage()
                    y_position = height - 72
                if wrap_idx == 0:
                    pdf.setFont("Helvetica", 11)
                    pdf.drawString(left_margin + 10, y_position, "•")
                
                # Draw formatted inline for each wrapped line
                current_x = left_margin + 25
                j = 0
                while j < len(wrap_line):
                    if wrap_line[j:j+2] == '**':
                        end = wrap_line.find('**', j + 2)
                        if end != -1:
                            pdf.setFont("Helvetica-Bold", 11)
                            chunk = wrap_line[j+2:end]
                            pdf.drawString(current_x, y_position, chunk)
                            current_x += pdf.stringWidth(chunk, "Helvetica-Bold", 11)
                            j = end + 2
                            continue
                    if wrap_line[j] == '*':
                        end = wrap_line.find('*', j + 1)
                        if end != -1:
                            pdf.setFont("Helvetica-Oblique", 11)
                            chunk = wrap_line[j+1:end]
                            pdf.drawString(current_x, y_position, chunk)
                            current_x += pdf.stringWidth(chunk, "Helvetica-Oblique", 11)
                            j = end + 1
                            continue
                    if wrap_line[j] == '`':
                        end = wrap_line.find('`', j + 1)
                        if end != -1:
                            pdf.setFont("Courier", 11)
                            chunk = wrap_line[j+1:end]
                            pdf.drawString(current_x, y_position, chunk)
                            current_x += pdf.stringWidth(chunk, "Courier", 11)
                            j = end + 1
                            continue
                    k = j
                    while k < len(wrap_line) and wrap_line[k] not in ['*', '`']:
                        k += 1
                    if k > j:
                        pdf.setFont("Helvetica", 11)
                        chunk = wrap_line[j:k]
                        pdf.drawString(current_x, y_position, chunk)
                        current_x += pdf.stringWidth(chunk, "Helvetica", 11)
                    j = k if k > j else j + 1
                
                y_position -= line_height
        
        # Handle numbered lists with wrapping
        elif re.match(r'^\d+\.\s', stripped):
            match = re.match(r'^(\d+\.)\s(.+)', stripped)
            if match:
                number = match.group(1)
                text = match.group(2)
                # Wrap text inline
                words = text.split()
                wrapped_lines = []
                current_line = []
                for word in words:
                    test_line = ' '.join(current_line + [word])
                    if pdf.stringWidth(test_line, "Helvetica", 11) <= max_width - 25:
                        current_line.append(word)
                    else:
                        if current_line:
                            wrapped_lines.append(' '.join(current_line))
                        current_line = [word]
                if current_line:
                    wrapped_lines.append(' '.join(current_line))
                
                for wrap_idx, wrap_line in enumerate(wrapped_lines if wrapped_lines else [text]):
                    if y_position < 72:
                        pdf.showPage()
                        y_position = height - 72
                    if wrap_idx == 0:
                        pdf.setFont("Helvetica", 11)
                        pdf.drawString(left_margin + 10, y_position, number)
                    
                    # Draw formatted inline for each wrapped line
                    current_x = left_margin + 25
                    j = 0
                    while j < len(wrap_line):
                        if wrap_line[j:j+2] == '**':
                            end = wrap_line.find('**', j + 2)
                            if end != -1:
                                pdf.setFont("Helvetica-Bold", 11)
                                chunk = wrap_line[j+2:end]
                                pdf.drawString(current_x, y_position, chunk)
                                current_x += pdf.stringWidth(chunk, "Helvetica-Bold", 11)
                                j = end + 2
                                continue
                        if wrap_line[j] == '*':
                            end = wrap_line.find('*', j + 1)
                            if end != -1:
                                pdf.setFont("Helvetica-Oblique", 11)
                                chunk = wrap_line[j+1:end]
                                pdf.drawString(current_x, y_position, chunk)
                                current_x += pdf.stringWidth(chunk, "Helvetica-Oblique", 11)
                                j = end + 1
                                continue
                        if wrap_line[j] == '`':
                            end = wrap_line.find('`', j + 1)
                            if end != -1:
                                pdf.setFont("Courier", 11)
                                chunk = wrap_line[j+1:end]
                                pdf.drawString(current_x, y_position, chunk)
                                current_x += pdf.stringWidth(chunk, "Courier", 11)
                                j = end + 1
                                continue
                        k = j
                        while k < len(wrap_line) and wrap_line[k] not in ['*', '`']:
                            k += 1
                        if k > j:
                            pdf.setFont("Helvetica", 11)
                            chunk = wrap_line[j:k]
                            pdf.drawString(current_x, y_position, chunk)
                            current_x += pdf.stringWidth(chunk, "Helvetica", 11)
                        j = k if k > j else j + 1
                    
                    y_position -= line_height
        
        # Handle empty lines
        elif not stripped:
            y_position -= line_height / 2
        
        # Regular paragraph with inline formatting and wrapping
        else:
            # Wrap text inline
            words = stripped.split()
            wrapped_lines = []
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                if pdf.stringWidth(test_line, "Helvetica", 11) <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        wrapped_lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                wrapped_lines.append(' '.join(current_line))
            
            for wrap_line in (wrapped_lines if wrapped_lines else [stripped]):
                if y_position < 72:
                    pdf.showPage()
                    y_position = height - 72
                
                # Draw formatted inline
                current_x = left_margin
                j = 0
                while j < len(wrap_line):
                    if wrap_line[j:j+2] == '**':
                        end = wrap_line.find('**', j + 2)
                        if end != -1:
                            pdf.setFont("Helvetica-Bold", 11)
                            chunk = wrap_line[j+2:end]
                            pdf.drawString(current_x, y_position, chunk)
                            current_x += pdf.stringWidth(chunk, "Helvetica-Bold", 11)
                            j = end + 2
                            continue
                    if wrap_line[j] == '*':
                        end = wrap_line.find('*', j + 1)
                        if end != -1:
                            pdf.setFont("Helvetica-Oblique", 11)
                            chunk = wrap_line[j+1:end]
                            pdf.drawString(current_x, y_position, chunk)
                            current_x += pdf.stringWidth(chunk, "Helvetica-Oblique", 11)
                            j = end + 1
                            continue
                    if wrap_line[j] == '`':
                        end = wrap_line.find('`', j + 1)
                        if end != -1:
                            pdf.setFont("Courier", 11)
                            chunk = wrap_line[j+1:end]
                            pdf.drawString(current_x, y_position, chunk)
                            current_x += pdf.stringWidth(chunk, "Courier", 11)
                            j = end + 1
                            continue
                    k = j
                    while k < len(wrap_line) and wrap_line[k] not in ['*', '`']:
                        k += 1
                    if k > j:
                        pdf.setFont("Helvetica", 11)
                        chunk = wrap_line[j:k]
                        pdf.drawString(current_x, y_position, chunk)
                        current_x += pdf.stringWidth(chunk, "Helvetica", 11)
                    j = k if k > j else j + 1
                
                y_position -= line_height
        
        i += 1

    pdf.showPage()
    pdf.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes