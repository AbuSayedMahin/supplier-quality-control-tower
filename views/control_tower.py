"""Quality control tower - the headline view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts
from src.config import POST_CHANGE_START, REPORTING_DATE
from src.data_loader import QualityData
from src.quality_metrics import summarise_quality, supplier_scorecard, weekly_trend

from .common import dataframe, fmt, interpretation, kpi_row, no_data, section_header


def render(data: QualityData, full: QualityData) -> None:
    st.header("Quality Control Tower")
    st.caption(
        "Incoming and in-process quality position across the supply base. "
        f"Figures reflect the current filter selection. Reporting date {REPORTING_DATE}."
    )

    if not len(data.inspections):
        no_data()
        return

    summary = summarise_quality(
        data.inspections, data.ncrs, data.actions, as_of=pd.Timestamp(REPORTING_DATE)
    )

    kpi_row(
        [
            ("Units inspected", fmt(summary.inspected), "Inspection records in the current selection."),
            ("Non-conforming units", fmt(summary.defects), "Units failing inspection for any reason."),
            ("Defect rate", f"{summary.defect_rate_pct:.2f}%", "Non-conforming units divided by units inspected."),
            ("PPM", fmt(summary.ppm), "Defective parts per million. The defect rate scaled by 1,000,000."),
            (
                "First pass yield",
                f"{summary.fpy_pct:.2f}%",
                "Share of units passing inspection first time. In this dataset each inspection is a "
                "first-pass check, so FPY is the complement of the defect rate.",
            ),
        ]
    )

    kpi_row(
        [
            ("Open NCRs", fmt(summary.open_ncrs), "Non-conformance reports not yet closed."),
            ("Closed NCRs", fmt(summary.closed_ncrs), "NCRs closed after corrective action verification."),
            (
                "Repeat NCRs",
                fmt(summary.repeat_ncrs),
                "NCRs where the same supplier, component and defect category had already been raised before. "
                "Repeats indicate corrective action that did not remove the cause.",
            ),
            (
                "Overdue actions",
                fmt(summary.overdue_actions),
                "Corrective actions past their due date and not yet complete, as at the reporting date.",
            ),
            ("Suppliers / components", f"{summary.suppliers} / {summary.components}", "Distinct entities in scope."),
        ]
    )

    st.divider()

    # ------------------------------------------------------------------
    # Trend
    # ------------------------------------------------------------------
    section_header(
        "Quality trend",
        "Weekly view. A single week is a small sample, so the shape of the trend matters more than any one point.",
    )

    trend = weekly_trend(data.inspections)
    metric_choice = st.radio(
        "Trend metric",
        ["PPM", "Defect rate (%)", "First pass yield (%)", "Units inspected"],
        horizontal=True,
        label_visibility="collapsed",
    )
    column_map = {
        "PPM": ("ppm", "Defective parts per million"),
        "Defect rate (%)": ("defect_rate_pct", "Defect rate (%)"),
        "First pass yield (%)": ("fpy_pct", "First pass yield (%)"),
        "Units inspected": ("inspected", "Units inspected"),
    }
    column, y_title = column_map[metric_choice]

    st.plotly_chart(
        charts.trend_chart(
            trend,
            column,
            f"Weekly {metric_choice.lower()}",
            y_title,
            reference_date=POST_CHANGE_START,
            reference_label="Corrective action<br>in effect",
        ),
        width='stretch',
    )

    st.divider()

    # ------------------------------------------------------------------
    # Supplier and component overviews
    # ------------------------------------------------------------------
    left, right = st.columns(2)

    with left:
        section_header("Supplier overview", "PPM by supplier for the current selection.")
        scorecard = supplier_scorecard(
            data.inspections, data.ncrs, data.actions, data.suppliers, as_of=pd.Timestamp(REPORTING_DATE)
        )
        scorecard = scorecard[scorecard["inspected"] > 0].sort_values("ppm", ascending=False)
        if len(scorecard):
            st.plotly_chart(
                charts.grouped_bar(
                    scorecard,
                    "supplier_name",
                    "ppm",
                    "PPM by supplier",
                    "PPM",
                    reference=25_000,
                    reference_label="Project review threshold",
                ),
                width='stretch',
            )

    with right:
        section_header("Component overview", "PPM by component for the current selection.")
        comp = (
            data.inspections.groupby("component_id")
            .agg(inspected=("defect_flag", "size"), defects=("defect_flag", "sum"))
            .reset_index()
        )
        comp["ppm"] = 1_000_000 * comp["defects"] / comp["inspected"]
        comp["component"] = comp["component_id"].map(full.label_map("component"))
        comp = comp.sort_values("ppm", ascending=False)
        st.plotly_chart(
            charts.grouped_bar(comp, "component_id", "ppm", "PPM by component", "PPM"),
            width='stretch',
        )

    st.divider()

    # ------------------------------------------------------------------
    # Open NCR status
    # ------------------------------------------------------------------
    section_header(
        "Open non-conformance status",
        "Where each open NCR currently sits in the containment, investigation, action and verification sequence.",
    )

    open_ncrs = data.ncrs[data.ncrs["closure_status"] != "Closed"].copy()
    if not len(open_ncrs):
        st.success("No open NCRs in the current selection.")
    else:
        display = open_ncrs[
            [
                "ncr_id", "date_raised", "supplier_id", "component_id", "defect_category", "severity",
                "containment_status", "root_cause_status", "corrective_action_status", "verification_status",
                "days_open",
            ]
        ].copy()
        display["date_raised"] = display["date_raised"].dt.strftime("%Y-%m-%d")
        display.columns = [
            "NCR", "Raised", "Supplier", "Component", "Defect category", "Severity",
            "Containment", "Root cause", "Corrective action", "Verification", "Days open",
        ]
        dataframe(display.sort_values("Days open", ascending=False))

    # ------------------------------------------------------------------
    # Interpretation
    # ------------------------------------------------------------------
    worst = None
    if len(data.inspections):
        by_supplier = (
            data.inspections.groupby("supplier_id")
            .agg(inspected=("defect_flag", "size"), defects=("defect_flag", "sum"))
            .reset_index()
        )
        by_supplier["ppm"] = 1_000_000 * by_supplier["defects"] / by_supplier["inspected"]
        by_supplier = by_supplier.sort_values("ppm", ascending=False)
        worst = by_supplier.iloc[0]

    lines = [
        f"Across {summary.inspected:,} inspection records the overall defect rate is "
        f"{summary.defect_rate_pct:.2f}% ({summary.ppm:,.0f} PPM), giving a first pass yield of "
        f"{summary.fpy_pct:.2f}%."
    ]
    if worst is not None:
        lines.append(
            f"{full.supplier_name(worst['supplier_id'])} shows the highest PPM in the selection at "
            f"{worst['ppm']:,.0f}. That figure on its own does not identify a cause; it identifies where to "
            "look next, which is the Pareto and then the individual non-conformance records."
        )
    if summary.repeat_ncrs:
        lines.append(
            f"{summary.repeat_ncrs} of {summary.open_ncrs + summary.closed_ncrs} NCRs are repeats of a "
            "previously recorded supplier, component and defect category combination. Repeat activity is the "
            "more useful signal here, because it points at corrective actions that contained a problem without "
            "removing its cause."
        )
    if summary.overdue_actions:
        lines.append(
            f"{summary.overdue_actions} corrective action(s) are past their due date and not yet complete."
        )

    interpretation(" ".join(lines))
