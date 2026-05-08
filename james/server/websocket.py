"""
JAMES WebSocket Handler.

Real-time bidirectional communication for:
  - Agent chat with streaming responses
  - Live command output
  - Task status push notifications
"""

import asyncio
import logging
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect, Query

from james.core.agent import Agent
from james.server.auth import decode_jwt

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Track active WebSocket connections."""

    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
        logger.info("WS connected (%d active)", len(self.active))

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
        logger.info("WS disconnected (%d active)", len(self.active))

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.discard(ws)

    async def send(self, ws: WebSocket, message: dict):
        try:
            await ws.send_json(message)
        except Exception:
            self.active.discard(ws)


manager = ConnectionManager()


async def websocket_endpoint(ws: WebSocket, agent: Agent, jwt_secret: str, api_key_set: bool):
    """
    WebSocket handler.

    Protocol:
      Client sends JSON: {"type": "chat", "message": "scan 192.168.1.1"}
      Server responds:   {"type": "chat_response", "message": "..."}
      Server may push:   {"type": "task_update", "data": {...}}
                         {"type": "ping"}
    """
    # authenticate via query param token
    token = ws.query_params.get("token", "")
    if api_key_set and not decode_jwt(token, jwt_secret):
        await ws.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(ws)

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "chat":
                message = data.get("message", "")
                if message:
                    # send thinking indicator
                    await manager.send(ws, {"type": "thinking"})

                    # run agent in thread to avoid blocking
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None, agent.process, message
                    )

                    await manager.send(ws, {
                        "type": "chat_response",
                        "message": response,
                    })

            elif msg_type == "ping":
                await manager.send(ws, {"type": "pong"})

            elif msg_type == "shell":
                cmd = data.get("command", "")
                if cmd:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: agent.orch.layer.run(cmd, timeout=60),
                    )
                    await manager.send(ws, {
                        "type": "shell_response",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                    })

    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        logger.error("WS error: %s", e)
        manager.disconnect(ws)


def get_task_update_callback(loop: asyncio.AbstractEventLoop):
    """
    Return a callback the Orchestrator can use to push task updates
    to all connected WebSocket clients.
    """
    def callback(entry):
        try:
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({
                    "type": "task_update",
                    "data": entry.as_dict(),
                }),
                loop,
            )
        except Exception:
            pass
    return callback
