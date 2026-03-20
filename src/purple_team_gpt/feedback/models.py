"""SQLModel models for human feedback storage.

This module defines the database models for storing human feedback
on agent interactions, including ratings, comments, and metadata.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class AgentType(str, Enum):
    """Type of agent that generated the interaction."""
    
    RED = "red"
    BLUE = "blue"
    ORCHESTRATOR = "orchestrator"


class FeedbackEntry(SQLModel, table=True):
    """Feedback entry for an agent interaction.
    
    Stores human feedback including star ratings (1-5) and optional comments.
    High-rated interactions (4-5 stars) can be exported for fine-tuning.
    """
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Session and interaction identification
    session_id: str = Field(index=True, description="ID of the simulation session")
    interaction_id: str = Field(index=True, description="Unique ID for the interaction")
    agent_type: AgentType = Field(description="Type of agent (red/blue/orchestrator)")
    
    # Interaction content
    prompt: str = Field(description="The input prompt/question")
    response: str = Field(description="The agent's response")
    
    # Feedback data
    rating: int = Field(ge=1, le=5, description="Star rating from 1-5")
    comment: Optional[str] = Field(default=None, description="Optional user comment")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When feedback was submitted")
    user_id: Optional[str] = Field(default=None, description="Optional user identifier")
    
    # Additional context
    context: Optional[str] = Field(default=None, description="Additional context (JSON)")
    
    class Config:
        """SQLModel configuration."""
        json_schema_extra = {
            "example": {
                "session_id": "session-123",
                "interaction_id": "interaction-456",
                "agent_type": "red",
                "prompt": "What are the potential vulnerabilities in this network?",
                "response": "Based on the scan results, I identified...",
                "rating": 5,
                "comment": "Excellent analysis, very thorough",
                "user_id": "analyst-1",
                "context": "{\"target\": \"192.168.1.0/24\", \"scan_type\": \"full\"}"
            }
        }


class FeedbackCreate(SQLModel):
    """Request model for creating new feedback."""
    
    session_id: str
    interaction_id: str
    agent_type: AgentType
    prompt: str
    response: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[str] = None


class FeedbackUpdate(SQLModel):
    """Request model for updating existing feedback."""
    
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None


class FeedbackResponse(SQLModel):
    """Response model for feedback data."""
    
    id: int
    session_id: str
    interaction_id: str
    agent_type: AgentType
    prompt: str
    response: str
    rating: int
    comment: Optional[str]
    created_at: datetime
    user_id: Optional[str]


class FeedbackListResponse(SQLModel):
    """Response model for paginated feedback list."""
    
    feedback: list[FeedbackResponse]
    total: int
    page: int
    page_size: int


class FeedbackStats(SQLModel):
    """Statistics about feedback entries."""
    
    total_feedback: int
    average_rating: float
    rating_distribution: dict[int, int]
    by_agent_type: dict[str, int]
    high_rated_count: int