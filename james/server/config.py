import json
import secrets
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".james" / "server_config.json"


@dataclass
class ServerConfig:
    host: str
    port: int
    api_key: str
    tls_enabled: bool
    jwt_secret: str


def load_config() -> ServerConfig:
    """Load configuration from JSON file or generate defaults."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
            return ServerConfig(
                host=data.get("host", "0.0.0.0"),
                port=data.get("port", 8443),
                api_key=data.get("api_key", ""),
                tls_enabled=data.get("tls_enabled", True),
                jwt_secret=data.get("jwt_secret", secrets.token_hex(32)),
            )
        except Exception:
            pass

    # Default config if file doesn't exist or is invalid
    return ServerConfig(
        host="0.0.0.0",
        port=8443,
        api_key="",
        tls_enabled=True,
        jwt_secret=secrets.token_hex(32),
    )
