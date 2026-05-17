"""
JAMES Server Configuration.

Reads from ~/.james/config.json or environment variables.
Auto-creates config directory and default config on first run.
"""

import json
import os
import secrets
from pathlib import Path
from dataclasses import dataclass, field

JAMES_HOME = Path.home() / ".james"
CONFIG_PATH = JAMES_HOME / "config.json"
CERTS_DIR = JAMES_HOME / "certs"

_DEFAULTS = {
    "host": "0.0.0.0",
    "port": 8443,
    "api_key": "",  # set on first run via --setup
    "tls_enabled": True,
    "tls_cert": str(CERTS_DIR / "cert.pem"),
    "tls_key": str(CERTS_DIR / "key.pem"),
    "cors_origins": ["*"],
    "jwt_secret": "",  # auto-generated
    "jwt_expire_minutes": 1440,  # 24 hours
}


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8443
    api_key: str = ""
    tls_enabled: bool = True
    tls_cert: str = ""
    tls_key: str = ""
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    jwt_secret: str = ""
    jwt_expire_minutes: int = 1440

    @property
    def base_url(self) -> str:
        scheme = "https" if self.tls_enabled else "http"
        return f"{scheme}://{self.host}:{self.port}"


def load_config() -> ServerConfig:
    """Load config from file, env overrides, or defaults."""
    data = dict(_DEFAULTS)

    # read config file if exists
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            data.update(json.load(f))

    # env overrides
    if v := os.environ.get("JAMES_HOST"):
        data["host"] = v
    if v := os.environ.get("JAMES_PORT"):
        data["port"] = int(v)
    if v := os.environ.get("JAMES_API_KEY"):
        data["api_key"] = v
    if v := os.environ.get("JAMES_TLS"):
        data["tls_enabled"] = v.lower() in ("1", "true", "yes")

    # auto-generate jwt_secret if missing
    if not data["jwt_secret"]:
        data["jwt_secret"] = secrets.token_hex(32)

    # set default cert paths
    if not data["tls_cert"]:
        data["tls_cert"] = str(CERTS_DIR / "cert.pem")
    if not data["tls_key"]:
        data["tls_key"] = str(CERTS_DIR / "key.pem")

    return ServerConfig(
        **{k: data[k] for k in ServerConfig.__dataclass_fields__}
    )


def save_config(cfg: ServerConfig) -> None:
    """Persist config to disk."""
    JAMES_HOME.mkdir(parents=True, exist_ok=True)
    data = {
        "host": cfg.host,
        "port": cfg.port,
        "api_key": cfg.api_key,
        "tls_enabled": cfg.tls_enabled,
        "tls_cert": cfg.tls_cert,
        "tls_key": cfg.tls_key,
        "cors_origins": cfg.cors_origins,
        "jwt_secret": cfg.jwt_secret,
        "jwt_expire_minutes": cfg.jwt_expire_minutes,
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)  # owner-only read/write


def generate_api_key() -> str:
    """Generate a strong random API key."""
    return secrets.token_urlsafe(32)
