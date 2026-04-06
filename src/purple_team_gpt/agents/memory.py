"""Agent memory persistence for learning across sessions."""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentLearning:
    """A learned pattern or technique."""

    pattern: str
    context: str
    success: bool
    tool_used: Optional[str] = None
    outcome: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class AgentMemory:
    """Persist agent state and learnings across sessions."""

    def __init__(self, agent_id: str, vector_store, collection_name: str = "agent_memory"):
        self.agent_id = agent_id
        self.vector_store = vector_store
        self.collection_name = collection_name
        self._sessions: Dict[str, Dict] = {}

    async def save_session(self, session_id: str, state: Dict[str, Any]) -> None:
        """Save agent state at end of session."""
        self._sessions[session_id] = {
            **state,
            "agent_id": self.agent_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Agent {self.agent_id} saved session {session_id}")

    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load previous session state."""
        return self._sessions.get(session_id)

    async def save_learning(self, learning: AgentLearning) -> None:
        """Store a learned pattern for future use."""
        document = (
            f"Pattern: {learning.pattern}\nContext: {learning.context}\nSuccess: {learning.success}"
        )
        await self.vector_store.add(
            collection_name=self.collection_name,
            documents=[document],
            metadatas=[
                {
                    "agent_id": self.agent_id,
                    "pattern": learning.pattern,
                    "success": learning.success,
                    "tool": learning.tool_used or "",
                    "outcome": learning.outcome or "",
                }
            ],
        )
        logger.info(f"Agent {self.agent_id} saved learning")

    async def get_relevant_learnings(self, context: str, n_results: int = 5) -> List[AgentLearning]:
        """Retrieve learnings relevant to current context."""
        try:
            results = await self.vector_store.query(
                collection_name=self.collection_name,
                query_text=context,
                n_results=n_results,
                where={"agent_id": self.agent_id},
            )
            learnings = []
            for doc, meta in zip(results.get("documents", []), results.get("metadatas", [])):
                learnings.append(
                    AgentLearning(
                        pattern=meta.get("pattern", ""),
                        context=doc,
                        success=meta.get("success", False),
                        tool_used=meta.get("tool"),
                        outcome=meta.get("outcome"),
                    )
                )
            return learnings
        except Exception as e:
            logger.warning(f"Failed to retrieve learnings: {e}")
            return []
