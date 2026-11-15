"""Release publication must preserve assets and finish verification before publishing."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


spec = importlib.util.spec_from_file_location(
    "publish_linux_release", Path(__file__).resolve().parents[1] / ".github/scripts/publish_linux_release.py",
)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


@pytest.fixture
def package(tmp_path):
    path = tmp_path / "james-linux_0.1.0_debian13_amd64.deb"
    path.write_bytes(b"compiled Debian package fixture")
    path.with_name(path.name + ".sha256").write_text(f"{publisher.digest(path)}  {path.name}\n")
    return path


class ReleaseGitHub(publisher.GitHub):
    def __init__(self, package, release=None):
        self.package = package
        self.release = release
        self.commands = []
        self.failure = None
        self.content = {}

    def api(self, endpoint):
        if self.failure:
            raise self.failure
        if self.release is None or ("/tags/" in endpoint and self.release["draft"]):
            raise publisher.GitHubError(404)
        return self.release

    def run(self, *args):
        self.commands.append(args)
        if args[:2] == ("release", "create"):
            self.release = {"id": 17, "tag_name": "v0.1.0", "draft": True, "assets": []}
        elif args[:2] == ("release", "upload"):
            path = Path(args[3])
            asset = matching_asset(path, len(self.release["assets"]) + 1)
            self.release["assets"].append(asset)
        elif args[:2] == ("release", "edit"):
            self.release["draft"] = False
        elif args[0] == "api":
            if args[1].endswith("/releases"):
                return json.dumps([[self.release] if self.release else []]).encode()
            return self.content[int(args[1].rsplit("/", 1)[1])]
        return b""


def matching_asset(path, asset_id=1):
    return {"id": asset_id, "name": path.name, "size": path.stat().st_size,
            "digest": "sha256:" + publisher.digest(path)}


def complete_release(package, draft=False):
    files = publisher.local_assets(package, "v0.1.0")
    return {"id": 17, "tag_name": "v0.1.0", "draft": draft,
            "assets": [matching_asset(path, i + 1) for i, path in enumerate(files)]}


def test_not_found_creates_draft_uploads_verified_files_then_publishes(package):
    gh = ReleaseGitHub(package)
    url = publisher.publish("owner/repo", "v0.1.0", package, gh)
    assert url == "https://github.com/owner/repo/releases/tag/v0.1.0"
    assert [command[:2] for command in gh.commands if command[0] == "release"] == [
        ("release", "create"), ("release", "upload"), ("release", "upload"), ("release", "edit"),
    ]
    creation = next(command for command in gh.commands if command[:2] == ("release", "create"))
    assert "--draft" in creation and "--verify-tag" in creation
    assert not any("--clobber" in command for command in gh.commands)


def test_forbidden_does_not_create_release(package):
    gh = ReleaseGitHub(package)
    gh.failure = publisher.GitHubError(403)
    with pytest.raises(publisher.GitHubError, match="HTTP 403"):
        publisher.publish("owner/repo", "v0.1.0", package, gh)
    assert gh.commands == []


def test_existing_matching_published_release_is_read_only(package):
    gh = ReleaseGitHub(package, complete_release(package))
    publisher.publish("owner/repo", "v0.1.0", package, gh)
    assert gh.commands == []


def test_collision_preserves_draft_and_does_not_upload_missing_package(package):
    release = complete_release(package, draft=True)
    release["assets"] = [release["assets"][1]]  # Package absent; checksum asset conflicts.
    release["assets"][0]["digest"] = "sha256:" + "0" * 64
    gh = ReleaseGitHub(package, release)
    with pytest.raises(publisher.PublishError, match="SHA256"):
        publisher.publish("owner/repo", "v0.1.0", package, gh)
    assert not any(command[0] == "release" for command in gh.commands)
    assert release["draft"]


def test_draft_hidden_from_tag_endpoint_resumes_without_duplicate_creation(package):
    release = complete_release(package, draft=True)
    release["assets"].pop()  # Resume a prior upload that stopped before its checksum.
    gh = ReleaseGitHub(package, release)
    publisher.publish("owner/repo", "v0.1.0", package, gh)
    assert any("--paginate" in command and "--slurp" in command for command in gh.commands)
    assert [command[:2] for command in gh.commands if command[0] == "release"] == [
        ("release", "upload"), ("release", "edit"),
    ]
    assert not release["draft"]


def test_partial_failure_keeps_new_release_draft(package):
    gh = ReleaseGitHub(package)
    original = gh.run

    def fail_checksum_upload(*args):
        if args[:2] == ("release", "upload") and args[3].endswith(".sha256"):
            raise publisher.GitHubError(503)
        return original(*args)

    gh.run = fail_checksum_upload
    with pytest.raises(publisher.GitHubError):
        publisher.publish("owner/repo", "v0.1.0", package, gh)
    assert gh.release["draft"]
    assert len(gh.release["assets"]) == 1
    assert not any(command[:2] == ("release", "edit") for command in gh.commands)


def test_uploaded_content_is_verified_before_undrafting(package):
    gh = ReleaseGitHub(package)
    original = gh.run

    def corrupt_upload(*args):
        output = original(*args)
        if args[:2] == ("release", "upload"):
            gh.release["assets"][-1]["size"] += 1
        return output

    gh.run = corrupt_upload
    with pytest.raises(publisher.PublishError, match="size"):
        publisher.publish("owner/repo", "v0.1.0", package, gh)
    assert gh.release["draft"]
    assert not any(command[:2] == ("release", "edit") for command in gh.commands)


def test_missing_digest_downloads_and_hashes_asset(package):
    release = complete_release(package)
    gh = ReleaseGitHub(package, release)
    for path, asset in zip(publisher.local_assets(package, "v0.1.0"), release["assets"]):
        asset.pop("digest")
        gh.content[asset["id"]] = path.read_bytes()
    publisher.publish("owner/repo", "v0.1.0", package, gh)
    assert all(command[0] == "api" for command in gh.commands)
    assert all("Accept: application/octet-stream" in command for command in gh.commands)


def test_checksum_and_tag_fail_before_network(package):
    gh = ReleaseGitHub(package)
    with pytest.raises(publisher.PublishError, match="version"):
        publisher.publish("owner/repo", "v0.2.0", package, gh)
    package.write_bytes(b"changed artifact")
    with pytest.raises(publisher.PublishError, match="checksum"):
        publisher.publish("owner/repo", "v0.1.0", package, gh)
    assert gh.commands == []


@pytest.mark.parametrize("status", [403, 404, 500])
def test_gh_adapter_preserves_http_status_without_echoing_diagnostics(status):
    result = SimpleNamespace(returncode=1, stdout=b"", stderr=f"gh: private detail (HTTP {status})".encode())
    with patch.object(publisher.subprocess, "run", return_value=result):
        with pytest.raises(publisher.GitHubError) as error:
            publisher.GitHub().api("repos/owner/repo/releases/tags/v0.1.0")
    assert error.value.status == status
    assert "private detail" not in str(error.value)
