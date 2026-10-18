"""Read-only inventory and metadata ingestion routes for Wireless SOC."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from james.api.wireless_soc import WirelessSOCStore

router = APIRouter(prefix="/api/wireless-soc", tags=["wireless-soc"])
_default_path = Path.home() / ".james" / "wireless_soc.sqlite3"
store = WirelessSOCStore(os.environ.get("JAMES_WIRELESS_SOC_DB", str(_default_path)))


class ObservationPayload(BaseModel):
    bssid: str
    ssid: str = ""
    security: str = "unknown"
    channel: int | None = None
    rssi: int | None = None
    sensor_id: str = "unknown"
    observed_at: str | None = None


class ApprovedAPPayload(BaseModel):
    bssid: str
    expected_ssid: str
    min_security: str = "wpa2"
    site: str = ""
    notes: str = ""


@router.get("/summary")
def get_summary() -> dict[str, int]:
    return store.summary()


@router.get("/assets")
def get_assets(limit: int = Query(default=500, ge=1, le=1000)) -> list[dict[str, Any]]:
    return store.list_assets(limit)


@router.get("/detections")
def get_detections(
    limit: int = Query(default=200, ge=1, le=500),
    unreviewed_only: bool = False,
) -> list[dict[str, Any]]:
    return store.list_detections(limit, unreviewed_only)


@router.post("/observations", status_code=201)
def ingest_observation(payload: ObservationPayload) -> dict[str, Any]:
    try:
        return store.ingest(payload.dict())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/approved-aps", status_code=201)
def approve_access_point(payload: ApprovedAPPayload) -> dict[str, Any]:
    try:
        return store.approve_ap(
            payload.bssid, payload.expected_ssid, payload.min_security,
            payload.site, payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/detections/{detection_id}/review")
def review_detection(detection_id: int) -> dict[str, bool]:
    if detection_id < 1 or not store.review_detection(detection_id):
        raise HTTPException(status_code=404, detail="Detection not found")
    return {"reviewed": True}
