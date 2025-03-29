import datetime
from flask import current_app
from app import db
from models import Workflow, WorkflowTask, Document, Notification, User
from sqlalchemy.exc import SQLAlchemyError

def create_workflow(name, description, created_by_id, document_id=None, tasks=None):
    """
    Create a new workflow with tasks.
    
    Args:
        name: Workflow name
        description: Workflow description
        created_by_id: User ID of creator
        document_id: Optional document ID to associate with workflow
        tasks: List of task dictionaries with name, description, assigned_to_id, etc.
        
    Returns:
        Newly created Workflow object
    """
    try:
        # Create the workflow
        workflow = Workflow(
            name=name,
            description=description,
            created_by_id=created_by_id
        )
        
        db.session.add(workflow)
        db.session.flush()  # Flush to get the workflow ID for tasks
        
        # Associate document with workflow if provided
        if document_id:
            document = Document.query.get(document_id)
            if document:
                document.workflow_id = workflow.id
        
        # Create tasks for the workflow
        if tasks:
            for task_data in tasks:
                due_date = None
                if task_data.get('due_date'):
                    try:
                        due_date = datetime.datetime.strptime(task_data['due_date'], '%Y-%m-%d')
                    except ValueError:
                        current_app.logger.warning(f"Invalid due date format: {task_data['due_date']}")
                
                task = WorkflowTask(
                    workflow_id=workflow.id,
                    name=task_data['name'],
                    description=task_data.get('description', ''),
                    order=task_data.get('order', 1),
                    assigned_to_id=task_data.get('assigned_to_id'),
                    due_date=due_date
                )
                
                db.session.add(task)
                
                # Create notification for assigned user
                if task.assigned_to_id:
                    notification = Notification(
                        user_id=task.assigned_to_id,
                        message=f"You have been assigned to task '{task.name}' in workflow '{workflow.name}'."
                    )
                    db.session.add(notification)
        
        db.session.commit()
        return workflow
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating workflow: {str(e)}")
        raise

def assign_workflow_task(task_id, user_id, due_date=None):
    """
    Assign a workflow task to a user.
    
    Args:
        task_id: ID of the task to assign
        user_id: ID of the user to assign the task to
        due_date: Optional due date for the task
        
    Returns:
        Updated WorkflowTask object
    """
    try:
        task = WorkflowTask.query.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        
        # Update task assignment
        task.assigned_to_id = user_id
        
        if due_date:
            # Convert string date to datetime if needed
            if isinstance(due_date, str):
                task.due_date = datetime.datetime.strptime(due_date, '%Y-%m-%d')
            else:
                task.due_date = due_date
        
        # Create notification for assigned user
        if user_id:
            workflow = Workflow.query.get(task.workflow_id)
            notification = Notification(
                user_id=user_id,
                message=f"You have been assigned to task '{task.name}' in workflow '{workflow.name}'."
            )
            db.session.add(notification)
        
        db.session.commit()
        return task
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error assigning workflow task: {str(e)}")
        raise

def complete_workflow_task(task_id, action='approve', comments=None):
    """
    Mark a workflow task as complete or rejected.
    
    Args:
        task_id: ID of the task to complete
        action: Either 'approve' or 'reject'
        comments: Optional comments about the completion
        
    Returns:
        Updated WorkflowTask object
    """
    try:
        task = WorkflowTask.query.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        
        # Update task status based on action
        if action.lower() == 'approve':
            task.status = 'complete'
        elif action.lower() == 'reject':
            task.status = 'rejected'
        else:
            raise ValueError(f"Invalid action '{action}'. Must be 'approve' or 'reject'.")
        
        task.completed_at = datetime.datetime.utcnow()
        
        if comments:
            task.comments = comments
        
        # Check if this is the last task and update workflow status
        workflow = Workflow.query.get(task.workflow_id)
        remaining_tasks = WorkflowTask.query.filter(
            WorkflowTask.workflow_id == workflow.id,
            WorkflowTask.status.in_(['pending', 'in_progress'])
        ).count()
        
        if remaining_tasks == 0:
            workflow.status = 'complete'
            
            # Notify workflow creator
            notification = Notification(
                user_id=workflow.created_by_id,
                message=f"Workflow '{workflow.name}' has been completed."
            )
            db.session.add(notification)
        
        # Find the next task in sequence if this was approved
        if action.lower() == 'approve':
            next_task = WorkflowTask.query.filter(
                WorkflowTask.workflow_id == workflow.id,
                WorkflowTask.order > task.order,
                WorkflowTask.status == 'pending'
            ).order_by(WorkflowTask.order).first()
            
            if next_task:
                next_task.status = 'in_progress'
                
                # Notify the assigned user of the next task
                if next_task.assigned_to_id:
                    notification = Notification(
                        user_id=next_task.assigned_to_id,
                        message=f"Your task '{next_task.name}' in workflow '{workflow.name}' is now ready to be worked on."
                    )
                    db.session.add(notification)
        
        db.session.commit()
        return task
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error completing workflow task: {str(e)}")
        raise

def cancel_workflow(workflow_id, reason=None):
    """
    Cancel a workflow and all its incomplete tasks.
    
    Args:
        workflow_id: ID of the workflow to cancel
        reason: Optional reason for cancellation
        
    Returns:
        Updated Workflow object
    """
    try:
        workflow = Workflow.query.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow with ID {workflow_id} not found")
        
        # Update workflow status
        workflow.status = 'cancelled'
        
        # Update all pending/in-progress tasks
        pending_tasks = WorkflowTask.query.filter(
            WorkflowTask.workflow_id == workflow_id,
            WorkflowTask.status.in_(['pending', 'in_progress'])
        ).all()
        
        for task in pending_tasks:
            task.status = 'cancelled'
            
            # Notify assigned users
            if task.assigned_to_id:
                notification = Notification(
                    user_id=task.assigned_to_id,
                    message=f"Task '{task.name}' in workflow '{workflow.name}' has been cancelled."
                )
                db.session.add(notification)
        
        db.session.commit()
        return workflow
    
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling workflow: {str(e)}")
        raise

def get_user_workflows(user_id):
    """
    Get all workflows where a user is involved (creator or task assignee).
    
    Args:
        user_id: User ID to find workflows for
        
    Returns:
        Dictionary with created_workflows and assigned_workflows
    """
    created_workflows = Workflow.query.filter_by(created_by_id=user_id).all()
    
    # Get workflow IDs where user is assigned to tasks
    workflow_ids = db.session.query(WorkflowTask.workflow_id).filter(
        WorkflowTask.assigned_to_id == user_id
    ).distinct().all()
    workflow_ids = [wf_id for (wf_id,) in workflow_ids]
    
    assigned_workflows = Workflow.query.filter(Workflow.id.in_(workflow_ids)).all()
    
    return {
        'created_workflows': created_workflows,
        'assigned_workflows': assigned_workflows
    }
