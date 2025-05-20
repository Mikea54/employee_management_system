// main.js - Common JavaScript functions for the Employee Management System

// Theme handling utilities
function applyTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    
    // If not authenticated, store in localStorage
    if (!document.body.classList.contains('authenticated')) {
        localStorage.setItem('theme_preference', theme);
    }
}

// Handle sidebar toggling
document.addEventListener('DOMContentLoaded', function() {
    // Check for theme in localStorage if not authenticated
    if (!document.body.classList.contains('authenticated')) {
        const savedTheme = localStorage.getItem('theme_preference');
        if (savedTheme) {
            applyTheme(savedTheme);
            updateClientThemeUI(savedTheme);
        }
        
        // Add event listener for client-side theme toggle
        const themeToggleBtn = document.getElementById('clientThemeToggle');
        if (themeToggleBtn) {
            themeToggleBtn.addEventListener('click', function() {
                const currentTheme = document.documentElement.getAttribute('data-bs-theme');
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                applyTheme(newTheme);
                updateClientThemeUI(newTheme);
            });
        }
    }
    
    // Function to update client theme toggle UI
    function updateClientThemeUI(theme) {
        const themeIcon = document.getElementById('themeIcon');
        const themeText = document.getElementById('themeText');
        
        if (themeIcon && themeText) {
            if (theme === 'dark') {
                themeIcon.className = 'fas fa-sun';
                themeText.textContent = 'Light Mode';
            } else {
                themeIcon.className = 'fas fa-moon';
                themeText.textContent = 'Dark Mode';
            }
        }
    }
    // Toggle sidebar on mobile
    const sidebarToggle = document.getElementById('sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            document.body.classList.toggle('sidebar-open');
        });
    }

    // Close sidebar when clicking the backdrop on mobile
    const backdrop = document.querySelector('.sidebar-backdrop');
    if (backdrop) {
        backdrop.addEventListener('click', function() {
            document.body.classList.remove('sidebar-open');
        });
    }

    // Close sidebar when clicking a nav link on mobile
    const sidebarLinks = document.querySelectorAll('.sidebar .nav-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth < 992) {
                document.body.classList.remove('sidebar-open');
            }
        });
    });

    // Handle responsive behavior
    function handleResponsive() {
        if (window.innerWidth >= 992) {
            // Always show sidebar on desktop/large tablets
            document.body.classList.remove('sidebar-open');
        } else {
            // Hide sidebar by default on mobile/small tablets
            document.body.classList.remove('sidebar-open');
        }
    }

    // Initial setup and add resize event listener
    handleResponsive();
    window.addEventListener('resize', handleResponsive);

    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(element => {
        new bootstrap.Tooltip(element);
    });

    // Initialize popovers
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    popoverTriggerList.forEach(element => {
        new bootstrap.Popover(element);
    });

    // Initialize date pickers
    const datePickers = document.querySelectorAll('.datepicker');
    datePickers.forEach(element => {
        // Use flatpickr or other date picker library
        if (typeof flatpickr === 'function') {
            flatpickr(element, {
                dateFormat: 'Y-m-d',
                allowInput: true
            });
        }
    });

    // Setup confirmation dialogs
    const confirmActions = document.querySelectorAll('[data-confirm]');
    confirmActions.forEach(element => {
        element.addEventListener('click', function(e) {
            if (!confirm(this.getAttribute('data-confirm') || 'Are you sure?')) {
                e.preventDefault();
            }
        });
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert-dismissible:not(.alert-persistent)');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Handle form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});

// Format date for display
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

// Format date and time for display
function formatDateTime(dateTimeString) {
    if (!dateTimeString) return '';
    const date = new Date(dateTimeString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Calculate difference between two dates in days
function dateDiffInDays(date1, date2) {
    const d1 = new Date(date1);
    const d2 = new Date(date2);
    const diffTime = Math.abs(d2 - d1);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // Include both start and end dates
}

// Export table data to CSV
function exportTableToCSV(tableId, filename = 'data.csv') {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    let csv = [];
    
    // Get header row
    const headerRow = table.querySelector('thead tr');
    if (headerRow) {
        const headers = Array.from(headerRow.querySelectorAll('th')).map(th => th.textContent);
        csv.push(headers.join(','));
    }
    
    // Get data rows
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const data = Array.from(row.querySelectorAll('td')).map(td => {
            // Replace commas with spaces and strip HTML
            let text = td.textContent.replace(/,/g, ' ');
            return `"${text.trim()}"`;
        });
        csv.push(data.join(','));
    });
    
    // Create and trigger download
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    // Create download URL
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Send table HTML to server to generate PDF
function exportTableToPDF(tableId, filename = 'report.pdf') {
    const table = document.getElementById(tableId);
    if (!table) return;

    fetch('/timesheets/export-pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ html: table.outerHTML })
    })
    .then(resp => resp.blob())
    .then(blob => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    })
    .catch(() => alert('Failed to export PDF'));
}
