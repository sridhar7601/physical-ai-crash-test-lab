"""End-to-end integrity of the loop.

The central test here is `test_analyser_rediscovers_the_seeded_weakness`. The
fixture detector is built with a known weak spot; the analyser is given only
the frames and must find it on its own. If that test ever fails, the
instrument is broken and nothing else in the report can be trusted.
"""

from __future__ import annotations

import unittest

from crashlab import fixtures
from crashlab.analysis import NoTargetError, analyse, target_conditions
from crashlab.compare import ComparisonError, compare
from crashlab.evaluate import EvalConfig, EvaluationError, ModelRef, evaluate
from crashlab.report import build_report, is_synthetic
from crashlab.suite import build_suite, stratified_split


def build(replicates=20, test_per_cell=10):
    full = build_suite("test_ppe", replicates=replicates)
    return stratified_split(full, test_per_cell=test_per_cell)


def run(profile, test, truth, config=None):
    preds = fixtures.prediction_set(test.scenarios, truth, profile)
    return evaluate(
        test, truth, preds,
        model=fixtures.model_ref(profile),
        config=config or EvalConfig(),
        data_source=fixtures.DATA_SOURCE,
    )


class TestFixtureGeometry(unittest.TestCase):
    """Guard the fixture itself: jittered predictions must remain matchable."""

    def test_jittered_predictions_clear_the_iou_threshold(self):
        from crashlab.boxes import iou

        _, test = build(replicates=6, test_per_cell=5)
        truth = fixtures.truth_set(test.scenarios)
        checked = 0
        for scenario in test.scenarios:
            gt = truth[scenario.scenario_id]
            preds = fixtures.predict(scenario, gt, fixtures.BASELINE_PROFILE)
            for pred in preds:
                match = next((g for g in gt if g.label == pred.label), None)
                if match is None:
                    continue  # hallucinated box: no truth to compare against
                checked += 1
                self.assertGreater(
                    iou(pred, match), 0.5,
                    f"jitter pushed {pred.label} below the IoU threshold on "
                    f"{scenario.scenario_id}; recall measurements would be "
                    f"contaminated by localisation error",
                )
        self.assertGreater(checked, 100, "too few boxes checked to be meaningful")

    def test_far_frames_contain_smaller_workers(self):
        from crashlab.schema import Condition
        from crashlab.schema import make_scenario

        heights = {}
        for distance in ("near", "mid", "far"):
            condition = Condition("bright", "eye_level", distance, "visible", "low")
            scenario = make_scenario("s", condition, 0)
            person = next(b for b in fixtures.truth_boxes(scenario) if b.label == "person")
            heights[distance] = person.y2 - person.y1
        self.assertGreater(heights["near"], heights["mid"])
        self.assertGreater(heights["mid"], heights["far"])

    def test_absent_helmet_state_produces_no_hat_ground_truth(self):
        from crashlab.schema import Condition, make_scenario

        condition = Condition("bright", "eye_level", "near", "absent", "low")
        boxes = fixtures.truth_boxes(make_scenario("s", condition, 0))
        self.assertEqual([b.label for b in boxes], ["person"])

    def test_predictions_are_reproducible(self):
        _, test = build(replicates=6, test_per_cell=5)
        truth = fixtures.truth_set(test.scenarios)
        a = fixtures.prediction_set(test.scenarios, truth, fixtures.BASELINE_PROFILE)
        b = fixtures.prediction_set(test.scenarios, truth, fixtures.BASELINE_PROFILE)
        self.assertEqual(a, b)

    def test_baseline_and_candidate_differ(self):
        _, test = build(replicates=6, test_per_cell=5)
        truth = fixtures.truth_set(test.scenarios)
        a = fixtures.prediction_set(test.scenarios, truth, fixtures.BASELINE_PROFILE)
        b = fixtures.prediction_set(test.scenarios, truth, fixtures.CANDIDATE_PROFILE)
        self.assertNotEqual(a, b)


