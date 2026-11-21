from functools import wraps
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from models import db, Student, Admin, Hostel, Room

auth_bp = Blueprint("auth", __name__)


def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "student" or not session.get("user_id"):
            flash("Please log in as a student to access that page.", "warning")
            return redirect(url_for("auth.login"))
        student = db.session.get(Student, session["user_id"])
        if not student or not student.is_active:
            session.clear()
            flash("Your student account is inactive or unavailable. Contact the warden.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin" or not session.get("user_id"):
            flash("Warden/Admin access is required to view that page.", "warning")
            return redirect(url_for("auth.login"))
        admin = db.session.get(Admin, session["user_id"])
        if not admin:
            session.clear()
            flash("Admin session invalid. Please log in again.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("role") == "student":
        return redirect(url_for("student.dashboard"))
    if session.get("role") == "admin":
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        role = request.form.get("role", "student").strip()
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        if not identifier or not password:
            flash("Please enter both your email/register number and password.", "danger")
            return render_template("auth/login.html", selected_role=role)

        if role == "admin":
            admin = Admin.query.filter_by(email=identifier.lower()).first()
            if admin and admin.check_password(password):
                session.clear()
                session["user_id"] = admin.id
                session["role"] = "admin"
                flash(f"Welcome back, {admin.full_name}!", "success")
                return redirect(url_for("admin.dashboard"))
            flash("Invalid warden email or password.", "danger")
            return render_template("auth/login.html", selected_role="admin")

        # Student login accepts either email or register number
        student = Student.query.filter(
            (Student.email == identifier.lower())
            | (Student.register_number == identifier.upper())
        ).first()

        if student and student.check_password(password):
            if not student.is_active:
                flash("Your account has been deactivated by the warden.", "danger")
                return render_template("auth/login.html", selected_role="student")
            session.clear()
            session["user_id"] = student.id
            session["role"] = "student"
            flash(f"Welcome back, {student.full_name}!", "success")
            return redirect(url_for("student.dashboard"))

        flash("Invalid student credentials. Check your email/register number and password.", "danger")
        return render_template("auth/login.html", selected_role="student")

    return render_template("auth/login.html", selected_role="student")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("role") == "student":
        return redirect(url_for("student.dashboard"))

    hostels = Hostel.query.order_by(Hostel.name.asc()).all()
    rooms = Room.query.order_by(Room.room_number.asc()).all()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        register_number = request.form.get("register_number", "").strip().upper()
        email = request.form.get("email", "").strip().lower()
        department = request.form.get("department", "").strip()
        year_of_study = request.form.get("year_of_study", "").strip()
        hostel_id = request.form.get("hostel_id", "").strip()
        room_id = request.form.get("room_id", "").strip()
        phone = request.form.get("phone", "").strip()
        parent_phone = request.form.get("parent_phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([full_name, register_number, email, department, year_of_study, hostel_id, room_id, phone, password]):
            flash("Please fill in all required fields.", "danger")
            return render_template("auth/register.html", hostels=hostels, rooms=rooms)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html", hostels=hostels, rooms=rooms)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/register.html", hostels=hostels, rooms=rooms)

        if Student.query.filter_by(register_number=register_number).first():
            flash("A student with this Register Number is already registered.", "danger")
            return render_template("auth/register.html", hostels=hostels, rooms=rooms)

        if Student.query.filter_by(email=email).first():
            flash("An account with this Email already exists.", "danger")
            return render_template("auth/register.html", hostels=hostels, rooms=rooms)

        try:
            year_int = int(year_of_study)
            hostel_int = int(hostel_id)
            room_int = int(room_id)
        except ValueError:
            flash("Invalid year, hostel, or room selection.", "danger")
            return render_template("auth/register.html", hostels=hostels, rooms=rooms)

        room = Room.query.filter_by(id=room_int, hostel_id=hostel_int).first()
        if not room:
            flash("Selected room does not belong to the chosen hostel.", "danger")
            return render_template("auth/register.html", hostels=hostels, rooms=rooms)

        student = Student(
            full_name=full_name,
            register_number=register_number,
            email=email,
            department=department,
            year_of_study=year_int,
            hostel_id=hostel_int,
            room_id=room_int,
            phone=phone,
            parent_phone=parent_phone or None,
            is_active=True,
        )
        student.set_password(password)
        db.session.add(student)
        db.session.commit()

        flash("Registration successful! You can now log in with your email or register number.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", hostels=hostels, rooms=rooms)


@auth_bp.route("/api/rooms/<int:hostel_id>")
def get_rooms_by_hostel(hostel_id):
    rooms = Room.query.filter_by(hostel_id=hostel_id).order_by(Room.room_number.asc()).all()
    return jsonify([{"id": r.id, "room_number": r.room_number} for r in rooms])


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out securely.", "info")
    return redirect(url_for("auth.login"))