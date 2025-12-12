from typing import Union
from io import BytesIO
import re
from ibm_watsonx_orchestrate.agent_builder.tools import tool
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def sanitize_text(text: str) -> str:
    """Sanitize text to prevent rendering issues with special characters.
    
    Replaces various dash and special characters that may render as black squares
    with standard ASCII equivalents.
    """
    # Replace various types of dashes with standard hyphen
    text = text.replace('—', '-')  # Em dash
    text = text.replace('–', '-')  # En dash
    text = text.replace('−', '-')  # Minus sign
    text = text.replace('‐', '-')  # Hyphen (Unicode)
    text = text.replace('‑', '-')  # Non-breaking hyphen
    text = text.replace('‒', '-')  # Figure dash
    text = text.replace('―', '-')  # Horizontal bar
    
    # Replace smart quotes with standard quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    # Replace ellipsis
    text = text.replace('…', '...')
    
    return text

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

    # Add the title (sanitize to prevent black squares)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 80, sanitize_text(title))

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
                
                # First pass: calculate header height based on wrapped content
                header_wrapped = []
                max_header_lines = 1
                for cell in header:
                    # Sanitize text to prevent black squares
                    cell = sanitize_text(cell)
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
                    header_wrapped.append(wrapped_lines if wrapped_lines else [cell])
                    max_header_lines = max(max_header_lines, len(header_wrapped[-1]))
                
                # Calculate dynamic header height
                header_height = max_header_lines * 10 + 5
                
                # Draw header cells with dynamic height
                for col_idx, wrapped_lines in enumerate(header_wrapped):
                    x_pos = left_margin + (col_idx * col_width)
                    pdf.rect(x_pos, y_position - header_height + 3, col_width, header_height)
                    
                    for wrap_idx, wrap_line in enumerate(wrapped_lines):
                        # Handle inline formatting in header cells
                        current_x = x_pos + 2
                        j = 0
                        while j < len(wrap_line):
                            if wrap_line[j:j+2] == '**':
                                end = wrap_line.find('**', j + 2)
                                if end != -1:
                                    pdf.setFont("Helvetica-Bold", 10)
                                    chunk = wrap_line[j+2:end]
                                    pdf.drawString(current_x, y_position - 10 - (wrap_idx * 10), chunk)
                                    current_x += pdf.stringWidth(chunk, "Helvetica-Bold", 10)
                                    j = end + 2
                                    continue
                            if wrap_line[j] == '*':
                                end = wrap_line.find('*', j + 1)
                                if end != -1:
                                    pdf.setFont("Helvetica-Oblique", 10)
                                    chunk = wrap_line[j+1:end]
                                    pdf.drawString(current_x, y_position - 10 - (wrap_idx * 10), chunk)
                                    current_x += pdf.stringWidth(chunk, "Helvetica-Oblique", 10)
                                    j = end + 1
                                    continue
                            if wrap_line[j] == '`':
                                end = wrap_line.find('`', j + 1)
                                if end != -1:
                                    pdf.setFont("Courier", 10)
                                    chunk = wrap_line[j+1:end]
                                    pdf.drawString(current_x, y_position - 10 - (wrap_idx * 10), chunk)
                                    current_x += pdf.stringWidth(chunk, "Courier", 10)
                                    j = end + 1
                                    continue
                            k = j
                            while k < len(wrap_line) and wrap_line[k] not in ['*', '`']:
                                k += 1
                            if k > j:
                                pdf.setFont("Helvetica-Bold", 10)
                                chunk = wrap_line[j:k]
                                pdf.drawString(current_x, y_position - 10 - (wrap_idx * 10), chunk)
                                current_x += pdf.stringWidth(chunk, "Helvetica-Bold", 10)
                            j = k if k > j else j + 1
                
                y_position -= header_height
                
                # Draw data rows
                pdf.setFont("Helvetica", 10)
                for row in data_rows:
                    if y_position < 72:
                        pdf.showPage()
                        y_position = height - 72
                    
                    # First pass: calculate row height based on wrapped content
                    row_wrapped = []
                    max_row_lines = 1
                    for col_idx, cell in enumerate(row):
                        if col_idx >= num_cols:
                            break
                        # Sanitize text to prevent black squares
                        cell = sanitize_text(cell)
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
                        row_wrapped.append(wrapped_lines if wrapped_lines else [cell])
                        max_row_lines = max(max_row_lines, len(row_wrapped[-1]))
                    
                    # Calculate dynamic row height
                    row_height = max_row_lines * 10 + 5
                    
                    # Draw row cells with dynamic height
                    for col_idx, wrapped_lines in enumerate(row_wrapped):
                        x_pos = left_margin + (col_idx * col_width)
                        pdf.rect(x_pos, y_position - row_height + 3, col_width, row_height)
                        
                        for wrap_idx, wrap_line in enumerate(wrapped_lines):
                            # Handle inline formatting in data cells
                            current_x = x_pos + 2
                            j = 0
                            while j < len(wrap_line):
                                if wrap_line[j:j+2] == '**':
                                    end = wrap_line.find('**', j + 2)
                                    if end != -1:
                                        pdf.setFont("Helvetica-Bold", 10)
                                        chunk = wrap_line[j+2:end]
                                        pdf.drawString(current_x, y_position - 10 - (wrap_idx * 10), chunk)
                                        current_x += pdf.stringWidth(chunk, "Helvetica-Bold", 10)
                                        j = end + 2
                                        continue
                                if wrap_line[j] == '*':
                                    end = wrap_line.find('*', j + 1)
                                    if end != -1:
                                        pdf.setFont("Helvetica-Oblique", 10)
                                        chunk = wrap_line[j+1:end]
                                        pdf.drawString(current_x, y_position - 10 - (wrap_idx * 10), chunk)
                                        current_x += pdf.stringWidth(chunk, "Helvetica-Oblique", 10)
                                        j = end + 1
                                        continue
                                if wrap_line[j] == '`':
                                    end = wrap_line.find('`', j + 1)
                                    if end != -1:
                                        pdf.setFont("Courier", 10)
                                        chunk = wrap_line[j+1:end]
                                        pdf.drawString(current_x, y_position - 10 - (wrap_idx * 10), chunk)
                                        current_x += pdf.stringWidth(chunk, "Courier", 10)
                                        j = end + 1
                                        continue
                                k = j
                                while k < len(wrap_line) and wrap_line[k] not in ['*', '`']:
                                    k += 1
                                if k > j:
                                    pdf.setFont("Helvetica", 10)
                                    chunk = wrap_line[j:k]
                                    pdf.drawString(current_x, y_position - 10 - (wrap_idx * 10), chunk)
                                    current_x += pdf.stringWidth(chunk, "Helvetica", 10)
                                j = k if k > j else j + 1
                    
                    y_position -= row_height
                
                y_position -= line_height
            continue
        
        # Handle horizontal rules (---, ___, ***)
        if re.match(r'^[-_*]{3,}$', stripped):
            if y_position < 72:
                pdf.showPage()
                y_position = height - 72
            pdf.setLineWidth(1)
            pdf.line(left_margin, y_position, right_margin, y_position)
            y_position -= line_height
            i += 1
            continue
        
        # Handle block quotes (>)
        if stripped.startswith('> '):
            text = sanitize_text(stripped[2:])
            # Wrap text inline with indentation
            words = text.split()
            wrapped_lines = []
            current_line = []
            indent_width = 20
            for word in words:
                test_line = ' '.join(current_line + [word])
                if pdf.stringWidth(test_line, "Helvetica-Oblique", 11) <= max_width - indent_width:
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
                pdf.setFont("Helvetica-Oblique", 11)
                pdf.drawString(left_margin + indent_width, y_position, wrap_line)
                y_position -= line_height
            i += 1
            continue
        
        # Handle headers with wrapping
        if stripped.startswith('### '):
            text = sanitize_text(stripped[4:])
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
            text = sanitize_text(stripped[3:])
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
            text = sanitize_text(stripped[2:])
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
            text = sanitize_text(stripped[2:])
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
                text = sanitize_text(match.group(2))
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
            # Sanitize and wrap text inline
            stripped = sanitize_text(stripped)
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
