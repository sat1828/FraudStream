"""WebSocket endpoint for real-time transaction streaming with JWT auth."""

import uuid

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.core.config import settings
from app.core.websocket_manager import manager

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.websocket("/ws/live")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """Real-time transaction stream via WebSocket. Requires valid JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_email = payload.get("sub")
        if not user_email:
            await websocket.close(code=4001, reason="Invalid token: no subject")
            return
    except JWTError:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    client_id = f"{user_email}:{uuid.uuid4()}"
    connected = await manager.connect(websocket, client_id)
    if not connected:
        await websocket.close(code=4002, reason="Connection limit reached")
        return

    try:
        await websocket.send_json({
            "event_type": "connected",
            "payload": {
                "client_id": client_id,
                "message": "Connected to UPI Fraud Detection stream",
            },
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        })

        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info("WebSocket client disconnected", client_id=client_id)
    except Exception as e:
        manager.disconnect(client_id)
        logger.error("WebSocket error", client_id=client_id, error=str(e))
