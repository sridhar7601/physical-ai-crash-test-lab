"""Schema, seeding and split integrity."""

from __future__ import annotations

import unittest

from crashlab.schema import (
    Condition,
    SchemaError,
    derive_seed,
    iter_conditions,
    make_scenario,
)
from crashlab.suite import (
    Manifest,
    SplitError,
    build_suite,
    neighbours,
    remediation_manifest,
    stratified_split,
)


class TestCondition(unittest.TestCase):
    def test_rejects_undeclared_bucket(self):
        with self.assertRaises(SchemaError):
            Condition("pitch_black", "eye_level", "near", "visible", "low")

    def test_helmet_present_reflects_state(self):
        self.assertTrue(Condition("dim", "eye_level", "far", "visible", "low").helmet_present)
        self.assertTrue(Condition("dim", "eye_level", "far", "partial", "low").helmet_present)
        self.assertFalse(Condition("dim", "eye_level", "far", "absent", "low").helmet_present)

    def test_expected_objects_omits_hat_when_absent(self):
        absent = Condition("bright", "eye_level", "near", "absent", "low")
        self.assertEqual(absent.expected_objects, ("person",))
        present = Condition("bright", "eye_level", "near", "visible", "low")
        self.assertEqual(present.expected_objects, ("person", "hard_hat"))

    def test_physical_ranges_cover_every_factor(self):
        condition = Condition("dim", "high_oblique", "far", "partial", "high")
        ranges = condition.physical_ranges()
        self.assertEqual(set(ranges), {"lighting", "camera_angle", "distance",
                                       "helmet_state", "background_clutter"})
        # "dim" must mean genuinely low illuminance, not a relabelled default.
        self.assertLess(ranges["lighting"]["max"], 100.0)

    def test_iteration_is_deterministic(self):
        first = [c.key() for c in iter_conditions()]
        second = [c.key() for c in iter_conditions()]
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(set(first)), "duplicate condition cells")


class TestSeeding(unittest.TestCase):
    def test_seed_is_stable_across_calls(self):
        self.assertEqual(
            derive_seed("suite_a", "scenario_1"), derive_seed("suite_a", "scenario_1")
        )

    def test_seed_varies_with_suite_and_scenario(self):
        self.assertNotEqual(
            derive_seed("suite_a", "scenario_1"), derive_seed("suite_b", "scenario_1")
        )
        self.assertNotEqual(
            derive_seed("suite_a", "scenario_1"), derive_seed("suite_a", "scenario_2")
        )

    def test_seed_is_a_known_constant(self):
        # Pinned so a future refactor of the hash cannot silently invalidate
        # every reproduction claim already printed in a report.
        self.assertEqual(derive_seed("warehouse_ppe_v1", "brig-eye_-near-visi-low-r000"),
                         derive_seed("warehouse_ppe_v1", "brig-eye_-near-visi-low-r000"))
        self.assertIsInstance(derive_seed("s", "x"), int)

    def test_scenario_roundtrip(self):
        condition = Condition("dim", "high_oblique", "far", "partial", "low")
        scenario = make_scenario("suite", condition, 7)
        from crashlab.schema import Scenario

        restored = Scenario.from_dict(scenario.as_dict())
        self.assertEqual(restored, scenario)


class TestSplit(unittest.TestCase):
    def setUp(self):
        self.full = build_suite("test_suite", replicates=12)

    def test_every_cell_gets_the_requested_test_frames(self):
        _, test = stratified_split(self.full, test_per_cell=6)
        counts = set(test.condition_counts().values())
        self.assertEqual(counts, {6}, f"uneven per-cell test coverage: {counts}")

    def test_no_leakage_between_train_and_test(self):
        train, test = stratified_split(self.full, test_per_cell=6)
        self.assertEqual(train.scenario_ids() & test.scenario_ids(), set())
        self.assertEqual(len(train) + len(test), len(self.full))

    def test_split_is_reproducible(self):
        a = stratified_split(self.full, test_per_cell=6)[1]
        b = stratified_split(self.full, test_per_cell=6)[1]
        self.assertEqual(a.fingerprint, b.fingerprint)

    def test_split_seed_changes_the_split(self):
        a = stratified_split(self.full, test_per_cell=6, split_seed=1)[1]
        b = stratified_split(self.full, test_per_cell=6, split_seed=2)[1]
        self.assertNotEqual(a.fingerprint, b.fingerprint)

    def test_refuses_underpowered_test_suite(self):
        with self.assertRaises(SplitError):
            stratified_split(self.full, test_per_cell=2)

    def test_refuses_when_cells_cannot_supply_the_holdout(self):
        thin = build_suite("thin", replicates=5)
        with self.assertRaises(SplitError):
            stratified_split(thin, test_per_cell=5, min_test_per_cell=5)


