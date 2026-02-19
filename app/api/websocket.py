"""
WebSocket endpoint for real-time batch processing updates.
Connect to ws://host:8000/ws/batches to receive live progress.
"""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.batch_service import register_ws, unregister_ws
from app.utils.logger import setup_logger

logger = setup_logger("docvision.ws")
ws_router = APIRouter()


@ws_router.websocket("/ws/batches")
async def batch_progress_ws(websocket: WebSocket):
    """
    WebSocket endpoint for real-time batch processing updates.

    Messages sent to client:
    - {"type": "batch_update", "batch_id": "...", "status": "processing", ...}
    - {"type": "batch_complete", "batch_id": "...", ...}
    - {"type": "connected"}

    Client can send:
    - {"type": "ping"} → receives {"type": "pong"}
    """
    await websocket.accept()

    # Store the event loop on the websocket so background threads can broadcast
    websocket._loop = asyncio.get_event_loop()
    register_ws(websocket)

    logger.info("WebSocket client connected")

    try:
        await websocket.send_json({"type": "connected", "message": "Connected to batch progress stream"})

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        unregister_ws(websocket)