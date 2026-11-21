from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Hostel(db.Model):
    __tablename__ = "hostels"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    warden_name = db.Column(db.String(100), nullable=False)
    block_code = db.Column(db.String(20), nullable=False)

    rooms = db.relationship("Room", backref="hostel", lazy=True, cascade="all, delete-orphan")
    students = db.relationship("Student", backref="hostel", lazy=True)
    admins = db.relationship("Admin", backref="hostel", lazy=True)


class Room(db.Model):
    __tablename__ = "rooms"
    __table_args__ = (db.UniqueConstraint("hostel_id", "room_number", name="uq_hostel_room"),)

    id = db.Column(db.Integer, primary_key=True)
    hostel_id = db.Column(db.Integer, db.ForeignKey("hostels.id", ondelete="CASCADE"), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=3)

    students = db.relationship("Student", backref="room", lazy=True)


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    register_number = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    year_of_study = db.Column(db.Integer, nullable=False)
    hostel_id = db.Column(db.Integer, db.ForeignKey("hostels.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    parent_phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    tickets = db.relationship("Ticket", backref="student", lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="student", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="Warden")
    hostel_id = db.Column(db.Integer, db.ForeignKey("hostels.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    reviewed_tickets = db.relationship("Ticket", backref="reviewer", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_code = db.Column(db.String(30), nullable=False, unique=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    departure_datetime = db.Column(db.DateTime, nullable=False)
    expected_return_datetime = db.Column(db.DateTime, nullable=False)
    parent_contact = db.Column(db.String(20), nullable=True)
    status = db.Column(
        db.Enum("Pending", "Approved", "Rejected", "Cancelled", "Completed", name="ticket_status_enum"),
        nullable=False,
        default="Pending",
    )
    reviewed_by = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    notifications = db.relationship("Notification", backref="ticket", lazy=True)

    @staticmethod
    def generate_ticket_code() -> str:
        year = datetime.now().year
        prefix = f"HST-{year}-"
        last_ticket = (
            Ticket.query.filter(Ticket.ticket_code.like(f"{prefix}%"))
            .order_by(Ticket.id.desc())
            .first()
        )
        if last_ticket:
            last_seq = int(last_ticket.ticket_code.split("-")[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1
        return f"{prefix}{next_seq:04d}"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
class MaintenanceTicket(db.Model):
    __tablename__ = "maintenance_tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_code = db.Column(db.String(30), nullable=False, unique=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    hostel_id = db.Column(db.Integer, db.ForeignKey("hostels.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    priority = db.Column(db.String(20), nullable=False)  # Critical, High, Medium, Low
    priority_rank = db.Column(db.Integer, nullable=False, default=4)  # 1=Critical .. 4=Low
    assigned_team = db.Column(db.String(100), nullable=False)
    matched_keywords = db.Column(db.String(255), nullable=True)
    triage_reason = db.Column(db.String(255), nullable=True)
    report_count = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(
        db.Enum("Reported", "Assigned", "In Progress", "Resolved", name="maint_status_enum"),
        nullable=False,
        default="Reported",
    )
    warden_remark = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    student = db.relationship("Student", backref=db.backref("maintenance_tickets", lazy=True))
    hostel = db.relationship("Hostel")
    room = db.relationship("Room")
    updates = db.relationship(
        "MaintenanceUpdate",
        backref="maintenance_ticket",
        lazy=True,
        order_by="MaintenanceUpdate.created_at.desc()",
        cascade="all, delete-orphan",
    )

    @staticmethod
    def generate_code() -> str:
        year = datetime.now().year
        prefix = f"MNT-{year}-"
        last = (
            MaintenanceTicket.query.filter(MaintenanceTicket.ticket_code.like(f"{prefix}%"))
            .order_by(MaintenanceTicket.id.desc())
            .first()
        )
        next_seq = (int(last.ticket_code.split("-")[-1]) + 1) if last else 1
        return f"{prefix}{next_seq:04d}"


class MaintenanceUpdate(db.Model):
    __tablename__ = "maintenance_updates"

    id = db.Column(db.Integer, primary_key=True)
    maintenance_ticket_id = db.Column(
        db.Integer, db.ForeignKey("maintenance_tickets.id", ondelete="CASCADE"), nullable=False
    )
    updated_by_name = db.Column(db.String(120), nullable=False)
    updated_by_role = db.Column(db.String(30), nullable=False)  # System, Warden, Student
    status_snapshot = db.Column(db.String(30), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

class FoodComplaint(db.Model):
    __tablename__ = "food_complaints"

    id = db.Column(db.Integer, primary_key=True)
    complaint_code = db.Column(db.String(30), nullable=False, unique=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    mess_name = db.Column(db.String(60), nullable=False)  # Boys Hostel Mess / Girls Hostel Mess
    meal_type = db.Column(db.String(30), nullable=False)  # Breakfast, Lunch, Snacks, Dinner
    issue_type = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=False)
    photo_filename = db.Column(db.String(255), nullable=True)
    priority = db.Column(db.String(20), nullable=False, default="Medium")
    priority_rank = db.Column(db.Integer, nullable=False, default=3)  # 1=Critical .. 4=Low
    matched_keywords = db.Column(db.String(255), nullable=True)
    triage_reason = db.Column(db.String(255), nullable=True)
    status = db.Column(
        db.Enum("Reported", "Under Inspection", "Action Taken", "Resolved", name="food_status_enum"),
        nullable=False,
        default="Reported",
    )
    warden_remark = db.Column(db.Text, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    student = db.relationship("Student", backref=db.backref("food_complaints", lazy=True))
    reviewer = db.relationship("Admin")

    @staticmethod
    def generate_code() -> str:
        year = datetime.now().year
        prefix = f"FD-{year}-"
        last = (
            FoodComplaint.query.filter(FoodComplaint.complaint_code.like(f"{prefix}%"))
            .order_by(FoodComplaint.id.desc())
            .first()
        )
        next_seq = (int(last.complaint_code.split("-")[-1]) + 1) if last else 1
        return f"{prefix}{next_seq:04d}"