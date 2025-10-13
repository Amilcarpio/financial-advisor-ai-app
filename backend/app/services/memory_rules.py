"""
Memory Rules Engine - Evaluate user-defined rules against events.

Allows users to define rules like:
- "When a contact is created in HubSpot, send me an email"
- "When I receive an email from a VIP contact, create a high-priority task"
- "When a calendar event is created, sync it to HubSpot"
"""

import logging
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.memory_rule import MemoryRule
from app.models.task import Task
from app.models.user import User

logger = logging.getLogger(__name__)


class RuleEvaluator:
    """
    Evaluates rules against events and triggers actions.
    
    Rules syntax (simplified for MVP):
    - "when {event_type} then {action}"
    - event_type: hubspot.contact.creation, gmail.message.received, etc.
    - action: create_task, send_email, create_contact, etc.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def parse_rule(self, rule_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse rule text into structured format.
        
        Supports two formats:
        1. Structured: "when hubspot.contact.creation then create_task priority=high"
        2. Natural language: "When someone emails me that is not in HubSpot, create a contact"
        
        For natural language, the rule is treated as an LLM instruction
        and will be passed to the LLM for interpretation at runtime.
        
        Returns: {
            "trigger": "event_type" or "*" (for natural language rules),
            "action": "call_llm" (for natural language),
            "params": {"instruction": "original rule text"}
        }
        """
        # Try structured format first
        pattern = r"when\s+(\S+)\s+then\s+(\S+)(?:\s+(.+))?"
        match = re.match(pattern, rule_text.strip(), re.IGNORECASE)
        
        if match:
            # Structured format parsed successfully
            trigger = match.group(1)
            action = match.group(2)
            params_str = match.group(3) or ""
            
            # Parse params: key=value key2=value2
            params = {}
            if params_str:
                for param in params_str.split():
                    if "=" in param:
                        key, value = param.split("=", 1)
                        params[key] = value
            
            return {
                "trigger": trigger,
                "action": action,
                "params": params
            }
        
        # Natural language format - treat as LLM instruction
        # These rules match ANY event and delegate decision to LLM
        logger.info(f"Treating as natural language rule (will use LLM): {rule_text[:50]}...")
        return {
            "trigger": "*",  # Matches all events
            "action": "call_llm",
            "params": {
                "instruction": rule_text,
                "rule_type": "natural_language"
            }
        }
    
    def matches_event(self, rule_trigger: str, event_type: str) -> bool:
        """
        Check if rule trigger matches event type.
        
        Supports wildcards:
        - "*" matches all events (for natural language rules)
        - "hubspot.*" matches any HubSpot event
        - "gmail.message.*" matches any Gmail message event
        """
        # Wildcard "*" matches everything
        if rule_trigger == "*":
            return True
        
        # Convert wildcard to regex
        pattern = rule_trigger.replace(".", r"\.").replace("*", ".*")
        return bool(re.match(f"^{pattern}$", event_type, re.IGNORECASE))
    
    async def execute_action(
        self,
        user: User,
        action: str,
        params: Dict[str, Any],
        event_data: Dict[str, Any]
    ) -> None:
        """
        Execute rule action.
        
        Supported actions:
        - create_task: Create a task for the worker
        - call_llm: Create a task for LLM to process proactively
        - log: Just log the event
        """
        if action == "create_task":
            # Create task based on rule
            priority_map = {"high": 3, "medium": 2, "low": 1}
            priority = priority_map.get(params.get("priority", "medium"), 2)
            
            task_type = params.get("type", "generic")
            
            task = Task(
                user_id=user.id,
                task_type=task_type,
                payload={
                    "rule_triggered": True,
                    "event_data": event_data,
                    "params": params
                },
                state="pending",
                priority=priority,
                max_attempts=3
            )
            self.db.add(task)
            self.db.commit()
            
            logger.info(
                f"Created task {task.id} for user {user.id} "
                f"from rule action: {action}"
            )
        
        elif action == "call_llm":
            # Create task for LLM to process proactively
            priority_map = {"high": 3, "medium": 2, "low": 1}
            priority = priority_map.get(params.get("priority", "medium"), 2)
            
            # Get parent task ID if provided
            parent_task_id = params.get("parent_task_id")
            
            task = Task(
                user_id=user.id,
                task_type="llm_process_event",
                parent_task_id=parent_task_id,
                payload={
                    "rule_triggered": True,
                    "event_data": event_data,
                    "params": params,
                    "instruction": params.get("instruction", "Review this event and take appropriate action if needed.")
                },
                state="pending",
                priority=priority,
                max_attempts=3
            )
            self.db.add(task)
            self.db.commit()
            
            logger.info(
                f"Created LLM processing task {task.id} for user {user.id} "
                f"from rule action: {action}"
            )
        
        elif action == "log":
            # Just log the event
            logger.info(
                f"Rule triggered for user {user.id}: {action} with params {params}"
            )
        
        else:
            logger.warning(f"Unknown rule action: {action}")
    
    async def evaluate_rules(
        self,
        user: User,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> int:
        """
        Evaluate all active rules for user against event.
        
        Returns: Number of rules triggered
        """
        # Get active rules for user
        rules = self.db.scalars(
            select(MemoryRule)
            .where(MemoryRule.user_id == user.id)
            .where(MemoryRule.is_active == True)
        ).all()
        
        triggered_count = 0
        
        for rule in rules:
            # Parse rule
            parsed = self.parse_rule(rule.rule_text)
            if not parsed:
                continue
            
            # Check if rule matches event
            if not self.matches_event(parsed["trigger"], event_type):
                continue
            
            logger.info(
                f"Rule {rule.id} triggered for user {user.id}: "
                f"{rule.rule_text}"
            )
            
            # Execute action
            try:
                await self.execute_action(
                    user=user,
                    action=parsed["action"],
                    params=parsed["params"],
                    event_data=event_data
                )
                triggered_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to execute rule {rule.id} action: {e}",
                    exc_info=True
                )
        
        return triggered_count


