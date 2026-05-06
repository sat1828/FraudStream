"""WebSocket connection manager with connection limits and proper cleanup."""

import asyncio
from typing import Dict

import structlog
from fastapi import WebSocket

from app.core.config import settings

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections with broadcast support."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._broadcast_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        if len(self.active_connections) >= settings.MAX_WS_CONNECTIONS:
            logger.warning(
                "WebSocket connection limit reached",
                current=len(self.active_connections),
                limit=settings.MAX_WS_CONNECTIONS,
            )
            return False

        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(
            "WebSocket connected",
            client_id=client_id,
            total=len(self.active_connections),
        )
        return True

    def disconnect(self, client_id: str) -> None:
        ws = self.active_connections.pop(client_id, None)
        if ws:
            try:
                # Fire-and-forget close
                asyncio.create_task(ws.close())
            except Exception:
                pass
        logger.info(
            "WebSocket disconnected",
            client_id=client_id,
            total=len(self.active_connections),
        )

    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return

        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(client_id)

        for client_id in disconnected:
            self.disconnect(client_id)

    async def enqueue(self, message: dict) -> None:
        """Add message to broadcast queue (non-blocking)."""
        try:
            self._message_queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning("WebSocket message queue full, dropping message")

    async def start_broadcast_loop(self) -> None:
        """Start the background broadcast task."""
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_loop_impl())
            logger.info("WebSocket broadcast loop started")

    async def stop_broadcast_loop(self) -> None:
        """Stop the background broadcast task."""
        if self._broadcast_task and not self._broadcast_task.done():
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
            logger.info("WebSocket broadcast loop stopped")

    async def _broadcast_loop_impl(self) -> None:
        while True:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(), timeout=1.0
                )
                await self.broadcast(message)
                self._message_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Broadcast loop error", error=str(e))
                await asyncio.sleep(0.1)

    async def close_all(self) -> None:
        """Close all active connections."""
        for client_id in list(self.active_connections.keys()):
            self.disconnect(client_id)


manager = ConnectionManager()
