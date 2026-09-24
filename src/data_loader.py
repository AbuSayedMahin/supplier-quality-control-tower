"""Loading, validating and filtering the synthetic dataset."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import DATA_DIR
from .quality_metrics import flag_repeat_ncrs
from .spc import order_for_analysis


@dataclass
class QualityData:
    suppliers: pd.DataFrame
    components: pd.DataFrame
    inspections: pd.DataFrame
    ncrs: pd.DataFrame
    actions: pd.DataFrame

    def supplier_name(self, supplier_id: str) -> str:
        match = self.suppliers.loc[self.suppliers["supplier_id"] == supplier_id, "supplier_name"]
        return str(match.iloc[0]) if len(match) else supplier_id

    def component_name(self, component_id: str) -> str:
        match = self.components.loc[self.components["component_id"] == component_id, "component_name"]
        return str(match.iloc[0]) if len(match) else component_id

    def component_spec(self, component_id: str) -> dict:
        """Nominal and specification limits for a component's critical characteristic."""
        row = self.components.loc[self.components["component_id"] == component_id]
        if not len(row):
            raise KeyError(f"Unknown component: {component_id}")
        return row.iloc[0].to_dict()

    def label_map(self, kind: str) -> dict:
        """'CMP-101 - High-Speed Rotating Shaft' style labels for select boxes."""
        if kind == "supplier":
            return dict(zip(self.suppliers["supplier_id"], self.suppliers["supplier_id"] + " - " + self.suppliers["supplier_name"]))
        return dict(zip(self.components["component_id"], self.components["component_id"] + " - " + self.components["component_name"]))


def load_data(data_dir=None) -> QualityData:
    """Read the five CSV files and derive the fields the application needs."""
    data_dir = data_dir or DATA_DIR

    suppliers = pd.read_csv(data_dir / "suppliers.csv")
    components = pd.read_csv(data_dir / "components.csv")

    inspections = pd.read_csv(data_dir / "inspections.csv", parse_dates=["inspection_date"])
    inspections["defect_category"] = inspections["defect_category"].fillna("")
    inspections["severity"] = inspections["severity"].fillna("")
    # Put the records into a single deterministic production order at the point
    # of loading. Moving ranges are calculated between consecutive parts, so the
    # sequence is part of the arithmetic - see order_for_analysis().
    inspections = order_for_analysis(inspections)

    ncrs = pd.read_csv(data_dir / "ncrs.csv", parse_dates=["date_raised"])
    ncrs["closure_date"] = pd.to_datetime(ncrs["closure_date"], errors="coerce")
    # Derived rather than stored, so the definition of "repeat" lives in one
    # place in code and can be explained and tested.
    ncrs["is_repeat"] = flag_repeat_ncrs(ncrs)
    ncrs["days_open"] = (
        ncrs["closure_date"].fillna(pd.Timestamp(inspections["inspection_date"].max())) - ncrs["date_raised"]
    ).dt.days

    actions = pd.read_csv(data_dir / "corrective_actions.csv", parse_dates=["due_date"])
    actions["closure_date"] = pd.to_datetime(actions["closure_date"], errors="coerce")

    return QualityData(
        suppliers=suppliers,
        components=components,
        inspections=inspections,
        ncrs=ncrs,
        actions=actions,
    )


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

@dataclass
class FilterState:
    suppliers: list
    components: list
    date_from: pd.Timestamp
    date_to: pd.Timestamp
    defect_categories: list
    severities: list

    def is_default(self, data: QualityData) -> bool:
        return (
            len(self.suppliers) == len(data.suppliers)
            and len(self.components) == len(data.components)
            and self.date_from <= data.inspections["inspection_date"].min()
            and self.date_to >= data.inspections["inspection_date"].max()
            and not self.defect_categories
            and not self.severities
        )


def apply_filters(data: QualityData, state: FilterState) -> QualityData:
    """Apply the sidebar filters consistently to inspections, NCRs and actions.

    Defect category and severity filters only make sense for records that
    describe a non-conformance, so they are applied to defective inspection rows
    and to NCRs. When either is active, conforming inspection rows are excluded
    as well, because a category filter is implicitly a question about defects.
    """
    insp = data.inspections
    insp = insp[insp["supplier_id"].isin(state.suppliers)]
    insp = insp[insp["component_id"].isin(state.components)]
    insp = insp[(insp["inspection_date"] >= state.date_from) & (insp["inspection_date"] <= state.date_to)]

    if state.defect_categories:
        insp = insp[insp["defect_category"].isin(state.defect_categories)]
    if state.severities:
        insp = insp[insp["severity"].isin(state.severities)]

    ncrs = data.ncrs
    ncrs = ncrs[ncrs["supplier_id"].isin(state.suppliers)]
    ncrs = ncrs[ncrs["component_id"].isin(state.components)]
    ncrs = ncrs[(ncrs["date_raised"] >= state.date_from) & (ncrs["date_raised"] <= state.date_to)]
    if state.defect_categories:
        ncrs = ncrs[ncrs["defect_category"].isin(state.defect_categories)]
    if state.severities:
        ncrs = ncrs[ncrs["severity"].isin(state.severities)]

    actions = data.actions[data.actions["ncr_id"].isin(set(ncrs["ncr_id"]))]

    return QualityData(
        suppliers=data.suppliers[data.suppliers["supplier_id"].isin(state.suppliers)],
        components=data.components[data.components["component_id"].isin(state.components)],
        inspections=insp,
        ncrs=ncrs,
        actions=actions,
    )
