/**
 * Workflow functionality for Document Management System
 */

document.addEventListener('DOMContentLoaded', () => {
    initWorkflowPage();
});

/**
 * Initialize the workflow page
 */
function initWorkflowPage() {
    // Setup workflow creation form if present
    setupWorkflowCreationForm();
    
    // Setup task completion functionality
    setupTaskCompletion();
    
    // Initialize the workflow diagram if present
    initWorkflowDiagram();
}

/**
 * Setup workflow creation form with dynamic task addition
 */
function setupWorkflowCreationForm() {
    const workflowForm = document.getElementById('workflowCreationForm');
    if (!workflowForm) return;
    
    // Setup add task button
    const addTaskButton = document.getElementById('addTaskButton');
    if (addTaskButton) {
        addTaskButton.addEventListener('click', addNewTask);
    }
    
    // Setup task removal buttons
    setupTaskRemovalButtons();
    
    // Form validation before submission
    workflowForm.addEventListener('submit', function(e) {
        if (!validateWorkflowForm()) {
            e.preventDefault();
        }
    });
}

/**
 * Add a new task input to the workflow creation form
 */
function addNewTask() {
    const tasksContainer = document.getElementById('tasksContainer');
    const taskCount = tasksContainer.querySelectorAll('.task-item').length + 1;
    
    // Create new task template
    const taskTemplate = `
        <div class="task-item card mb-3" id="task-${taskCount}">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Task #${taskCount}</h5>
                <button type="button" class="btn btn-sm btn-danger remove-task" data-task-id="${taskCount}">
                    <i class="bi bi-trash"></i> Remove
                </button>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <label for="task_name_${taskCount}" class="form-label">Task Name*</label>
                    <input type="text" class="form-control" id="task_name_${taskCount}" name="task_name_${taskCount}" required>
                </div>
                <div class="mb-3">
                    <label for="task_description_${taskCount}" class="form-label">Description</label>
                    <textarea class="form-control" id="task_description_${taskCount}" name="task_description_${taskCount}" rows="2"></textarea>
                </div>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="task_assigned_to_${taskCount}" class="form-label">Assigned To*</label>
                        <select class="form-select" id="task_assigned_to_${taskCount}" name="task_assigned_to_${taskCount}" required>
                            <option value="">Select User</option>
                            ${getUserOptions()}
                        </select>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="task_due_date_${taskCount}" class="form-label">Due Date</label>
                        <input type="date" class="form-control" id="task_due_date_${taskCount}" name="task_due_date_${taskCount}">
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add to the DOM
    tasksContainer.insertAdjacentHTML('beforeend', taskTemplate);
    
    // Setup the remove button for this new task
    setupTaskRemovalButtons();
}

/**
 * Setup task removal buttons
 */
function setupTaskRemovalButtons() {
    const removeButtons = document.querySelectorAll('.remove-task');
    removeButtons.forEach(button => {
        // Remove existing event listeners to prevent duplicates
        button.removeEventListener('click', handleTaskRemoval);
        // Add new event listener
        button.addEventListener('click', handleTaskRemoval);
    });
}

/**
 * Handle task removal
 */
function handleTaskRemoval(e) {
    const taskId = this.dataset.taskId;
    const taskElement = document.getElementById(`task-${taskId}`);
    
    if (taskElement) {
        taskElement.remove();
        
        // Renumber remaining tasks
        const taskItems = document.querySelectorAll('.task-item');
        taskItems.forEach((item, index) => {
            const newIndex = index + 1;
            item.id = `task-${newIndex}`;
            item.querySelector('h5').textContent = `Task #${newIndex}`;
            item.querySelector('.remove-task').dataset.taskId = newIndex;
            
            // Update input names and IDs
            const inputs = item.querySelectorAll('input, textarea, select');
            inputs.forEach(input => {
                const baseName = input.name.split('_').slice(0, -1).join('_');
                input.name = `${baseName}_${newIndex}`;
                input.id = `${baseName}_${newIndex}`;
                
                // Update corresponding labels
                const label = item.querySelector(`label[for="${input.id.replace(newIndex, index + 1)}"]`);
                if (label) {
                    label.setAttribute('for', input.id);
                }
            });
        });
    }
}

/**
 * Get options for user selection in task assignment
 */
function getUserOptions() {
    // Get users from the hidden data element if available
    const usersData = document.getElementById('usersData');
    if (!usersData) return '';
    
    try {
        const users = JSON.parse(usersData.textContent);
        return users.map(user => {
            const displayName = user.first_name && user.last_name ? 
                `${user.username} (${user.first_name} ${user.last_name})` : user.username;
            return `<option value="${user.id}">${displayName}</option>`;
        }).join('');
    } catch (e) {
        console.error('Error parsing users data:', e);
        return '';
    }
}

/**
 * Validate the workflow creation form
 */
