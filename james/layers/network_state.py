"""Undo only network changes successfully made by this JAMES process."""
import shlex
import threading


class NetworkState:
    def __init__(self, layer):
        self.layer = layer
        self._undo = []
        self._forwarding = None
        self._lock = threading.RLock()

    def add_rule(self, command):
        args = shlex.split(command)
        if not args or args[0] != "iptables" or args.count("-A") != 1:
            raise ValueError("Expected an iptables append command")
        # A unique ownership comment prevents deleting another application's rule.
        import uuid
        args.extend(["-m", "comment", "--comment", "james-" + uuid.uuid4().hex])
        with self._lock:
            result = self.layer.run(shlex.join(args), sudo=True, timeout=5)
            if result.success:
                args[args.index("-A")] = "-D"
                self._undo.append(shlex.join(args))
            return result

    def enable_forwarding(self):
        with self._lock:
            if self._forwarding is not None:
                return
            previous = self.layer.run("cat /proc/sys/net/ipv4/ip_forward", timeout=5)
            value = previous.stdout.strip()
            if not previous.success or value not in {"0", "1"}:
                raise RuntimeError("Cannot read initial IP forwarding state")
            if value == "1":
                return
            result = self.layer.run("echo 1 > /proc/sys/net/ipv4/ip_forward", sudo=True, timeout=5)
            if not result.success:
                raise RuntimeError("Cannot enable IP forwarding")
            self._forwarding = value

    def restore(self):
        errors = []
        with self._lock:
            remaining = []
            for command in reversed(self._undo):
                result = self.layer.run(command, sudo=True, timeout=5)
                if not result.success:
                    remaining.append(command)
                    errors.append("Failed to remove a JAMES firewall rule")
            self._undo = list(reversed(remaining))
            if self._forwarding is not None:
                result = self.layer.run(
                    f"echo {self._forwarding} > /proc/sys/net/ipv4/ip_forward",
                    sudo=True, timeout=5,
                )
                if result.success:
                    self._forwarding = None
                else:
                    errors.append("Failed to restore IP forwarding")
        return errors
