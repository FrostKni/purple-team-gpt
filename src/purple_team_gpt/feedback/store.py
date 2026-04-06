"""SQLite storage for feedback entries using SQLModel.

This module provides the FeedbackStore class for managing feedback
data in a SQLite database with async support.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from sqlmodel import Session, SQLModel, create_engine, func, select

from purple_team_gpt.feedback.models import (
    AgentType,
    FeedbackEntry,
    FeedbackStats,
    FeedbackUpdate,
)

logger = logging.getLogger(__name__)


class FeedbackStore:
    """SQLite-based storage for feedback entries.
    
    Provides CRUD operations and statistics for feedback data.
    Uses SQLModel for ORM and SQLite for persistence.
    """
    
    def __init__(self, db_path: str = "./data/feedback.db"):
        """Initialize the feedback store.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._ensure_directory()
        self.engine = create_engine(f"sqlite:///{db_path}")
        self._create_tables()
        logger.info(f"FeedbackStore initialized with database: {db_path}")
    
    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
    
    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        SQLModel.metadata.create_all(self.engine)
    
    def add_feedback(self, entry: FeedbackEntry) -> FeedbackEntry:
        """Add a new feedback entry.
        
        Args:
            entry: The feedback entry to add.
            
        Returns:
            The created feedback entry with ID.
        """
        with Session(self.engine) as session:
            session.add(entry)
            session.commit()
            session.refresh(entry)
            logger.info(f"Added feedback entry {entry.id} for session {entry.session_id}")
            return entry
    
    def get_feedback(self, feedback_id: int) -> Optional[FeedbackEntry]:
        """Get a feedback entry by ID.
        
        Args:
            feedback_id: The ID of the feedback entry.
            
        Returns:
            The feedback entry or None if not found.
        """
        with Session(self.engine) as session:
            return session.get(FeedbackEntry, feedback_id)
    
    def get_feedback_by_interaction(
        self, session_id: str, interaction_id: str
    ) -> Optional[FeedbackEntry]:
        """Get feedback for a specific interaction.
        
        Args:
            session_id: The session ID.
            interaction_id: The interaction ID.
            
        Returns:
            The feedback entry or None if not found.
        """
        with Session(self.engine) as session:
            statement = select(FeedbackEntry).where(
                FeedbackEntry.session_id == session_id,
                FeedbackEntry.interaction_id == interaction_id,
            )
            return session.exec(statement).first()
    
    def update_feedback(
        self, feedback_id: int, update: FeedbackUpdate
    ) -> Optional[FeedbackEntry]:
        """Update an existing feedback entry.
        
        Args:
            feedback_id: The ID of the feedback to update.
            update: The update data.
            
        Returns:
            The updated feedback entry or None if not found.
        """
        with Session(self.engine) as session:
            entry = session.get(FeedbackEntry, feedback_id)
            if not entry:
                return None
            
            if update.rating is not None:
                entry.rating = update.rating
            if update.comment is not None:
                entry.comment = update.comment
            
            session.add(entry)
            session.commit()
            session.refresh(entry)
            logger.info(f"Updated feedback entry {feedback_id}")
            return entry
    
    def delete_feedback(self, feedback_id: int) -> bool:
        """Delete a feedback entry.
        
        Args:
            feedback_id: The ID of the feedback to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        with Session(self.engine) as session:
            entry = session.get(FeedbackEntry, feedback_id)
            if not entry:
                return False
            
            session.delete(entry)
            session.commit()
            logger.info(f"Deleted feedback entry {feedback_id}")
            return True
    
    def list_feedback(
        self,
        session_id: Optional[str] = None,
        agent_type: Optional[AgentType] = None,
        min_rating: Optional[int] = None,
        max_rating: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FeedbackEntry]:
        """List feedback entries with optional filters.
        
        Args:
            session_id: Filter by session ID.
            agent_type: Filter by agent type.
            min_rating: Minimum rating filter.
            max_rating: Maximum rating filter.
            limit: Maximum number of results.
            offset: Offset for pagination.
            
        Returns:
            List of feedback entries.
        """
        with Session(self.engine) as session:
            statement = select(FeedbackEntry)
            
            if session_id:
                statement = statement.where(FeedbackEntry.session_id == session_id)
            if agent_type:
                statement = statement.where(FeedbackEntry.agent_type == agent_type)
            if min_rating is not None:
                statement = statement.where(FeedbackEntry.rating >= min_rating)
            if max_rating is not None:
                statement = statement.where(FeedbackEntry.rating <= max_rating)
            
            statement = statement.order_by(FeedbackEntry.created_at.desc())
            statement = statement.offset(offset).limit(limit)
            
            return list(session.exec(statement))
    
    def count_feedback(
        self,
        session_id: Optional[str] = None,
        agent_type: Optional[AgentType] = None,
        min_rating: Optional[int] = None,
        max_rating: Optional[int] = None,
    ) -> int:
        """Count feedback entries with optional filters.
        
        Args:
            session_id: Filter by session ID.
            agent_type: Filter by agent type.
            min_rating: Minimum rating filter.
            max_rating: Maximum rating filter.
            
        Returns:
            Count of matching feedback entries.
        """
        with Session(self.engine) as session:
            statement = select(func.count(FeedbackEntry.id))
            
            if session_id:
                statement = statement.where(FeedbackEntry.session_id == session_id)
            if agent_type:
                statement = statement.where(FeedbackEntry.agent_type == agent_type)
            if min_rating is not None:
                statement = statement.where(FeedbackEntry.rating >= min_rating)
            if max_rating is not None:
                statement = statement.where(FeedbackEntry.rating <= max_rating)
            
            return session.exec(statement).one()
    
    def get_high_rated(self, min_rating: int = 4) -> list[FeedbackEntry]:
        """Get all high-rated feedback entries for fine-tuning.
        
        Args:
            min_rating: Minimum rating threshold (default 4).
            
        Returns:
            List of high-rated feedback entries.
        """
        with Session(self.engine) as session:
            statement = (
                select(FeedbackEntry)
                .where(FeedbackEntry.rating >= min_rating)
                .order_by(FeedbackEntry.created_at.desc())
            )
            return list(session.exec(statement))
    
    def get_stats(self) -> FeedbackStats:
        """Get statistics about feedback entries.
        
        Returns:
            FeedbackStats with aggregate statistics.
        """
        with Session(self.engine) as session:
            # Get all entries for stats calculation
            statement = select(FeedbackEntry)
            all_entries = list(session.exec(statement))
            
            if not all_entries:
                return FeedbackStats(
                    total_feedback=0,
                    average_rating=0.0,
                    rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                    by_agent_type={at.value: 0 for at in AgentType},
                    high_rated_count=0,
                )
            
            # Calculate statistics
            total = len(all_entries)
            avg_rating = sum(e.rating for e in all_entries) / total
            
            # Rating distribution
            rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for entry in all_entries:
                rating_dist[entry.rating] += 1
            
            # By agent type
            by_agent = {at.value: 0 for at in AgentType}
            for entry in all_entries:
                by_agent[entry.agent_type.value] += 1
            
            # High rated count
            high_rated = sum(1 for e in all_entries if e.rating >= 4)
            
            return FeedbackStats(
                total_feedback=total,
                average_rating=round(avg_rating, 2),
                rating_distribution=rating_dist,
                by_agent_type=by_agent,
                high_rated_count=high_rated,
            )
    
    def delete_session_feedback(self, session_id: str) -> int:
        """Delete all feedback for a session.
        
        Args:
            session_id: The session ID.
            
        Returns:
            Number of entries deleted.
        """
        with Session(self.engine) as session:
            statement = select(FeedbackEntry).where(
                FeedbackEntry.session_id == session_id
            )
            entries = list(session.exec(statement))
            count = len(entries)
            
            for entry in entries:
                session.delete(entry)
            
            session.commit()
            logger.info(f"Deleted {count} feedback entries for session {session_id}")
            return count