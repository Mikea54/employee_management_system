// dashboard.js - JavaScript for dashboard charts and components

document.addEventListener('DOMContentLoaded', function() {
    // Load department distribution chart if element exists
    const deptChartElement = document.getElementById('departmentDistributionChart');
    if (deptChartElement) {
        fetch('/charts/department_distribution')
            .then(response => response.json())
            .then(data => {
                const ctx = deptChartElement.getContext('2d');
                new Chart(ctx, {
                    type: 'doughnut',
                    data: data,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '70%',
                        plugins: {
                            legend: {
                                position: 'bottom',
                            },
                            title: {
                                display: true,
                                text: 'Employee Distribution by Department'
                            }
                        }
                    }
                });
            })
            .catch(error => console.error('Error loading department chart:', error));
    }

    // Load monthly attendance chart if element exists
    const attendanceChartElement = document.getElementById('monthlyAttendanceChart');
    if (attendanceChartElement) {
        fetch('/charts/monthly_attendance')
            .then(response => response.json())
            .then(data => {
                const ctx = attendanceChartElement.getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: data,
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                title: {
                                    display: true,
                                    text: 'Day of Month'
                                }
                            },
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Employee Count'
                                }
                            }
                        },
                        plugins: {
                            title: {
                                display: true,
                                text: 'Monthly Attendance Overview'
                            }
                        }
                    }
                });
            })
            .catch(error => console.error('Error loading attendance chart:', error));
    }

    // Load recent activities if element exists
    const recentActivitiesElement = document.getElementById('recentActivities');
    if (recentActivitiesElement) {
        // This would be a fetch to an API endpoint if we had activity logs
        // For now we'll just display a message
        recentActivitiesElement.innerHTML = `
            <div class="text-center py-4">
                <p class="text-muted">Activity log will appear here</p>
            </div>
        `;
    }

    // Initialize date range picker if exists
    const dateRangePicker = document.getElementById('dateRangePicker');
    if (dateRangePicker && typeof flatpickr === 'function') {
        flatpickr(dateRangePicker, {
            mode: 'range',
            dateFormat: 'Y-m-d',
            defaultDate: [
                new Date().toISOString().slice(0, 10),
                new Date(new Date().setDate(new Date().getDate() + 30)).toISOString().slice(0, 10)
            ],
            onChange: function(selectedDates, dateStr) {
                if (selectedDates.length === 2) {
                    // Here you could trigger a dashboard refresh with the new date range
                    console.log('Date range selected:', dateStr);
                }
            }
        });
    }

    // Handle dashboard card clicks to navigate to respective modules
    const dashboardCards = document.querySelectorAll('.dashboard-card');
    dashboardCards.forEach(card => {
        card.addEventListener('click', function() {
            const targetUrl = this.getAttribute('data-target-url');
            if (targetUrl) {
                window.location.href = targetUrl;
            }
        });
    });
});

// Function to refresh dashboard data
function refreshDashboard() {
    // This function could be called periodically or manually
    // to refresh the dashboard with the latest data
    location.reload();
}

// Function to filter dashboard by department
function filterDashboardByDepartment(departmentId) {
    // This would apply filters to the dashboard based on department
    console.log('Filtering dashboard by department:', departmentId);
    // You would typically reload charts with filtered data
}

// Function to export dashboard data
function exportDashboardData(format) {
    // This would export the dashboard data in the specified format
    alert(`Exporting dashboard data in ${format} format`);
    // Implementation would depend on what data needs to be exported
}
