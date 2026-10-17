"""Regression checks for core recovery and safe unattended operation."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _methods(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_restored_orchestrator_implements_api_contract():
    source = ROOT / "james/core/orchestrator/orchestrator.py"
    methods = _methods(source)
    required = {
        "system_check",
        "wifi_interfaces",
        "audit_wifi_hardware",
        "get_loot_summary",
        "list_wordlists",
        "export_log",
        "scan_nearby_aps",
        "start_monitor",
        "stop_monitor",
        "ensure_monitor_mode",
        "kill_james",
        "handle_command",
    }
    assert required <= methods, f"Missing orchestrator methods: {sorted(required - methods)}"


def test_orchestrator_does_not_contain_known_minimal_restore_stubs():
    source = (ROOT / "james/core/orchestrator/orchestrator.py").read_text(encoding="utf-8")
    assert "Full implementation pending complete history restore" not in source
    assert "Skill {name} (stub)" not in source
    assert "def oneclick_pineapple(self, iface, portal=\"wifi_login\"):\n        pass" not in source


def test_autonomous_agent_never_discards_or_commits_unreviewed_work():
    source = (ROOT / "james/core/auto_agent.py").read_text(encoding="utf-8")
    assert '"reset", "--hard"' not in source
    assert '"clean", "-fd"' not in source
    assert '"add", "."' not in source
    assert '["pip", "install"' not in source
    assert "def _assert_safe_workspace" in source
    assert "human review" in source.lower()
    assert "self.implementation_success: bool = False" in source
    assert "result.returncode == 0 and self.implementation_success" in source


def test_api_defaults_to_loopback_and_requires_tls_for_remote_binding():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'os.environ.get("JAMES_API_HOST", "127.0.0.1")' in source
    assert "JAMES_API_SSL_CERTFILE" in source
    assert "JAMES_API_SSL_KEYFILE" in source
    assert "not api_token or not certfile or not keyfile" in source
    server_source = (ROOT / "james/api/server.py").read_text(encoding="utf-8")
    assert 'os.environ.get("JAMES_API_HOST", "127.0.0.1")' in server_source
    assert 'host="0.0.0.0"' not in server_source
    assert "JAMES_API_SSL_CERTFILE" in server_source
    assert "JAMES_API_SSL_KEYFILE" in server_source


def test_api_token_is_checked_for_rest_and_websocket():
    source = (ROOT / "james/api/server.py").read_text(encoding="utf-8")
    assert "async def require_api_token" in source
    assert 'request.headers.get("x-james-api-token", "")' in source
    assert 'ws.query_params.get("token", "")' in source
