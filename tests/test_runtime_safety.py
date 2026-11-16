"""Recovery tests use fake processes and never change host networking."""
import ast
import fcntl
import io
import logging
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from james.layers.native import CommandResult, NativeLayer
from james.layers.network_state import NetworkState


def result(success=True, stdout=""):
    return CommandResult("fake", 0 if success else 1, stdout, "")


@pytest.mark.parametrize("mode", ["blocking", "streaming", "background"])
def test_sudo_secret_uses_pipe_only(monkeypatch, tmp_path, caplog, mode):
    monkeypatch.setenv("JAMES_SUDO_PASS", "secret-test-credential")
    monkeypatch.setattr("james.layers.native._BG_LOG_DIR", tmp_path)
    layer = NativeLayer()
    layer._is_root = False
    proc = Mock()
    proc.pid = 123
    proc.returncode = 0
    proc.stdin = io.StringIO()
    proc.stdout = io.StringIO("ok\n")
    proc.stderr = io.StringIO("")
    proc.communicate.return_value = ("ok", "")
    factory = Mock(return_value=proc)
    monkeypatch.setattr("james.layers.native.subprocess.Popen", factory)
    with caplog.at_level(logging.DEBUG):
        if mode == "background":
            layer.run_background("printf ok", sudo=True)
            proc._james_log_fh.close()
        else:
            layer.run("printf ok", sudo=True, on_output=Mock() if mode == "streaming" else None)
    args, kwargs = factory.call_args
    assert "secret-test-credential" not in str(args)
    assert "JAMES_SUDO_PASS" not in kwargs["env"]
    assert kwargs["stdin"] == -1  # subprocess.PIPE
    assert "secret-test-credential" not in caplog.text
    assert all("secret-test-credential" not in p.read_text() for p in tmp_path.glob("*.log"))
    if mode == "blocking":
        assert proc.communicate.call_args.kwargs["input"] == "secret-test-credential\n"


def test_network_restoration_is_owned_and_retryable():
    layer = Mock()
    layer.run.return_value = result()
    state = NetworkState(layer)
    state.add_rule("iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE")
    added = layer.run.call_args.args[0]
    assert "--comment james-" in added
    layer.run.return_value = result(False)
    assert state.restore()
    delete = layer.run.call_args.args[0]
    assert delete == added.replace(" -A ", " -D ")
    layer.run.return_value = result()
    assert state.restore() == []
    count = layer.run.call_count
    assert state.restore() == []
    assert layer.run.call_count == count


@pytest.mark.parametrize("initial", ["0", "1"])
def test_forwarding_restores_original_state(initial):
    layer = Mock()
    layer.run.side_effect = lambda command, **kw: result(stdout=initial if command.startswith("cat ") else "")
    state = NetworkState(layer)
    state.enable_forwarding()
    state.enable_forwarding()
    assert state.restore() == []
    commands = [call.args[0] for call in layer.run.call_args_list]
    if initial == "1":
        assert not any(command.startswith("echo ") for command in commands)
    else:
        assert commands.count("echo 1 > /proc/sys/net/ipv4/ip_forward") == 1
        assert commands[-1] == "echo 0 > /proc/sys/net/ipv4/ip_forward"


def test_singleton_contender_does_not_truncate_owner_pid(tmp_path):
    source = Path("main.py").read_text()
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "acquire_singleton_lock")
    lock = tmp_path / "lock"
    with lock.open("w") as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        owner.write("12345")
        owner.flush()
        namespace = dict(LOCK_FILE=str(lock), _lock_fd=None, fcntl=fcntl, os=os, logger=Mock())
        exec(compile(ast.Module(body=[node], type_ignores=[]), "main.py", "exec"), namespace)
        assert namespace["acquire_singleton_lock"]() is False
        assert lock.read_text() == "12345"


def test_monitor_transition_rejects_unverified_success():
    from james.core.orchestrator import Orchestrator
    orch = Orchestrator.__new__(Orchestrator)
    orch._mon_iface = Mock(return_value="wlan1mon")
    orch._is_monitor_mode = Mock(return_value=False)
    orch._print = Mock()
    orch.start_monitor = Mock(return_value={"success": True})
    orch.stop_monitor = Mock()
    with pytest.raises(RuntimeError, match="verification failed"):
        orch.ensure_monitor_mode("wlan1")
    orch.stop_monitor.assert_called_once_with("wlan1")


def test_monitor_transition_obeys_network_guard():
    from types import SimpleNamespace
    from james.core.orchestrator import Orchestrator
    orch = Orchestrator.__new__(Orchestrator)
    orch.net_guard = Mock()
    orch.net_guard.check_monitor_safe.return_value = (True, "")
    orch.net_guard.get_active_connection.return_value = SimpleNamespace(is_wifi=False)
    orch.net_guard.check_check_kill_safe.return_value = (False, "Protected connection")
    orch._print = Mock()
    orch._log = Mock()
    orch._finish = Mock()
    orch.aircrack = Mock()
    orch.aircrack.enable_monitor.return_value = result()
    orch.start_monitor("wlan1")
    orch.aircrack.check_kill.assert_not_called()


def test_ollama_unavailable_returns_without_inference(monkeypatch):
    from james.core.ai_engine import GeminiEngine
    engine = GeminiEngine.__new__(GeminiEngine)
    engine.local_ollama_available = False
    engine._refresh_local_ollama = Mock(return_value=False)
    post = Mock()
    monkeypatch.setattr("james.core.ai_engine.requests.post", post)
    assert engine._call_ollama([]) is None
    post.assert_not_called()


def test_ollama_timeout_invalidates_health(monkeypatch):
    import requests
    from james.core.ai_engine import GeminiEngine
    engine = GeminiEngine.__new__(GeminiEngine)
    engine.local_ollama_available = True
    engine.local_model = "test-model"
    post = Mock(side_effect=requests.Timeout("test timeout"))
    monkeypatch.setattr("james.core.ai_engine.requests.post", post)
    assert engine._call_ollama([]) is None
    assert engine.local_ollama_available is False
    assert post.call_args.kwargs["timeout"] == (3, 90)
