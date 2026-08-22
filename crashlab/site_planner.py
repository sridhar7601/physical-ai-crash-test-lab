"""Warehouse site planner: zone threat scoring and camera placement.

Derives installer guidance and floor-manager alerts from the same physical
rules the crash-test lab measured — lux buckets, occlusion, and camera angle —
without requiring a live GPU or detector run.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal
import math

from .schema import PHYSICAL_RANGES

ThreatLevel = Literal["low", "medium", "high"]
LuxBucket = Literal["bright", "normal", "dim"]

# Measured recall on the locked test suite (warehouse_ppe_v2).
_MEASURED_FAILURES: dict[tuple[str, str], float] = {
    ("dim", "partial"): 0.165,
    ("high_oblique", "partial"): 0.238,
    ("bright", "visible"): 0.934,
}

LUX_THREAT: dict[LuxBucket, float] = {"bright": 0.1, "normal": 0.4, "dim": 0.9}
OCCLUSION_THREAT: dict[str, float] = {"clear": 0.1, "partial": 0.8, "heavy": 0.95}
ANGLE_PENALTY_UNCOVERED = 0.3

HIGH_THRESHOLD = 0.7
MEDIUM_THRESHOLD = 0.4

# SimReady warehouse_multiple_shelves — nominal floor layout (metres).
COLS = ("A", "B", "C", "D", "E", "F")
ROWS = (1, 2, 3, 4)
CELL_W = 4.0
CELL_H = 5.0
ORIGIN_X = -10.0
ORIGIN_Y = -2.0
WINDOW_WALL_X = 12.0


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    col: int
    row: int
    x: float
    y: float
    lux: float
    lux_bucket: LuxBucket
    occlusion: str
    occlusion_factor: float
    near_shelving: bool

    @property
    def centre(self) -> tuple[float, float]:
        return (self.x + CELL_W / 2, self.y + CELL_H / 2)


@dataclass
class CameraMount:
    id: str
    x: float
    y: float
    height_m: float
    angle_deg: float
    covers: list[str] = field(default_factory=list)
    note: str = ""
    avoid: bool = False


@dataclass
class ZonePlan:
    id: str
    name: str
    x: float
    y: float
    width: float
    height: float
    lux: float
    lux_bucket: LuxBucket
    occlusion: str
    threat: ThreatLevel
    threat_score: float
    reason: str
    actions: list[str]
    covered_by: list[str]


def _lux_bucket(lux: float) -> LuxBucket:
    buckets = PHYSICAL_RANGES["lighting"]["buckets"]  # type: ignore[index]
    if lux >= buckets["bright"][0]:  # type: ignore[index]
        return "bright"
    if lux >= buckets["normal"][0]:  # type: ignore[index]
        return "normal"
    return "dim"


def _estimate_lux(col: int, row: int) -> float:
    """Heuristic lux from distance to window wall and depth into the warehouse."""
    cx = ORIGIN_X + col * CELL_W + CELL_W / 2
    window_dist = max(0.5, WINDOW_WALL_X - cx)
    depth = row * CELL_H + CELL_H / 2
    base = 1050.0 / (1.0 + window_dist * 0.1)
    depth_penalty = depth * 28.0
    shelf_shadow = 45.0 if col in (0, 5) else 0.0
    corner_dim = 60.0 if row >= 3 and col <= 1 else 0.0
    return max(12.0, base - depth_penalty - shelf_shadow - corner_dim)


def _occlusion_for_zone(col: int, row: int) -> tuple[str, float, bool]:
    near_shelving = col in (0, 5) or row in (3, 4)
    if col in (0, 5) and row >= 3:
        return "heavy", 0.85, True
    if near_shelving:
        return "partial", 0.55, True
    return "clear", 0.05, False


def _zone_name(col: int, row: int) -> str:
    labels = {
        (0, 0): "Receiving Dock",
        (1, 0): "Staging Bay",
        (2, 0): "Main Aisle North",
        (3, 0): "Pack Station",
        (4, 0): "Outbound Lane",
        (5, 0): "Loading Ramp",
        (0, 1): "Rack Row West",
        (1, 1): "Aisle B Intersection",
        (2, 1): "Central Walkway",
        (3, 1): "Aisle C Intersection",
        (4, 1): "Pick Face East",
        (5, 1): "Rack Row East",
        (0, 2): "Deep Storage West",
        (1, 2): "Pallet Stack Bay",
        (2, 2): "Forklift Path",
        (3, 2): "High-Bay Storage",
        (4, 2): "Overflow Racks",
        (5, 2): "Deep Storage East",
        (0, 3): "Dim Corner West",
        (1, 3): "Loading Bay 4",
        (2, 3): "Aisle C South",
        (3, 3): "Blind Spot South",
        (4, 3): "Pallet Maze",
        (5, 3): "Dim Corner East",
    }
    return labels.get((col, row), f"Zone {COLS[col]}{row + 1}")


def build_warehouse_grid() -> list[Zone]:
    zones: list[Zone] = []
    for row in range(len(ROWS)):
        for col in range(len(COLS)):
            lux = _estimate_lux(col, row)
            occ_label, occ_factor, near_shelf = _occlusion_for_zone(col, row)
            zones.append(
                Zone(
                    id=f"{COLS[col]}{row + 1}",
                    name=_zone_name(col, row),
                    col=col,
                    row=row,
                    x=ORIGIN_X + col * CELL_W,
                    y=ORIGIN_Y + row * CELL_H,
                    lux=round(lux, 1),
                    lux_bucket=_lux_bucket(lux),
                    occlusion=occ_label,
                    occlusion_factor=occ_factor,
                    near_shelving=near_shelf,
                )
            )
    return zones


def score_threat(zone: Zone, covered: bool = False) -> tuple[float, ThreatLevel]:
    lux_t = LUX_THREAT[zone.lux_bucket]
    occ_t = OCCLUSION_THREAT.get(zone.occlusion, 0.5)
    angle_penalty = 0.0 if covered else ANGLE_PENALTY_UNCOVERED
    score = min(1.0, max(lux_t, occ_t) + angle_penalty)
    if score >= HIGH_THRESHOLD:
        level: ThreatLevel = "high"
    elif score >= MEDIUM_THRESHOLD:
        level = "medium"
    else:
        level = "low"
    return round(score, 3), level


def _coverage_distance(cam: tuple[float, float], zone: Zone) -> float:
    zx, zy = zone.centre
    return math.hypot(cam[0] - zx, cam[1] - zy)


def _camera_covers(cam_pos: tuple[float, float], zone: Zone) -> bool:
    dist = _coverage_distance(cam_pos, zone)
    if dist > 9.0:
        return False
    if zone.lux_bucket == "dim" and dist > 6.5:
        return False
    return True


def recommend_cameras(zones: list[Zone]) -> list[CameraMount]:
    """Place eye-level cameras at aisle intersections; avoid high-angle in dim zones."""
    candidates = [
        (1, 1, "CAM-01", "Aisle B intersection — primary PPE coverage"),
        (3, 1, "CAM-02", "Aisle C intersection — central walkway"),
        (2, 0, "CAM-03", "Main aisle north — outbound traffic"),
        (1, 3, "CAM-04", "Loading Bay 4 — dim zone requires eye-level mount"),
        (3, 3, "CAM-05", "South blind spot — secondary coverage for pallet maze"),
        (2, 2, "CAM-06", "Forklift path — mid-warehouse overlap"),
    ]
    mounts: list[CameraMount] = []
    for col, row, cam_id, note in candidates:
        x = ORIGIN_X + col * CELL_W + CELL_W / 2
        y = ORIGIN_Y + row * CELL_H + CELL_H / 2
        zone_here = next(z for z in zones if z.col == col and z.row == row)
        angle = 8.0 if zone_here.lux_bucket != "dim" else 5.0
        if zone_here.lux_bucket == "dim":
            note += " · Never use high-angle mount here"
        mount = CameraMount(
            id=cam_id,
            x=round(x, 2),
            y=round(y, 2),
            height_m=1.8,
            angle_deg=angle,
            note=note,
        )
        mount.covers = [
            z.id for z in zones if _camera_covers((mount.x, mount.y), z)
        ]
        mounts.append(mount)

    mounts.append(
        CameraMount(
            id="AVOID-01",
            x=ORIGIN_X + 0 * CELL_W + CELL_W / 2,
            y=ORIGIN_Y + 3 * CELL_H + CELL_H / 2,
            height_m=4.2,
            angle_deg=48.0,
            note="High oblique mount in dim corner — detection recall ~24%",
            avoid=True,
        )
    )
    return mounts


def _threat_reason(zone: Zone, covered: bool) -> str:
    parts: list[str] = []
    if zone.lux_bucket == "dim":
        parts.append(f"Dim lighting ({zone.lux:.0f} lux)")
    elif zone.lux_bucket == "normal":
        parts.append(f"Moderate lighting ({zone.lux:.0f} lux)")
    if zone.occlusion in ("partial", "heavy"):
        parts.append(f"{zone.occlusion} shelf occlusion")
    if not covered:
        parts.append("no eye-level camera coverage")
    if zone.lux_bucket == "dim" and zone.occlusion == "partial":
        parts.append("measured detection recall ~17% under similar conditions")
    elif zone.lux_bucket == "dim":
        parts.append("high risk for PPE blind spots")
    return " + ".join(parts) if parts else "Within acceptable monitoring range"


def _actions_for_zone(zone: Zone, covered: bool) -> list[str]:
    actions: list[str] = []
    if zone.lux_bucket == "dim":
        actions.append("Add supplemental LED lighting")
    if zone.occlusion in ("partial", "heavy"):
        actions.append("Clear sightlines near shelving or pallet stacks")
    if not covered:
        actions.append("Install eye-level camera (1.5–3 m from worker path)")
    if zone.lux_bucket == "dim" and not covered:
        actions.append("Avoid high-angle mounts — use eye level (0–10°)")
    if not actions:
        actions.append("Maintain current lighting and camera coverage")
    return actions


def build_site_plan() -> dict[str, object]:
    zones = build_warehouse_grid()
    cameras = recommend_cameras(zones)
    cam_positions = {c.id: (c.x, c.y) for c in cameras if not c.avoid}

    zone_plans: list[ZonePlan] = []
    for z in zones:
        covered_by = [
            cid
            for cid, pos in cam_positions.items()
            if _camera_covers(pos, z)
        ]
        covered = len(covered_by) > 0
        score, threat = score_threat(z, covered=covered)
        zone_plans.append(
            ZonePlan(
                id=z.id,
                name=z.name,
                x=z.x,
                y=z.y,
                width=CELL_W,
                height=CELL_H,
                lux=z.lux,
                lux_bucket=z.lux_bucket,
                occlusion=z.occlusion,
                threat=threat,
                threat_score=score,
                reason=_threat_reason(z, covered),
                actions=_actions_for_zone(z, covered),
                covered_by=covered_by,
            )
        )

    high_threat = [zp for zp in zone_plans if zp.threat == "high"]
    return {
        "warehouse": "SimReady warehouse_multiple_shelves",
        "generated_by": "crashlab site_planner",
        "disclaimer": (
            "Simulation-based guidance supports engineering review; "
            "it does not replace on-site surveys or real-world validation."
        ),
        "measured_baselines": {
            "dim_partial_recall": _MEASURED_FAILURES[("dim", "partial")],
            "high_oblique_partial_recall": _MEASURED_FAILURES[("high_oblique", "partial")],
            "bright_visible_recall": _MEASURED_FAILURES[("bright", "visible")],
        },
        "summary": {
            "total_zones": len(zone_plans),
            "high_threat_zones": len(high_threat),
            "cameras_recommended": len([c for c in cameras if not c.avoid]),
            "zones_needing_lighting": len(
                [zp for zp in zone_plans if zp.lux_bucket == "dim"]
            ),
        },
        "zones": [asdict(zp) for zp in zone_plans],
        "cameras": [asdict(c) for c in cameras],
    }


def export_site_plan(out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = build_site_plan()
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out