async def evaluate_rules_for_event(
    db: Session,
    user: User,
    event_type: str,
    event_data: Dict[str, Any],
    create_fallback_task: bool = True
) -> int:
    """
    Convenience function to evaluate rules for an event.
    
    Args:
        db: Database session
        user: User who owns the rules
        event_type: Type of event (e.g., "hubspot.contact.creation")
        event_data: Event payload data
        create_fallback_task: If True and no rules match, create a generic
                             task for LLM to review proactively
    
    Returns:
        Number of rules triggered (or 1 if fallback task created)
    """
    evaluator = RuleEvaluator(db)
    triggered_count = await evaluator.evaluate_rules(user, event_type, event_data)
    
    # If no rules were triggered and fallback is enabled, create generic task
    # This enables proactive agent behavior even without explicit rules
    if triggered_count == 0 and create_fallback_task:
        # Only create fallback for certain event types to avoid noise
        proactive_event_types = [
            "gmail.message.received",
            "hubspot.contact.creation",
            "calendar.event.created",
        ]
        
        # Check if this event type should trigger proactive review
        should_review = any(
            event_type.startswith(et) or event_type == et 
            for et in proactive_event_types
        )
        
        if should_review:
            logger.info(
                f"No rules matched for {event_type}, creating fallback task "
                f"for proactive LLM review"
            )
            
            task = Task(
                user_id=user.id,
                task_type="llm_process_event",
                payload={
                    "event_type": event_type,
                    "event_data": event_data,
                    "instruction": (
                        "A new event occurred. Please review and take appropriate "
                        "action if needed."
                    ),
                    "fallback_task": True
                },
                state="pending",
                priority=1,  # Lower priority for proactive reviews
                max_attempts=2  # Fewer retries for optional tasks
            )
            db.add(task)
            db.commit()
            
            logger.info(f"Created fallback task {task.id} for event {event_type}")
            return 1
    
    return triggered_count


def create_default_rules(db: Session, user: User) -> List[MemoryRule]:
    """
    Create default rules for new users.
    
    These provide examples and useful starting points.
    """
    if not user.id:
        raise ValueError("User must have an ID")
    
    default_rules = [
        {
            "rule_text": "when hubspot.contact.creation then log",
            "description": "Log when new contacts are created in HubSpot"
        },
        {
            "rule_text": "when gmail.message.received then create_task type=process_email priority=medium",
            "description": "Create task to process new emails"
        }
    ]
    
    created_rules = []
    for rule_config in default_rules:
        rule = MemoryRule(
            user_id=user.id,
            rule_text=rule_config["rule_text"],
            is_active=False  # Disabled by default, user must enable
        )
        db.add(rule)
        created_rules.append(rule)
    
    db.commit()
    
    logger.info(f"Created {len(created_rules)} default rules for user {user.id}")
    return created_rules
