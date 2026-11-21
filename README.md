# Hostick — College Hostel Ticket & Complaint Management System

A responsive Flask web application built for **Coimbatore Institute of Technology** to digitize hostel outing passes, automatically triage student maintenance complaints by safety priority, and manage Boys/Girls Hostel Mess food complaints with photo evidence.

---

## Core Modules

### 1. Outing Pass Management
- **Student Portal:** Register with dynamic Hostel/Room selection, submit outing requests, cancel pending requests, receive in-app notifications, and download **Approved Outing Pass PDFs** (generated via ReportLab).
- **Warden Portal:** Approve or reject outing requests (with mandatory rejection reasons), mark student returns as completed, search/filter tickets, view individual student histories, and export **Excel (.xlsx)** and **PDF** analytics reports.

### 2. Smart Maintenance Triage & Live Tracking
- **Deterministic Keyword & Safety Engine (`utils/maintenance_triage.py`):** Reads free-text complaints, identifies the category (`Electrical`, `Plumbing`, `Carpentry & Furniture`, `Housekeeping & Sanitation`, `Internet & IT`), assigns safety priority (`Critical` → `High` → `Medium` → `Low`), and routes to the right team.
- **Duplicate Merging:** Multiple complaints for the same room and category merge into one active ticket, increment the report counter, and auto-escalate priority if new hazard keywords appear.
- **Urgent-First Warden Queue & Live Tracker:** Wardens view critical hazards ranked at the top and push live updates (`Reported` → `Assigned` → `In Progress` → `Resolved`) that auto-sync every 8 seconds on the student's live tracking page.

### 3. Hostel Food / Mess Complaints (Boys & Girls Mess)
- Dedicated complaint portal split by **Boys Hostel Mess** and **Girls Hostel Mess**.
- Supports **photo evidence uploads** (`.png`, `.jpg`, `.jpeg`, `.webp`, up to 5 MB) for insects, foreign objects, or rotten/spoiled food.
- Automatically flags contamination/spoiled-food reports as **Critical** at the top of the Warden's Mess Complaints Queue.

---

## Tech Stack
- **Backend:** Python 3, Flask, Flask-SQLAlchemy, Werkzeug Password Hashing
- **Database:** SQLite (`hostick.db`, easily switchable to MySQL via `config.py`)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript, Bootstrap 5.3, Bootstrap Icons, Chart.js
- **Reports & PDFs:** ReportLab, Pandas, OpenPyXL

---

## Quick Setup & Run Instructions (macOS / Linux)

1. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate