"""
JAMES REST API Routes.

All pentesting operations exposed as REST endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from james.core.orchestrator import Orchestrator
from james.core.agent import Agent
from james.server.auth import AuthManager, verify_api_key, create_jwt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── request/response models ────────────────────────────────────


class LoginRequest(BaseModel):
    api_key: str


class TokenResponse(BaseModel):
    token: str
    expires_in: int


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class TargetRequest(BaseModel):
    target: str
    ports: Optional[str] = None


class MonitorRequest(BaseModel):
    interface: str
    action: str = "enable"  # enable | disable


class DeauthRequest(BaseModel):
    interface: str
    bssid: str
    count: int = 10


class CrackWpaRequest(BaseModel):
    capture_file: str
    wordlist: str = "/home/malcolm/Desktop/rockyou.txt"
    bssid: Optional[str] = None


class CrackHashRequest(BaseModel):
    hash_file: str
    wordlist: str = "/home/malcolm/Desktop/rockyou.txt"
    hash_mode: int = 0


class AutoPwnRequest(BaseModel):
    interface: str
    wordlist: str = "/home/malcolm/Desktop/rockyou.txt"


class RunSkillRequest(BaseModel):
    name: str
    context: dict = {}


# ── route setup (called from app.py with dependencies) ──────────


def setup_routes(
    app_router: APIRouter,
    orchestrator: Orchestrator,
    agent: Agent,
    auth: AuthManager,
    config,
):
    """Register all routes with their dependencies."""

    # ── Auth ────────────────────────────────────────────────────

    @app_router.post("/auth/login", response_model=TokenResponse)
    async def login(req: LoginRequest):
        if not config.api_key:
            # no auth configured, return token anyway
            token = create_jwt(
                {"sub": "user"}, config.jwt_secret, config.jwt_expire_minutes
            )
            return TokenResponse(
                token=token, expires_in=config.jwt_expire_minutes * 60
            )

        if not verify_api_key(req.api_key, config.api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")

        token = create_jwt(
            {"sub": "user"}, config.jwt_secret, config.jwt_expire_minutes
        )
        return TokenResponse(
            token=token, expires_in=config.jwt_expire_minutes * 60
        )

    # ── Agent Chat ──────────────────────────────────────────────

    @app_router.post("/agent/chat", response_model=ChatResponse)
    async def agent_chat(req: ChatRequest, user=Depends(auth)):
        response = agent.process(req.message)
        return ChatResponse(response=response)

    # ── System ──────────────────────────────────────────────────

    @app_router.get("/system/status")
    async def system_status(user=Depends(auth)):
        return orchestrator.system_check()

    @app_router.get("/system/info")
    async def system_info(user=Depends(auth)):
        result = orchestrator.layer.run("uname -a", timeout=10)
        return {"uname": result.stdout.strip()}

    # ── Recon ───────────────────────────────────────────────────

    @app_router.post("/recon/quick")
    async def recon_quick(req: TargetRequest, user=Depends(auth)):
        return orchestrator.quick_recon(req.target)

    @app_router.post("/recon/full")
    async def recon_full(req: TargetRequest, user=Depends(auth)):
        ports = req.ports or "1-65535"
        return orchestrator.full_scan(req.target, ports)

    # ── Wi-Fi ───────────────────────────────────────────────────

    @app_router.get("/wifi/interfaces")
    async def wifi_interfaces(user=Depends(auth)):
        return orchestrator.wifi_interfaces()

    @app_router.post("/wifi/monitor")
    async def wifi_monitor(req: MonitorRequest, user=Depends(auth)):
        if req.action == "enable":
            return orchestrator.start_monitor(req.interface)
        else:
            return orchestrator.stop_monitor(req.interface)

    @app_router.post("/wifi/deauth")
    async def wifi_deauth(req: DeauthRequest, user=Depends(auth)):
        result = orchestrator.aircrack.deauth(
            req.interface, req.bssid, count=req.count
        )
        return result.as_dict()

    # ── Cracking ────────────────────────────────────────────────

    @app_router.post("/crack/wpa")
    async def crack_wpa(req: CrackWpaRequest, user=Depends(auth)):
        return orchestrator.crack_handshake(
            req.capture_file, req.wordlist, req.bssid
        )

    @app_router.post("/crack/hash")
    async def crack_hash(req: CrackHashRequest, user=Depends(auth)):
        return orchestrator.crack_hash(
            req.hash_file, req.wordlist, req.hash_mode
        )

    # ── AutoPwn ──────────────────────────────────────────────────

    @app_router.post("/wifi/autopwn")
    async def wifi_autopwn(req: AutoPwnRequest, user=Depends(auth)):
        import threading

        result_holder = {}
        error_holder = {}
        done_event = threading.Event()

        def _run():
            try:
                result_holder["data"] = orchestrator.auto_wifi_pwn(
                    req.interface, req.wordlist
                )
            except Exception as e:
                error_holder["error"] = str(e)
            done_event.set()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        # For now return immediately; the client can poll /api/log for progress
        return {
            "status": "started",
            "message": f"AutoPwn initiated on {req.interface}",
        }

    # ── Log & Skills ────────────────────────────────────────────

    @app_router.get("/log")
    async def task_log(user=Depends(auth)):
        return orchestrator.export_log()

    @app_router.get("/skills")
    async def list_skills(user=Depends(auth)):
        names = orchestrator.list_skills()
        skills = []
        for name in names:
            data = orchestrator.load_skill(name)
            skills.append(
                {"name": name, "description": data.get("description", "")}
            )
        return skills

    @app_router.get("/skills/{name}")
    async def get_skill(name: str, user=Depends(auth)):
        data = orchestrator.load_skill(name)
        if "error" in data:
            raise HTTPException(status_code=404, detail=data["error"])
        return data

    @app_router.post("/skills/run")
    async def run_skill(req: RunSkillRequest, user=Depends(auth)):
        import threading

        skill = orchestrator.load_skill(req.name)
        if "error" in skill:
            raise HTTPException(status_code=404, detail=skill["error"])
        t = threading.Thread(
            target=orchestrator.execute_skill_steps,
            args=(skill, req.context),
            daemon=True,
        )
        t.start()
        return {"status": "started", "skill": req.name}

    return app_router
