"""
Memory Rules API - CRUD endpoints for user-defined rules.

Routes:
- GET /api/rules - List all rules for authenticated user
- POST /api/rules - Create a new rule
- GET /api/rules/{rule_id} - Get a specific rule
- PUT /api/rules/{rule_id} - Update a rule
- DELETE /api/rules/{rule_id} - Delete a rule
"""

import logging
from typing import Any, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.utils.security import get_current_user_from_cookie
from app.models.memory_rule import MemoryRule
from app.models.user import User

router = APIRouter(prefix="/api/rules", tags=["rules"])

logger = logging.getLogger(__name__)


# Request/Response Models
class CreateRuleRequest(BaseModel):
    rule_text: str
    description: str | None = None
    is_active: bool = True


class UpdateRuleRequest(BaseModel):
    rule_text: str | None = None
    description: str | None = None
    is_active: bool | None = None


class RuleResponse(BaseModel):
    id: int
    rule_text: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Endpoints
@router.get("", response_model=List[RuleResponse])
async def list_rules(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_from_cookie),
) -> List[MemoryRule]:
    """List all memory rules for the authenticated user."""
    logger.info(f"Listing rules for user {current_user.id}")
    
    rules = db.scalars(
        select(MemoryRule)
        .where(MemoryRule.user_id == current_user.id)
        .order_by(MemoryRule.created_at.desc())
    ).all()
    
    return list(rules)


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: CreateRuleRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_from_cookie),
) -> MemoryRule:
    """Create a new memory rule."""
    logger.info(f"Creating rule for user {current_user.id}: {request.rule_text}")
    
    # Validate rule_text is not empty
    if not request.rule_text or not request.rule_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rule_text cannot be empty"
        )
    
    rule = MemoryRule(
        user_id=current_user.id,
        rule_text=request.rule_text.strip(),
        is_active=request.is_active,
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    from app.services.memory_rules import RuleEvaluator
    from app.core.config import settings
    from app.services.gmail_sync import GmailSyncService
    try:
        evaluator = RuleEvaluator(db)
        parsed = evaluator.parse_rule(rule.rule_text)
        is_gmail_rule = parsed and parsed.get("trigger", "").startswith("gmail.message.")
        if is_gmail_rule and rule.is_active and settings.google_pubsub_topic:
            
            if not current_user.google_history_id:
                gmail_service = GmailSyncService(user=current_user, db=db)
                response = gmail_service.setup_push_notifications(topic_name=settings.google_pubsub_topic)
                
                current_user.google_history_id = response.get("historyId")
                db.add(current_user)
                db.commit()
                logger.info(f"Auto-setup Gmail push notifications for user {current_user.id} after rule creation.")
            else:
                logger.info(f"Gmail watcher already active for user {current_user.id}, not creating new.")
    except Exception as e:
        logger.error(f"Failed to auto-setup Gmail push notifications: {e}")
    logger.info(f"Created rule {rule.id} for user {current_user.id}")
    return rule


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_from_cookie),
) -> MemoryRule:
    """Get a specific memory rule."""
    rule = db.get(MemoryRule, rule_id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    # Verify ownership
    if rule.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this rule"
        )
    
    return rule


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    request: UpdateRuleRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_from_cookie),
) -> MemoryRule:
    """Update a memory rule."""
    logger.info(f"Updating rule {rule_id} for user {current_user.id}")
    
    rule = db.get(MemoryRule, rule_id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    # Verify ownership
    if rule.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this rule"
        )
    
    # Update fields if provided
    if request.rule_text is not None:
        if not request.rule_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rule_text cannot be empty"
            )
        rule.rule_text = request.rule_text.strip()
    if request.is_active is not None:
        rule.is_active = request.is_active
    rule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rule)
    from app.services.memory_rules import RuleEvaluator
    from app.core.config import settings
    from app.services.gmail_sync import GmailSyncService
    try:
        evaluator = RuleEvaluator(db)
        parsed = evaluator.parse_rule(rule.rule_text)
        is_gmail_rule = parsed and parsed.get("trigger", "").startswith("gmail.message.")
        # If a Gmail rule was activated, ensure Gmail push notifications are set up
        if is_gmail_rule and rule.is_active and settings.google_pubsub_topic:
            if not current_user.google_history_id:
                gmail_service = GmailSyncService(user=current_user, db=db)
                response = gmail_service.setup_push_notifications(topic_name=settings.google_pubsub_topic)
                current_user.google_history_id = response.get("historyId")
                db.add(current_user)
                db.commit()
                logger.info(f"Auto-setup Gmail push notifications for user {current_user.id} after rule update.")
            else:
                logger.info(f"Gmail watcher already active for user {current_user.id}, not creating new.")
        # If a Gmail rule was deactivated, check if there are still other active ones
        if is_gmail_rule and not rule.is_active:
            # Count how many gmail.message.* active rules remain
            gmail_rules_ativas = db.scalars(
                select(MemoryRule).where(
                    MemoryRule.user_id == current_user.id,
                    MemoryRule.is_active == True
                )
            ).all()
            from app.services.memory_rules import RuleEvaluator
            gmail_count = 0
            for r in gmail_rules_ativas:
                parsed_r = RuleEvaluator(db).parse_rule(r.rule_text)
                if parsed_r and parsed_r.get("trigger", "").startswith("gmail.message."):
                    gmail_count += 1
            if gmail_count == 0 and current_user.google_history_id:
                gmail_service = GmailSyncService(user=current_user, db=db)
                gmail_service.stop_push_notifications()
                current_user.google_history_id = None
                db.add(current_user)
                db.commit()
                logger.info(f"Watcher Gmail removed for user {current_user.id} as there are no more active rules.")
    except Exception as e:
        logger.error(f"Failed to manage Gmail watcher: {e}")
    logger.info(f"Updated rule {rule_id}")
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user_from_cookie),
) -> None:
    """Delete a memory rule."""
    logger.info(f"Deleting rule {rule_id} for user {current_user.id}")
    
    rule = db.get(MemoryRule, rule_id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    # Verify ownership
    if rule.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this rule"
        )
    
    is_gmail_rule = False
    from app.services.memory_rules import RuleEvaluator
    try:
        evaluator = RuleEvaluator(db)
        parsed = evaluator.parse_rule(rule.rule_text)
        is_gmail_rule = parsed and parsed.get("trigger", "").startswith("gmail.message.")
    except Exception:
        pass
    db.delete(rule)
    db.commit()
    # After deleting, if it was a Gmail rule, check if there are still other active ones
    if is_gmail_rule:
        gmail_rules_ativas = db.scalars(
            select(MemoryRule).where(
                MemoryRule.user_id == current_user.id,
                MemoryRule.is_active == True
            )
        ).all()
        from app.services.memory_rules import RuleEvaluator
        gmail_count = 0
        for r in gmail_rules_ativas:
            parsed_r = RuleEvaluator(db).parse_rule(r.rule_text)
            if parsed_r and parsed_r.get("trigger", "").startswith("gmail.message."):
                gmail_count += 1
        if gmail_count == 0 and current_user.google_history_id:
            from app.services.gmail_sync import GmailSyncService
            gmail_service = GmailSyncService(user=current_user, db=db)
            gmail_service.stop_push_notifications()
            current_user.google_history_id = None
            db.add(current_user)
            db.commit()
            logger.info(f"Gmail watcher removed for user {current_user.id} after deleting the last Gmail rule.")
    logger.info(f"Deleted rule {rule_id}")


@router.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "rules-api"}