function validateWorkflowForm() {
    const workflowName = document.getElementById('workflow_name').value.trim();
    
    if (!workflowName) {
        showToast('Workflow name is required', 'danger');
        return false;
    }
    
    const taskItems = document.querySelectorAll('.task-item');
    if (taskItems.length === 0) {
        showToast('At least one task is required', 'danger');
        return false;
    }
    
    // Check if all required fields in tasks are filled
    let isValid = true;
    taskItems.forEach((item, index) => {
        const taskNum = index + 1;
        const taskName = document.getElementById(`task_name_${taskNum}`).value.trim();
        const assignedTo = document.getElementById(`task_assigned_to_${taskNum}`).value;
        
        if (!taskName) {
            showToast(`Task #${taskNum}: Name is required`, 'danger');
            isValid = false;
        }
        
        if (!assignedTo) {
            showToast(`Task #${taskNum}: Assigned user is required`, 'danger');
            isValid = false;
        }
    });
    
    return isValid;
}

/**
 * Setup task completion functionality
 */
function setupTaskCompletion() {
    // Setup approve task buttons
    const approveButtons = document.querySelectorAll('.btn-approve-task');
    approveButtons.forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.dataset.taskId;
            const taskForm = document.getElementById(`completeTaskForm-${taskId}`);
            if (taskForm) {
                const actionInput = taskForm.querySelector('input[name="action"]');
                if (actionInput) {
                    actionInput.value = 'approve';
                    taskForm.submit();
                }
            }
        });
    });
    
    // Setup reject task buttons
    const rejectButtons = document.querySelectorAll('.btn-reject-task');
    rejectButtons.forEach(button => {
        button.addEventListener('click', function() {
            const taskId = this.dataset.taskId;
            const taskForm = document.getElementById(`completeTaskForm-${taskId}`);
            if (taskForm) {
                const actionInput = taskForm.querySelector('input[name="action"]');
                if (actionInput) {
                    actionInput.value = 'reject';
                    taskForm.submit();
                }
            }
        });
    });
}

/**
 * Initialize the workflow diagram visualization
 */
function initWorkflowDiagram() {
    const workflowDiagram = document.getElementById('workflowDiagram');
    if (!workflowDiagram) return;
    
    try {
        // Get workflow tasks data from the hidden element
        const tasksDataElement = document.getElementById('workflowTasksData');
        if (!tasksDataElement) return;
        
        const tasks = JSON.parse(tasksDataElement.textContent);
        
        // Create SVG diagram
        const diagramWidth = workflowDiagram.clientWidth;
        const taskWidth = 180;
        const taskHeight = 80;
        const taskMargin = 40;
        const totalWidth = tasks.length * (taskWidth + taskMargin);
        const startX = (diagramWidth - totalWidth) / 2;
        
        let svgHtml = `
            <svg width="100%" height="150" class="workflow-svg">
                <defs>
                    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="0" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#adb5bd" />
                    </marker>
                </defs>
                <g>
        `;
        
        // Add tasks and connectors
        tasks.forEach((task, index) => {
            const x = startX + index * (taskWidth + taskMargin);
            const statusColor = getStatusColor(task.status);
            
            // Add task box
            svgHtml += `
                <g transform="translate(${x},10)">
                    <rect width="${taskWidth}" height="${taskHeight}" rx="5" ry="5" 
                        fill="none" stroke="${statusColor}" stroke-width="2" />
                    <text x="10" y="25" font-size="14" fill="currentColor">${task.name}</text>
                    <text x="10" y="45" font-size="12" fill="#6c757d">${task.assignedToUsername || 'Unassigned'}</text>
                    <text x="10" y="65" font-size="12" fill="${statusColor}">Status: ${task.status}</text>
                </g>
            `;
            
            // Add connector arrow if not the last task
            if (index < tasks.length - 1) {
                const startX = x + taskWidth;
                const endX = x + taskWidth + taskMargin;
                svgHtml += `
                    <line x1="${startX}" y1="${taskHeight/2 + 10}" x2="${endX}" y2="${taskHeight/2 + 10}" 
                        stroke="#adb5bd" stroke-width="2" marker-end="url(#arrowhead)" />
                `;
            }
        });
        
        svgHtml += `</g></svg>`;
        workflowDiagram.innerHTML = svgHtml;
    } catch (e) {
        console.error('Error creating workflow diagram:', e);
        workflowDiagram.innerHTML = '<div class="alert alert-danger">Error creating workflow diagram</div>';
    }
}

/**
 * Get color for task status
 */
function getStatusColor(status) {
    switch (status.toLowerCase()) {
        case 'complete':
            return '#198754'; // Green
        case 'rejected':
        case 'cancelled':
            return '#dc3545'; // Red
        case 'in_progress':
            return '#0d6efd'; // Blue
        case 'pending':
        default:
            return '#6c757d'; // Gray
    }
}
