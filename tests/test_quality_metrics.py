"""Tests for the quality engineering calculations.

Where possible a calculation is checked against a hand-worked example with a
known answer rather than against whatever the code happens to produce. A test
that only asserts the code agrees with itself would not catch a wrong formula.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.capability import calculate_capability, capability_is_trustworthy
from src.config import CASE_STUDY_COMPONENT, CASE_STUDY_SUPPLIER, PHASE_WINDOWS, REPORTING_DATE
from src.data_loader import load_data
from src.quality_metrics import (
    before_after_comparison,
    count_overdue_actions,
    defect_rate,
    first_pass_yield,
    pareto_table,
    ppm,
    supplier_scorecard,
    vital_few,
    weekly_trend,
)
from src.spc import (
    apply_control_rules,
    build_imr_table,
    calculate_control_limits,
    moving_ranges,
    order_for_analysis,
)


@pytest.fixture(scope="module")
def data():
    return load_data()


# ---------------------------------------------------------------------------
# Rate metrics - checked against arithmetic that can be done by hand
# ---------------------------------------------------------------------------

def test_defect_rate_basic():
    assert defect_rate(5, 100) == 0.05
    assert defect_rate(0, 250) == 0.0
    assert defect_rate(100, 100) == 1.0


def test_defect_rate_with_no_inspections_is_not_a_number():
    assert np.isnan(defect_rate(0, 0))


def test_ppm_is_defect_rate_scaled_by_one_million():
    assert ppm(5, 100) == 50_000
    assert ppm(1, 1_000_000) == 1.0
    assert ppm(3, 2000) == pytest.approx(1500.0)


def test_first_pass_yield_is_the_complement_of_the_defect_rate():
    assert first_pass_yield(5, 100) == pytest.approx(95.0)
    assert first_pass_yield(0, 500) == pytest.approx(100.0)


def test_ppm_and_fpy_are_consistent_with_each_other():
    defects, inspected = 37, 2040
    assert ppm(defects, inspected) / 1_000_000 + first_pass_yield(defects, inspected) / 100 == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Capability - worked example
#
# Using USL = 10.10, LSL = 9.90, mean = 10.05, sigma = 0.025:
#   Cp  = 0.20 / (6 x 0.025)          = 1.3333
#   Cpu = (10.10 - 10.05) / (3 x 0.025) = 0.6667
#   Cpl = (10.05 - 9.90)  / (3 x 0.025) = 2.0000
#   Cpk = min(Cpu, Cpl)                 = 0.6667
# ---------------------------------------------------------------------------

def _series_with(mean: float, sigma: float, n: int = 400, seed: int = 7) -> np.ndarray:
    """A sample rescaled to have exactly the requested mean and sample sd."""
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    x = (x - x.mean()) / x.std(ddof=1)
    return mean + sigma * x


def test_cp_and_cpk_match_the_hand_worked_example():
    values = _series_with(mean=10.05, sigma=0.025)
    result = calculate_capability(values, lsl=9.90, usl=10.10, nominal=10.00)

    assert result.mean == pytest.approx(10.05, abs=1e-9)
    assert result.sigma_overall == pytest.approx(0.025, abs=1e-9)

    # Pp and Ppk use the overall sigma, which is exactly the value set above.
    assert result.pp == pytest.approx(1.3333, abs=1e-3)
    assert result.ppk == pytest.approx(0.6667, abs=1e-3)


def test_cpk_never_exceeds_cp():
    for offset in [-0.04, -0.01, 0.0, 0.01, 0.04]:
        result = calculate_capability(_series_with(10.00 + offset, 0.02), lsl=9.90, usl=10.10, nominal=10.00)
        assert result.cpk <= result.cp + 1e-9
        assert result.ppk <= result.pp + 1e-9


def test_cp_equals_cpk_for_a_perfectly_centred_process():
    result = calculate_capability(_series_with(10.00, 0.02), lsl=9.90, usl=10.10, nominal=10.00)
    assert result.pp == pytest.approx(result.ppk, abs=1e-6)


def test_cpk_falls_as_the_process_moves_off_centre():
    """Cp stays put while Cpk drops - the diagnostic pattern in the case study."""
    centred = calculate_capability(_series_with(10.00, 0.02), lsl=9.90, usl=10.10, nominal=10.00)
    shifted = calculate_capability(_series_with(10.06, 0.02), lsl=9.90, usl=10.10, nominal=10.00)

    assert shifted.pp == pytest.approx(centred.pp, abs=1e-6)
    assert shifted.ppk < centred.ppk


def test_capability_reports_the_correct_observed_out_of_spec_count():
    values = np.array([9.85, 9.95, 10.00, 10.05, 10.15, 10.00, 10.02, 9.98])
    result = calculate_capability(values, lsl=9.90, usl=10.10, nominal=10.00)
    assert result.observed_out_of_spec == 2
    assert result.observed_out_of_spec_ppm == pytest.approx(250_000.0)


def test_capability_requires_at_least_two_measurements():
    with pytest.raises(ValueError):
        calculate_capability([10.0], lsl=9.9, usl=10.1)


def test_capability_caveats_fire_when_they_should():
    assert capability_is_trustworthy(True, 0.5, 200)  # unstable
    assert capability_is_trustworthy(False, 0.001, 200)  # not normal
    assert capability_is_trustworthy(False, 0.5, 12)  # small sample
    assert not capability_is_trustworthy(False, 0.5, 200)  # nothing wrong


# ---------------------------------------------------------------------------
# SPC
# ---------------------------------------------------------------------------

def test_moving_ranges_are_absolute_consecutive_differences():
    values = [10.0, 10.2, 9.9, 10.1]
    np.testing.assert_allclose(moving_ranges(values), [0.2, 0.3, 0.2])
    assert len(moving_ranges(values)) == len(values) - 1


def test_control_limits_use_the_published_constants():
    """UCL = X-bar + 2.660 x MR-bar, and sigma = MR-bar / 1.128."""
    values = np.array([10.0, 10.2, 9.9, 10.1, 10.0, 10.3, 9.8, 10.1])
    limits = calculate_control_limits(values)

    mr_bar = np.abs(np.diff(values)).mean()
    assert limits.center_line == pytest.approx(values.mean())
    assert limits.mr_center_line == pytest.approx(mr_bar)
    assert limits.ucl == pytest.approx(values.mean() + 2.660 * mr_bar)
    assert limits.lcl == pytest.approx(values.mean() - 2.660 * mr_bar)
    assert limits.sigma_within == pytest.approx(mr_bar / 1.128)
    assert limits.mr_ucl == pytest.approx(3.267 * mr_bar)
    assert limits.mr_lcl == 0.0


def test_control_limits_are_symmetric_about_the_centre_line():
    limits = calculate_control_limits([5.0, 5.1, 4.9, 5.05, 4.95, 5.02])
    assert (limits.ucl - limits.center_line) == pytest.approx(limits.center_line - limits.lcl)


def test_control_limits_need_at_least_two_observations():
    with pytest.raises(ValueError):
        calculate_control_limits([1.0])


def test_rule_1_detects_a_point_beyond_a_control_limit():
    baseline = np.array([10.0, 10.05, 9.95, 10.02, 9.98, 10.01, 9.99, 10.03])
    limits = calculate_control_limits(baseline)
    values = np.append(baseline, 99.0)
    flags = apply_control_rules(values, limits)
    assert flags["rule_1"].iloc[-1]
    assert not flags["rule_1"].iloc[:-1].any()


def test_rule_4_detects_eight_consecutive_points_on_one_side():
    baseline = np.array([10.0, 10.1, 9.9, 10.05, 9.95, 10.02, 9.98, 10.0])
    limits = calculate_control_limits(baseline)
    # Eight points just above the centre line: no single point is extreme, but
    # the run itself is the signal.
    values = np.append(baseline, np.full(8, limits.center_line + 0.01))
    flags = apply_control_rules(values, limits)
    assert flags["rule_4"].iloc[-8:].all()


def test_a_stable_series_produces_no_violations():
    rng = np.random.default_rng(3)
    values = rng.normal(10.0, 0.01, 60)
    limits = calculate_control_limits(values)
    flags = apply_control_rules(values, limits)
    # A little tolerance: random runs occasionally trip a rule by chance, which
    # is exactly the false alarm rate a control chart is designed to have.
    assert flags["any_rule"].mean() < 0.15


def test_ordering_is_deterministic_and_idempotent(data):
    """Record order is part of the moving range calculation, not presentation.

    Several parts share an inspection date. Sorting by date alone leaves their
    relative order undefined, and pandas' default sort is not stable, so the
    same data sorted twice could interleave same-day records differently and
    produce a different MR-bar and different control limits.
    """
    subset = data.inspections[
        (data.inspections["component_id"] == CASE_STUDY_COMPONENT)
        & (data.inspections["supplier_id"] == CASE_STUDY_SUPPLIER)
    ]
    once = order_for_analysis(subset)
    twice = order_for_analysis(once)
    pd.testing.assert_frame_equal(once, twice)

    # Ordering a shuffled copy must recover exactly the same sequence.
    shuffled = subset.sample(frac=1.0, random_state=11)
    pd.testing.assert_frame_equal(order_for_analysis(shuffled), once)


def test_spc_and_capability_agree_on_sigma_for_the_same_window(data):
    """Both routes estimate sigma from the moving range, so they must match.

    They disagreed at one point because build_imr_table re-sorted the records by
    date with an unstable sort, silently changing which parts were consecutive.
    """
    subset = data.inspections[
        (data.inspections["component_id"] == CASE_STUDY_COMPONENT)
        & (data.inspections["supplier_id"] == CASE_STUDY_SUPPLIER)
    ]
    subset = order_for_analysis(subset)
    spec = data.components[data.components["component_id"] == CASE_STUDY_COMPONENT].iloc[0]

    baseline_mask = (
        (subset["inspection_date"] >= "2026-01-05") & (subset["inspection_date"] <= "2026-02-27")
    ).reset_index(drop=True)
    _, limits = build_imr_table(subset, baseline_mask=baseline_mask)

    baseline_rows = subset[baseline_mask.to_numpy()]
    capability = calculate_capability(
        baseline_rows["measured_value"], lsl=spec["lsl"], usl=spec["usl"], nominal=spec["nominal"]
    )

    assert limits.n_baseline == capability.n
    assert limits.sigma_within == pytest.approx(capability.sigma_within, abs=1e-12)


def test_drift_is_detected_before_the_specification_is_breached(data):
    """The central SPC claim in the case study, asserted against the data."""
    subset = order_for_analysis(
        data.inspections[
            (data.inspections["component_id"] == CASE_STUDY_COMPONENT)
            & (data.inspections["supplier_id"] == CASE_STUDY_SUPPLIER)
        ]
    )

    baseline_mask = (
        (subset["inspection_date"] >= "2026-01-05") & (subset["inspection_date"] <= "2026-02-27")
    ).reset_index(drop=True)
    imr, _ = build_imr_table(subset, baseline_mask=baseline_mask)

    first_violation = imr.loc[imr["any_rule"], "inspection_date"].min()
    first_out_of_spec = imr.loc[imr["in_spec"] == 0, "inspection_date"].min()

    assert pd.notna(first_violation), "The control chart should signal the drift"
    assert pd.notna(first_out_of_spec), "The excursion should breach specification"
    assert first_violation < first_out_of_spec, "SPC must signal before the tolerance is breached"


def test_fitting_limits_to_drifting_data_misplaces_the_centre_line(data):
    """Why the baseline period matters.

    For an individuals chart, a slow drift does not widen the limits much - the
    moving range between consecutive parts hardly changes. What it does is drag
    the CENTRE LINE toward the middle of the drift. The consequence is the
    opposite of what people expect: the genuinely stable baseline period starts
    tripping run rules, because it now sits well below a centre line that has
    been pulled up by data from a process that had already changed.
    """
    subset = order_for_analysis(
        data.inspections[
            (data.inspections["component_id"] == CASE_STUDY_COMPONENT)
            & (data.inspections["supplier_id"] == CASE_STUDY_SUPPLIER)
        ]
    )

    baseline_mask = (
        (subset["inspection_date"] >= "2026-01-05") & (subset["inspection_date"] <= "2026-02-27")
    ).reset_index(drop=True)

    baseline_imr, baseline_limits = build_imr_table(subset, baseline_mask=baseline_mask)
    all_imr, all_limits = build_imr_table(subset, baseline_mask=None)

    # The centre line moves upward when the drifting data is included.
    assert all_limits.center_line > baseline_limits.center_line

    baseline_window = baseline_imr["inspection_date"] <= "2026-02-27"
    drift_window = (baseline_imr["inspection_date"] >= "2026-03-02") & (
        baseline_imr["inspection_date"] <= "2026-05-15"
    )

    # Correctly placed limits: the stable period is clean, the drift is flagged.
    assert baseline_imr.loc[baseline_window, "any_rule"].sum() == 0
    assert baseline_imr.loc[drift_window, "any_rule"].sum() > 50

    # Limits fitted to everything raise false signals on the stable period.
    assert all_imr.loc[baseline_window, "any_rule"].sum() > 0

    # And they miss real signals: fewer points now breach the control limits.
    assert all_imr["rule_1"].sum() < baseline_imr["rule_1"].sum()


# ---------------------------------------------------------------------------
# Pareto
# ---------------------------------------------------------------------------

def test_pareto_table_sorts_descending_and_accumulates_to_one_hundred():
    frame = pd.DataFrame({"defect_category": ["A"] * 5 + ["B"] * 3 + ["C"] * 2})
    table = pareto_table(frame, "defect_category")

    assert list(table["defect_category"]) == ["A", "B", "C"]
    assert list(table["count"]) == [5, 3, 2]
    assert list(table["cumulative_count"]) == [5, 8, 10]
    assert table["cumulative_percent"].iloc[-1] == pytest.approx(100.0)
    assert table["percent"].sum() == pytest.approx(100.0)


def test_vital_few_includes_the_category_that_crosses_the_threshold():
    frame = pd.DataFrame({"c": ["A"] * 50 + ["B"] * 30 + ["C"] * 15 + ["D"] * 5})
    table = pareto_table(frame, "c")
    # A = 50%, A+B = 80%, so the 80% group is A and B.
    assert vital_few(table, 80.0) == ["A", "B"]
    # At 85% the group must extend to include C.
    assert vital_few(table, 85.0) == ["A", "B", "C"]


def test_pareto_of_an_empty_frame_is_empty():
    empty = pd.DataFrame({"defect_category": pd.Series(dtype=str)})
    assert len(pareto_table(empty, "defect_category")) == 0


def test_pareto_counts_match_the_underlying_records(data):
    defects = data.inspections[data.inspections["defect_flag"] == 1]
    table = pareto_table(defects, "defect_category")
    assert table["count"].sum() == len(defects)


# ---------------------------------------------------------------------------
# Overdue actions and scorecard
# ---------------------------------------------------------------------------

def test_overdue_counts_only_incomplete_actions_past_their_due_date():
    actions = pd.DataFrame(
        {
            "status": ["Complete", "In progress", "In progress", "Not started"],
            "due_date": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-12-01", "2026-02-01"]),
        }
    )
    # Two are past 2026-06-01 and not complete; the completed one does not count
    # even though it was also past its due date.
    assert count_overdue_actions(actions, as_of="2026-06-01") == 2


def test_scorecard_ppm_matches_a_direct_calculation(data):
    scorecard = supplier_scorecard(
        data.inspections, data.ncrs, data.actions, data.suppliers, as_of=pd.Timestamp(REPORTING_DATE)
    )
    for _, row in scorecard.iterrows():
        subset = data.inspections[data.inspections["supplier_id"] == row["supplier_id"]]
        if not len(subset):
            continue
        expected = 1_000_000 * subset["defect_flag"].sum() / len(subset)
        assert row["ppm"] == pytest.approx(expected)
        assert row["fpy_pct"] == pytest.approx(100 - 100 * subset["defect_flag"].sum() / len(subset))


def test_scorecard_covers_every_supplier(data):
    scorecard = supplier_scorecard(data.inspections, data.ncrs, data.actions, data.suppliers)
    assert set(scorecard["supplier_id"]) == set(data.suppliers["supplier_id"])


def test_scorecard_inspected_totals_reconcile_with_the_dataset(data):
    scorecard = supplier_scorecard(data.inspections, data.ncrs, data.actions, data.suppliers)
    assert scorecard["inspected"].sum() == len(data.inspections)
    assert scorecard["defects"].sum() == data.inspections["defect_flag"].sum()


# ---------------------------------------------------------------------------
# Trend and before/after
# ---------------------------------------------------------------------------

def test_weekly_trend_totals_reconcile_with_the_source(data):
    trend = weekly_trend(data.inspections)
    assert trend["inspected"].sum() == len(data.inspections)
    assert trend["defects"].sum() == data.inspections["defect_flag"].sum()
    assert (trend["fpy_pct"] + trend["defect_rate_pct"]).round(6).eq(100.0).all()


def test_before_after_split_partitions_the_data_without_loss(data):
    comparison = before_after_comparison(data.inspections, "2026-05-18")
    assert comparison["inspected"].sum() == len(data.inspections)
    assert comparison["defects"].sum() == data.inspections["defect_flag"].sum()
    assert list(comparison["period"]) == ["Before corrective action", "After corrective action"]


# ---------------------------------------------------------------------------
# The case study must actually hold up
# ---------------------------------------------------------------------------

def test_the_case_study_shows_the_expected_capability_pattern(data):
    """Cp roughly holds while Cpk collapses, then both recover after the action."""
    subset = data.inspections[
        (data.inspections["component_id"] == CASE_STUDY_COMPONENT)
        & (data.inspections["supplier_id"] == CASE_STUDY_SUPPLIER)
    ]
    spec = data.components[data.components["component_id"] == CASE_STUDY_COMPONENT].iloc[0]

    results = {}
    for label, (start, end) in PHASE_WINDOWS.items():
        phase = subset[(subset["inspection_date"] >= start) & (subset["inspection_date"] <= end)]
        results[label] = calculate_capability(
            phase["measured_value"], lsl=spec["lsl"], usl=spec["usl"], nominal=spec["nominal"]
        )

    baseline = results["Baseline (stable)"]
    excursion = results["Excursion period"]
    post = results["Post-corrective action"]

    assert baseline.cpk > 1.33, "The baseline process should be capable"
    assert excursion.cpk < 1.00, "The excursion should be clearly incapable"
    assert post.cpk > 1.33, "Capability should recover after the corrective action"

    # The signature of a centring problem rather than a spread problem.
    assert excursion.cp - excursion.cpk > 0.5
    assert abs(excursion.centering_offset) > abs(baseline.centering_offset)
    assert abs(post.centering_offset) < abs(excursion.centering_offset)


def test_no_dimensional_non_conformances_after_the_corrective_action(data):
    """The verification claim in the case study, asserted against the data."""
    subset = data.inspections[
        (data.inspections["component_id"] == CASE_STUDY_COMPONENT)
        & (data.inspections["supplier_id"] == CASE_STUDY_SUPPLIER)
        & (data.inspections["inspection_date"] >= "2026-05-18")
    ]
    assert len(subset) > 100, "There must be enough post-change data to draw a conclusion"
    assert int((subset["in_spec"] == 0).sum()) == 0


def test_the_case_study_ncrs_are_closed_only_after_verification(data):
    case_ncrs = data.ncrs[
        (data.ncrs["supplier_id"] == CASE_STUDY_SUPPLIER)
        & (data.ncrs["component_id"] == CASE_STUDY_COMPONENT)
        & (data.ncrs["defect_category"] == "Dimensional deviation")
    ]
    assert len(case_ncrs) == 3
    assert (case_ncrs["closure_status"] == "Closed").all()
    assert (case_ncrs["verification_status"] == "Verified").all()

    # Closure must follow the date the corrective action was implemented.
    assert (case_ncrs["closure_date"] > pd.Timestamp("2026-05-15")).all()


def test_the_failed_first_corrective_action_is_recorded(data):
    """The dataset deliberately contains an action that did not work."""
    not_effective = data.actions[data.actions["verification_result"].str.startswith("Not effective")]
    assert len(not_effective) >= 1
