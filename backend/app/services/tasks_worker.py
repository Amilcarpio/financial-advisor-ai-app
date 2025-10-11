"""
Background task worker for processing asynchronous jobs.

This worker:
- Polls the Task table for pending tasks
- Acquires DB row-level locks to prevent duplicate processing
- Executes tasks with state machine transitions
- Implements retry logic with exponential backoff
- Handles graceful shutdown
- Reclaims orphaned tasks on startup
"""

import asyncio
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional, Any
import json
import logging

from sqlmodel import Session, select, or_
from sqlalchemy import text

from app.core.database import engine
from app.models.task import Task
from app.models.user import User
from app.services.tools import execute_tool, ToolExecutionError


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TaskWorker:
    """
    Background worker that processes tasks from the database.
    
    Features:
    - Polling with configurable interval
    - DB row-level locking for concurrency safety
    - Exponential backoff retry logic
    - Graceful shutdown handling
    - Orphaned task recovery
    """
    
    def __init__(
        self,
        poll_interval: int = 5,
        max_concurrent_tasks: int = 10,
        lock_timeout: int = 300,  # 5 minutes
    ):
        """
        Initialize the task worker.
        
        Args:
            poll_interval: Seconds between polling cycles
            max_concurrent_tasks: Maximum tasks to process concurrently
            lock_timeout: Seconds before considering a locked task orphaned
        """
        self.poll_interval = poll_interval
        self.max_concurrent_tasks = max_concurrent_tasks
        self.lock_timeout = lock_timeout
        self.running = False
        self.tasks_in_progress = 0
        
    def start(self) -> None:
        """Start the worker (blocking call)."""
        self.running = True
        logger.info("Task worker starting...")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Reclaim orphaned tasks on startup
        self._reclaim_orphaned_tasks()
        
        # Start polling loop
        asyncio.run(self._poll_loop())
        
    def stop(self) -> None:
        """Stop the worker gracefully."""
        logger.info("Task worker stopping...")
        self.running = False
        
    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)
        
    def _reclaim_orphaned_tasks(self) -> None:
        """
        Reclaim tasks that were locked but never completed.
        This handles cases where the worker crashed mid-execution.
        """
        try:
            with Session(engine) as db:
                # Find tasks locked longer than timeout
                timeout_threshold = datetime.utcnow() - timedelta(seconds=self.lock_timeout)
                
                orphaned_tasks = db.exec(
                    select(Task).where(
                        Task.state == "in_progress",
                        Task.locked_at != None,  # type: ignore
                        Task.locked_at < timeout_threshold,  # type: ignore
                    )
                ).all()
                
                if orphaned_tasks:
                    logger.info(f"Reclaiming {len(orphaned_tasks)} orphaned tasks")
                    
                    for task in orphaned_tasks:
                        task.state = "pending"
                        task.locked_at = None
                        task.touch()
                        db.add(task)
                    
                    db.commit()
                    
        except Exception as e:
            logger.error(f"Error reclaiming orphaned tasks: {e}")
            
    async def _poll_loop(self) -> None:
        """Main polling loop."""
        logger.info(f"Worker polling every {self.poll_interval} seconds")
        
        while self.running:
            try:
                # Check if we can process more tasks
                if self.tasks_in_progress < self.max_concurrent_tasks:
                    # Try to acquire and process a task
                    await self._process_next_task()
                
                # Wait before next poll
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in poll loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
                
    async def _process_next_task(self) -> None:
        """Acquire and process the next available task."""
        task = self._acquire_task()
        
        if task:
            self.tasks_in_progress += 1
            try:
                await self._execute_task(task)
            finally:
                self.tasks_in_progress -= 1
                
    def _acquire_task(self) -> Optional[Task]:
        """
        Acquire a task using DB row-level locking.
        
        Returns:
            Task if acquired, None if no tasks available
        """
        try:
            with Session(engine) as db:
                # Use SELECT FOR UPDATE SKIP LOCKED for concurrency
                # This ensures only one worker gets each task
                query = text(
                    """
                    SELECT * FROM task
                    WHERE state = 'pending'
                    AND (scheduled_for IS NULL OR scheduled_for <= :now)
                    AND attempts < max_attempts
                    ORDER BY priority DESC, scheduled_for ASC, created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                    """
                )
                
                result = db.execute(query, {"now": datetime.utcnow()})  # type: ignore
                
                row = result.fetchone()
                if not row:
                    return None
                
                # Get the task and lock it
                task = db.get(Task, row[0])  # row[0] is the id
                if not task:
                    return None
                
                task.state = "in_progress"
                task.locked_at = datetime.utcnow()
                task.attempts += 1
                task.last_attempt_at = datetime.utcnow()
                task.touch()
                
                db.add(task)
                db.commit()
                db.refresh(task)
                
                logger.info(f"Acquired task {task.id} (type: {task.task_type}, attempt: {task.attempts})")
                return task
                
        except Exception as e:
            logger.error(f"Error acquiring task: {e}")
            return None
            
    async def _execute_task(self, task: Task) -> None:
        """
        Execute a task and update its state.
        
        Args:
            task: Task to execute
        """
        try:
            logger.info(f"Executing task {task.id} (type: {task.task_type})")
            
            # Get user for the task
            with Session(engine) as db:
                user = db.get(User, task.user_id)
                if not user:
                    raise Exception(f"User {task.user_id} not found")
                
                # Parse payload
                payload = task.payload if isinstance(task.payload, dict) else {}
                
                # Execute based on task type
                if task.task_type in ["send_email", "schedule_event", "find_contact", "create_contact"]:
                    # Execute tool
                    result = await execute_tool(
                        tool_name=task.task_type,
                        arguments=payload,
                        user=user,
                        db=db,
                    )
                    
                    # Mark as completed
                    task.state = "done"
                    task.result = result
                    task.completed_at = datetime.utcnow()
                    task.locked_at = None
                    task.touch()
                    
                    db.add(task)
                    db.commit()
                    
                    logger.info(f"Task {task.id} completed successfully")
                    
                else:
                    raise Exception(f"Unknown task type: {task.task_type}")
                    
        except ToolExecutionError as e:
            logger.error(f"Tool execution error for task {task.id}: {e}")
            await self._handle_task_failure(task, str(e))
            
        except Exception as e:
            logger.error(f"Error executing task {task.id}: {e}", exc_info=True)
            await self._handle_task_failure(task, str(e))
            
    async def _handle_task_failure(self, task: Task, error: str) -> None:
        """
        Handle task failure with retry logic.
        
        Args:
            task: Failed task
            error: Error message
        """
        try:
            with Session(engine) as db:
                # Refresh task to get latest state
                db_task = db.get(Task, task.id)
                if not db_task:
                    return
                
                db_task.last_error = error
                db_task.locked_at = None
                
                # Check if we should retry
                if db_task.attempts < db_task.max_attempts:
                    # Calculate backoff delay (exponential: 2^attempts minutes)
                    backoff_minutes = 2 ** db_task.attempts
                    db_task.scheduled_for = datetime.utcnow() + timedelta(minutes=backoff_minutes)
                    db_task.state = "pending"
                    db_task.touch()
                    
                    logger.info(
                        f"Task {task.id} will retry in {backoff_minutes} minutes "
                        f"(attempt {db_task.attempts}/{db_task.max_attempts})"
                    )
                else:
                    # Max attempts reached, mark as failed
                    db_task.state = "failed"
                    db_task.completed_at = datetime.utcnow()
                    db_task.touch()
                    
                    logger.error(
                        f"Task {task.id} failed permanently after {db_task.attempts} attempts: {error}"
                    )
                
                db.add(db_task)
                db.commit()
                
        except Exception as e:
            logger.error(f"Error handling task failure: {e}")
            

def main() -> None:
    """Main entry point for the worker."""
    logger.info("Starting task worker...")
    
    worker = TaskWorker(
        poll_interval=5,
        max_concurrent_tasks=10,
        lock_timeout=300,
    )
    
    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker crashed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        worker.stop()
        logger.info("Worker stopped")


if __name__ == "__main__":
    main()

