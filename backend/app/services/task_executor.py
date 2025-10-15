"""
Task execution utility for immediate (synchronous) processing of tasks.
Reuses logic from the background worker, but callable directly from API/webhooks.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.user import User
from app.services.gmail_sync import GmailSyncService
from app.services.calendar_sync import CalendarSyncService
from app.services.embedding_pipeline import EmbeddingPipeline
from app.services.tools import execute_tool, ToolExecutionError
from app.services.memory_rules import evaluate_rules_for_event
from app.core.database import engine

logger = logging.getLogger(__name__)

async def execute_task_now(task: Task, db: Session) -> None:
    """
    Execute a task immediately and update its state/result in the DB.
    Args:
        task: Task instance (must be added to session)
        db: SQLAlchemy session
    """
    try:
        user = db.get(User, task.user_id)
        if not user:
            raise Exception(f"User {task.user_id} not found")
        payload = task.payload if isinstance(task.payload, dict) else {}

        if task.task_type == "gmail_sync":
            gmail_service = GmailSyncService(user=user, db=db)
            sync_result = gmail_service.sync(max_results=50)
            if sync_result.get("new_emails", 0) > 0:
                embedding_pipeline = EmbeddingPipeline(db=db)
                embedding_stats = embedding_pipeline.process_emails(user_id=user.id, batch_size=50)
                logger.info(f"Generated embeddings for Gmail sync: {embedding_stats}")
            if sync_result.get("new_emails", 0) > 0:
                try:
                    triggered = await evaluate_rules_for_event(
                        db=db,
                        user=user,
                        event_type="gmail.message.received",
                        event_data={
                            "history_id": payload.get("history_id"),
                            "new_count": sync_result.get("new_emails", 0),
                            "sync_result": sync_result
                        }
                    )
                    logger.info(f"Gmail sync triggered {triggered} memory rules")
                except Exception as e:
                    logger.error(f"Failed to evaluate memory rules: {e}")
            task.state = "completed"
            task.result = sync_result
            task.completed_at = datetime.utcnow()
            task.locked_at = None
            task.touch()
            db.add(task)
            db.commit()
            logger.info(f"Gmail sync task {task.id} completed: {sync_result}")

        elif task.task_type == "calendar_sync":
            calendar_service = CalendarSyncService(user=user, db=db)
            sync_result = calendar_service.sync(max_results=50)
            if sync_result.get("new_events", 0) > 0 or sync_result.get("updated_events", 0) > 0:
                try:
                    event_type = "calendar.event.created" if sync_result.get("new_events", 0) > 0 else "calendar.event.updated"
                    triggered = await evaluate_rules_for_event(
                        db=db,
                        user=user,
                        event_type=event_type,
                        event_data={
                            "channel_id": payload.get("channel_id"),
                            "resource_state": payload.get("resource_state"),
                            "new_count": sync_result.get("new_events", 0),
                            "updated_count": sync_result.get("updated_events", 0),
                            "sync_result": sync_result
                        }
                    )
                    logger.info(f"Calendar sync triggered {triggered} memory rules")
                except Exception as e:
                    logger.error(f"Failed to evaluate memory rules: {e}")
            task.state = "completed"
            task.result = sync_result
            task.completed_at = datetime.utcnow()
            task.locked_at = None
            task.touch()
            db.add(task)
            db.commit()
            logger.info(f"Calendar sync task {task.id} completed: {sync_result}")

        elif task.task_type in ["send_email", "schedule_event", "find_contact", "create_contact"]:
            result = await execute_tool(
                tool_name=task.task_type,
                arguments=payload,
                user=user,
                db=db,
            )
            task.state = "completed"
            task.result = result
            task.completed_at = datetime.utcnow()
            task.locked_at = None
            task.touch()
            db.add(task)
            db.commit()
            logger.info(f"Task {task.id} completed successfully")

        elif task.task_type in ["llm_process_event", "generic", "process_email"]:
            from app.services.tasks_worker import TaskWorker
            worker = TaskWorker()
            await worker._process_event_with_llm(task, user, db, payload)
            # _process_event_with_llm already updates task state/result
        else:
            raise Exception(f"Unknown task type: {task.task_type}")

    except ToolExecutionError as e:
        logger.error(f"Tool execution error for task {task.id}: {e}")
        await handle_task_failure_now(task, str(e), db)
    except Exception as e:
        logger.error(f"Error executing task {task.id}: {e}", exc_info=True)
        await handle_task_failure_now(task, str(e), db)

async def handle_task_failure_now(task: Task, error: str, db: Session) -> None:
    """
    Mark task as failed and persist error.
    """
    task.last_error = error
    task.locked_at = None
    task.state = "failed"
    task.completed_at = datetime.utcnow()
    task.touch()
    db.add(task)
    db.commit()
