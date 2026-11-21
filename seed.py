from datetime import datetime, timedelta
from app import create_app
from models import (
    db,
    Hostel,
    Room,
    Student,
    Admin,
    Ticket,
    Notification,
    MaintenanceTicket,
    MaintenanceUpdate,
)
from utils.maintenance_triage import analyze_complaint


def seed_database():
    app = create_app()
    with app.app_context():
        db.create_all()

        # 1. Seed Hostels
        if Hostel.query.count() == 0:
            hostels = [
                Hostel(name="Bharathi Boys Hostel", warden_name="Dr. Rajesh Kumar", block_code="B-BLK"),
                Hostel(name="Kaveri Girls Hostel", warden_name="Prof. Meena Sundaram", block_code="K-BLK"),
                Hostel(name="Tagore PG Hostel", warden_name="Mr. Karthik Nair", block_code="T-BLK"),
            ]
            db.session.add_all(hostels)
            db.session.commit()

        bharathi = Hostel.query.filter_by(block_code="B-BLK").first()
        kaveri = Hostel.query.filter_by(block_code="K-BLK").first()
        tagore = Hostel.query.filter_by(block_code="T-BLK").first()

        # 2. Seed Rooms
        if Room.query.count() == 0:
            rooms = [
                Room(hostel_id=bharathi.id, room_number="101", capacity=3),
                Room(hostel_id=bharathi.id, room_number="102", capacity=3),
                Room(hostel_id=bharathi.id, room_number="201", capacity=2),
                Room(hostel_id=kaveri.id, room_number="101", capacity=3),
                Room(hostel_id=kaveri.id, room_number="102", capacity=2),
                Room(hostel_id=kaveri.id, room_number="205", capacity=3),
                Room(hostel_id=tagore.id, room_number="301", capacity=2),
                Room(hostel_id=tagore.id, room_number="302", capacity=2),
            ]
            db.session.add_all(rooms)
            db.session.commit()

        # 3. Seed Admin / Warden
        if not Admin.query.filter_by(email="warden@hostick.edu").first():
            warden = Admin(
                full_name="Dr. Rajesh Kumar",
                email="warden@hostick.edu",
                role="Chief Warden",
                hostel_id=bharathi.id,
            )
            warden.set_password("admin123")
            db.session.add(warden)
            db.session.commit()

        warden = Admin.query.filter_by(email="warden@hostick.edu").first()

        # 4. Seed Sample Students
        if not Student.query.filter_by(register_number="21CS101").first():
            room_b101 = Room.query.filter_by(hostel_id=bharathi.id, room_number="101").first()
            s1 = Student(
                full_name="Arjun Krishnan",
                register_number="21CS101",
                email="arjun@student.edu",
                department="Computer Science",
                year_of_study=3,
                hostel_id=bharathi.id,
                room_id=room_b101.id,
                phone="9876543210",
                parent_phone="9876500001",
                is_active=True,
            )
            s1.set_password("student123")
            db.session.add(s1)

        if not Student.query.filter_by(register_number="22EC204").first():
            room_k102 = Room.query.filter_by(hostel_id=kaveri.id, room_number="102").first()
            s2 = Student(
                full_name="Divya Prakash",
                register_number="22EC204",
                email="divya@student.edu",
                department="Electronics & Communication",
                year_of_study=2,
                hostel_id=kaveri.id,
                room_id=room_k102.id,
                phone="9876543211",
                parent_phone="9876500002",
                is_active=True,
            )
            s2.set_password("student123")
            db.session.add(s2)

        db.session.commit()

        s1 = Student.query.filter_by(register_number="21CS101").first()
        s2 = Student.query.filter_by(register_number="22EC204").first()
        now = datetime.now()

        # 5. Seed Sample Outing Tickets
        if Ticket.query.count() == 0:
            t1 = Ticket(
                ticket_code=f"HST-{now.year}-0001",
                student_id=s1.id,
                reason="Visiting home for weekend family function",
                destination="Coimbatore - RS Puram",
                departure_datetime=now + timedelta(hours=4),
                expected_return_datetime=now + timedelta(days=2),
                parent_contact=s1.parent_phone,
                status="Approved",
                reviewed_by=warden.id,
                reviewed_at=now - timedelta(hours=1),
                created_at=now - timedelta(hours=3),
            )
            t2 = Ticket(
                ticket_code=f"HST-{now.year}-0002",
                student_id=s1.id,
                reason="Buying reference textbooks and lab components",
                destination="Gandhipuram Town Hall",
                departure_datetime=now + timedelta(days=3, hours=2),
                expected_return_datetime=now + timedelta(days=3, hours=7),
                parent_contact=s1.parent_phone,
                status="Pending",
                created_at=now - timedelta(minutes=30),
            )
            db.session.add_all([t1, t2])
            db.session.commit()

            db.session.add(
                Notification(
                    student_id=s1.id,
                    ticket_id=t1.id,
                    message=f"Outing Ticket {t1.ticket_code} was APPROVED by {warden.full_name}.",
                )
            )
            db.session.commit()

        # 6. Seed Sample Maintenance Tickets (Auto-triaged)
        if MaintenanceTicket.query.count() == 0:
            samples = [
                (
                    s1,
                    "The switchboard near my desk is sparking with a burning smell when we plug in a charger.",
                    "In Progress",
                    1,
                    "Electrician dispatched immediately. Main room breaker inspected; replacing switchboard module.",
                    now - timedelta(minutes=45),
                ),
                (
                    s2,
                    "The bathroom corridor is very dusty and needs cleaning and mopping.",
                    "Reported",
                    1,
                    None,
                    now - timedelta(hours=2),
                ),
                (
                    s1,
                    "Ceiling fan not working and making noise since last night.",
                    "Assigned",
                    3,
                    "Assigned to Electrical Maintenance Team. Capacitor replacement scheduled for 4:00 PM.",
                    now - timedelta(hours=1, minutes=20),
                ),
            ]

            for idx, (stu, desc, status, rep_count, remark, created_time) in enumerate(samples, start=1):
                triage = analyze_complaint(desc)
                mt = MaintenanceTicket(
                    ticket_code=f"MNT-{now.year}-{idx:04d}",
                    student_id=stu.id,
                    hostel_id=stu.hostel_id,
                    room_id=stu.room_id,
                    description=desc,
                    category=triage["category"],
                    priority=triage["priority"],
                    priority_rank=triage["priority_rank"],
                    assigned_team=triage["assigned_team"],
                    matched_keywords=triage["matched_keywords"],
                    triage_reason=triage["triage_reason"],
                    report_count=rep_count,
                    status=status,
                    warden_remark=remark,
                    created_at=created_time,
                    updated_at=created_time + timedelta(minutes=15),
                )
                db.session.add(mt)
                db.session.flush()

                db.session.add(
                    MaintenanceUpdate(
                        maintenance_ticket_id=mt.id,
                        updated_by_name="Hostick Auto-Triage",
                        updated_by_role="System",
                        status_snapshot="Reported",
                        message=f"Auto-classified as {triage['category']} ({triage['priority']} Priority). Routed to {triage['assigned_team']}.",
                        created_at=created_time,
                    )
                )
                if remark:
                    db.session.add(
                        MaintenanceUpdate(
                            maintenance_ticket_id=mt.id,
                            updated_by_name=warden.full_name,
                            updated_by_role="Warden",
                            status_snapshot=status,
                            message=remark,
                            created_at=created_time + timedelta(minutes=15),
                        )
                    )

            db.session.commit()
            print("Seeded sample auto-triaged maintenance tickets.")

        print("Database seeding completed successfully.")


if __name__ == "__main__":
    seed_database()