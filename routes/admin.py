from collections import Counter
from datetime import datetime, timedelta
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file,
    current_app,
)
from sqlalchemy import or_, case
from models import (
    db,
    Student,
    Admin,
    Ticket,
    Notification,
    MaintenanceTicket,
    MaintenanceUpdate,
    FoodComplaint,
)
from routes.auth import admin_required
from utils.report_generator import generate_excel_report, generate_pdf_report

admin_bp = Blueprint("admin", __name__)


def _get_current_admin():
    return db.session.get(Admin, session["user_id"])


def _filter_tickets_query(search_q="", status="All", start_date="", end_date=""):
    query = Ticket.query.join(Student)

    if search_q:
        like_term = f"%{search_q}%"
        query = query.filter(
            or_(
                Student.full_name.ilike(like_term),
                Student.register_number.ilike(like_term),
                Ticket.ticket_code.ilike(like_term),
                Ticket.destination.ilike(like_term),
            )
        )

    if status and status != "All":
        query = query.filter(Ticket.status == status)

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Ticket.created_at >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Ticket.created_at < end_dt)
        except ValueError:
            pass

    return query.order_by(Ticket.created_at.desc())


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    stats = {
        "total_students": Student.query.count(),
        "total_tickets": Ticket.query.count(),
        "pending_tickets": Ticket.query.filter_by(status="Pending").count(),
        "approved_tickets": Ticket.query.filter(Ticket.status.in_(["Approved", "Completed"])).count(),
        "rejected_tickets": Ticket.query.filter_by(status="Rejected").count(),
    }

    recent_pending = (
        Ticket.query.filter_by(status="Pending")
        .order_by(Ticket.created_at.desc())
        .limit(8)
        .all()
    )
    recent_all = Ticket.query.order_by(Ticket.created_at.desc()).limit(6).all()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_pending=recent_pending,
        recent_all=recent_all,
    )


@admin_bp.route("/tickets")
@admin_required
def manage_tickets():
    search_q = request.args.get("q", "").strip()
    status = request.args.get("status", "All").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    tickets = _filter_tickets_query(search_q, status, start_date, end_date).all()

    return render_template(
        "admin/manage_tickets.html",
        tickets=tickets,
        search_q=search_q,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )


@admin_bp.route("/tickets/<int:ticket_id>/approve", methods=["POST"])
@admin_required
def approve_ticket(ticket_id):
    admin = _get_current_admin()
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        flash("Ticket not found.", "danger")
        return redirect(url_for("admin.manage_tickets"))

    if ticket.status != "Pending":
        flash(f"Ticket {ticket.ticket_code} has already been processed ({ticket.status}).", "warning")
        return redirect(request.referrer or url_for("admin.manage_tickets"))

    ticket.status = "Approved"
    ticket.reviewed_by = admin.id
    ticket.reviewed_at = datetime.now()
    ticket.rejection_reason = None

    notif = Notification(
        student_id=ticket.student_id,
        ticket_id=ticket.id,
        message=(
            f"Ticket {ticket.ticket_code} has been APPROVED by {admin.full_name}. "
            "You can now download your PDF pass."
        ),
    )
    db.session.add(notif)
    db.session.commit()

    flash(f"Ticket {ticket.ticket_code} approved successfully.", "success")
    return redirect(request.referrer or url_for("admin.manage_tickets"))


@admin_bp.route("/tickets/<int:ticket_id>/reject", methods=["POST"])
@admin_required
def reject_ticket(ticket_id):
    admin = _get_current_admin()
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        flash("Ticket not found.", "danger")
        return redirect(url_for("admin.manage_tickets"))

    if ticket.status != "Pending":
        flash(f"Ticket {ticket.ticket_code} has already been processed ({ticket.status}).", "warning")
        return redirect(request.referrer or url_for("admin.manage_tickets"))

    reason = request.form.get("rejection_reason", "").strip()
    if not reason:
        flash("A rejection reason is required when rejecting a ticket.", "danger")
        return redirect(request.referrer or url_for("admin.manage_tickets"))

    ticket.status = "Rejected"
    ticket.reviewed_by = admin.id
    ticket.reviewed_at = datetime.now()
    ticket.rejection_reason = reason

    notif = Notification(
        student_id=ticket.student_id,
        ticket_id=ticket.id,
        message=f"Ticket {ticket.ticket_code} was REJECTED by {admin.full_name}. Reason: {reason}",
    )
    db.session.add(notif)
    db.session.commit()

    flash(f"Ticket {ticket.ticket_code} rejected.", "info")
    return redirect(request.referrer or url_for("admin.manage_tickets"))


@admin_bp.route("/tickets/<int:ticket_id>/complete", methods=["POST"])
@admin_required
def complete_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        flash("Ticket not found.", "danger")
        return redirect(url_for("admin.manage_tickets"))

    if ticket.status != "Approved":
        flash("Only approved tickets can be marked as completed.", "warning")
        return redirect(request.referrer or url_for("admin.manage_tickets"))

    ticket.status = "Completed"
    notif = Notification(
        student_id=ticket.student_id,
        ticket_id=ticket.id,
        message=f"Your return for ticket {ticket.ticket_code} has been recorded. Status: Completed.",
    )
    db.session.add(notif)
    db.session.commit()

    flash(f"Ticket {ticket.ticket_code} marked as Completed.", "success")
    return redirect(request.referrer or url_for("admin.manage_tickets"))


@admin_bp.route("/students")
@admin_required
def manage_students():
    search_q = request.args.get("q", "").strip()
    query = Student.query
    if search_q:
        like_term = f"%{search_q}%"
        query = query.filter(
            or_(
                Student.full_name.ilike(like_term),
                Student.register_number.ilike(like_term),
                Student.department.ilike(like_term),
                Student.email.ilike(like_term),
            )
        )
    students = query.order_by(Student.created_at.desc()).all()
    return render_template("admin/manage_students.html", students=students, search_q=search_q)


@admin_bp.route("/students/<int:student_id>/toggle-status", methods=["POST"])
@admin_required
def toggle_student_status(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("admin.manage_students"))

    student.is_active = not student.is_active
    db.session.commit()
    state = "activated" if student.is_active else "deactivated"
    flash(f"Student account for {student.full_name} has been {state}.", "info")
    return redirect(url_for("admin.manage_students"))


