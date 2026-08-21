"""Box matching, safety verdicts, and metric arithmetic."""

from __future__ import annotations

import unittest

from crashlab.boxes import Box, BoxError, iou
from crashlab.matching import match_frame
from crashlab.metrics import Rate, wilson_interval


def box(label, x1, y1, x2, y2, score=None):
    return Box(label=label, x1=x1, y1=y1, x2=x2, y2=y2, score=score)


class TestBoxes(unittest.TestCase):
    def test_rejects_degenerate_box(self):
        with self.assertRaises(BoxError):
            box("person", 10, 10, 10, 20)
        with self.assertRaises(BoxError):
            box("person", 10, 10, 20, 5)

    def test_rejects_out_of_range_score(self):
        with self.assertRaises(BoxError):
            box("person", 0, 0, 10, 10, score=1.5)

    def test_identical_boxes_have_iou_one(self):
        a = box("person", 0, 0, 10, 10)
        self.assertAlmostEqual(iou(a, a), 1.0)

    def test_disjoint_boxes_have_iou_zero(self):
        self.assertEqual(iou(box("p", 0, 0, 10, 10), box("p", 20, 20, 30, 30)), 0.0)

    def test_touching_boxes_have_iou_zero(self):
        self.assertEqual(iou(box("p", 0, 0, 10, 10), box("p", 10, 0, 20, 10)), 0.0)

    def test_half_overlap_iou_is_one_third(self):
        # Two 10x10 boxes overlapping by 5x10: intersection 50, union 150.
        a, b = box("p", 0, 0, 10, 10), box("p", 5, 0, 15, 10)
        self.assertAlmostEqual(iou(a, b), 50 / 150)


class TestMatching(unittest.TestCase):
    def test_clean_match_is_a_true_positive(self):
        truth = [box("hard_hat", 0, 0, 10, 10)]
        preds = [box("hard_hat", 1, 1, 11, 11, score=0.9)]
        result = match_frame("s1", truth, preds, truth_compliant=True)
        counts = result.counts["hard_hat"]
        self.assertEqual((counts.tp, counts.fp, counts.fn), (1, 0, 0))

    def test_poor_overlap_is_both_a_false_positive_and_a_miss(self):
        truth = [box("hard_hat", 0, 0, 10, 10)]
        preds = [box("hard_hat", 8, 8, 18, 18, score=0.9)]
        result = match_frame("s1", truth, preds, truth_compliant=True)
        counts = result.counts["hard_hat"]
        self.assertEqual((counts.tp, counts.fp, counts.fn), (0, 1, 1))

    def test_low_confidence_prediction_is_discarded(self):
        truth = [box("hard_hat", 0, 0, 10, 10)]
        preds = [box("hard_hat", 0, 0, 10, 10, score=0.10)]
        result = match_frame("s1", truth, preds, truth_compliant=True, score_threshold=0.35)
        counts = result.counts["hard_hat"]
        self.assertEqual((counts.tp, counts.fp, counts.fn), (0, 0, 1))

    def test_one_truth_box_cannot_be_claimed_twice(self):
        truth = [box("hard_hat", 0, 0, 10, 10)]
        preds = [
            box("hard_hat", 0, 0, 10, 10, score=0.9),
            box("hard_hat", 1, 1, 11, 11, score=0.8),
        ]
        result = match_frame("s1", truth, preds, truth_compliant=True)
        counts = result.counts["hard_hat"]
        self.assertEqual((counts.tp, counts.fp), (1, 1))

    def test_classes_do_not_cross_match(self):
        truth = [box("person", 0, 0, 10, 10)]
        preds = [box("hard_hat", 0, 0, 10, 10, score=0.9)]
        result = match_frame("s1", truth, preds, truth_compliant=False)
        self.assertEqual(result.counts["person"].fn, 1)
        self.assertEqual(result.counts["hard_hat"].fp, 1)

    def test_higher_confidence_prediction_wins_the_match(self):
        truth = [box("hard_hat", 0, 0, 10, 10)]
        preds = [
            box("hard_hat", 4, 4, 14, 14, score=0.55),  # weaker overlap, lower score
            box("hard_hat", 0, 0, 10, 10, score=0.95),  # exact, higher score
        ]
        result = match_frame("s1", truth, preds, truth_compliant=True)
        self.assertEqual(result.counts["hard_hat"].tp, 1)
        self.assertAlmostEqual(max(result.matched_ious), 1.0)


class TestSafetyVerdict(unittest.TestCase):
    def test_hallucinated_hat_on_bare_head_is_a_dangerous_miss(self):
        truth = [box("person", 0, 0, 10, 40)]  # no hard hat: non-compliant
        preds = [box("hard_hat", 0, 0, 10, 8, score=0.6)]
        result = match_frame("s1", truth, preds, truth_compliant=False)
        self.assertTrue(result.safety.dangerous_miss)
        self.assertFalse(result.safety.false_alarm)
        self.assertFalse(result.safety.correct)

    def test_missed_hat_on_compliant_worker_is_only_a_false_alarm(self):
        truth = [box("person", 0, 0, 10, 40), box("hard_hat", 0, 0, 10, 8)]
        result = match_frame("s1", truth, [], truth_compliant=True)
        self.assertTrue(result.safety.false_alarm)
        self.assertFalse(result.safety.dangerous_miss)

    def test_correct_non_compliant_call(self):
        truth = [box("person", 0, 0, 10, 40)]
        preds = [box("person", 0, 0, 10, 40, score=0.9)]
        result = match_frame("s1", truth, preds, truth_compliant=False)
        self.assertTrue(result.safety.correct)
        self.assertFalse(result.safety.dangerous_miss)

    def test_below_threshold_hat_does_not_create_a_dangerous_miss(self):
        # A discarded low-confidence detection must not flip the verdict.
        truth = [box("person", 0, 0, 10, 40)]
        preds = [box("hard_hat", 0, 0, 10, 8, score=0.05)]
        result = match_frame("s1", truth, preds, truth_compliant=False, score_threshold=0.35)
        self.assertFalse(result.safety.dangerous_miss)


class TestRateAndInterval(unittest.TestCase):
    def test_zero_denominator_is_undefined_not_zero(self):
        rate = Rate("recall", 0, 0)
        self.assertIsNone(rate.value)
        self.assertIsNone(rate.interval)
        self.assertFalse(rate.is_reportable)
        self.assertIn("n/a", rate.format())

    def test_interval_contains_the_point_estimate(self):
        for successes, total in ((0, 10), (1, 10), (5, 10), (9, 10), (10, 10), (37, 60)):
            low, high = wilson_interval(successes, total)
            point = successes / total
            self.assertLessEqual(low, point + 1e-9, f"{successes}/{total}")
            self.assertGreaterEqual(high, point - 1e-9, f"{successes}/{total}")

    def test_interval_narrows_as_samples_grow(self):
        small = wilson_interval(5, 10)
        large = wilson_interval(500, 1000)
        self.assertGreater(small[1] - small[0], large[1] - large[0])

    def test_interval_stays_within_zero_and_one(self):
        for successes, total in ((0, 5), (5, 5), (0, 1000), (1000, 1000)):
            low, high = wilson_interval(successes, total)
            self.assertGreaterEqual(low, 0.0)
            self.assertLessEqual(high, 1.0)

    def test_interval_rejects_impossible_counts(self):
        with self.assertRaises(ValueError):
            wilson_interval(11, 10)

    def test_format_always_carries_the_denominator(self):
        self.assertIn("n=60", Rate("recall", 30, 60).format())


if __name__ == "__main__":
    unittest.main()
