document.addEventListener("DOMContentLoaded", function () {
    // 1. Mobile Sidebar Toggle
    const sidebar = document.getElementById("appSidebar");
    const backdrop = document.getElementById("sidebarBackdrop");
    const toggleBtn = document.getElementById("sidebarToggleBtn");

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove("show");
        if (backdrop) backdrop.classList.remove("show");
    }

    if (toggleBtn && sidebar && backdrop) {
        toggleBtn.addEventListener("click", function () {
            sidebar.classList.toggle("show");
            backdrop.classList.toggle("show");
        });
        backdrop.addEventListener("click", closeSidebar);
    }

    // 2. Dynamic Hostel -> Room Dropdown on Registration Page
    const hostelSelect = document.getElementById("hostelSelect");
    const roomSelect = document.getElementById("roomSelect");

    if (hostelSelect && roomSelect) {
        hostelSelect.addEventListener("change", function () {
            const hostelId = this.value;
            roomSelect.innerHTML = '<option value="">Loading rooms...</option>';

            if (!hostelId) {
                roomSelect.innerHTML = '<option value="">Select Hostel First</option>';
                return;
            }

            fetch(`/api/rooms/${hostelId}`)
                .then((res) => res.json())
                .then((rooms) => {
                    roomSelect.innerHTML = '<option value="">Select Room</option>';
                    rooms.forEach((r) => {
                        const opt = document.createElement("option");
                        opt.value = r.id;
                        opt.textContent = `Room ${r.room_number}`;
                        roomSelect.appendChild(opt);
                    });
                })
                .catch(() => {
                    roomSelect.innerHTML = '<option value="">Error loading rooms</option>';
                });
        });
    }

    // 3. Ticket Form Departure vs Expected Return Client Validation
    const ticketForm = document.getElementById("generateTicketForm");
    if (ticketForm) {
        ticketForm.addEventListener("submit", function (e) {
            const depDate = document.getElementById("departure_date").value;
            const depTime = document.getElementById("departure_time").value;
            const retDate = document.getElementById("return_date").value;
            const retTime = document.getElementById("return_time").value;

            if (depDate && depTime && retDate && retTime) {
                const dep = new Date(`${depDate}T${depTime}`);
                const ret = new Date(`${retDate}T${retTime}`);
                if (ret <= dep) {
                    e.preventDefault();
                    alert("Expected return date & time must be after departure date & time.");
                }
            }
        });
    }

    // 4. Admin Reject Ticket Modal Wiring
    const rejectModal = document.getElementById("rejectTicketModal");
    if (rejectModal) {
        rejectModal.addEventListener("show.bs.modal", function (event) {
            const button = event.relatedTarget;
            const ticketId = button.getAttribute("data-ticket-id");
            const ticketCode = button.getAttribute("data-ticket-code");
            const studentName = button.getAttribute("data-student-name");

            const form = document.getElementById("rejectTicketForm");
            const label = document.getElementById("rejectModalTicketInfo");
            const textarea = document.getElementById("rejection_reason");

            if (form) form.action = `/admin/tickets/${ticketId}/reject`;
            if (label) label.textContent = `${ticketCode} — ${studentName}`;
            if (textarea) textarea.value = "";
        });
    }

    // 5. Auto-dismiss flash alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach((alertEl) => {
        setTimeout(() => {
            if (typeof bootstrap !== "undefined") {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
                bsAlert.close();
            }
        }, 5000);
    });
});