@admin_bp.route("/students/<int:student_id>/history")
@admin_required
def student_history(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("admin.manage_students"))

    tickets = (
        Ticket.query.filter_by(student_id=student.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return render_template("admin/student_history.html", student=student, tickets=tickets)


@admin_bp.route("/reports")
@admin_required
def reports():
    all_tickets = Ticket.query.join(Student).order_by(Ticket.created_at.desc()).all()
    now = datetime.now()

    # 1. Daily requests (Last 7 days)
    daily_labels = []
    daily_counts = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        daily_labels.append(day.strftime("%d %b"))
        daily_counts.append(sum(1 for t in all_tickets if t.created_at.date() == day))

    # 2. Weekly requests (Last 4 weeks)
    weekly_labels = []
    weekly_counts = []
    for w in range(3, -1, -1):
        end_w = (now - timedelta(days=w * 7)).date()
        start_w = end_w - timedelta(days=6)
        weekly_labels.append(f"{start_w.strftime('%d %b')} - {end_w.strftime('%d %b')}")
        weekly_counts.append(
            sum(1 for t in all_tickets if start_w <= t.created_at.date() <= end_w)
        )

    # 3. Monthly requests (Last 6 months)
    monthly_labels = []
    monthly_counts = []
    curr_year, curr_month = now.year, now.month
    months_seq = []
    for _ in range(6):
        months_seq.append((curr_year, curr_month))
        curr_month -= 1
        if curr_month == 0:
            curr_month = 12
            curr_year -= 1
    months_seq.reverse()

    for yr, mo in months_seq:
        label = datetime(yr, mo, 1).strftime("%b %Y")
        monthly_labels.append(label)
        monthly_counts.append(
            sum(1 for t in all_tickets if t.created_at.year == yr and t.created_at.month == mo)
        )

    # 4. Status breakdown
    status_counter = Counter(t.status for t in all_tickets)
    status_data = {
        "Approved": status_counter.get("Approved", 0) + status_counter.get("Completed", 0),
        "Rejected": status_counter.get("Rejected", 0),
        "Pending": status_counter.get("Pending", 0),
        "Cancelled": status_counter.get("Cancelled", 0),
    }

    # 5. Department-wise statistics
    dept_counter = Counter(t.student.department for t in all_tickets)
    dept_labels = list(dept_counter.keys())
    dept_counts = list(dept_counter.values())

    summary = {
        "today": sum(1 for t in all_tickets if t.created_at.date() == now.date()),
        "this_week": sum(1 for t in all_tickets if t.created_at >= now - timedelta(days=7)),
        "this_month": sum(
            1 for t in all_tickets if t.created_at.year == now.year and t.created_at.month == now.month
        ),
        "total": len(all_tickets),
    }

    return render_template(
        "admin/reports.html",
        summary=summary,
        daily_labels=daily_labels,
        daily_counts=daily_counts,
        weekly_labels=weekly_labels,
        weekly_counts=weekly_counts,
        monthly_labels=monthly_labels,
        monthly_counts=monthly_counts,
        status_data=status_data,
        dept_labels=dept_labels,
        dept_counts=dept_counts,
        recent_tickets=all_tickets[:15],
    )


@admin_bp.route("/reports/export/excel")
@admin_required
def export_excel():
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    status = request.args.get("status", "All").strip()

    tickets = _filter_tickets_query("", status, start_date, end_date).all()
    excel_buffer = generate_excel_report(tickets)
    filename = f"Hostick_Tickets_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return send_file(
        excel_buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@admin_bp.route("/reports/export/pdf")
@admin_required
def export_pdf():
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    status = request.args.get("status", "All").strip()

    tickets = _filter_tickets_query("", status, start_date, end_date).all()
    pdf_buffer = generate_pdf_report(
        tickets=tickets,
        college_name=current_app.config["COLLEGE_NAME"],
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    filename = f"Hostick_Tickets_Report_{datetime.now().strftime('%Y%m%d')}.pdf"

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
@admin_bp.route("/maintenance")
@admin_required
def manage_maintenance():
    status_filter = request.args.get("status", "All").strip()
    priority_filter = request.args.get("priority", "All").strip()
    category_filter = request.args.get("category", "All").strip()
    search_q = request.args.get("q", "").strip()

    query = MaintenanceTicket.query.join(Student)

    if status_filter != "All":
        query = query.filter(MaintenanceTicket.status == status_filter)
    if priority_filter != "All":
        query = query.filter(MaintenanceTicket.priority == priority_filter)
    if category_filter != "All":
        query = query.filter(MaintenanceTicket.category == category_filter)
    if search_q:
        like_term = f"%{search_q}%"
        query = query.filter(
            or_(
                MaintenanceTicket.ticket_code.ilike(like_term),
                MaintenanceTicket.description.ilike(like_term),
                MaintenanceTicket.assigned_team.ilike(like_term),
                Student.full_name.ilike(like_term),
                Student.register_number.ilike(like_term),
            )
        )

    # Active urgent complaints ALWAYS stay at the top; Resolved tickets go to the bottom
    resolved_last = case((MaintenanceTicket.status == "Resolved", 1), else_=0)
    tickets = query.order_by(
        resolved_last.asc(),
        MaintenanceTicket.priority_rank.asc(),
        MaintenanceTicket.report_count.desc(),
        MaintenanceTicket.created_at.asc(),
    ).all()

    counts = {
        "critical": MaintenanceTicket.query.filter(
            MaintenanceTicket.priority == "Critical", MaintenanceTicket.status != "Resolved"
        ).count(),
        "high": MaintenanceTicket.query.filter(
            MaintenanceTicket.priority == "High", MaintenanceTicket.status != "Resolved"
        ).count(),
        "open": MaintenanceTicket.query.filter(MaintenanceTicket.status != "Resolved").count(),
        "resolved": MaintenanceTicket.query.filter_by(status="Resolved").count(),
    }

    return render_template(
        "admin/manage_maintenance.html",
        tickets=tickets,
        counts=counts,
        status_filter=status_filter,
        priority_filter=priority_filter,
        category_filter=category_filter,
        search_q=search_q,
    )


@admin_bp.route("/maintenance/<int:ticket_id>/update", methods=["POST"])
@admin_required
def update_maintenance(ticket_id):
    admin = _get_current_admin()
    ticket = db.session.get(MaintenanceTicket, ticket_id)
    if not ticket:
        flash("Maintenance ticket not found.", "danger")
        return redirect(url_for("admin.manage_maintenance"))

    new_status = request.form.get("status", ticket.status).strip()
    new_team = request.form.get("assigned_team", ticket.assigned_team).strip()
    warden_update = request.form.get("warden_remark", "").strip()

    if new_status not in ("Reported", "Assigned", "In Progress", "Resolved"):
        flash("Invalid maintenance status selected.", "danger")
        return redirect(url_for("admin.manage_maintenance"))

    if not warden_update:
        warden_update = f"Status updated to {new_status} ({new_team})."

    ticket.status = new_status
    ticket.assigned_team = new_team or ticket.assigned_team
    ticket.warden_remark = warden_update
    ticket.updated_at = datetime.now()

    db.session.add(
        MaintenanceUpdate(
            maintenance_ticket_id=ticket.id,
            updated_by_name=admin.full_name,
            updated_by_role="Warden",
            status_snapshot=new_status,
            message=warden_update,
        )
    )
    db.session.add(
        Notification(
            student_id=ticket.student_id,
            message=f"Maintenance {ticket.ticket_code} [{new_status}]: {warden_update}",
        )
    )
    db.session.commit()

    flash(f"Maintenance ticket {ticket.ticket_code} updated to {new_status}.", "success")
    return redirect(url_for("admin.manage_maintenance"))

@admin_bp.route("/food-complaints")
@admin_required
def manage_food_complaints():
    mess_filter = request.args.get("mess", "All").strip()
    status_filter = request.args.get("status", "All").strip()
    priority_filter = request.args.get("priority", "All").strip()

    query = FoodComplaint.query.join(Student)

    if mess_filter != "All":
        query = query.filter(FoodComplaint.mess_name == mess_filter)
    if status_filter != "All":
        query = query.filter(FoodComplaint.status == status_filter)
    if priority_filter != "All":
        query = query.filter(FoodComplaint.priority == priority_filter)

    # Unresolved Critical food-safety alerts (insects / rotten food) always appear first
    resolved_last = case((FoodComplaint.status == "Resolved", 1), else_=0)
    complaints = query.order_by(
        resolved_last.asc(),
        FoodComplaint.priority_rank.asc(),
        FoodComplaint.created_at.desc(),
    ).all()

    counts = {
        "boys_open": FoodComplaint.query.filter(
            FoodComplaint.mess_name == "Boys Hostel Mess", FoodComplaint.status != "Resolved"
        ).count(),
        "girls_open": FoodComplaint.query.filter(
            FoodComplaint.mess_name == "Girls Hostel Mess", FoodComplaint.status != "Resolved"
        ).count(),
        "critical_open": FoodComplaint.query.filter(
            FoodComplaint.priority == "Critical", FoodComplaint.status != "Resolved"
        ).count(),
        "resolved": FoodComplaint.query.filter_by(status="Resolved").count(),
    }

    return render_template(
        "admin/manage_food_complaints.html",
        complaints=complaints,
        counts=counts,
        mess_filter=mess_filter,
        status_filter=status_filter,
        priority_filter=priority_filter,
    )


@admin_bp.route("/food-complaints/<int:complaint_id>/update", methods=["POST"])
@admin_required
def update_food_complaint(complaint_id):
    admin = _get_current_admin()
    fc = db.session.get(FoodComplaint, complaint_id)
    if not fc:
        flash("Food complaint not found.", "danger")
        return redirect(url_for("admin.manage_food_complaints"))

    new_status = request.form.get("status", fc.status).strip()
    warden_remark = request.form.get("warden_remark", "").strip()

    if new_status not in ("Reported", "Under Inspection", "Action Taken", "Resolved"):
        flash("Invalid status selected.", "danger")
        return redirect(url_for("admin.manage_food_complaints"))

    if not warden_remark:
        warden_remark = f"Mess complaint status updated to {new_status}."

    fc.status = new_status
    fc.warden_remark = warden_remark
    fc.reviewed_by = admin.id
    fc.updated_at = datetime.now()

    db.session.add(
        Notification(
            student_id=fc.student_id,
            message=f"Food Complaint {fc.complaint_code} ({fc.mess_name}) [{new_status}]: {warden_remark}",
        )
    )
    db.session.commit()

    flash(f"Food complaint {fc.complaint_code} updated to {new_status}.", "success")
    return redirect(url_for("admin.manage_food_complaints"))