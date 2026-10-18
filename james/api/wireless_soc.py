"""Defensive wireless telemetry store for JAMES Wireless SOC.

This module stores metadata-only observations from authorized sensors. It does
not capture payloads, collect credentials, inject frames, or initiate scans.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BSSID_RE = re.compile(r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
_ALLOWED_SECURITY = {"open", "wep", "wpa", "wpa2", "wpa3", "unknown"}
_MAX_SSID_LENGTH = 32


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_bssid(value: str) -> str:
    value = str(value).strip().lower()
    if not _BSSID_RE.fullmatch(value):
        raise ValueError("bssid must be a MAC address in AA:BB:CC:DD:EE:FF form")
    return value


def validate_observation(item: dict[str, Any]) -> dict[str, Any]:
    """Validate a single passive AP metadata observation."""
    if not isinstance(item, dict):
        raise ValueError("observation must be an object")
    bssid = normalize_bssid(item.get("bssid", ""))
    ssid = item.get("ssid", "")
    if not isinstance(ssid, str) or len(ssid.encode("utf-8")) > _MAX_SSID_LENGTH:
        raise ValueError("ssid must be a string of at most 32 UTF-8 bytes")
    security = str(item.get("security", "unknown")).strip().lower()
    if security not in _ALLOWED_SECURITY:
        raise ValueError("unsupported security value")
    channel = item.get("channel")
    if channel is not None and (isinstance(channel, bool) or not isinstance(channel, int) or not 1 <= channel <= 233):
        raise ValueError("channel must be an integer between 1 and 233")
    rssi = item.get("rssi")
    if rssi is not None and (isinstance(rssi, bool) or not isinstance(rssi, int) or not -127 <= rssi <= 0):
        raise ValueError("rssi must be an integer between -127 and 0")
    sensor = str(item.get("sensor_id", "unknown")).strip()
    if not sensor or len(sensor) > 80:
        raise ValueError("sensor_id must contain 1–80 characters")
    return {
        "bssid": bssid,
        "ssid": ssid,
        "security": security,
        "channel": channel,
        "rssi": rssi,
        "sensor_id": sensor,
        "observed_at": str(item.get("observed_at") or utc_now())[:64],
    }


class WirelessSOCStore:
    """SQLite-backed approved inventory and metadata-only detection events."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS approved_aps (
                    bssid TEXT PRIMARY KEY,
                    expected_ssid TEXT NOT NULL,
                    min_security TEXT NOT NULL DEFAULT 'wpa2',
                    site TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bssid TEXT NOT NULL,
                    ssid TEXT NOT NULL,
                    security TEXT NOT NULL,
                    channel INTEGER,
                    rssi INTEGER,
                    sensor_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    received_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_observations_time
                    ON observations(observed_at DESC);
                CREATE INDEX IF NOT EXISTS idx_observations_bssid
                    ON observations(bssid, observed_at DESC);
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    bssid TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    reviewed INTEGER NOT NULL DEFAULT 0
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def approve_ap(self, bssid: str, expected_ssid: str, min_security: str = "wpa2",
                   site: str = "", notes: str = "") -> dict[str, Any]:
        bssid = normalize_bssid(bssid)
        if not isinstance(expected_ssid, str) or len(expected_ssid.encode("utf-8")) > _MAX_SSID_LENGTH:
            raise ValueError("expected_ssid must be at most 32 UTF-8 bytes")
        min_security = min_security.strip().lower()
        if min_security not in {"wpa2", "wpa3"}:
            raise ValueError("min_security must be wpa2 or wpa3")
        now = utc_now()
        with self._connect() as db:
            db.execute("""INSERT INTO approved_aps
                (bssid, expected_ssid, min_security, site, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(bssid) DO UPDATE SET expected_ssid=excluded.expected_ssid,
                min_security=excluded.min_security, site=excluded.site, notes=excluded.notes""",
                (bssid, expected_ssid, min_security, site[:120], notes[:500], now))
        return {"bssid": bssid, "expected_ssid": expected_ssid, "min_security": min_security,
                "site": site[:120], "notes": notes[:500]}

    def ingest(self, raw: dict[str, Any]) -> dict[str, Any]:
        obs = validate_observation(raw)
        alerts: list[dict[str, str]] = []
        with self._connect() as db:
            approved = db.execute("SELECT * FROM approved_aps WHERE bssid=?", (obs["bssid"],)).fetchone()
            if approved is None:
                alerts.append({"kind": "unknown_bssid", "severity": "medium",
                               "summary": "Observed BSSID is not in the approved AP inventory"})
            else:
                if obs["ssid"] != approved["expected_ssid"]:
                    alerts.append({"kind": "ssid_mismatch", "severity": "high",
                                   "summary": "Approved BSSID is broadcasting an unexpected SSID"})
                rank = {"open": 0, "wep": 1, "wpa": 2, "wpa2": 3, "wpa3": 4, "unknown": 0}
                if rank[obs["security"]] < rank[approved["min_security"]]:
                    alerts.append({"kind": "security_downgrade", "severity": "high",
                                   "summary": "Observed security is weaker than the approved baseline"})
            if obs["security"] in {"open", "wep"}:
                alerts.append({"kind": "weak_security", "severity": "high",
                               "summary": "Open or WEP security observed"})
            db.execute("""INSERT INTO observations
                (bssid, ssid, security, channel, rssi, sensor_id, observed_at, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (obs["bssid"], obs["ssid"], obs["security"], obs["channel"], obs["rssi"],
                 obs["sensor_id"], obs["observed_at"], utc_now()))
            for alert in alerts:
                db.execute("""INSERT INTO detections
                    (kind, severity, bssid, summary, observed_at)
                    VALUES (?, ?, ?, ?, ?)""",
                    (alert["kind"], alert["severity"], obs["bssid"], alert["summary"], obs["observed_at"]))
        return {"observation": obs, "detections": alerts}

    def list_assets(self, limit: int = 500) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        with self._connect() as db:
            rows = db.execute("""
                SELECT o.bssid, o.ssid, o.security, o.channel, o.rssi, o.sensor_id,
                       o.observed_at, a.site, a.expected_ssid,
                       CASE WHEN a.bssid IS NULL THEN 1 ELSE 0 END AS unapproved
                FROM observations o
                JOIN (SELECT bssid, MAX(id) AS latest_id FROM observations GROUP BY bssid) latest
                  ON latest.latest_id=o.id
                LEFT JOIN approved_aps a ON a.bssid=o.bssid
                ORDER BY o.observed_at DESC LIMIT ?
            """, (limit,)).fetchall()
        return [dict(row) for row in rows]

    def list_detections(self, limit: int = 200, unreviewed_only: bool = False) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        sql = "SELECT * FROM detections"
        if unreviewed_only:
            sql += " WHERE reviewed=0"
        sql += " ORDER BY id DESC LIMIT ?"
        with self._connect() as db:
            return [dict(row) for row in db.execute(sql, (limit,)).fetchall()]

    def review_detection(self, detection_id: int) -> bool:
        with self._connect() as db:
            cursor = db.execute("UPDATE detections SET reviewed=1 WHERE id=?", (int(detection_id),))
            return cursor.rowcount > 0

    def summary(self) -> dict[str, int]:
        with self._connect() as db:
            assets = db.execute("SELECT COUNT(DISTINCT bssid) FROM observations").fetchone()[0]
            approved = db.execute("SELECT COUNT(*) FROM approved_aps").fetchone()[0]
            unreviewed = db.execute("SELECT COUNT(*) FROM detections WHERE reviewed=0").fetchone()[0]
            observations = db.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        return {"assets_seen": assets, "approved_aps": approved,
                "unreviewed_detections": unreviewed, "observations": observations}
