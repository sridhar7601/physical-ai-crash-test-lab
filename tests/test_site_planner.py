"""Tests for warehouse site planner."""

from __future__ import annotations

import unittest

from crashlab.site_planner import (
    HIGH_THRESHOLD,
    build_site_plan,
    build_warehouse_grid,
    recommend_cameras,
    score_threat,
)


class SitePlannerTests(unittest.TestCase):
    def test_grid_has_24_zones(self) -> None:
        zones = build_warehouse_grid()
        self.assertEqual(len(zones), 24)
        ids = {z.id for z in zones}
        self.assertEqual(len(ids), 24)
        self.assertIn("A1", ids)
        self.assertIn("F4", ids)

    def test_dim_corners_score_high_without_coverage(self) -> None:
        zones = build_warehouse_grid()
        dim_corner = next(z for z in zones if z.id == "A4")
        score, level = score_threat(dim_corner, covered=False)
        self.assertGreaterEqual(score, HIGH_THRESHOLD)
        self.assertEqual(level, "high")

    def test_bright_zone_scores_low(self) -> None:
        zones = build_warehouse_grid()
        bright = next(z for z in zones if z.lux_bucket == "bright" and z.occlusion == "clear")
        score, level = score_threat(bright, covered=True)
        self.assertLess(score, HIGH_THRESHOLD)
        self.assertEqual(level, "low")

    def test_coverage_reduces_threat(self) -> None:
        zones = build_warehouse_grid()
        zone = next(z for z in zones if z.occlusion in ("partial", "heavy"))
        uncovered, _ = score_threat(zone, covered=False)
        covered, _ = score_threat(zone, covered=True)
        self.assertGreater(uncovered, covered)

    def test_cameras_recommend_eye_level(self) -> None:
        zones = build_warehouse_grid()
        cameras = recommend_cameras(zones)
        mounts = [c for c in cameras if not c.avoid]
        self.assertGreaterEqual(len(mounts), 4)
        for cam in mounts:
            self.assertAlmostEqual(cam.height_m, 1.8)
            self.assertLessEqual(cam.angle_deg, 10.0)
            self.assertGreater(len(cam.covers), 0)

    def test_avoid_placement_flagged(self) -> None:
        zones = build_warehouse_grid()
        cameras = recommend_cameras(zones)
        avoid = [c for c in cameras if c.avoid]
        self.assertEqual(len(avoid), 1)
        self.assertGreater(avoid[0].angle_deg, 35.0)

    def test_site_plan_structure(self) -> None:
        plan = build_site_plan()
        self.assertEqual(plan["summary"]["total_zones"], 24)
        self.assertIn("zones", plan)
        self.assertIn("cameras", plan)
        self.assertIn("disclaimer", plan)
        self.assertGreater(plan["summary"]["high_threat_zones"], 0)

    def test_every_zone_has_actions(self) -> None:
        plan = build_site_plan()
        for zone in plan["zones"]:
            self.assertTrue(zone["actions"])
            self.assertIn(zone["threat"], ("low", "medium", "high"))


if __name__ == "__main__":
    unittest.main()
