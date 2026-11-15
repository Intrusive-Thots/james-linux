"""The installed client and API share a port without hiding missing endpoints."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from james.api.static_web import mount_web_client


def test_production_client_keeps_api_priority(tmp_path):
    (tmp_path / "index.html").write_text("<html>JAMES client</html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('JAMES')")
    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    assert mount_web_client(app, tmp_path)
    with TestClient(app) as client:
        assert client.get("/").text == "<html>JAMES client</html>"
        assert client.get("/assets/app.js").text == "console.log('JAMES')"
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/api/missing").status_code == 404
        assert client.get("/missing.js").status_code == 404
        assert client.get("/assets/%2e%2e/%2e%2e/private").status_code == 404


def test_unbuilt_checkout_does_not_mount_a_missing_directory(tmp_path):
    app = FastAPI()
    assert not mount_web_client(app, tmp_path)
    with TestClient(app) as client:
        assert client.get("/").status_code == 404