class TestEvaluationGuards(unittest.TestCase):
    def setUp(self):
        self.train, self.test = build(replicates=6, test_per_cell=5)
        self.truth = fixtures.truth_set(self.test.scenarios)

    def test_missing_ground_truth_is_refused(self):
        partial = dict(self.truth)
        partial.pop(self.test.scenarios[0].scenario_id)
        with self.assertRaises(EvaluationError):
            evaluate(self.test, partial, {}, model=ModelRef("m", "v"))

    def test_silently_skipped_frames_are_refused(self):
        # A model that crashes on dark frames would otherwise score beautifully
        # on the frames it survived.
        preds = fixtures.prediction_set(self.test.scenarios, self.truth,
                                        fixtures.BASELINE_PROFILE)
        preds.pop(self.test.scenarios[0].scenario_id)
        with self.assertRaises(EvaluationError) as ctx:
            evaluate(self.test, self.truth, preds, model=ModelRef("m", "v"))
        self.assertIn("overstate", str(ctx.exception))

    def test_empty_predictions_allowed_when_declared_deliberate(self):
        evaluation = evaluate(
            self.test, self.truth, {}, model=ModelRef("m", "v"), require_complete=False
        )
        # Detected nothing: every hat is a miss, and no hat is hallucinated.
        self.assertEqual(evaluation.overall().detection["hard_hat"].counts.tp, 0)
        self.assertEqual(evaluation.overall().safety.dangerous_misses, 0)


class TestFailureDiscovery(unittest.TestCase):
    """The instrument must find the planted fault without being told."""

    @classmethod
    def setUpClass(cls):
        cls.train, cls.test = build()
        cls.truth = fixtures.truth_set(cls.test.scenarios)
        cls.baseline = run(fixtures.BASELINE_PROFILE, cls.test, cls.truth)
        cls.analysis = analyse(cls.baseline)

    def test_analyser_rediscovers_the_seeded_weakness(self):
        # BASELINE_PROFILE degrades hardest at dim + partial. The analyser sees
        # only frames and must rank that interaction worst.
        worst_names = [f.slice_name for f in self.analysis.findings[:3]]
        self.assertTrue(
            any("dim+partial" in name for name in worst_names),
            f"analyser failed to surface the seeded dim+partial weakness; "
            f"top three were {worst_names}",
        )

    def test_easy_conditions_look_healthy(self):
        # The premise of the product: a model can pass the conditions a team
        # happens to test while failing badly elsewhere.
        easy = self.baseline.by_factor_pair("lighting", "helmet_state")["bright+visible"]
        self.assertGreater(easy.primary("hard_hat_recall").value, 0.90)

    def test_the_hole_is_far_worse_than_the_headline(self):
        overall = self.baseline.overall().primary("hard_hat_recall").value
        worst = self.analysis.findings[0].rate.value
        self.assertLess(worst, overall - 0.25,
                        "the weak slice is not meaningfully worse than the average, "
                        "so there is nothing for the product to reveal")

    def test_underpowered_slices_are_withheld_from_findings(self):
        for finding in self.analysis.findings:
            self.assertGreaterEqual(finding.rate.denominator, self.analysis.min_samples)
        for finding in self.analysis.underpowered:
            self.assertLess(finding.rate.denominator, self.analysis.min_samples)

    def test_undefined_metrics_are_excluded_entirely(self):
        # hard_hat recall is undefined where no hats exist (helmet_state=absent).
        every = list(self.analysis.findings) + list(self.analysis.underpowered)
        for finding in every:
            self.assertTrue(finding.rate.is_reportable)
            self.assertNotIn("absent", finding.slice_name)

    def test_dangerous_miss_ranking_inverts_correctly(self):
        inverted = analyse(
            self.baseline, metric="dangerous_miss_rate", higher_is_better=False
        )
        # For a metric where high is bad, "worst first" means ordering by the
        # UPPER confidence bound — the worst plausible value — mirroring the
        # lower bound used for higher-is-better metrics. Point estimates are
        # therefore not monotonic: a wide interval around 0.25 can legitimately
        # outrank a narrow one around 0.32.
        uppers = [
            f.rate.interval[1] for f in inverted.findings if f.rate.interval is not None
        ]
        self.assertEqual(uppers, sorted(uppers, reverse=True),
                         "dangerous-miss ranking is not ordered by worst plausible rate")
        self.assertGreater(len(uppers), 5, "too few slices to verify ordering")

    def test_ranking_direction_actually_differs_between_metrics(self):
        # A guard against the higher_is_better flag being ignored entirely.
        ascending = analyse(self.baseline, metric="hard_hat_recall")
        descending = analyse(
            self.baseline, metric="dangerous_miss_rate", higher_is_better=False
        )
        self.assertNotEqual(
            ascending.findings[0].slice_name, descending.findings[0].slice_name
        )


