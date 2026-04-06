"""WebSocket endpoints for real-time updates.

This module provides WebSocket support for:
- Real-time session event streaming
- Live agent step and finding updates
- Bidirectional communication for feedback
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from purple_team_gpt.core.orchestrator import AgentEvent, PurpleOrchestrator
from purple_team_gpt.core.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter()


# Global references - set by main.py during lifespan
_orchestrator: Optional[PurpleOrchestrator] = None
_vector_store: Optional[VectorStore] = None


def set_dependencies(orch: PurpleOrchestrator, vs: VectorStore) -> None:
    """Set the orchestrator and vector store references.

    Called by main.py during application startup.
    Registers a single persistent event callback on the orchestrator
    so all WebSocket clients receive events via the ConnectionManager.
    """
    global _orchestrator, _vector_store
    _orchestrator = orch
    _vector_store = vs

    # Register a single persistent callback that broadcasts to all connected clients.
    # This avoids the per-connection callback overwrite race condition.
    def _global_on_event(event: AgentEvent) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(manager.broadcast_event(event.session_id, event))
        except RuntimeError:
            logger.warning(f"No event loop for global event callback: {event.event_type}")

    orch.on_event = _global_on_event


def get_orchestrator() -> PurpleOrchestrator:
    """Get the orchestrator instance."""
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized")
    return _orchestrator


def get_vector_store() -> Optional[VectorStore]:
    """Get the vector store instance."""
    return _vector_store


class ConnectionManager:
    """Manages WebSocket connections per session.

    Allows multiple clients to connect to the same session
    and broadcasts events to all connected clients.
    """

    def __init__(self):
        """Initialize the connection manager."""
        # Map of session_id -> list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept a new WebSocket connection for a session.

        Args:
            websocket: The WebSocket connection
            session_id: The session to subscribe to
        """
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = []

        self.active_connections[session_id].append(websocket)

        logger.debug(f"WebSocket connected to session {session_id}")

        # Send initial connection confirmation
        await websocket.send_json(
            {
                "type": "connected",
                "session_id": session_id,
                "message": f"Connected to session {session_id}",
            }
        )

    def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: The WebSocket to disconnect
            session_id: The session the WebSocket was connected to
        """
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)

            # Clean up empty session entries
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

        logger.debug(f"WebSocket disconnected from session {session_id}")

    async def broadcast(self, session_id: str, message: dict) -> None:
        """Broadcast a message to all connections for a session.

        Args:
            session_id: The session to broadcast to
            message: The message to send
        """
        if session_id not in self.active_connections:
            return

        # Send to all connections, removing any that fail
        disconnected = []

        for connection in self.active_connections[session_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to connection: {e}")
                disconnected.append(connection)

        # Clean up disconnected WebSockets
        for conn in disconnected:
            self.disconnect(conn, session_id)

    async def broadcast_event(self, session_id: str, event: AgentEvent) -> None:
        """Broadcast an agent event to all connections.

        Args:
            session_id: The session ID
            event: The agent event to broadcast
        """
        await self.broadcast(
            session_id,
            {
                "type": "event",
                "agent": event.agent,
                "event_type": event.event_type,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
            },
        )

    def get_connection_count(self, session_id: str) -> int:
        """Get the number of active connections for a session.

        Args:
            session_id: The session ID

        Returns:
            Number of active connections
        """
        return len(self.active_connections.get(session_id, []))

    def get_all_sessions(self) -> List[str]:
        """Get all session IDs with active connections.

        Returns:
            List of session IDs
        """
        return list(self.active_connections.keys())


# Global connection manager
manager = ConnectionManager()


@router.websocket("")
async def websocket_general(
    websocket: WebSocket,
    token: Optional[str] = None,
):
    """General WebSocket endpoint for connection status when no session is selected.

    Provides:
    - Connection confirmation
    - Server status updates
    - Heartbeat for connection keep-alive

    Authentication: Pass JWT token via query parameter 'token'
    """
    from purple_team_gpt.backend.security import verify_token

    await websocket.accept()

    # Authenticate WebSocket connection
    if not token:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Authentication required. Provide token query parameter.",
            }
        )
        await websocket.close()
        return

    try:
        user_payload = verify_token(token)
    except Exception as e:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Authentication failed: {str(e)}",
            }
        )
        await websocket.close()
        return

    # Send connection confirmation
    await websocket.send_json(
        {
            "type": "connected",
            "message": "Connected to Purple Team GPT",
            "user": user_payload.get("sub", "unknown"),
        }
    )

    try:
        while True:
            # Wait for any message (heartbeat/keepalive)
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                # Respond to ping with pong
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        logger.info(f"General WebSocket disconnected for user {user_payload.get('sub', 'unknown')}")
    except Exception as e:
        logger.error(f"General WebSocket error: {e}")


@router.websocket("/session/{session_id}")
async def websocket_session(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None,
):
    """WebSocket endpoint for session updates.

    Provides real-time updates for:
    - Agent steps and actions
    - Findings from Red and Blue agents
    - Session status changes
    - Output messages

    Also accepts incoming messages for:
    - Feedback submission
    - Pause/resume commands

    Authentication: Pass JWT token via query parameter 'token'
    """
    from purple_team_gpt.backend.security import verify_token, validate_session_id

    # Validate session ID format
    try:
        session_id = validate_session_id(session_id)
    except Exception as e:
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Invalid session ID: {str(e)}",
            }
        )
        await websocket.close()
        return

    # Authenticate WebSocket connection
    if not token:
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "error",
                "message": "Authentication required. Provide token query parameter.",
            }
        )
        await websocket.close()
        return

    try:
        user_payload = verify_token(token)
    except Exception as e:
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Authentication failed: {str(e)}",
            }
        )
        await websocket.close()
        return

    try:
        orch = get_orchestrator()
    except RuntimeError:
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "error",
                "message": "Orchestrator not initialized",
            }
        )
        await websocket.close()
        return

    # Check if session exists
    session = orch.get_session(session_id)
    if not session:
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Session {session_id} not found",
            }
        )
        await websocket.close()
        return

    # Connect to the session
    await manager.connect(websocket, session_id)

    # Send connection confirmation with user info
    await websocket.send_json(
        {
            "type": "connected",
            "session_id": session_id,
            "message": f"Connected to session {session_id}",
            "user": user_payload.get("sub", "unknown"),
        }
    )

    # Send current session state
    await websocket.send_json(
        {
            "type": "session_state",
            "session": session.to_dict(),
        }
    )

    try:
        # Main message loop
        while True:
            # Wait for incoming messages
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type", "unknown")

                # Handle different message types
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif message_type == "feedback":
                    # Handle feedback submission
                    await handle_feedback(session_id, message, websocket)

                elif message_type == "command":
                    # Handle commands
                    await handle_command(session_id, message, websocket, orch)

                elif message_type == "get_metrics":
                    # Send current metrics
                    metrics = orch.get_metrics(session_id)
                    await websocket.send_json(
                        {
                            "type": "metrics",
                            "data": metrics,
                        }
                    )

                else:
                    # Unknown message type
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                        }
                    )

            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Invalid JSON message",
                    }
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        logger.info(f"WebSocket disconnected from session {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, session_id)


async def handle_feedback(session_id: str, message: dict, websocket: WebSocket) -> None:
    """Handle feedback submission from WebSocket.

    Stores feedback in the vector store for learning.

    Args:
        session_id: The session ID
        message: The feedback message
        websocket: The WebSocket connection
    """
    feedback_type = message.get("feedback_type", "general")
    content = message.get("content", "")
    rating = message.get("rating")
    metadata = message.get("metadata", {})

    if not content:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Feedback content required",
            }
        )
        return

    # Store feedback in vector store
    vs = get_vector_store()
    if vs:
        try:
            doc_id = await vs.store_feedback(
                content=content,
                feedback_type=feedback_type,
                rating=rating,
                metadata={
                    "session_id": session_id,
                    **metadata,
                },
            )

            await websocket.send_json(
                {
                    "type": "feedback_stored",
                    "doc_id": doc_id,
                    "message": "Feedback stored successfully",
                }
            )

            logger.info(f"Stored feedback for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to store feedback: {e}")
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Failed to store feedback: {str(e)}",
                }
            )
    else:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Vector store not available",
            }
        )


async def handle_command(
    session_id: str,
    message: dict,
    websocket: WebSocket,
    orch: PurpleOrchestrator,
) -> None:
    """Handle command messages from WebSocket.

    Supports commands:
    - pause: Pause the session
    - resume: Resume a paused session
    - stop: Stop the session

    Args:
        session_id: The session ID
        message: The command message
        websocket: The WebSocket connection
        orch: The orchestrator instance
    """
    command = message.get("command", "").lower()

    if command == "pause":
        if orch.pause_session(session_id):
            await websocket.send_json(
                {
                    "type": "command_result",
                    "command": "pause",
                    "success": True,
                    "message": "Session paused",
                }
            )
        else:
            await websocket.send_json(
                {
                    "type": "command_result",
                    "command": "pause",
                    "success": False,
                    "message": "Failed to pause session",
                }
            )

    elif command == "resume":
        if orch.resume_session(session_id):
            await websocket.send_json(
                {
                    "type": "command_result",
                    "command": "resume",
                    "success": True,
                    "message": "Session resumed",
                }
            )
        else:
            await websocket.send_json(
                {
                    "type": "command_result",
                    "command": "resume",
                    "success": False,
                    "message": "Failed to resume session",
                }
            )

    elif command == "stop":
        session = orch.stop_session(session_id)
        if session:
            await websocket.send_json(
                {
                    "type": "command_result",
                    "command": "stop",
                    "success": True,
                    "message": "Session stopped",
                    "session": session.to_dict(),
                }
            )
        else:
            await websocket.send_json(
                {
                    "type": "command_result",
                    "command": "stop",
                    "success": False,
                    "message": "Failed to stop session",
                }
            )

    else:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Unknown command: {command}",
            }
        )


@router.get("/status")
async def websocket_status() -> dict:
    """Get WebSocket connection status.

    Returns information about active WebSocket connections.
    """
    return {
        "active_sessions": manager.get_all_sessions(),
        "connections_per_session": {
            session_id: manager.get_connection_count(session_id)
            for session_id in manager.get_all_sessions()
        },
    }
