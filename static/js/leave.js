// leave.js - JavaScript for leave management features

document.addEventListener('DOMContentLoaded', function() {
    // Initialize date pickers for leave request form
    initializeDatePickers();
    
    // Set up leave type change handler
    setupLeaveTypeChangeHandler();
    
    // Set up date range change handler
    setupDateRangeChangeHandler();
    
    // Initialize leave balance display
    updateLeaveBalanceDisplay();
    
    // Set up export buttons
    setupExportButtons();
});

// Function to initialize date pickers
function initializeDatePickers() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    
    if (!startDateInput || !endDateInput) return;
    
    // Initialize datepickers if flatpickr is available
    if (typeof flatpickr === 'function') {
        // Get current date for min date validation
        const today = new Date();
        const todayStr = today.toISOString().slice(0, 10);
        
        // Configure date pickers
        flatpickr(startDateInput, {
            dateFormat: 'Y-m-d',
            minDate: todayStr,
            onChange: function(selectedDates, dateStr) {
                // Update end date min value when start date changes
                if (selectedDates.length > 0) {
                    const endDatePicker = endDateInput._flatpickr;
                    if (endDatePicker) {
                        endDatePicker.set('minDate', dateStr);
                        
                        // If end date is before start date, update it
                        if (new Date(endDateInput.value) < new Date(dateStr)) {
                            endDateInput.value = dateStr;
                        }
                    }
                }
                
                // Update days calculation
                calculateLeaveDays();
            }
        });
        
        flatpickr(endDateInput, {
            dateFormat: 'Y-m-d',
            minDate: todayStr,
            onChange: function() {
                // Update days calculation
                calculateLeaveDays();
            }
        });
    }
}

// Function to calculate leave days and hours between selected dates
function calculateLeaveDays() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const daysElement = document.getElementById('leaveDays');
    const hoursElement = document.getElementById('leaveHours');
    const partialWrapper = document.getElementById('partialHoursWrapper');
    const hoursInput = document.getElementById('hoursInput');

    if (!startDateInput || !endDateInput || !daysElement || !hoursElement || !hoursInput || !partialWrapper) return;
    
    const startDate = new Date(startDateInput.value);
    const endDate = new Date(endDateInput.value);
    
    if (!isNaN(startDate.getTime()) && !isNaN(endDate.getTime())) {
        // Calculate business days (excluding weekends)
        let days = 0;
        let currentDate = new Date(startDate);
        
        while (currentDate <= endDate) {
            const dayOfWeek = currentDate.getDay();
            // Skip weekends (0 = Sunday, 6 = Saturday)
            if (dayOfWeek !== 0 && dayOfWeek !== 6) {
                days++;
            }
            
            // Move to next day
            currentDate.setDate(currentDate.getDate() + 1);
        }
        
        let hours;

        if (days === 1) {
            partialWrapper.style.display = 'block';
            hours = parseFloat(hoursInput.value) || 8;
            if (hours > 8) hours = 8;
            hoursInput.value = hours;
        } else {
            partialWrapper.style.display = 'none';
            hours = days * 8;
            hoursInput.value = hours;
        }

        daysElement.textContent = days;
        hoursElement.textContent = hours;

        // Update warning message if selected hours exceed balance
        updateLeaveBalanceWarning(hours);
    }
}

// Function to set up leave type change handler
function setupLeaveTypeChangeHandler() {
    const leaveTypeSelect = document.getElementById('leaveTypeId');
    if (!leaveTypeSelect) return;
    
    leaveTypeSelect.addEventListener('change', function() {
        updateLeaveBalanceDisplay();
        calculateLeaveDays(); // Recalculate to update warnings
    });
}

