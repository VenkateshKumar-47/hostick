import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
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
    jsonify,
)
from models import (
    db,
    Student,
    Ticket,
    Notification,
    MaintenanceTicket,
    MaintenanceUpdate,
    FoodComplaint,
)
from routes.auth import student_required
from utils.pdf_generator import generate_ticket_pdf
from utils.maintenance_triage import analyze_complaint
from utils.food_triage import analyze_food_complaint


student_bp = Blueprint("student", __name__)


def _get_current_student():
    return db.session.get(Student, session["user_id"])


@student_bp.route("/dashboard")
@student_required
def dashboard():
    student = _get_current_student()
    all_tickets = (
        Ticket.query.filter_by(student_id=student.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )

    stats = {
        "total": len(all_tickets),
        "pending": sum(1 for t in all_tickets if t.status == "Pending"),
        "approved": sum(1 for t in all_tickets if t.status in ("Approved", "Completed")),
        "rejected": sum(1 for t in all_tickets if t.status == "Rejected"),
    }
    recent_tickets = all_tickets[:5]

    return render_template(
        "student/dashboard.html",
        student=student,
        stats=stats,
        recent_tickets=recent_tickets,
    )


@student_bp.route("/generate-ticket", methods=["GET", "POST"])
@student_required
def generate_ticket():
    student = _get_current_student()

    if request.method == "POST":
        destination = request.form.get("destination", "").strip()
        reason = request.form.get("reason", "").strip()
        departure_date = request.form.get("departure_date", "").strip()
        departure_time = request.form.get("departure_time", "").strip()
        return_date = request.form.get("return_date", "").strip()
        return_time = request.form.get("return_time", "").strip()
        parent_contact = request.form.get("parent_contact", "").strip()

        if not all([destination, reason, departure_date, departure_time, return_date, return_time]):
            flash("Please complete all required ticket fields.", "danger")
            return render_template("student/generate_ticket.html", student=student)

        try:
            departure_dt = datetime.strptime(f"{departure_date} {departure_time}", "%Y-%m-%d %H:%M")
            return_dt = datetime.strptime(f"{return_date} {return_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash("Invalid date or time format provided.", "danger")
            return render_template("student/generate_ticket.html", student=student)

        if return_dt <= departure_dt:
            flash("Expected return date and time must be after the departure date and time.", "danger")
            return render_template("student/generate_ticket.html", student=student)

        ticket_code = Ticket.generate_ticket_code()
        ticket = Ticket(
            ticket_code=ticket_code,
            student_id=student.id,
            destination=destination,
            reason=reason,
            departure_datetime=departure_dt,
            expected_return_datetime=return_dt,
            parent_contact=parent_contact or student.parent_phone,
            status="Pending",
        )
        db.session.add(ticket)
        db.session.flush()

        notif = Notification(
            student_id=student.id,
            ticket_id=ticket.id,
            message=f"Ticket {ticket.ticket_code} for {destination} has been submitted and is pending warden approval.",
        )
        db.session.add(notif)
        db.session.commit()

        flash(f"Ticket {ticket.ticket_code} submitted successfully!", "success")
        return redirect(url_for("student.my_tickets"))

    return render_template("student/generate_ticket.html", student=student)


@student_bp.route("/my-tickets")
@student_required
def my_tickets():
    student = _get_current_student()
    status_filter = request.args.get("status", "All").strip()

    query = Ticket.query.filter_by(student_id=student.id)
    if status_filter and status_filter != "All":
        query = query.filter_by(status=status_filter)

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return render_template(
        "student/my_tickets.html",
        tickets=tickets,
        status_filter=status_filter,
        page_title="My Tickets",
        is_history=False,
    )


@student_bp.route("/history")
@student_required
def ticket_history():
    student = _get_current_student()
    status_filter = request.args.get("status", "All").strip()

    query = Ticket.query.filter_by(student_id=student.id)
    if status_filter and status_filter != "All":
        query = query.filter_by(status=status_filter)

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return render_template(
        "student/my_tickets.html",
        tickets=tickets,
        status_filter=status_filter,
        page_title="Ticket History",
        is_history=True,
    )


@student_bp.route("/tickets/<int:ticket_id>/cancel", methods=["POST"])
@student_required
def cancel_ticket(ticket_id):
    student = _get_current_student()
    ticket = Ticket.query.filter_by(id=ticket_id, student_id=student.id).first_or_404()

    if ticket.status != "Pending":
        flash("Only pending tickets can be cancelled.", "warning")
        return redirect(url_for("student.my_tickets"))

    ticket.status = "Cancelled"
    notif = Notification(
        student_id=student.id,
        ticket_id=ticket.id,
        message=f"You cancelled ticket {ticket.ticket_code}.",
    )
    db.session.add(notif)
    db.session.commit()

    flash(f"Ticket {ticket.ticket_code} has been cancelled.", "info")
    return redirect(url_for("student.my_tickets"))


@student_bp.route("/tickets/<int:ticket_id>/pdf")
@student_required
def download_ticket_pdf(ticket_id):
    student = _get_current_student()
    ticket = Ticket.query.filter_by(id=ticket_id, student_id=student.id).first_or_404()

    if ticket.status not in ("Approved", "Completed"):
        flash("PDF pass can only be downloaded for approved or completed tickets.", "warning")
        return redirect(url_for("student.my_tickets"))

    pdf_buffer = generate_ticket_pdf(ticket, current_app.config["COLLEGE_NAME"])
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{ticket.ticket_code}_Outing_Pass.pdf",
    )


@student_bp.route("/notifications")
@student_required
def notifications():
    student = _get_current_student()
    items = (
        Notification.query.filter_by(student_id=student.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template("student/notifications.html", notifications=items)


@student_bp.route("/notifications/mark-read", methods=["POST"])
@student_required
def mark_all_read():
    student = _get_current_student()
    Notification.query.filter_by(student_id=student.id, is_read=False).update({"is_read": True})
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("student.notifications"))


@student_bp.route("/profile", methods=["GET", "POST"])
@student_required
def profile():
    student = _get_current_student()

    if request.method == "POST":
        action = request.form.get("action", "update_contact")

        if action == "update_contact":
            phone = request.form.get("phone", "").strip()
            parent_phone = request.form.get("parent_phone", "").strip()
            if not phone:
                flash("Phone number cannot be empty.", "danger")
            else:
                student.phone = phone
                student.parent_phone = parent_phone or None
                db.session.commit()
                flash("Contact details updated successfully.", "success")

        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            confirm_pw = request.form.get("confirm_password", "")

            if not student.check_password(current_pw):
                flash("Current password is incorrect.", "danger")
            elif len(new_pw) < 6:
                flash("New password must be at least 6 characters.", "danger")
            elif new_pw != confirm_pw:
                flash("New passwords do not match.", "danger")
            else:
                student.set_password(new_pw)
                db.session.commit()
                flash("Password changed successfully.", "success")

        return redirect(url_for("student.profile"))

    return render_template("student/profile.html", student=student)
@student_bp.route("/maintenance", methods=["GET", "POST"])
@student_required
def maintenance():
    student = _get_current_student()

    if request.method == "POST":
        description = request.form.get("description", "").strip()
        if len(description) < 8:
            flash("Please describe the maintenance issue in at least a few words.", "danger")
            return redirect(url_for("student.maintenance"))

        triage = analyze_complaint(description)

        # Duplicate Detection: same hostel + same room + same category + still open
        existing = MaintenanceTicket.query.filter(
            MaintenanceTicket.hostel_id == student.hostel_id,
            MaintenanceTicket.room_id == student.room_id,
            MaintenanceTicket.category == triage["category"],
            MaintenanceTicket.status != "Resolved",
        ).first()

        if existing:
            existing.report_count += 1
            existing.updated_at = datetime.now()
            escalated_msg = ""

            # Escalate priority if the new description flags a higher safety risk
            if triage["priority_rank"] < existing.priority_rank:
                existing.priority = triage["priority"]
                existing.priority_rank = triage["priority_rank"]
                existing.triage_reason = triage["triage_reason"]
                existing.matched_keywords = triage["matched_keywords"]
                escalated_msg = f" Priority escalated to {triage['priority']} due to safety keywords."

            db.session.add(
                MaintenanceUpdate(
                    maintenance_ticket_id=existing.id,
                    updated_by_name=student.full_name,
                    updated_by_role="Student",
                    status_snapshot=existing.status,
                    message=f"Duplicate report merged (Total reports: {existing.report_count}): \"{description}\"{escalated_msg}",
                )
            )
            db.session.add(
                Notification(
                    student_id=student.id,
                    message=(
                        f"Your {triage['category']} complaint matched active ticket {existing.ticket_code} "
                        f"for Room {student.room.room_number} and was merged (Reports: {existing.report_count})."
                    ),
                )
            )
            db.session.commit()
            flash(
                f"Duplicate detected! Merged into active ticket {existing.ticket_code} "
                f"(Total reports: {existing.report_count}) instead of creating a duplicate slip.{escalated_msg}",
                "info",
            )
            return redirect(url_for("student.track_maintenance", ticket_id=existing.id))

        # Create a brand new auto-triaged maintenance ticket
        code = MaintenanceTicket.generate_code()
        mt = MaintenanceTicket(
            ticket_code=code,
            student_id=student.id,
            hostel_id=student.hostel_id,
            room_id=student.room_id,
            description=description,
            category=triage["category"],
            priority=triage["priority"],
            priority_rank=triage["priority_rank"],
            assigned_team=triage["assigned_team"],
            matched_keywords=triage["matched_keywords"],
            triage_reason=triage["triage_reason"],
            report_count=1,
            status="Reported",
        )
        db.session.add(mt)
        db.session.flush()

        db.session.add(
            MaintenanceUpdate(
                maintenance_ticket_id=mt.id,
                updated_by_name="Hostick Auto-Triage",
                updated_by_role="System",
                status_snapshot="Reported",
                message=(
                    f"Auto-classified as {triage['category']} | Priority: {triage['priority']} | "
                    f"Routed to {triage['assigned_team']}. ({triage['triage_reason']})"
                ),
            )
        )
        db.session.add(
            Notification(
                student_id=student.id,
                message=(
                    f"Maintenance Ticket {mt.ticket_code} created ({mt.category} — {mt.priority} Priority) "
                    f"and routed to {mt.assigned_team}."
                ),
            )
        )
        db.session.commit()

        flash(
            f"Ticket {mt.ticket_code} logged! Auto-assigned to {mt.assigned_team} with {mt.priority} Priority.",
            "success",
        )
        return redirect(url_for("student.track_maintenance", ticket_id=mt.id))

    # Show tickets submitted by student OR belonging to student's room
    tickets = (
        MaintenanceTicket.query.filter(
            (MaintenanceTicket.student_id == student.id)
            | (
                (MaintenanceTicket.hostel_id == student.hostel_id)
                & (MaintenanceTicket.room_id == student.room_id)
            )
        )
        .order_by(MaintenanceTicket.updated_at.desc())
        .all()
    )
    return render_template("student/maintenance.html", student=student, tickets=tickets)


@student_bp.route("/maintenance/<int:ticket_id>")
@student_required
def track_maintenance(ticket_id):
    student = _get_current_student()
    ticket = db.session.get(MaintenanceTicket, ticket_id)
    if not ticket or (
        ticket.student_id != student.id
        and not (ticket.hostel_id == student.hostel_id and ticket.room_id == student.room_id)
    ):
        flash("Maintenance ticket not found.", "danger")
        return redirect(url_for("student.maintenance"))

    return render_template("student/track_maintenance.html", ticket=ticket)


@student_bp.route("/api/maintenance/<int:ticket_id>/live")
@student_required
def maintenance_live_api(ticket_id):
    student = _get_current_student()
    ticket = db.session.get(MaintenanceTicket, ticket_id)
    if not ticket or (
        ticket.student_id != student.id
        and not (ticket.hostel_id == student.hostel_id and ticket.room_id == student.room_id)
    ):
        return jsonify({"error": "Not found"}), 404

    return jsonify(
        {
            "ticket_code": ticket.ticket_code,
            "status": ticket.status,
            "priority": ticket.priority,
            "category": ticket.category,
            "assigned_team": ticket.assigned_team,
            "report_count": ticket.report_count,
            "warden_remark": ticket.warden_remark or "Waiting for warden update...",
            "updated_at": ticket.updated_at.strftime("%d %b %Y, %I:%M %p"),
            "updates": [
                {
                    "by": u.updated_by_name,
                    "role": u.updated_by_role,
                    "status": u.status_snapshot,
                    "message": u.message,
                    "time": u.created_at.strftime("%d %b %Y, %I:%M %p"),
                }
                for u in ticket.updates
            ],
        }
    )

def _allowed_image(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


@student_bp.route("/food-complaints", methods=["GET", "POST"])
@student_required
def food_complaints():
    student = _get_current_student()

    # Smart default mess based on student's hostel name
    hostel_lower = student.hostel.name.lower()
    default_mess = "Girls Hostel Mess" if "girl" in hostel_lower else "Boys Hostel Mess"

    if request.method == "POST":
        mess_name = request.form.get("mess_name", "").strip()
        meal_type = request.form.get("meal_type", "").strip()
        issue_type = request.form.get("issue_type", "").strip()
        description = request.form.get("description", "").strip()
        photo = request.files.get("photo")

        if mess_name not in ("Boys Hostel Mess", "Girls Hostel Mess"):
            flash("Please select either Boys Hostel Mess or Girls Hostel Mess.", "danger")
            return redirect(url_for("student.food_complaints"))

        if not meal_type or not issue_type or len(description) < 6:
            flash("Please fill in the meal type, issue category, and complaint details.", "danger")
            return redirect(url_for("student.food_complaints"))

        saved_filename = None
        if photo and photo.filename:
            if not _allowed_image(photo.filename):
                flash("Only PNG, JPG, JPEG, or WEBP images are allowed for photo evidence.", "danger")
                return redirect(url_for("student.food_complaints"))

            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)
            safe_name = secure_filename(photo.filename)
            ext = safe_name.rsplit(".", 1)[1].lower()
            saved_filename = f"{uuid.uuid4().hex}.{ext}"
            photo.save(os.path.join(upload_dir, saved_filename))

        triage = analyze_food_complaint(issue_type, description, has_photo=bool(saved_filename))
        code = FoodComplaint.generate_code()

        fc = FoodComplaint(
            complaint_code=code,
            student_id=student.id,
            mess_name=mess_name,
            meal_type=meal_type,
            issue_type=issue_type,
            description=description,
            photo_filename=saved_filename,
            priority=triage["priority"],
            priority_rank=triage["priority_rank"],
            matched_keywords=triage["matched_keywords"],
            triage_reason=triage["triage_reason"],
            status="Reported",
        )
        db.session.add(fc)
        db.session.flush()

        db.session.add(
            Notification(
                student_id=student.id,
                message=(
                    f"Food Complaint {fc.complaint_code} ({mess_name} — {fc.priority} Priority) "
                    "submitted to the Warden."
                ),
            )
        )
        db.session.commit()

        flash(
            f"Food complaint {fc.complaint_code} submitted for {mess_name} ({fc.priority} Priority).",
            "success",
        )
        return redirect(url_for("student.food_complaints"))

    complaints = (
        FoodComplaint.query.filter_by(student_id=student.id)
        .order_by(FoodComplaint.created_at.desc())
        .all()
    )
    return render_template(
        "student/food_complaints.html",
        student=student,
        default_mess=default_mess,
        complaints=complaints,
    )