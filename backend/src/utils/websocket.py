"""
WebSocket Connection Manager for real-time progress updates.

This module provides a connection manager for WebSocket connections,
enabling real-time progress updates during tool execution.

Usage:
    from backend.src.utils.websocket import ConnectionManager

    # Create singleton instance
    manager = ConnectionManager()

    # In WebSocket endpoint
    await manager.connect(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)

    # Broadcast progress from tool service
    await manager.broadcast(job_id, {"stage": "scanning", "percentage": 50})
"""

import asyncio
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from backend.src.utils.logging_config import get_logger

logger = get_logger("websocket")


class ConnectionManager:
    """
    Manages WebSocket connections for job progress broadcasting.

    Maintains a mapping of job IDs to sets of connected WebSocket clients,
    enabling multiple clients to monitor the same job simultaneously.

    Also supports a global "jobs" channel for broadcasting all job updates
    to clients monitoring the jobs list (e.g., Tools page).
    """

    # Special channel ID for global job updates
    GLOBAL_JOBS_CHANNEL = "__global_jobs__"

    def __init__(self):
        """Initialize the connection manager with empty connection registry."""
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        """
        Accept and register a WebSocket connection for a job.

        Args:
            job_id: Unique identifier for the job to monitor
            websocket: WebSocket connection to register

        Note:
            Multiple connections per job are supported for multi-tab/multi-client scenarios.
        """
        await websocket.accept()
        async with self._lock:
            if job_id not in self._connections:
                self._connections[job_id] = set()
            self._connections[job_id].add(websocket)
            logger.debug(
                f"WebSocket connected for job {job_id}. "
                f"Total connections for job: {len(self._connections[job_id])}"
            )

    def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        """
        Unregister a WebSocket connection.

        Args:
            job_id: Job identifier the connection was monitoring
            websocket: WebSocket connection to remove

        Note:
            This method is synchronous for use in exception handlers.
            Thread-safe removal is handled by discarding from the set.
        """
        if job_id in self._connections:
            self._connections[job_id].discard(websocket)
            logger.debug(
                f"WebSocket disconnected for job {job_id}. "
                f"Remaining connections: {len(self._connections[job_id])}"
            )
            # Clean up empty connection sets
            if not self._connections[job_id]:
                del self._connections[job_id]

    async def broadcast(self, job_id: str, data: Dict[str, Any]) -> None:
        """
        Broadcast a message to all clients monitoring a job.

        Args:
            job_id: Job identifier to broadcast to
            data: Dictionary data to send as JSON

        Note:
            Failed connections are silently removed.
            Broadcast continues to all valid connections.
        """
        if job_id not in self._connections:
            return

        # Copy set to avoid modification during iteration
        connections = self._connections[job_id].copy()
        disconnected: Set[WebSocket] = set()

        for connection in connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.debug(f"Failed to send to WebSocket: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(job_id, conn)

    async def broadcast_global_job_update(self, job_data: Dict[str, Any]) -> None:
        """
        Broadcast a job update to all clients monitoring the global jobs channel.

        This is used to push job status changes to clients watching the Tools page
        without requiring polling.

        Args:
            job_data: Job data to broadcast (typically the full job object)
        """
        await self.broadcast(self.GLOBAL_JOBS_CHANNEL, {
            "type": "job_update",
            "job": job_data
        })

    async def send_personal(
        self, job_id: str, websocket: WebSocket, data: Dict[str, Any]
    ) -> bool:
        """
        Send a message to a specific WebSocket connection.

        Args:
            job_id: Job identifier the connection is monitoring
            websocket: Specific WebSocket to send to
            data: Dictionary data to send as JSON

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.debug(f"Failed to send personal message: {e}")
            self.disconnect(job_id, websocket)
            return False

    def get_connection_count(self, job_id: Optional[str] = None) -> int:
        """
        Get the number of active connections.

        Args:
            job_id: Optional job ID to get connections for.
                   If None, returns total connections across all jobs.

        Returns:
            Number of active WebSocket connections
        """
        if job_id:
            return len(self._connections.get(job_id, set()))
        return sum(len(conns) for conns in self._connections.values())

    def get_monitored_jobs(self) -> Set[str]:
        """
        Get set of job IDs currently being monitored.

        Returns:
            Set of job IDs with active connections
        """
        return set(self._connections.keys())

    async def close_all_for_job(self, job_id: str, reason: str = "Job completed") -> None:
        """
        Close all connections for a specific job.

        Args:
            job_id: Job identifier to close connections for
            reason: Reason message to send before closing

        Note:
            Sends a final status message before closing connections.
        """
        if job_id not in self._connections:
            return

        # Send completion message
        await self.broadcast(job_id, {"status": "closed", "reason": reason})

        # Close all connections
        connections = self._connections.get(job_id, set()).copy()
        for connection in connections:
            try:
                await connection.close()
            except Exception:
                pass  # Connection may already be closed

        # Clean up
        if job_id in self._connections:
            del self._connections[job_id]
        logger.debug(f"Closed all WebSocket connections for job {job_id}")


# Singleton instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """
    Get the singleton ConnectionManager instance.

    Returns:
        The global ConnectionManager instance

    Note:
        Creates the instance on first call.
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
