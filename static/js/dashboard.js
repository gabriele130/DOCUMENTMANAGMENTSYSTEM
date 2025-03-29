/**
 * Dashboard functionality for Document Management System
 */

document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
});

/**
 * Initialize the dashboard
 */
function initDashboard() {
    // Initialize dashboard charts
    initCharts();
    
    // Setup quick actions
    setupQuickActions();
    
    // Initialize task calendar if available
    initTaskCalendar();
}

/**
 * Initialize dashboard charts using Chart.js
 */
function initCharts() {
    // Get the dashboard stats from the data elements
    const docCountByTypeElement = document.getElementById('docCountByTypeData');
    const docCountByMonthElement = document.getElementById('docCountByMonthData');
    
    if (docCountByTypeElement) {
        try {
            const docTypeData = JSON.parse(docCountByTypeElement.textContent);
            createDocumentTypeChart(docTypeData);
        } catch (e) {
            console.error('Error parsing document type data:', e);
        }
    }
    
    if (docCountByMonthElement) {
        try {
            const docMonthData = JSON.parse(docCountByMonthElement.textContent);
            createDocumentTrendChart(docMonthData);
        } catch (e) {
            console.error('Error parsing document month data:', e);
        }
    }
}

/**
 * Create a pie chart showing document distribution by type
 */
function createDocumentTypeChart(data) {
    const ctx = document.getElementById('documentTypeChart');
    if (!ctx || !window.Chart) return;
    
    // Prepare the data
    const labels = data.map(item => item.type);
    const counts = data.map(item => item.count);
    
    // Generate colors
    const colors = generateChartColors(labels.length);
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: 'rgb(255, 255, 255)',
                        padding: 10
                    }
                },
                title: {
                    display: true,
                    text: 'Documents by Type',
                    color: 'rgb(255, 255, 255)',
                    font: {
                        size: 16
                    }
                }
            }
        }
    });
}

/**
 * Create a line chart showing document upload trends by month
 */
function createDocumentTrendChart(data) {
    const ctx = document.getElementById('documentTrendChart');
    if (!ctx || !window.Chart) return;
    
    // Prepare the data
    const labels = data.map(item => item.month);
    const counts = data.map(item => item.count);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Documents Uploaded',
                data: counts,
                fill: false,
                borderColor: '#0d6efd',
                tension: 0.1,
                backgroundColor: 'rgba(13, 110, 253, 0.5)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: 'rgb(200, 200, 200)'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: 'rgb(200, 200, 200)'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: 'rgb(255, 255, 255)'
                    }
                },
                title: {
                    display: true,
                    text: 'Document Upload Trends',
                    color: 'rgb(255, 255, 255)',
                    font: {
                        size: 16
                    }
                }
            }
        }
    });
}

/**
 * Generate colors for charts
 */
function generateChartColors(count) {
    const baseColors = [
        '#0d6efd', '#dc3545', '#ffc107', '#198754', '#6610f2',
        '#fd7e14', '#20c997', '#d63384', '#6c757d', '#0dcaf0'
    ];
    
    // If we have enough base colors, use them
    if (count <= baseColors.length) {
        return baseColors.slice(0, count);
    }
    
    // Otherwise, generate additional colors
    const colors = [...baseColors];
    
    for (let i = baseColors.length; i < count; i++) {
        const r = Math.floor(Math.random() * 255);
        const g = Math.floor(Math.random() * 255);
        const b = Math.floor(Math.random() * 255);
        colors.push(`rgba(${r}, ${g}, ${b}, 0.8)`);
    }
    
    return colors;
}

/**
 * Setup quick action buttons on dashboard
 */
function setupQuickActions() {
    // Setup upload document button
    const uploadButton = document.getElementById('quickUploadButton');
    if (uploadButton) {
        uploadButton.addEventListener('click', function() {
            window.location.href = '/documents/upload';
        });
    }
    
    // Setup create workflow button
    const workflowButton = document.getElementById('quickWorkflowButton');
    if (workflowButton) {
        workflowButton.addEventListener('click', function() {
            window.location.href = '/workflow/create';
        });
    }
    
    // Setup search button
    const searchButton = document.getElementById('quickSearchButton');
    if (searchButton) {
        searchButton.addEventListener('click', function() {
            window.location.href = '/search';
        });
    }
}