// Function to update leave balance display
function updateLeaveBalanceDisplay() {
    const leaveTypeSelect = document.getElementById('leaveTypeId');
    const balanceElement = document.getElementById('leaveBalance');
    
    if (!leaveTypeSelect || !balanceElement) return;
    
    const selectedLeaveTypeId = leaveTypeSelect.value;
    
    if (selectedLeaveTypeId) {
        // Get balance from data attribute
        const balanceDataElement = document.querySelector(`[data-leave-type-id="${selectedLeaveTypeId}"]`);
        
        if (balanceDataElement) {
            const balance = balanceDataElement.getAttribute('data-balance');
            balanceElement.textContent = balance || '0';
            balanceElement.parentElement.style.display = 'block';
        } else {
            balanceElement.textContent = '0';
            balanceElement.parentElement.style.display = 'none';
        }
    } else {
        balanceElement.textContent = '0';
        balanceElement.parentElement.style.display = 'none';
    }
}

// Function to update leave balance warning
function updateLeaveBalanceWarning(requestedHours) {
    const leaveTypeSelect = document.getElementById('leaveTypeId');
    const warningElement = document.getElementById('leaveBalanceWarning');
    
    if (!leaveTypeSelect || !warningElement) return;
    
    const selectedLeaveTypeId = leaveTypeSelect.value;
    
    if (selectedLeaveTypeId) {
        // Get balance from data attribute
        const balanceDataElement = document.querySelector(`[data-leave-type-id="${selectedLeaveTypeId}"]`);
        
        if (balanceDataElement) {
            const balance = parseFloat(balanceDataElement.getAttribute('data-balance') || '0');
            
            if (requestedHours > balance) {
                warningElement.textContent = `Warning: Requested hours (${requestedHours}) exceed your available balance (${balance} hours).`;
                warningElement.style.display = 'block';
            } else {
                warningElement.style.display = 'none';
            }
        } else {
            warningElement.style.display = 'none';
        }
    } else {
        warningElement.style.display = 'none';
    }
}

// Function to set up date range change handler
function setupDateRangeChangeHandler() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const hoursInput = document.getElementById('hoursInput');

    if (!startDateInput || !endDateInput) return;

    // Add change event listeners
    startDateInput.addEventListener('change', calculateLeaveDays);
    endDateInput.addEventListener('change', calculateLeaveDays);
    if (hoursInput) {
        hoursInput.addEventListener('input', calculateLeaveDays);
    }
}

// Function to validate leave request form before submission
function validateLeaveRequestForm() {
    const form = document.getElementById('leaveRequestForm');
    if (!form) return false;
    
    // Check if form is valid
    const isValid = form.checkValidity();
    form.classList.add('was-validated');
    
    if (!isValid) {
        return false;
    }
    
    // Additional validation for leave balance
    const leaveTypeSelect = document.getElementById('leaveTypeId');
    const selectedLeaveTypeId = leaveTypeSelect.value;
    
    if (selectedLeaveTypeId) {
        const balanceDataElement = document.querySelector(`[data-leave-type-id="${selectedLeaveTypeId}"]`);
        
        if (balanceDataElement) {
            const balance = parseFloat(balanceDataElement.getAttribute('data-balance') || '0');
            const hoursInput = document.getElementById('hoursInput');
            const requestedHours = parseFloat(hoursInput.value || '0');
            
            if (requestedHours > balance) {
                const confirm = window.confirm('The requested leave hours exceed your available balance. Do you still want to submit this request?');
                return confirm;
            }
        }
    }
    
    return true;
}

// Function to approve or reject leave request
function processLeaveRequest(requestId, action) {
    // Create hidden form for submission
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/leave/${action}/${requestId}`;
    document.body.appendChild(form);
    form.submit();
}

// Function to set up export buttons
function setupExportButtons() {
    const exportButtons = document.querySelectorAll('[data-export-table]');
    exportButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tableId = this.getAttribute('data-export-table');
            const format = this.getAttribute('data-export-format') || 'csv';
            
            if (format === 'csv') {
                exportTableToCSV(tableId, `leave_report_${new Date().toISOString().slice(0, 10)}.csv`);
            } else if (format === 'pdf') {
                // PDF export would be implemented here
                alert('PDF export functionality would be implemented here');
            }
        });
    });
}