class TestTargeting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train, cls.test = build()
        cls.truth = fixtures.truth_set(cls.test.scenarios)
        cls.baseline = run(fixtures.BASELINE_PROFILE, cls.test, cls.truth)

    def test_target_is_renderable_and_matches_the_finding(self):
        analysis = analyse(self.baseline)
        target = target_conditions(analysis, self.baseline, top_n=1)
        self.assertGreater(len(target.conditions), 0)
        constraints = target.source_finding.constraints
        direct = len(target.conditions) - target.neighbour_count
        for condition in target.conditions[:direct]:
            for factor, bucket in constraints.items():
                self.assertEqual(getattr(condition, factor), bucket)

    def test_neighbours_are_included(self):
        analysis = analyse(self.baseline)
        target = target_conditions(analysis, self.baseline, top_n=1)
        self.assertGreater(target.neighbour_count, 0,
                           "remediation should widen beyond the exact cell")

    def test_impossible_target_raises_rather_than_returning_nothing(self):
        # An absurdly high sample bar leaves no eligible finding at all.
        analysis = analyse(self.baseline, min_samples=10_000)
        self.assertEqual(analysis.findings, ())
        with self.assertRaises(NoTargetError):
            target_conditions(analysis, self.baseline)


class TestComparisonGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train, cls.test = build()
        cls.truth = fixtures.truth_set(cls.test.scenarios)
        cls.baseline = run(fixtures.BASELINE_PROFILE, cls.test, cls.truth)
        cls.candidate = run(fixtures.CANDIDATE_PROFILE, cls.test, cls.truth)

    def test_refuses_a_different_test_suite(self):
        _, other = build(replicates=20, test_per_cell=11)
        other_truth = fixtures.truth_set(other.scenarios)
        other_eval = run(fixtures.CANDIDATE_PROFILE, other, other_truth)
        with self.assertRaises(ComparisonError) as ctx:
            compare(self.baseline, other_eval)
        self.assertIn("different test suites", str(ctx.exception))

    def test_refuses_different_thresholds(self):
        strict = run(fixtures.CANDIDATE_PROFILE, self.test, self.truth,
                     config=EvalConfig(score_threshold=0.7))
        with self.assertRaises(ComparisonError) as ctx:
            compare(self.baseline, strict)
        self.assertIn("threshold", str(ctx.exception))

    def test_refuses_to_compare_a_model_with_itself(self):
        with self.assertRaises(ComparisonError):
            compare(self.baseline, self.baseline)

    def test_targeted_weakness_improves(self):
        comparison = compare(self.baseline, self.candidate)
        improved = {s.slice_name for s in comparison.improved()}
        self.assertTrue(
            any("dim+partial" in name for name in improved),
            f"remediation did not improve the targeted slice; improved={sorted(improved)}",
        )

    def test_deliberate_long_range_regression_is_reported(self):
        # CANDIDATE_PROFILE trades away long-range accuracy. A tool that hides
        # that is a sales demo, not an instrument.
        comparison = compare(self.baseline, self.candidate)
        regressed = {s.slice_name for s in comparison.regressed()}
        self.assertTrue(
            any("far" in name for name in regressed),
            f"the seeded long-range regression was not surfaced; "
            f"regressed={sorted(regressed)}",
        )

    def test_no_verdict_is_issued_on_thin_samples(self):
        comparison = compare(self.baseline, self.candidate)
        min_samples = self.baseline.config.min_samples_for_finding
        for delta in comparison.improved() + comparison.regressed():
            self.assertGreaterEqual(delta.baseline.denominator, min_samples,
                                    f"{delta.slice_name} claimed on too few samples")
            self.assertGreaterEqual(delta.candidate.denominator, min_samples)

    def test_every_slice_receives_exactly_one_classification(self):
        comparison = compare(self.baseline, self.candidate)
        buckets = (comparison.improved() + comparison.regressed()
                   + comparison.inconclusive() + comparison.underpowered()
                   + comparison.unchanged())
        self.assertEqual(len(buckets), len(comparison.slices))
        self.assertEqual(len({s.slice_name for s in buckets}), len(comparison.slices))


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train, cls.test = build()
        cls.truth = fixtures.truth_set(cls.test.scenarios)
        cls.baseline = run(fixtures.BASELINE_PROFILE, cls.test, cls.truth)
        cls.candidate = run(fixtures.CANDIDATE_PROFILE, cls.test, cls.truth)
        cls.analysis = analyse(cls.baseline)
        cls.comparison = compare(cls.baseline, cls.candidate)

    def render(self, **kwargs):
        return build_report(
            self.baseline, self.analysis, candidate=self.candidate,
            comparison=self.comparison, generated_at="test", **kwargs
        )

    def test_fixture_data_is_stamped_as_not_a_measurement(self):
        self.assertTrue(is_synthetic(self.baseline))
        report = self.render()
        self.assertIn("SYNTHETIC PLACEHOLDER", report.markdown)
        self.assertIn("Do not quote", report.markdown)
        self.assertTrue(report.payload["synthetic_placeholder"])

    def test_real_source_carries_no_banner(self):
        self.baseline.data_source = "isaac_sim_replicator"
        self.candidate.data_source = "isaac_sim_replicator"
        try:
            report = self.render()
            self.assertNotIn("SYNTHETIC PLACEHOLDER", report.markdown)
            self.assertFalse(report.payload["synthetic_placeholder"])
        finally:
            self.baseline.data_source = fixtures.DATA_SOURCE
            self.candidate.data_source = fixtures.DATA_SOURCE

    def test_report_states_its_limitations(self):
        report = self.render()
        self.assertIn("does not replace real-world validation", report.markdown)
        self.assertIn("domain gap", report.markdown)
        self.assertIn("No claim of safety certification", report.markdown)

    def test_report_records_the_fingerprint_for_reproduction(self):
        report = self.render()
        self.assertIn(self.baseline.manifest_fingerprint, report.markdown)

    def test_report_quotes_physical_units(self):
        report = self.render()
        self.assertIn("lux", report.markdown)
        self.assertIn("metres", report.markdown)

    def test_report_lists_what_was_not_tested(self):
        report = self.render(untested_notes=["Weather.", "Multiple workers."])
        self.assertIn("Weather.", report.markdown)
        self.assertIn("Multiple workers.", report.payload["untested"])

    def test_report_is_deterministic(self):
        self.assertEqual(self.render().markdown, self.render().markdown)

    def test_report_without_candidate_makes_no_improvement_claim(self):
        report = build_report(self.baseline, self.analysis, generated_at="test")
        self.assertIn("makes no improvement claim", report.markdown)


if __name__ == "__main__":
    unittest.main()
