"""Desktop controls and live output for the Wi-Fi Lab runner."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from PyQt5.QtCore import QProcess, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from james.core.wifi_lab import EXERCISES, _parse_args

_ROOT = Path(__file__).resolve().parents[3]
_MODES = {
    "sniff": "Packet capture",
    "hidden": "Hidden SSID",
    "mac-filter": "MAC filter",
    "wep-replay": "WEP shared-key replay",
    "wep": "WEP key recovery",
    "wpa": "WPA/WPA2 handshake",
    "twin": "WPA2 lab twin",
    "wpa3": "WPA3 / transition mode",
    "traffic": "Lab bridge traffic",
}
_OUTCOMES = {
    "observed": "Exercise complete",
    "not_observed": "Expected evidence absent",
    "error": "Exercise failed",
    "interrupted": "Exercise stopped",
    "cleanup_error": "Adapter cleanup failed",
}


class WifiLabTab(QWidget):
    run_finished = pyqtSignal()

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self._stdout = b""
        self._stderr = ""
        self._key = b""
        self._stop_requested = False
        self._outcome = ""
        self._process = QProcess(self)
        self._process.setWorkingDirectory(str(_ROOT))
        self._process.started.connect(self._started)
        self._process.readyReadStandardOutput.connect(self._read_stdout)
        self._process.readyReadStandardError.connect(self._read_stderr)
        self._process.finished.connect(self._finished)
        self._process.errorOccurred.connect(self._process_error)

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        title = QLabel("Wi-Fi Lab")
        title.setObjectName("sectionLabel")
        controls.addWidget(title)
        controls.addStretch()
        self.start_button = QPushButton("Run exercise")
        self.start_button.setToolTip("Run the selected Wi-Fi Lab exercise")
        self.start_button.clicked.connect(self._start)
        controls.addWidget(self.start_button)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setToolTip("Stop the exercise and restore the adapters")
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.setEnabled(False)
        controls.addWidget(self.stop_button)
        layout.addLayout(controls)

        self.status = QLabel(
            "Choose a dedicated adapter and enter your lab AP's BSSID and channel."
        )
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_inputs())
        splitter.addWidget(self._build_results())
        splitter.setSizes([295, 520])
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self.exercise.currentIndexChanged.connect(self._update_exercise)
        self.second_adapter.currentIndexChanged.connect(self._update_fields)
        self.adapter.currentIndexChanged.connect(self._update_start_button)
        self.refresh_adapters()
        self._update_exercise()

    def _build_inputs(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.inputs = QWidget()
        self.form = QFormLayout(self.inputs)
        self.form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.exercise = QComboBox()
        for mode, description in EXERCISES.items():
            self.exercise.addItem(_MODES[mode], mode)
            self.exercise.setItemData(self.exercise.count() - 1, description, Qt.ToolTipRole)
        self.form.addRow("Exercise", self.exercise)

        self.adapter = QComboBox()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh_adapters)
        adapter_row = QHBoxLayout()
        adapter_row.addWidget(self.adapter, 1)
        adapter_row.addWidget(refresh)
        self.form.addRow("Adapter", adapter_row)

        self.bssid = QLineEdit()
        self.bssid.setPlaceholderText("AA:BB:CC:DD:EE:FF")
        selected = QPushButton("Use selected AP")
        selected.setToolTip("Use the BSSID and channel selected in Wi-Fi Arsenal")
        selected.clicked.connect(self._use_selected_ap)
        self.form.addRow("Lab BSSID", self.bssid)
        self.form.addRow("", selected)
        self.channel = QSpinBox()
        self.channel.setRange(1, 14)
        self.channel.setValue(6)
        self.form.addRow("Channel", self.channel)
        self.seconds = QSpinBox()
        self.seconds.setRange(12, 600)
        self.seconds.setSuffix(" s")
        self.form.addRow("Capture time", self.seconds)

        self.client = QLineEdit()
        self.client.setPlaceholderText("Client Wi-Fi MAC")
        self.form.addRow("Lab client", self.client)
        self.second_adapter = QComboBox()
        self.form.addRow("Second adapter", self.second_adapter)
        self.country = QLineEdit()
        self.country.setPlaceholderText("Two-letter country code")
        self.country.setMaxLength(2)
        self.form.addRow("Country", self.country)
        self.bridge = QLineEdit()
        self.bridge.setPlaceholderText("Existing lab bridge")
        self.form.addRow("Bridge", self.bridge)
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setMaxLength(64)
        self.form.addRow("Lab passphrase", self.key)

        self.wordlist = QLineEdit()
        self.wordlist.setPlaceholderText("Optional wordlist")
        self.choose_wordlist = QPushButton("Browse wordlists")
        self.choose_wordlist.clicked.connect(self._choose_wordlist)
        self.form.addRow("Wordlist", self.wordlist)
        self.form.addRow("", self.choose_wordlist)
        self.crack_seconds = QSpinBox()
        self.crack_seconds.setRange(1, 1800)
        self.crack_seconds.setValue(120)
        self.crack_seconds.setSuffix(" s")
        self.form.addRow("Recovery limit", self.crack_seconds)

        self.deauth = QCheckBox("Targeted deauthentication")
        self.arp_replay = QCheckBox("ARP replay")
        self.inject_test = QCheckBox("Check packet injection")
        for toggle in (self.deauth, self.arp_replay, self.inject_test):
            self.form.addRow(toggle)
        scroll.setWidget(self.inputs)
        return scroll

    def _build_results(self):
        tabs = QTabWidget()
        self.findings = QPlainTextEdit()
        self.findings.setReadOnly(True)
        self.findings.setPlaceholderText("Findings appear here once the lab AP is observed.")
        tabs.addTab(self.findings, "Findings")

        packet_page = QWidget()
        packet_layout = QVBoxLayout(packet_page)
        self.packet_status = QLabel("Packet details appear after JAMES decodes the saved capture.")
        self.packet_status.setTextFormat(Qt.PlainText)
        self.packet_status.setWordWrap(True)
        packet_layout.addWidget(self.packet_status)
        self.packets = QTableWidget(0, 6)
        self.packets.setHorizontalHeaderLabels(
            ["Frame", "Time (s)", "Source", "Destination", "Protocol", "Info"]
        )
        self.packets.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.packets.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.packets.verticalHeader().hide()
        self.packets.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.packets.horizontalHeader().setStretchLastSection(True)
        packet_layout.addWidget(self.packets, 1)
        tabs.addTab(packet_page, "Packets")

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(400)
        tabs.addTab(self.log, "Run log")
        return tabs

    @property
    def running(self):
        return self._process.state() != QProcess.NotRunning

    def refresh_adapters(self):
        if self.running:
            return
        adapters = [
            item["interface"]
            for item in self.main_window.orchestrator.aircrack.list_interfaces()
            if item["mode"] == "managed"
        ]
        for box, placeholder in (
            (self.adapter, "Select adapter" if adapters else "No managed adapters"),
            (self.second_adapter, "None"),
        ):
            selected = box.currentData()
            box.blockSignals(True)
            box.clear()
            box.addItem(placeholder, None)
            for name in adapters:
                box.addItem(name, name)
            box.setCurrentIndex(max(0, box.findData(selected)))
            box.blockSignals(False)
        self._update_fields()
        self._update_start_button()

    def _update_start_button(self):
        self.start_button.setEnabled(not self.running and bool(self.adapter.currentData()))

    def _update_exercise(self):
        self.seconds.setValue(120 if self.exercise.currentData() == "wep" else 30)
        self._update_fields()

    def _update_fields(self):
        mode = self.exercise.currentData()
        second = self.second_adapter.currentData()
        uses_wordlist = mode in {"wpa", "wpa3", "twin"}
        for widget, shown in (
            (self.client, mode != "sniff"),
            (self.second_adapter, mode in {"mac-filter", "twin", "traffic", "wpa3"}),
            (self.country, mode in {"twin", "traffic"} or (mode == "wpa3" and bool(second))),
            (self.bridge, mode == "traffic"),
            (self.key, mode == "traffic"),
            (self.wordlist, uses_wordlist),
            (self.choose_wordlist, uses_wordlist),
            (self.crack_seconds, uses_wordlist or mode == "wep"),
            (self.deauth, mode in {"hidden", "wep", "wep-replay", "wpa"}),
            (self.arp_replay, mode == "wep"),
            (self.inject_test, mode == "sniff"),
        ):
            widget.setVisible(shown)
            label = self.form.labelForField(widget)
            if label is not None:
                label.setVisible(shown)
            if not shown and isinstance(widget, QCheckBox):
                widget.setChecked(False)

    def _use_selected_ap(self):
        bssid = self.main_window.selected_bssid
        try:
            channel = int(self.main_window.selected_channel)
        except (TypeError, ValueError):
            channel = 0
        if not bssid or not 1 <= channel <= 14:
            self.status.setText("Select a 2.4 GHz lab AP in Wi-Fi Arsenal first.")
            return
        self.bssid.setText(bssid)
        self.channel.setValue(channel)

    def _choose_wordlist(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a lab wordlist")
        if path:
            self.wordlist.setText(path)

    def _arguments(self):
        mode = self.exercise.currentData()
        args = [
            mode,
            "--interface",
            self.adapter.currentData() or "",
            "--bssid",
            self.bssid.text().strip(),
            "--channel",
            str(self.channel.value()),
            "--seconds",
            str(self.seconds.value()),
            "--crack-seconds",
            str(self.crack_seconds.value()),
            "--event-stream",
        ]
        client = self.client.text().strip()
        if client and mode != "sniff":
            args.extend(["--client", client])
        second = self.second_adapter.currentData()
        if second and mode == "mac-filter":
            args.extend(["--client-interface", second])
        if second and mode in {"wpa3", "twin", "traffic"}:
            args.extend(["--ap-interface", second, "--country", self.country.text().strip()])
        if mode == "traffic" and self.bridge.text().strip():
            args.extend(["--bridge", self.bridge.text().strip()])
        if mode in {"wpa", "wpa3", "twin"} and self.wordlist.text().strip():
            args.extend(
                ["--wordlist", str(Path(self.wordlist.text().strip()).expanduser().resolve())]
            )
        for flag, toggle in (
            ("--deauth", self.deauth),
            ("--arp-replay", self.arp_replay),
            ("--inject-test", self.inject_test),
        ):
            if toggle.isChecked():
                args.append(flag)
        return args

    def _start(self):
        if self.running:
            return
        try:
            args = self._arguments()
            parsed = _parse_args(args, exit_on_error=False)
        except (ValueError, argparse.ArgumentError, OSError) as exc:
            self.status.setText(str(exc))
            return
        key = self.key.text() if parsed.exercise == "traffic" else ""
        if parsed.exercise == "traffic" and not key:
            self.status.setText("Enter the lab WPA2 passphrase.")
            return

        program = sys.executable
        arguments = ["-m", "james.core.wifi_lab", *args]
        if os.geteuid() != 0:
            sudo = shutil.which("sudo")
            if not sudo:
                self.status.setText("Wi-Fi Lab needs sudo for radio operations.")
                return
            program, arguments = sudo, ["-n", "--", program, *arguments]

        self._stdout = b""
        self._stderr = ""
        self._key = key.encode() + b"\n" if key else b""
        self.key.clear()
        self._stop_requested = False
        self._outcome = ""
        self.findings.clear()
        self.packets.setRowCount(0)
        self.packet_status.setText("Waiting for a saved capture.")
        self.packet_status.setToolTip("")
        self.log.clear()
        self.status.setText("Starting Wi-Fi Lab…")
        self.inputs.setEnabled(False)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self._process.start(program, arguments)

    def _started(self):
        if self._key:
            self._process.write(self._key)
            self._key = b""
        if self._stop_requested:
            self._send_stop()

    def _send_stop(self):
        self._process.write(b"\n")
        self._process.closeWriteChannel()

    def stop(self):
        if self.running and not self._stop_requested:
            self._stop_requested = True
            self.stop_button.setEnabled(False)
            self.status.setText("Stopping the exercise and restoring the adapters…")
            if self._process.state() == QProcess.Running:
                self._send_stop()

    def _read_stdout(self):
        self._stdout += bytes(self._process.readAllStandardOutput())
        lines = self._stdout.split(b"\n")
        self._stdout = lines.pop()
        for line in lines:
            if line:
                self._handle_line(line.decode("utf-8", errors="replace"))

    def _read_stderr(self):
        output = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace")
        if output:
            self._stderr = (self._stderr + output)[-2000:]
            self.log.appendPlainText(output.rstrip())

    def _handle_line(self, line: str):
        try:
            event = json.loads(line)
        except ValueError:
            self.log.appendPlainText(line)
            return
        if not isinstance(event, dict):
            return
        kind = event.get("kind")
        if kind == "progress":
            self.log.appendPlainText(event["message"])
            if not self._stop_requested:
                self.status.setText(event["message"])
        elif kind == "capture":
            self.log.appendPlainText(f"Saved capture {event['path']}")
        elif kind == "discovery":
            self._show_findings(event)
        elif kind == "packets":
            self._show_packets(event)
        elif kind == "preview_error":
            self.packet_status.setText(event["message"])
        elif kind == "failure":
            self._outcome = event["message"]
            self.log.appendPlainText(self._outcome)
        elif kind == "report":
            report = event["report"]
            self._show_findings(report)
            self._outcome = _OUTCOMES.get(report.get("status"), "Exercise finished")

    def _show_findings(self, report: dict):
        lines = []
        if outcome := report.get("status"):
            lines.append(_OUTCOMES.get(outcome, outcome))
        if reason := report.get("reason"):
            lines.append(reason)
        if ap := report.get("ap"):
            lines.extend(
                [
                    "",
                    f"SSID  {ap.get('essid') or 'Hidden'}",
                    f"BSSID  {ap['bssid']}",
                    f"Channel  {ap['channel']}",
                    f"Security  {' / '.join(ap[key] for key in ('privacy', 'cipher', 'authentication') if ap.get(key))}",
                    f"Signal  {ap['power']} dBm",
                    f"Data frames  {ap['data_packets']}",
                ]
            )
        if "stations" in report:
            lines.append(f"Observed clients  {', '.join(report['stations']) or 'None'}")
        for key, label in (
            ("hidden_beacon_seen", "Hidden beacon"),
            ("revealed_ssid", "Revealed SSID"),
            ("associated_with_original_mac", "Associated with original MAC"),
            ("associated_with_allowlisted_mac", "Associated with allow-listed MAC"),
            ("associated_via_keystream", "Associated using WEP keystream"),
            ("handshake_verified", "Handshake verified"),
            ("wpa3_mode", "WPA3 mode"),
            ("client_frames", "Lab client frames"),
            ("key_recovered", "Key recovered"),
            ("lab_ap_bssid", "Lab twin BSSID"),
            ("capture", "Capture"),
            ("handshake_capture", "Client capture"),
            ("keystream", "Keystream file"),
            ("injection_log", "Injection log"),
            ("key_file", "Recovered key file"),
        ):
            if key in report:
                value = report[key]
                if isinstance(value, bool):
                    value = "Yes" if value else "No"
                lines.append(f"{label}  {value}")
        if directory := report.get("output_dir"):
            lines.append(f"Report  {Path(directory) / 'report.json'}")
        lines.extend(report.get("cleanup_errors", []))
        self.findings.setPlainText("\n".join(lines).strip())

    def _show_packets(self, event: dict):
        rows = event["rows"]
        self.packets.setRowCount(len(rows))
        for row_number, row in enumerate(rows):
            for column, value in enumerate(row):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.packets.setItem(row_number, column, item)
        self.packet_status.setText(
            f"{len(rows)} matching rows · first {event['read_limit']:,} captured frames · {Path(event['path']).name}"
        )
        self.packet_status.setToolTip(f"Display filter  {event['display_filter']}")

    def _process_error(self, error):
        if error == QProcess.FailedToStart:
            self._outcome = self._process.errorString()
            self._finished(2, QProcess.CrashExit)

    def _finished(self, code, _exit_status):
        self._read_stdout()
        self._read_stderr()
        if self._stdout:
            self._handle_line(self._stdout.decode("utf-8", errors="replace"))
        self._stdout = self._key = b""
        if not self._outcome:
            if code == 130 or self._stop_requested:
                self._outcome = "Exercise stopped"
            elif "sudo:" in self._stderr:
                self._outcome = "Authorize sudo in the terminal that launches JAMES, then retry."
            else:
                self._outcome = f"Wi-Fi Lab exited with code {code}. See Run log."
        self.status.setText(self._outcome)
        self.inputs.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._update_start_button()
        self.run_finished.emit()
