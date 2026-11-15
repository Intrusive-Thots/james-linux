#!/usr/bin/env python3
"""Publish verified Debian assets without replacing an existing release asset."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


class PublishError(RuntimeError):
    pass


class GitHubError(PublishError):
    def __init__(self, status: int | None = None):
        self.status = status
        super().__init__(f"GitHub request failed (HTTP {status})" if status else "GitHub request failed")


class GitHub:
    """Use gh's supported token binding; never read or print credential values."""

    def run(self, *arguments: str) -> bytes:
        result = subprocess.run(
            ["gh", *arguments], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode:
            match = re.search(rb"\bHTTP\s+(\d{3})\b", result.stderr)
            raise GitHubError(int(match[1]) if match else None)
        return result.stdout

    def api(self, endpoint: str) -> dict:
        return json.loads(self.run("api", endpoint))


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def local_assets(package: Path, tag: str) -> list[Path]:
    match = re.fullmatch(r"james-linux_(\d+\.\d+\.\d+)_debian13_amd64\.deb", package.name)
    if not match or tag != f"v{match[1]}":
        raise PublishError("Tag and Debian package version must match")
    checksum = package.with_name(package.name + ".sha256")
    if not package.is_file() or not checksum.is_file():
        raise PublishError("Package and adjacent .sha256 file are required")
    fields = checksum.read_text(encoding="utf-8").split()
    if (len(fields) != 2 or not re.fullmatch(r"[a-fA-F0-9]{64}", fields[0])
            or fields[1].lstrip("*") != package.name):
        raise PublishError("Checksum file must describe exactly this package")
    if digest(package) != fields[0].lower():
        raise PublishError("Local package checksum does not match")
    return [package, checksum]


def verify_asset(client: GitHub, repository: str, asset: dict, path: Path) -> None:
    if asset.get("size") != path.stat().st_size:
        raise PublishError(f"Existing release asset differs: {path.name} (size)")
    expected = digest(path)
    remote_digest = asset.get("digest") or ""
    if remote_digest.startswith("sha256:"):
        actual = remote_digest.removeprefix("sha256:").lower()
    else:
        asset_id = asset.get("id")
        if not isinstance(asset_id, int) or isinstance(asset_id, bool) or asset_id <= 0:
            raise PublishError(f"Invalid release asset ID for {path.name}")
        content = client.run(
            "api", f"repos/{repository}/releases/assets/{asset_id}",
            "--header", "Accept: application/octet-stream",
        )
        actual = hashlib.sha256(content).hexdigest()
    if actual != expected:
        raise PublishError(f"Existing release asset differs: {path.name} (SHA256)")


def named_assets(release: dict) -> dict[str, dict]:
    result = {}
    for asset in release.get("assets", []):
        name = asset.get("name")
        if name in result:
            raise PublishError(f"Duplicate release asset: {name}")
        result[name] = asset
    return result


def find_release(client: GitHub, repository: str, tag: str) -> dict | None:
    try:
        return client.api(f"repos/{repository}/releases/tags/{tag}")
    except GitHubError as exc:
        if exc.status != 404:
            raise
    # The tag endpoint can hide drafts; an authenticated listing includes them.
    pages = json.loads(client.run("api", f"repos/{repository}/releases", "--paginate", "--slurp"))
    matches = [release for page in pages for release in page if release.get("tag_name") == tag]
    if len(matches) > 1:
        raise PublishError(f"Multiple releases exist for {tag}; refusing to mutate them")
    return matches[0] if matches else None


def refresh_release(client: GitHub, repository: str, release: dict) -> dict:
    release_id = release.get("id")
    if not isinstance(release_id, int) or isinstance(release_id, bool) or release_id <= 0:
        raise PublishError("Invalid release ID")
    return client.api(f"repos/{repository}/releases/{release_id}")


def publish(repository: str, tag: str, package: Path, client: GitHub | None = None) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise PublishError("Repository must be owner/name")
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise PublishError("Release tag must use vMAJOR.MINOR.PATCH")
    files = local_assets(package, tag)
    client = client or GitHub()
    release = find_release(client, repository, tag)
    if release is None:
        client.run(
            "release", "create", tag, "--repo", repository, "--verify-tag", "--draft",
            "--title", f"JAMES Linux {tag[1:]} — Debian 13 amd64",
            "--notes", "Compiled desktop, local API, and web client for Debian 13 amd64. "
            "Verify the attached SHA256 file before installing. See the repository's Linux installer documentation.",
        )
        release = find_release(client, repository, tag)
        if release is None:
            raise PublishError("Created release could not be found; refusing further changes")

    existing = named_assets(release)
    # Verify every existing target before any upload, so collisions preserve the release.
    for path in files:
        if path.name in existing:
            verify_asset(client, repository, existing[path.name], path)
    for path in files:
        if path.name not in existing:
            client.run("release", "upload", tag, str(path), "--repo", repository)

    release = refresh_release(client, repository, release)
    uploaded = named_assets(release)
    for path in files:
        if path.name not in uploaded:
            raise PublishError(f"Upload did not produce release asset: {path.name}")
        verify_asset(client, repository, uploaded[path.name], path)
    if release.get("draft"):
        client.run("release", "edit", tag, "--repo", repository, "--draft=false")
        if refresh_release(client, repository, release).get("draft"):
            raise PublishError("Release remains a draft after publication")
    return f"https://github.com/{repository}/releases/tag/{tag}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(publish(args.repository, args.tag, args.package.resolve()))
    except (PublishError, OSError, ValueError) as exc:
        print(f"Release publication failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
