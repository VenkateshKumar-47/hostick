from io import BytesIO
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def generate_excel_report(tickets) -> BytesIO:
    rows = []
    for t in tickets:
        rows.append(
            {
                "Ticket ID": t.ticket_code,
                "Student Name": t.student.full_name,
                "Register Number": t.student.register_number,
                "Department": t.student.department,
                "Hostel": t.student.hostel.name,
                "Room": t.student.room.room_number,
                "Destination": t.destination,
                "Reason": t.reason,
                "Departure": t.departure_datetime.strftime("%Y-%m-%d %H:%M"),
                "Expected Return": t.expected_return_datetime.strftime("%Y-%m-%d %H:%M"),
                "Status": t.status,
                "Reviewed By": t.reviewer.full_name if t.reviewer else "-",
                "Rejection Reason": t.rejection_reason or "-",
                "Submitted At": t.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        )

    columns = [
        "Ticket ID",
        "Student Name",
        "Register Number",
        "Department",
        "Hostel",
        "Room",
        "Destination",
        "Reason",
        "Departure",
        "Expected Return",
        "Status",
        "Reviewed By",
        "Rejection Reason",
        "Submitted At",
    ]
    df = pd.DataFrame(rows, columns=columns)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Hostel Tickets")
        worksheet = writer.sheets["Hostel Tickets"]
        for col_idx, col_name in enumerate(columns, start=1):
            max_len = max(
                [len(str(col_name))] + [len(str(val)) for val in df[col_name].tolist()]
            )
            worksheet.column_dimensions[worksheet.cell(row=1, column=col_idx).column_letter].width = min(
                max_len + 4, 38
            )

    buffer.seek(0)
    return buffer


def generate_pdf_report(
    tickets,
    college_name: str,
    start_date: str = "",
    end_date: str = "",
    status: str = "All",
) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0.4 * inch,
        leftMargin=0.4 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()
    navy = colors.HexColor("#0F2942")

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=16,
        textColor=navy,
        alignment=0,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=9.5,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=12,
    )
    cell_style = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
    )
    header_cell_style = ParagraphStyle(
        "HeaderCellText",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=10,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    elements = []
    elements.append(Paragraph(f"{college_name} — Hostel Ticket Summary Report", title_style))

    filter_desc = f"Generated on: {datetime.now().strftime('%d %b %Y, %I:%M %p')} | Status Filter: {status or 'All'}"
    if start_date or end_date:
        filter_desc += f" | Date Range: {start_date or 'Start'} to {end_date or 'Present'}"
    elements.append(Paragraph(filter_desc, subtitle_style))

    # Summary strip
    total = len(tickets)
    approved = sum(1 for t in tickets if t.status in ("Approved", "Completed"))
    pending = sum(1 for t in tickets if t.status == "Pending")
    rejected = sum(1 for t in tickets if t.status == "Rejected")

    summary_table = Table(
        [[f"Total Tickets: {total}", f"Approved/Completed: {approved}", f"Pending: {pending}", f"Rejected: {rejected}"]],
        colWidths=[2.6 * inch] * 4,
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F6F9")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (-1, -1), navy),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Data table
    table_data = [
        [
            Paragraph("Ticket ID", header_cell_style),
            Paragraph("Student", header_cell_style),
            Paragraph("Reg. No", header_cell_style),
            Paragraph("Dept", header_cell_style),
            Paragraph("Hostel / Room", header_cell_style),
            Paragraph("Destination", header_cell_style),
            Paragraph("Departure", header_cell_style),
            Paragraph("Return", header_cell_style),
            Paragraph("Status", header_cell_style),
        ]
    ]

    if not tickets:
        table_data.append([Paragraph("No ticket records found for the selected criteria.", cell_style)] + [""] * 8)
    else:
        for t in tickets:
            table_data.append(
                [
                    Paragraph(t.ticket_code, cell_style),
                    Paragraph(t.student.full_name, cell_style),
                    Paragraph(t.student.register_number, cell_style),
                    Paragraph(t.student.department, cell_style),
                    Paragraph(f"{t.student.hostel.block_code} - {t.student.room.room_number}", cell_style),
                    Paragraph(t.destination, cell_style),
                    Paragraph(t.departure_datetime.strftime("%d %b %y %H:%M"), cell_style),
                    Paragraph(t.expected_return_datetime.strftime("%d %b %y %H:%M"), cell_style),
                    Paragraph(f"<b>{t.status}</b>", cell_style),
                ]
            )

    col_widths = [
        1.05 * inch,
        1.35 * inch,
        0.9 * inch,
        1.25 * inch,
        1.0 * inch,
        1.65 * inch,
        1.15 * inch,
        1.15 * inch,
        0.9 * inch,
    ]
    data_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    data_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(data_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer