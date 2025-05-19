// attendance.js - JavaScript for attendance tracking and reporting

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the clock display
    initializeClock();
    
    // Update clock in/out status
    updateAttendanceStatus();
    
    // Set up a timer to refresh attendance status every 30 seconds
    setInterval(updateAttendanceStatus, 30000);
    
    // Set up date range filters for attendance reports
    setupDateRangeFilter();
    
    // Initialize attendance calendar view if present
    initializeAttendanceCalendar();
    
    // Set up export buttons
    setupExportButtons();
});

// Function to initialize the clock display
function initializeClock() {
    const clockElement = document.getElementById('currentTime');
    if (!clockElement) return;
    
    function updateClock() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString();
        const dateStr = now.toLocaleDateString();
        clockElement.textContent = `${dateStr} ${timeStr}`;
    }
    
    // Update once immediately and then every second
    updateClock();
    setInterval(updateClock, 1000);
}

// Function to update attendance status display
function updateAttendanceStatus() {
    const statusElement = document.getElementById('attendanceStatus');
    const clockInBtn = document.getElementById('clockInBtn');
    const clockOutBtn = document.getElementById('clockOutBtn');
    
    if (!statusElement || !clockInBtn || !clockOutBtn) return;
    
    // Fetch today's attendance status from the server
    fetch('/attendance/status')
        .then(response => response.json())
        .then(data => {
            // Display the appropriate status message
            let statusHTML = '';
            
            // Check if we have multiple sessions
            if (data.multiple_sessions) {
                statusHTML += '<div class="mb-2"><small class="text-info">Multiple sessions today</small></div>';
            }
            
            if (data.clocked_in) {
                // Currently clocked in
                const clockInTime = new Date(data.clock_in).toLocaleTimeString();
                statusHTML += `<span class="badge bg-success">Clocked In</span> at ${clockInTime}`;
                
                // Disable clock-in button, enable clock-out button
                clockInBtn.disabled = true;
                clockOutBtn.disabled = false;
                
                // Add a clear visual indication
                statusHTML += `<div class="mt-2 text-success"><small><i class="fas fa-circle-check"></i> Ready to clock out</small></div>`;
            } else if (data.clocked_out) {
                // Last session was completed (clocked in and out)
                const clockInTime = new Date(data.clock_in).toLocaleTimeString();
                const clockOutTime = new Date(data.clock_out).toLocaleTimeString();
                statusHTML += `<span class="badge bg-success">Last Session</span>: ${clockInTime} to ${clockOutTime}`;
                statusHTML += `<br><span class="badge bg-info">Ready for new session</span>`;
                
                // Allow a new clock in
                clockInBtn.disabled = false;
                clockOutBtn.disabled = true;
            } else {
                // Not clocked in at all today
                statusHTML = '<span class="badge bg-warning">Not Clocked In</span>';
                clockInBtn.disabled = false;
                clockOutBtn.disabled = true;
            }
            
            statusElement.innerHTML = statusHTML;
        })
        .catch(error => {
            console.error('Error fetching attendance status:', error);
            // Fallback to showing default status
            statusElement.innerHTML = '<span class="badge bg-secondary">Status Unavailable</span>';
            
            // Disable both buttons as a safety measure when status can't be determined
            clockInBtn.disabled = false;
            clockOutBtn.disabled = true;
        });
}

// Function to set up date range filter for attendance reports
function setupDateRangeFilter() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const filterForm = document.getElementById('attendanceFilterForm');
    
    if (!startDateInput || !endDateInput || !filterForm) return;
    
    // Initialize datepickers if flatpickr is available
    if (typeof flatpickr === 'function') {
        const dateConfig = {
            dateFormat: 'Y-m-d',
            maxDate: 'today'
        };
        
        flatpickr(startDateInput, dateConfig);
        flatpickr(endDateInput, dateConfig);
    }
    
    // Set default values if not already set
    if (!startDateInput.value) {
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        startDateInput.value = firstDay.toISOString().slice(0, 10);
    }
    
    if (!endDateInput.value) {
        const today = new Date();
        endDateInput.value = today.toISOString().slice(0, 10);
    }
}

// Function to initialize calendar view of attendance
function initializeAttendanceCalendar() {
    const calendarElement = document.getElementById('attendanceCalendar');
    if (!calendarElement) return;
    
    // This would be implemented with a calendar library like FullCalendar
    // For this example, we'll just display a placeholder
    calendarElement.innerHTML = `
        <div class="text-center py-4">
            <p class="text-muted">Calendar view would be rendered here</p>
            <small>Implement with FullCalendar or similar library</small>
        </div>
    `;
}

// Function to set up export buttons
function setupExportButtons() {
    const exportButtons = document.querySelectorAll('[data-export-table]');
    exportButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tableId = this.getAttribute('data-export-table');
            const format = this.getAttribute('data-export-format') || 'csv';
            
            if (format === 'csv') {
                exportTableToCSV(tableId, `attendance_report_${new Date().toISOString().slice(0, 10)}.csv`);
            } else if (format === 'pdf') {
                // PDF export would be implemented here
                alert('PDF export functionality would be implemented here');
            }
        });
    });
}

// Function to generate attendance report
function generateAttendanceReport(employeeId, startDate, endDate) {
    // This function would fetch attendance data for the specified parameters
    // and generate a report
    
    // Redirect to the reports page with query parameters
    const url = `/attendance/reports?employee_id=${employeeId}&start_date=${startDate}&end_date=${endDate}`;
    window.location.href = url;
}

// Function to manually add attendance record (for admin/HR)
function addAttendanceRecord() {
    const form = document.getElementById('addAttendanceForm');
    if (!form) return;
    
    // Form validation would happen here
    const isValid = form.checkValidity();
    form.classList.add('was-validated');
    
    if (isValid) {
        // Submit the form
        form.submit();
    }
}
