"""
pdf_generator.py — Generates a formatted RTI application PDF
Uses ReportLab library
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


def generate_rti_pdf(rti_data: dict) -> bytes:
    """
    Generate a PDF for an RTI application.
    
    Args:
        rti_data: dict with keys:
            ref_number, applicant_name, applicant_address, applicant_mobile,
            applicant_email, is_bpl, bpl_card_no, department, pio_name,
            pio_address, subject, questions (list), draft_text, filed_date
    
    Returns:
        bytes: PDF file content
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    # ── Styles ─────────────────────────────────────────────
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'RTITitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#1a3c5e'),
        alignment=TA_CENTER,
        spaceAfter=6
    )
    heading_style = ParagraphStyle(
        'RTIHeading',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#1a3c5e'),
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'RTIBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )
    bold_style = ParagraphStyle(
        'RTIBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    small_style = ParagraphStyle(
        'RTISmall',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey
    )

    story = []

    # ── Header Banner ────────────────────────────────────────
    header_data = [[
        Paragraph("🇮🇳 RTI-SAARTHI", ParagraphStyle('h', parent=title_style, fontSize=16, textColor=colors.white)),
        Paragraph("Right to Information Application", ParagraphStyle('s', parent=small_style, textColor=colors.lightgrey, alignment=TA_CENTER))
    ]]
    header_table = Table(header_data, colWidths=[17*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1a3c5e')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#1a3c5e')]),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [5, 5, 5, 5]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Ref Number + Date ─────────────────────────────────────
    ref_data = [
        ["Reference Number:", rti_data.get('ref_number', 'N/A'),
         "Date:", rti_data.get('filed_date', datetime.now().strftime('%d/%m/%Y'))]
    ]
    ref_table = Table(ref_data, colWidths=[4*cm, 5*cm, 2*cm, 6*cm])
    ref_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f7ff')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cce0f5')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(ref_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Main Title ────────────────────────────────────────────
    story.append(Paragraph("APPLICATION UNDER THE RIGHT TO INFORMATION ACT, 2005", title_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a3c5e')))
    story.append(Spacer(1, 0.4*cm))

    # ── TO Address ───────────────────────────────────────────
    story.append(Paragraph("TO:", heading_style))
    story.append(Paragraph(f"The Public Information Officer,", body_style))
    story.append(Paragraph(f"<b>{rti_data.get('department', '')}</b>,", body_style))
    story.append(Paragraph(f"{rti_data.get('pio_address', 'India')}", body_style))
    story.append(Spacer(1, 0.3*cm))

    # ── Applicant Details ─────────────────────────────────────
    story.append(Paragraph("APPLICANT DETAILS:", heading_style))
    appl_data = [
        ["Name:", rti_data.get('applicant_name', ''), "Mobile:", rti_data.get('applicant_mobile', '')],
        ["Email:", rti_data.get('applicant_email', ''), "BPL Status:", "Yes (Exempt)" if rti_data.get('is_bpl') else "No (Fee Paid ₹10)"],
        ["Address:", rti_data.get('applicant_address', ''), "", ""],
    ]
    appl_table = Table(appl_data, colWidths=[3*cm, 6.5*cm, 3*cm, 4.5*cm])
    appl_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('SPAN', (1, 2), (3, 2)),
    ]))
    story.append(appl_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Subject ───────────────────────────────────────────────
    story.append(Paragraph(f"<b>Subject:</b> {rti_data.get('subject', 'Request for Information under RTI Act 2005')}", body_style))
    story.append(Spacer(1, 0.3*cm))

    # ── Info Requested ────────────────────────────────────────
    story.append(Paragraph("INFORMATION SOUGHT:", heading_style))
    story.append(Paragraph(
        "I, the undersigned, hereby request the following information under Section 6(1) of the Right to Information Act, 2005:",
        body_style
    ))
    story.append(Spacer(1, 0.2*cm))

    questions = rti_data.get('questions', [])
    for i, q in enumerate(questions, 1):
        story.append(Paragraph(f"<b>{i}.</b> {q}", body_style))
    story.append(Spacer(1, 0.4*cm))

    # ── Legal Provisions ──────────────────────────────────────
    story.append(Paragraph("LEGAL BASIS:", heading_style))
    legal_text = (
        "This request is made under Section 6(1) of the Right to Information Act, 2005. "
        "As per Section 7(1) of the RTI Act, 2005, the requested information should be "
        "provided within <b>30 days</b> of receipt of this application. "
        "In case the information is not provided within the stipulated time, I reserve the "
        "right to file a First Appeal under Section 19(1) of the RTI Act, 2005."
    )
    story.append(Paragraph(legal_text, body_style))
    story.append(Spacer(1, 0.3*cm))

    # ── Declaration ───────────────────────────────────────────
    story.append(Paragraph(
        "I hereby declare that I am a citizen of India and the information sought does not "
        "fall under any of the exemptions listed in Section 8 or Section 9 of the RTI Act, 2005.",
        body_style
    ))
    story.append(Spacer(1, 0.5*cm))

    # ── Signature Block ───────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.3*cm))
    sig_data = [
        ["Yours faithfully,", ""],
        ["", ""],
        [f"<b>{rti_data.get('applicant_name', '')}</b>", f"Deadline: {rti_data.get('deadline_date', '')}"],
        [f"Date: {rti_data.get('filed_date', '')}", f"Filed via: RTI-Saarthi Platform"],
        [f"Mobile: {rti_data.get('applicant_mobile', '')}", "rtisaarthi.in"],
    ]
    sig_table = Table(sig_data, colWidths=[9*cm, 8*cm])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 2), (0, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TEXTCOLOR', (1, 3), (1, 4), colors.grey),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 0.3*cm))

    # ── Footer ────────────────────────────────────────────────
    footer_text = "Generated by RTI-Saarthi | AI-Powered RTI Filing Agent | Democratizing Transparency"
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#1a3c5e')))
    story.append(Paragraph(footer_text, small_style))

    doc.build(story)
    return buffer.getvalue()