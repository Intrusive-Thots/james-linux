# Linux installer

The `james-linux_VERSION_debian13_amd64.deb` release package targets **Debian 13
(trixie), x86_64**. It bundles the Python interpreter, Qt desktop, API, production
React client, and application data. Node and Python are not needed after install.
This binary is built on glibc 2.41 and does not target older Debian or Ubuntu releases.

Verify the checksum beside the downloaded package, then install with apt so system
GUI libraries are resolved:

```sh
sha256sum -c james-linux_0.1.0_debian13_amd64.deb.sha256
sudo apt install ./james-linux_0.1.0_debian13_amd64.deb
james                 # desktop (also available in the applications menu)
james --server        # local API and web client on port 8745
```

Open `http://127.0.0.1:8745` when running `james --server`. The API health check is
`curl --fail http://127.0.0.1:8745/api/health`. The server defaults to loopback;
remote binding still requires the token and TLS settings documented in
[SECURITY_DEPLOYMENT.md](SECURITY_DEPLOYMENT.md). The bundled browser client is
currently intended for the default local mode without a token. It does not yet
provide a token-entry flow; when `JAMES_API_TOKEN` is set, static pages also require
the token header. Authenticated remote API access is intended for external clients
that can supply this header and the WebSocket token.
User settings and logs live under
the invoking user's home. For a managed environment with a read-only home, set
`JAMES_DATA_DIR` to an absolute writable directory for logs, database, and runtime
state, for example `JAMES_DATA_DIR=/workspace/.onboarding/james-state james --server`.
Do not launch the entire application as root.

The package does not install wireless drivers, auditing binaries, wordlist
collections, or remote access services, and installation starts no services.
Features that need external tools or wireless hardware report their availability
through system diagnostics. AI features require separate provider configuration.
Uninstall with `sudo apt remove james-linux`; personal settings remain in the home
directory.

## Build

Build on Debian 13 amd64 with Python 3.12 and Node 22 or newer. Install `dpkg-dev`
and the GUI libraries listed in the package dependencies. Use a clean virtual
environment and the frozen web lockfile:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
cd web
pnpm install --frozen-lockfile  # pnpm 10
pnpm run build
cd ..
.venv/bin/python scripts/build_linux_package.py --skip-web-build
```

The script compiles an executable runtime using PyInstaller and assembles the
installer plus SHA256 file in `dist/`. It needs no root access, does not modify the
system, and replaces only its generated `build/linux-package` staging files.
Build inputs are recorded inside `/usr/share/doc/james-linux/BUILD-INFO` and
`python-dependencies.txt`. Runtime dependencies currently have ranges in
`requirements.txt`; this is a repeatable build procedure, not a claim of
byte-identical artifacts across dependency updates.

For release validation, extract the package with `dpkg-deb --extract`, run the
extracted `opt/james-linux/james --server` from a different working directory, and
check `/api/health`, `/`, and a referenced `/assets/...` file. Exercise desktop
startup with `QT_QPA_PLATFORM=offscreen` where no display is available. A desktop
display and supported wireless adapter are required for manual hardware checks.

## Automated releases

The `Linux installer release` GitHub Actions workflow builds on Debian 13 with
Python 3.12, Node 22, and pnpm 10.34.0. It checks out the exact version tag, runs
Python and web tests, compiles the installer, and checks the extracted API, web
assets, WebSocket initialization, and offscreen desktop before publishing.

Push a `vMAJOR.MINOR.PATCH` tag from a commit containing the workflow; the tag must
match `james.__version__`. The release branch `release/james-linux-0.1.0` also
triggers the initial build of the existing `v0.1.0` tag without moving that tag.
Manual dispatch accepts an existing tag once the workflow is on the default
branch. GitHub Actions must be enabled for the repository.

Publication uses GitHub's built-in token with `contents: write` only in the
publish job. No personal access token or cloud-environment network edits are
needed for the GitHub-hosted job. It creates a draft, uploads and verifies the
installer/checksum, then publishes. Existing assets are never overwritten;
different contents with the same release filename stop publication. A failed
upload leaves the draft available for inspection or retry. Build artifacts and
smoke logs are retained for 14 days, including when validation fails.

CI rebuilds can differ from local packages because runtime dependency versions
are ranges. Each release has its own verified checksum and source provenance;
do not assume a CI package is byte-identical to a local build.
