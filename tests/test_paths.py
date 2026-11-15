from pathlib import Path

from james.paths import data_dir


def test_default_state_preserves_user_directory(monkeypatch, tmp_path):
    monkeypatch.delenv("JAMES_DATA_DIR", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert data_dir() == tmp_path / ".james"


def test_explicit_state_can_be_written_without_changing_home(monkeypatch, tmp_path):
    target = tmp_path / "state"
    monkeypatch.setenv("JAMES_DATA_DIR", str(target))
    directory = data_dir()
    directory.mkdir()
    (directory / "probe").write_text("persisted")
    assert (target / "probe").read_text() == "persisted"