/**
 * Initialize task calendar with due dates
 */
function initTaskCalendar() {
    const taskCalendar = document.getElementById('taskCalendar');
    if (!taskCalendar) return;
    
    // Get tasks data from the hidden element
    const tasksDataElement = document.getElementById('tasksData');
    if (!tasksDataElement) return;
    
    try {
        const tasks = JSON.parse(tasksDataElement.textContent);
        
        // Get the current month
        const today = new Date();
        const currentMonth = today.getMonth();
        const currentYear = today.getFullYear();
        
        // Generate calendar HTML
        generateCalendar(taskCalendar, currentMonth, currentYear, tasks);
    } catch (e) {
        console.error('Error initializing task calendar:', e);
        taskCalendar.innerHTML = '<div class="alert alert-danger">Error loading task calendar</div>';
    }
}

/**
 * Generate a calendar for the given month with tasks
 */
function generateCalendar(container, month, year, tasks) {
    // Get the first day of the month
    const firstDay = new Date(year, month, 1);
    const startingDay = firstDay.getDay(); // 0 = Sunday, 1 = Monday, etc.
    
    // Get the number of days in the month
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    
    // Get the name of the month
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                        'July', 'August', 'September', 'October', 'November', 'December'];
    
    // Create the calendar HTML
    let calendarHTML = `
        <div class="calendar-header d-flex justify-content-between align-items-center mb-3">
            <h4>${monthNames[month]} ${year}</h4>
        </div>
        <table class="table table-bordered calendar-table">
            <thead>
                <tr>
                    <th>Sun</th>
                    <th>Mon</th>
                    <th>Tue</th>
                    <th>Wed</th>
                    <th>Thu</th>
                    <th>Fri</th>
                    <th>Sat</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    // Create calendar days
    let day = 1;
    for (let i = 0; i < 6; i++) {
        calendarHTML += '<tr>';
        
        for (let j = 0; j < 7; j++) {
            if (i === 0 && j < startingDay) {
                // Empty cells before the first day
                calendarHTML += '<td class="empty-day"></td>';
            } else if (day > daysInMonth) {
                // Empty cells after the last day
                calendarHTML += '<td class="empty-day"></td>';
            } else {
                // Get tasks for this day
                const date = new Date(year, month, day);
                const dayTasks = tasks.filter(task => {
                    if (!task.due_date) return false;
                    const dueDate = new Date(task.due_date);
                    return dueDate.getDate() === day && 
                           dueDate.getMonth() === month && 
                           dueDate.getFullYear() === year;
                });
                
                // Determine day styling
                const isToday = (day === new Date().getDate() && 
                                month === new Date().getMonth() && 
                                year === new Date().getFullYear());
                const dayClass = isToday ? 'today' : '';
                const hasTask = dayTasks.length > 0;
                
                calendarHTML += `<td class="${dayClass}">
                    <div class="calendar-day">
                        <span class="day-number">${day}</span>
                        ${hasTask ? `<div class="task-indicator" data-bs-toggle="tooltip" title="${dayTasks.length} tasks due">${dayTasks.length}</div>` : ''}
                    </div>
                    ${hasTask ? `<div class="day-tasks">
                        ${dayTasks.slice(0, 2).map(task => `
                            <div class="small task-item" data-bs-toggle="tooltip" 
                                title="${task.workflow_name}: ${task.task_name}">
                                <a href="/workflow/${task.workflow_id}" class="stretched-link">
                                    ${task.task_name.substring(0, 15)}${task.task_name.length > 15 ? '...' : ''}
                                </a>
                            </div>
                        `).join('')}
                        ${dayTasks.length > 2 ? `<div class="small text-muted">+${dayTasks.length - 2} more</div>` : ''}
                    </div>` : ''}
                </td>`;
                
                day++;
            }
        }
        
        calendarHTML += '</tr>';
        
        // Stop if we've reached the end of the month
        if (day > daysInMonth) {
            break;
        }
    }
    
    calendarHTML += '</tbody></table>';
    
    // Add to the container
    container.innerHTML = calendarHTML;
    
    // Initialize tooltips
    const tooltips = container.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });
}
