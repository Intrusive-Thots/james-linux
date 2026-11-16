# Runtime safety repairs

The November 15–16 log review describes an older build. This checkout already
contains `AircrackSuite.check_kill` and connection-aware adapter selection.
The additional repairs cover:

- Sudo authentication travels through subprocess stdin. Passwords are excluded
  from generated command strings, background log headers, and child environments.
- Monitor transitions require observed monitor mode on the requested interface;
  failed verification attempts to restore managed mode. The network guard's veto
  on global `airmon-ng check kill` is respected.
- Firewall rules receive unique ownership comments. Cleanup removes only rules
  successfully added by this process and restores its saved forwarding setting.
  Failed removals remain queued for another cleanup attempt.
- Singleton contenders acquire the lock before truncating the PID file.
- The dependency installer is located relative to the repository root. Installed
  packages skip installation and package metadata refreshes are skipped when no
  core package is missing. Counter increments work under Bash `set -e`.
- Ollama health-check failure skips inference; connection establishment has a
  three-second timeout and inference retains its 90-second read timeout. Failures
  invalidate cached availability and return the existing graceful fallback.

## Validation and limits

`python -m pytest tests/test_runtime_safety.py tests/test_repair_regressions.py
 tests/test_wifi_lab.py tests/test_list_interfaces.py -q` passes 31 tests.
`bash -n install_deps.sh` and `git diff --check` also pass.
The broader suite encounters sandbox socket restrictions in `test_remote_cors.py`;
its run was interrupted after it stopped progressing. Live radio, sudo, Ollama,
and package installation tests were not performed.

Network ownership records are in memory and cannot recover changes after an
abrupt process or machine crash. A durable recovery journal and an allowlisted
privileged helper remain separate architectural work. The execution layer still
supports privileged shell commands. Existing log files are not rewritten: rotate
any password exposed by the older build and remove it from retained logs.
