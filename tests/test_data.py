"""Data consistency tests.

These check that the synthetic dataset holds together as a quality record set:
that references resolve, that dates run in a sensible order, and that the NCR
workflow statuses are logically coherent. A dataset that fails these would
undermine every analysis built on top of it.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.config import DEFECT_CATEGORIES, REPORTING_DATE, SEVERITIES
from src.data_loader import load_data


@pytest.fixture(scope="module")
def data():
    return load_data()


# ---------------------------------------------------------------------------
# Shape and volume
# ---------------------------------------------------------------------------

def test_expected_record_volumes(data):
    assert len(data.suppliers) == 5
    assert 5 <= len(data.components) <= 7
    assert 1500 <= len(data.inspections) <= 3000
    assert 25 <= len(data.ncrs) <= 40
    assert 15 <= len(data.actions) <= 25


def test_identifiers_are_unique(data):
    for frame, column in [
        (data.suppliers, "supplier_id"),
        (data.components, "component_id"),
        (data.inspections, "inspection_id"),
        (data.ncrs, "ncr_id"),
        (data.actions, "action_id"),
    ]:
        assert frame[column].is_unique, f"{column} contains duplicates"


def test_no_missing_values_in_key_columns(data):
    required = {
        "inspections": ["inspection_id", "inspection_date", "supplier_id", "component_id", "measured_value"],
        "ncrs": ["ncr_id", "date_raised", "supplier_id", "component_id", "defect_category", "severity"],
        "actions": ["action_id", "ncr_id", "owner", "due_date", "status"],
    }
    for name, columns in required.items():
        frame = getattr(data, name)
        for column in columns:
            assert frame[column].notna().all(), f"{name}.{column} has missing values"


# ---------------------------------------------------------------------------
# Referential integrity
# ---------------------------------------------------------------------------

def test_inspection_references_resolve(data):
    supplier_ids = set(data.suppliers["supplier_id"])
    component_ids = set(data.components["component_id"])
    assert set(data.inspections["supplier_id"]) <= supplier_ids
    assert set(data.inspections["component_id"]) <= component_ids


def test_ncr_references_resolve(data):
    assert set(data.ncrs["supplier_id"]) <= set(data.suppliers["supplier_id"])
    assert set(data.ncrs["component_id"]) <= set(data.components["component_id"])


def test_ncr_supplier_component_pairs_exist_in_inspections(data):
    """An NCR must be raised against a combination the supplier actually makes."""
    valid_pairs = set(zip(data.inspections["supplier_id"], data.inspections["component_id"]))
    ncr_pairs = set(zip(data.ncrs["supplier_id"], data.ncrs["component_id"]))
    assert ncr_pairs <= valid_pairs


def test_corrective_actions_reference_valid_ncrs(data):
    assert set(data.actions["ncr_id"]) <= set(data.ncrs["ncr_id"])


def test_ncrs_needing_a_capa_have_one(data):
    """Any NCR with a corrective action underway must appear in the tracker."""
    needs_capa = data.ncrs[data.ncrs["corrective_action_status"].isin(["In progress", "Complete"])]
    tracked = set(data.actions["ncr_id"])
    missing = set(needs_capa["ncr_id"]) - tracked
    assert not missing, f"NCRs with a corrective action but no tracker record: {sorted(missing)}"


def test_categories_and_severities_are_from_the_controlled_lists(data):
    assert set(data.ncrs["defect_category"]) <= set(DEFECT_CATEGORIES)
    assert set(data.ncrs["severity"]) <= set(SEVERITIES)

    defects = data.inspections[data.inspections["defect_flag"] == 1]
    assert set(defects["defect_category"]) <= set(DEFECT_CATEGORIES)
    assert set(defects["severity"]) <= set(SEVERITIES)


# ---------------------------------------------------------------------------
# Inspection record internal logic
# ---------------------------------------------------------------------------

def test_out_of_specification_measurements_are_flagged_as_defects(data):
    """A measurement outside the limits must be recorded as non-conforming."""
    out_of_spec = data.inspections[
        (data.inspections["measured_value"] > data.inspections["usl"])
        | (data.inspections["measured_value"] < data.inspections["lsl"])
    ]
    assert (out_of_spec["in_spec"] == 0).all()
    assert (out_of_spec["defect_flag"] == 1).all()
    assert out_of_spec["defect_category"].isin(["Dimensional deviation", "Positional tolerance"]).all()


def test_in_specification_measurements_are_marked_in_spec(data):
    within = data.inspections[
        (data.inspections["measured_value"] <= data.inspections["usl"])
        & (data.inspections["measured_value"] >= data.inspections["lsl"])
    ]
    assert (within["in_spec"] == 1).all()


def test_defect_flag_and_category_agree(data):
    """A defect must name a category; a conforming unit must not."""
    flagged = data.inspections["defect_flag"] == 1
    assert (data.inspections.loc[flagged, "defect_category"].astype(str).str.len() > 0).all()
    assert (data.inspections.loc[~flagged, "defect_category"].astype(str) == "").all()
    assert (data.inspections.loc[~flagged, "severity"].astype(str) == "").all()


def test_specification_limits_match_the_component_master(data):
    """Limits on an inspection row must match the component record, not drift."""
    merged = data.inspections.merge(
        data.components[["component_id", "nominal", "lsl", "usl"]],
        on="component_id",
        suffixes=("", "_master"),
    )
    assert (merged["lsl"] == merged["lsl_master"]).all()
    assert (merged["usl"] == merged["usl_master"]).all()
    assert (merged["nominal"] == merged["nominal_master"]).all()


def test_specification_limits_bracket_nominal(data):
    assert (data.components["lsl"] < data.components["nominal"]).all()
    assert (data.components["nominal"] < data.components["usl"]).all()


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

def test_inspection_dates_are_weekdays_within_the_reporting_window(data):
    dates = data.inspections["inspection_date"]
    assert dates.dt.dayofweek.max() <= 4, "Inspection records fall on a weekend"
    assert dates.max() <= pd.Timestamp(REPORTING_DATE)


def test_closed_ncrs_close_after_they_were_raised(data):
    closed = data.ncrs[data.ncrs["closure_status"] == "Closed"]
    assert (closed["closure_date"] >= closed["date_raised"]).all()
    assert (closed["closure_date"] <= pd.Timestamp(REPORTING_DATE)).all()


def test_open_ncrs_have_no_closure_date(data):
    open_ncrs = data.ncrs[data.ncrs["closure_status"] != "Closed"]
    assert open_ncrs["closure_date"].isna().all()


def test_closed_ncrs_have_a_closure_date(data):
    closed = data.ncrs[data.ncrs["closure_status"] == "Closed"]
    assert closed["closure_date"].notna().all()


def test_completed_actions_close_after_they_are_due_or_before(data):
    """A completed action must record a closure date; an open one must not."""
    complete = data.actions[data.actions["status"] == "Complete"]
    assert complete["closure_date"].notna().all()

    incomplete = data.actions[data.actions["status"] != "Complete"]
    assert incomplete["closure_date"].isna().all()


def test_action_closure_follows_the_ncr_being_raised(data):
    merged = data.actions.merge(data.ncrs[["ncr_id", "date_raised"]], on="ncr_id")
    closed = merged[merged["closure_date"].notna()]
    assert (closed["closure_date"] >= closed["date_raised"]).all()


# ---------------------------------------------------------------------------
# NCR workflow logic
#
# The order of the quality process is containment, investigation, corrective
# action, verification, closure. These tests assert that the recorded statuses
# cannot describe a sequence that skips a step.
# ---------------------------------------------------------------------------

def test_closed_ncrs_completed_containment_and_root_cause(data):
    closed = data.ncrs[data.ncrs["closure_status"] == "Closed"]
    assert (closed["containment_status"] == "Complete").all()
    assert (closed["root_cause_status"] == "Confirmed").all()


def test_closed_ncrs_were_verified_or_needed_no_action(data):
    """Closure requires either a verified corrective action, or an explicit
    decision that no formal corrective action was required."""
    closed = data.ncrs[data.ncrs["closure_status"] == "Closed"]
    verified = (closed["corrective_action_status"] == "Complete") & (closed["verification_status"] == "Verified")
    not_required = (closed["corrective_action_status"] == "Not required") & (
        closed["verification_status"] == "Not applicable"
    )
    assert (verified | not_required).all(), "An NCR is closed without verification or a 'not required' decision"


def test_corrective_action_never_starts_before_the_root_cause_is_confirmed(data):
    acting = data.ncrs[data.ncrs["corrective_action_status"].isin(["In progress", "Complete"])]
    assert (acting["root_cause_status"] == "Confirmed").all()


def test_verification_never_precedes_a_completed_corrective_action(data):
    verified = data.ncrs[data.ncrs["verification_status"] == "Verified"]
    assert (verified["corrective_action_status"] == "Complete").all()


def test_status_values_come_from_the_controlled_vocabularies(data):
    vocabularies = {
        "containment_status": {"Not started", "In progress", "Complete"},
        "root_cause_status": {"Not started", "Under investigation", "Confirmed"},
        "corrective_action_status": {"Not started", "Not required", "In progress", "Complete"},
        "verification_status": {"Not started", "In progress", "Verified", "Not applicable"},
        "closure_status": {"Open", "Closed"},
    }
    for column, allowed in vocabularies.items():
        unexpected = set(data.ncrs[column]) - allowed
        assert not unexpected, f"{column} contains unexpected values: {unexpected}"


def test_quantity_affected_is_positive(data):
    assert (data.ncrs["quantity_affected"] > 0).all()


# ---------------------------------------------------------------------------
# Derived fields
# ---------------------------------------------------------------------------

def test_repeat_flag_marks_only_subsequent_occurrences(data):
    """The first occurrence of a supplier/component/category is never a repeat."""
    ordered = data.ncrs.sort_values("date_raised")
    seen = set()
    for _, row in ordered.iterrows():
        key = (row["supplier_id"], row["component_id"], row["defect_category"])
        expected = key in seen
        assert bool(row["is_repeat"]) == expected, f"{row['ncr_id']} repeat flag is wrong"
        seen.add(key)


def test_at_least_one_repeat_exists(data):
    """The dataset is meant to contain repeat activity to analyse."""
    assert data.ncrs["is_repeat"].sum() >= 1


def test_dataset_is_reproducible():
    """Two loads of the same files must agree - the generator uses a fixed seed."""
    first = load_data()
    second = load_data()
    pd.testing.assert_frame_equal(first.inspections, second.inspections)
