from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def generate_ticket_pdf(ticket, college_name: str) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = getSampleStyleSheet()
    navy = colors.HexColor("#0F2942")
    light_bg = colors.HexColor("#F4F6F9")
    green = colors.HexColor("#198754")

    header_title_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.white,
        alignment=1,
        spaceAfter=4,
    )
    header_sub_style = ParagraphStyle(
        "HeaderSub",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#D6E4F0"),
        alignment=1,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading3"],
        fontSize=12,
        textColor=navy,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyCell",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1F2937"),
    )
    label_style = ParagraphStyle(
        "LabelCell",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        fontName="Helvetica-Bold",
        textColor=navy,
    )

    elements = []

    # Navy Banner Header
    banner_data = [
        [Paragraph(college_name.upper(), header_title_style)],
        [Paragraph("OFFICIAL HOSTEL OUTING PASS", header_sub_style)],
    ]
    banner_table = Table(banner_data, colWidths=[7.0 * inch])
    banner_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), navy),
                ("TOPPADDING", (0, 0), (-1, 0), 14),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 14),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    elements.append(banner_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Ticket Metadata Strip
    meta_data = [
        [
            Paragraph(f"<b>Ticket ID:</b> {ticket.ticket_code}", body_style),
            Paragraph(
                f"<b>Status:</b> <font color='#198754'><b>{ticket.status.upper()}</b></font>",
                body_style,
            ),
            Paragraph(
                f"<b>Issued On:</b> {ticket.created_at.strftime('%d %b %Y, %I:%M %p')}",
                body_style,
            ),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[2.2 * inch, 2.0 * inch, 2.8 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), light_bg),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 0.15 * inch))

    # Student Details Section
    elements.append(Paragraph("Student Information", section_heading))
    student = ticket.student
    student_rows = [
        [Paragraph("Student Name", label_style), Paragraph(student.full_name, body_style)],
        [Paragraph("Register Number", label_style), Paragraph(student.register_number, body_style)],
        [
            Paragraph("Department & Year", label_style),
            Paragraph(f"{student.department} (Year {student.year_of_study})", body_style),
        ],
        [
            Paragraph("Hostel & Room", label_style),
            Paragraph(f"{student.hostel.name} — Room {student.room.room_number}", body_style),
        ],
        [
            Paragraph("Contact Numbers", label_style),
            Paragraph(
                f"Student: {student.phone} | Parent/Guardian: {ticket.parent_contact or student.parent_phone or 'N/A'}",
                body_style,
            ),
        ],
    ]
    student_table = Table(student_rows, colWidths=[2.2 * inch, 4.8 * inch])
    student_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("BACKGROUND", (0, 0), (0, -1), light_bg),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(student_table)
    elements.append(Spacer(1, 0.15 * inch))

    # Outing Details Section
    elements.append(Paragraph("Outing Schedule & Reason", section_heading))
    outing_rows = [
        [Paragraph("Destination", label_style), Paragraph(ticket.destination, body_style)],
        [Paragraph("Reason for Leaving", label_style), Paragraph(ticket.reason, body_style)],
        [
            Paragraph("Departure Date & Time", label_style),
            Paragraph(ticket.departure_datetime.strftime("%d %b %Y at %I:%M %p"), body_style),
        ],
        [
            Paragraph("Expected Return", label_style),
            Paragraph(ticket.expected_return_datetime.strftime("%d %b %Y at %I:%M %p"), body_style),
        ],
    ]
    outing_table = Table(outing_rows, colWidths=[2.2 * inch, 4.8 * inch])
    outing_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("BACKGROUND", (0, 0), (0, -1), light_bg),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(outing_table)
    elements.append(Spacer(1, 0.15 * inch))

    # Warden Approval Section
    elements.append(Paragraph("Warden Approval Details", section_heading))
    reviewer_name = ticket.reviewer.full_name if ticket.reviewer else "Hostel Administration"
    reviewer_role = ticket.reviewer.role if ticket.reviewer else "Warden"
    approved_time = (
        ticket.reviewed_at.strftime("%d %b %Y at %I:%M %p")
        if ticket.reviewed_at
        else "Verified Digitally"
    )

    approval_rows = [
        [Paragraph("Approved By", label_style), Paragraph(f"{reviewer_name} ({reviewer_role})", body_style)],
        [Paragraph("Approval Timestamp", label_style), Paragraph(approved_time, body_style)],
        [
            Paragraph("Verification Note", label_style),
            Paragraph(
                "Digitally approved via Hostick Hostel Ticket Management System. Present this pass at the hostel security gate.",
                body_style,
            ),
        ],
    ]
    approval_table = Table(approval_rows, colWidths=[2.2 * inch, 4.8 * inch])
    approval_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, green),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ECFDF5")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(approval_table)
    elements.append(Spacer(1, 0.4 * inch))

    # Footer Signatures
    sig_data = [
        [
            Paragraph("___________________________<br/>Student Signature", body_style),
            Paragraph("___________________________<br/>Security Gate Check-Out / In", body_style),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.5 * inch, 3.5 * inch])
    sig_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer