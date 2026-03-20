"""Feedback management endpoints.

This module provides REST endpoints for:
- Submitting feedback on agent interactions
- Retrieving and updating feedback
- Getting feedback statistics
- Exporting fine-tuning data
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from purple_team_gpt.feedback.models import (
    AgentType,
    FeedbackCreate,
    FeedbackEntry,
    FeedbackListResponse,
    FeedbackResponse,
    FeedbackStats,
    FeedbackUpdate,
)
from purple_team_gpt.feedback.store import FeedbackStore
from purple_team_gpt.feedback.export import export_fine_tuning_data

logger = logging.getLogger(__name__)

router = APIRouter()

# Global store reference - set by main.py during lifespan
_store: Optional[FeedbackStore] = None


def set_feedback_store(store: FeedbackStore) -> None:
    """Set the feedback store reference.
    
    Called by main.py during application startup.
    """
    global _store
    _store = store


def get_store() -> FeedbackStore:
    """Get the feedback store instance.
    
    Raises HTTPException if store is not initialized.
    """
    if _store is None:
        raise HTTPException(status_code=503, detail="Feedback store not initialized")
    return _store


@router.post("/", response_model=FeedbackResponse, status_code=201)
async def create_feedback(data: FeedbackCreate) -> FeedbackResponse:
    """Submit feedback for an agent interaction.
    
    Creates a new feedback entry with rating and optional comment.
    """
    store = get_store()
    
    # Check if feedback already exists for this interaction
    existing = store.get_feedback_by_interaction(
        data.session_id, data.interaction_id
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Feedback already exists for this interaction. Use PUT to update.",
        )
    
    entry = FeedbackEntry(
        session_id=data.session_id,
        interaction_id=data.interaction_id,
        agent_type=data.agent_type,
        prompt=data.prompt,
        response=data.response,
        rating=data.rating,
        comment=data.comment,
        user_id=data.user_id,
        context=data.context,
    )
    
    created = store.add_feedback(entry)
    logger.info(
        f"Created feedback {created.id} for interaction {data.interaction_id} "
        f"in session {data.session_id}"
    )
    
    return FeedbackResponse(
        id=created.id,
        session_id=created.session_id,
        interaction_id=created.interaction_id,
        agent_type=created.agent_type,
        prompt=created.prompt,
        response=created.response,
        rating=created.rating,
        comment=created.comment,
        created_at=created.created_at,
        user_id=created.user_id,
    )


@router.get("/", response_model=FeedbackListResponse)
async def list_feedback(
    session_id: Optional[str] = None,
    agent_type: Optional[AgentType] = None,
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    max_rating: Optional[int] = Query(None, ge=1, le=5),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> FeedbackListResponse:
    """List feedback entries with optional filters.
    
    Returns paginated feedback entries.
    """
    store = get_store()
    
    offset = (page - 1) * page_size
    
    entries = store.list_feedback(
        session_id=session_id,
        agent_type=agent_type,
        min_rating=min_rating,
        max_rating=max_rating,
        limit=page_size,
        offset=offset,
    )
    
    total = store.count_feedback(
        session_id=session_id,
        agent_type=agent_type,
        min_rating=min_rating,
        max_rating=max_rating,
    )
    
    return FeedbackListResponse(
        feedback=[
            FeedbackResponse(
                id=e.id,
                session_id=e.session_id,
                interaction_id=e.interaction_id,
                agent_type=e.agent_type,
                prompt=e.prompt,
                response=e.response,
                rating=e.rating,
                comment=e.comment,
                created_at=e.created_at,
                user_id=e.user_id,
            )
            for e in entries
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats() -> FeedbackStats:
    """Get feedback statistics.
    
    Returns aggregate statistics about all feedback entries.
    """
    store = get_store()
    return store.get_stats()


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(feedback_id: int) -> FeedbackResponse:
    """Get a specific feedback entry by ID.
    """
    store = get_store()
    entry = store.get_feedback(feedback_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return FeedbackResponse(
        id=entry.id,
        session_id=entry.session_id,
        interaction_id=entry.interaction_id,
        agent_type=entry.agent_type,
        prompt=entry.prompt,
        response=entry.response,
        rating=entry.rating,
        comment=entry.comment,
        created_at=entry.created_at,
        user_id=entry.user_id,
    )


@router.put("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: int,
    data: FeedbackUpdate,
) -> FeedbackResponse:
    """Update an existing feedback entry.
    
    Updates rating and/or comment for an existing feedback entry.
    """
    store = get_store()
    entry = store.update_feedback(feedback_id, data)
    
    if not entry:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    logger.info(f"Updated feedback {feedback_id}")
    
    return FeedbackResponse(
        id=entry.id,
        session_id=entry.session_id,
        interaction_id=entry.interaction_id,
        agent_type=entry.agent_type,
        prompt=entry.prompt,
        response=entry.response,
        rating=entry.rating,
        comment=entry.comment,
        created_at=entry.created_at,
        user_id=entry.user_id,
    )


@router.delete("/{feedback_id}")
async def delete_feedback(feedback_id: int) -> dict:
    """Delete a feedback entry.
    """
    store = get_store()
    
    if not store.delete_feedback(feedback_id):
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    logger.info(f"Deleted feedback {feedback_id}")
    
    return {"message": "Feedback deleted", "id": feedback_id}


@router.post("/export")
async def export_feedback(
    min_rating: int = Query(4, ge=1, le=5, description="Minimum rating threshold"),
    agent_type: Optional[AgentType] = Query(None, description="Filter by agent type"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    output_path: str = Query(
        "./data/finetuning/feedback_export.jsonl",
        description="Output file path",
    ),
) -> dict:
    """Export high-rated feedback to JSONL for fine-tuning.
    
    Exports feedback entries with rating >= min_rating to JSONL format
    suitable for LLM fine-tuning.
    """
    store = get_store()
    
    result = export_fine_tuning_data(
        store=store,
        output_path=output_path,
        min_rating=min_rating,
        agent_type=agent_type,
        session_id=session_id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    logger.info(f"Exported {result['count']} feedback entries to {output_path}")
    
    return result


@router.delete("/session/{session_id}")
async def delete_session_feedback(session_id: str) -> dict:
    """Delete all feedback for a session.
    
    Removes all feedback entries associated with the specified session.
    """
    store = get_store()
    count = store.delete_session_feedback(session_id)
    
    return {
        "message": f"Deleted all feedback for session",
        "session_id": session_id,
        "count": count,
    }