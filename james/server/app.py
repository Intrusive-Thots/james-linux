"""
JAMES FastAPI Application.

Wires together routes, WebSocket, auth, and static file serving.
"""

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from james.core.orchestrator import Orchestrator
from james.core.agent import Agent
from james.server.config import load_config, ServerConfig
from james.server.auth import AuthManager
from james.server.routes import router as api_router, setup_routes
from james.server.websocket import websocket_endpoint, get_task_update_callback

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def create_app(config: ServerConfig = None) -> FastAPI:
    """Factory function to create the FastAPI application."""
    if config is None:
        config = load_config()

    app = FastAPI(
        title="JAMES Linux",
        description="Autonomous AI Pentesting Agent — Remote API",
        version="0.2.0",
        docs_url="/docs",
        redoc_url=None,
    )

    # ── CORS ────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── shared instances ────────────────────────────────────────
    orchestrator = Orchestrator()
    agent = Agent(orchestrator)
    auth = AuthManager(config)

    # ── REST routes ─────────────────────────────────────────────
    setup_routes(api_router, orchestrator, agent, auth, config)
    app.include_router(api_router)

    # ── WebSocket ───────────────────────────────────────────────
    @app.websocket("/ws")
    async def ws_route(ws: WebSocket):
        await websocket_endpoint(
            ws, agent, config.jwt_secret, bool(config.api_key)
        )

    # ── task update broadcast ───────────────────────────────────
    @app.on_event("startup")
    async def on_startup():
        loop = asyncio.get_event_loop()
        orchestrator.on_task_update = get_task_update_callback(loop)
        logger.info("JAMES server started on %s:%d", config.host, config.port)

    # ── static web dashboard ────────────────────────────────────
    if WEB_DIR.exists():
        # serve index.html at root
        @app.get("/")
        async def serve_index():
            return FileResponse(WEB_DIR / "index.html")

        # serve other static files
        app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

        # PWA files at root level
        for fname in ["manifest.json", "sw.js"]:
            fpath = WEB_DIR / fname
            if fpath.exists():
                @app.get(f"/{fname}")
                async def serve_pwa_file(p=fpath):
                    return FileResponse(p)

    return app