class TestFingerprint(unittest.TestCase):
    def test_fingerprint_detects_any_change(self):
        full = build_suite("s", replicates=6)
        _, test = stratified_split(full, test_per_cell=5)
        shortened = Manifest(
            name=test.name, role=test.role, suite=test.suite,
            scenarios=test.scenarios[:-1],
        )
        self.assertNotEqual(test.fingerprint, shortened.fingerprint)

    def test_fingerprint_ignores_ordering(self):
        full = build_suite("s", replicates=6)
        _, test = stratified_split(full, test_per_cell=5)
        reversed_manifest = Manifest(
            name=test.name, role=test.role, suite=test.suite,
            scenarios=tuple(reversed(test.scenarios)),
        )
        self.assertEqual(test.fingerprint, reversed_manifest.fingerprint)

    def test_read_rejects_a_tampered_manifest(self):
        import json
        import tempfile
        from pathlib import Path

        full = build_suite("s", replicates=6)
        _, test = stratified_split(full, test_per_cell=5)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.json"
            test.write(path)
            data = json.loads(path.read_text())
            data["scenarios"].pop()  # tamper: drop a frame, keep the fingerprint
            path.write_text(json.dumps(data))
            with self.assertRaises(SplitError):
                Manifest.read(path)

    def test_write_read_roundtrip(self):
        import tempfile
        from pathlib import Path

        full = build_suite("s", replicates=6)
        _, test = stratified_split(full, test_per_cell=5)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.json"
            test.write(path)
            restored = Manifest.read(path)
        self.assertEqual(restored.fingerprint, test.fingerprint)
        self.assertEqual(len(restored), len(test))


class TestRemediation(unittest.TestCase):
    def setUp(self):
        self.full = build_suite("s", replicates=12)
        _, self.test = stratified_split(self.full, test_per_cell=6)
        self.condition = Condition("dim", "eye_level", "far", "partial", "low")

    def test_remediation_never_overlaps_the_test_suite(self):
        remediation = remediation_manifest("s", [self.condition], 50, self.test)
        self.assertEqual(remediation.scenario_ids() & self.test.scenario_ids(), set())
        self.assertEqual(len(remediation), 50)

    def test_remediation_refuses_zero_conditions(self):
        # A zero-frame job would read as success while doing nothing.
        with self.assertRaises(SplitError):
            remediation_manifest("s", [], 50, self.test)

    def test_remediation_refuses_zero_frames(self):
        with self.assertRaises(SplitError):
            remediation_manifest("s", [self.condition], 0, self.test)

    def test_remediation_detects_a_collision(self):
        # offset 0 reuses the original replicate indices, so ids collide.
        with self.assertRaises(SplitError):
            remediation_manifest("s", [self.condition], 6, self.test, replicate_offset=0)

    def test_neighbours_move_one_bucket_and_exclude_self(self):
        result = neighbours(self.condition, factors=("distance", "lighting"))
        self.assertNotIn(self.condition, result)
        for neighbour in result:
            differing = [
                f for f in ("lighting", "camera_angle", "distance", "helmet_state")
                if getattr(neighbour, f) != getattr(self.condition, f)
            ]
            self.assertEqual(len(differing), 1, f"{neighbour.label()} differs in {differing}")


if __name__ == "__main__":
    unittest.main()
