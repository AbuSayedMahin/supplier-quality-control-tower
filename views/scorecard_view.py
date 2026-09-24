"""Supplier quality scorecard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts
from src.config import REPORTING_DATE
from src.data_loader import QualityData
from src.quality_metrics import attention_flags, supplier_scorecard

from .common import dataframe, interpretation, no_data, section_header

PPM_THRESHOLD = 25_000


def render(data: QualityData, full: QualityData) -> None:
    st.header("Supplier Quality Scorecard")
    st.caption(
        "Per-supplier quality performance across the current filter selection. Deliberately not reduced to a "
        "single ranking score."
    )

    if not len(data.inspections):
        no_data()
        return

    scorecard = supplier_scorecard(
        data.inspections, data.ncrs, data.actions, data.suppliers, as_of=pd.Timestamp(REPORTING_DATE)
    )
    scorecard = scorecard[scorecard["inspected"] > 0]
    if not len(scorecard):
        no_data()
        return

    scorecard = attention_flags(scorecard, ppm_threshold=PPM_THRESHOLD)
    scorecard = scorecard.sort_values("ppm", ascending=False)

    st.info(
        "There is no overall supplier score in this view. Combining PPM, delivery and open actions into one "
        "number hides which of them is the problem, and any weighting used to do so would be arbitrary. The "
        "purpose of a scorecard is to show an engineer where attention is needed, not to produce a league table."
    )

    # ------------------------------------------------------------------
    # Table
    # ------------------------------------------------------------------
    table = scorecard[
        [
            "supplier_name", "category", "inspected", "defects", "ppm", "fpy_pct",
            "total_ncrs", "open_ncrs", "repeat_ncrs", "critical_ncrs", "overdue_actions",
            "on_time_delivery_pct",
        ]
    ].copy()
    table["ppm"] = table["ppm"].round(0)
    table["fpy_pct"] = table["fpy_pct"].round(2)
    table.columns = [
        "Supplier", "Category", "Inspected", "Defects", "PPM", "FPY %",
        "NCRs", "Open", "Repeat", "Critical", "Overdue actions", "OTD %",
    ]
    dataframe(table)

    st.markdown("**Where attention is required**")
    flags = scorecard[["supplier_name", "attention_required"]].copy()
    flags.columns = ["Supplier", "Threshold exceeded"]
    dataframe(flags)
    st.caption(
        f"Thresholds used here are project conventions: PPM above {PPM_THRESHOLD:,}, two or more repeat NCRs, "
        "any overdue corrective action, any critical NCR, or on-time delivery below 92%. In a real programme "
        "these would come from the quality agreement with each supplier rather than being chosen by the analyst."
    )

    # ------------------------------------------------------------------
    # Charts
    # ------------------------------------------------------------------
    st.divider()
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            charts.grouped_bar(
                scorecard, "supplier_name", "ppm", "PPM by supplier", "PPM",
                reference=PPM_THRESHOLD, reference_label="Review threshold",
            ),
            width='stretch',
        )
    with right:
        st.plotly_chart(
            charts.grouped_bar(
                scorecard.sort_values("on_time_delivery_pct"),
                "supplier_name", "on_time_delivery_pct", "On-time delivery", "On-time delivery (%)",
                colour=charts.OK_COLOUR, reference=92, reference_label="92% threshold",
            ),
            width='stretch',
        )

    ncr_view = scorecard.melt(
        id_vars="supplier_name",
        value_vars=["open_ncrs", "repeat_ncrs", "overdue_actions"],
        var_name="measure",
        value_name="count",
    )
    ncr_view["measure"] = ncr_view["measure"].map(
        {"open_ncrs": "Open NCRs", "repeat_ncrs": "Repeat NCRs", "overdue_actions": "Overdue actions"}
    )

    import plotly.express as px  # local import keeps the module's dependency surface obvious

    fig = px.bar(
        ncr_view, x="supplier_name", y="count", color="measure", barmode="group",
        color_discrete_sequence=[charts.SERIES_COLOUR, charts.SPEC_COLOUR, charts.CONTROL_COLOUR],
    )
    fig.update_layout(
        title="Open NCRs, repeats and overdue actions by supplier",
        xaxis_title="", yaxis_title="Count", height=380, **charts.LAYOUT,
    )
    st.plotly_chart(fig, width='stretch')

    # ------------------------------------------------------------------
    # Detail
    # ------------------------------------------------------------------
    st.divider()
    section_header("Supplier detail")

    supplier_id = st.selectbox(
        "Supplier",
        scorecard["supplier_id"],
        format_func=lambda s: full.label_map("supplier").get(s, s),
    )
    row = scorecard[scorecard["supplier_id"] == supplier_id].iloc[0]
    meta = full.suppliers[full.suppliers["supplier_id"] == supplier_id].iloc[0]

    cols = st.columns(5)
    cols[0].metric("PPM", f"{row['ppm']:,.0f}")
    cols[1].metric("First pass yield", f"{row['fpy_pct']:.2f}%")
    cols[2].metric("Open NCRs", int(row["open_ncrs"]))
    cols[3].metric("Repeat NCRs", int(row["repeat_ncrs"]))
    cols[4].metric("On-time delivery", f"{row['on_time_delivery_pct']:.1f}%")

    st.caption(
        f"{meta['supplier_name']} | {meta['category']} | {meta['location']} | "
        f"Approval: {meta['approval_status']} | Supplying for {meta['years_supplying']} years"
    )

    supplier_ncrs = data.ncrs[data.ncrs["supplier_id"] == supplier_id]
    if len(supplier_ncrs):
        st.markdown("**NCR history**")
        history = supplier_ncrs[
            ["ncr_id", "date_raised", "component_id", "defect_category", "severity", "closure_status", "is_repeat"]
        ].copy()
        history["date_raised"] = history["date_raised"].dt.strftime("%Y-%m-%d")
        history["is_repeat"] = history["is_repeat"].map({True: "Yes", False: ""})
        history.columns = ["NCR", "Raised", "Component", "Defect category", "Severity", "Status", "Repeat"]
        dataframe(history.sort_values("Raised", ascending=False))

    by_component = (
        data.inspections[data.inspections["supplier_id"] == supplier_id]
        .groupby("component_id")
        .agg(inspected=("defect_flag", "size"), defects=("defect_flag", "sum"))
        .reset_index()
    )
    by_component["ppm"] = (1_000_000 * by_component["defects"] / by_component["inspected"]).round(0)
    by_component.columns = ["Component", "Inspected", "Defects", "PPM"]
    st.markdown("**Performance by component**")
    dataframe(by_component.sort_values("PPM", ascending=False))

    # ------------------------------------------------------------------
    # Interpretation
    # ------------------------------------------------------------------
    flagged = scorecard[scorecard["attention_required"] != "No threshold exceeded"]
    if len(flagged):
        names = ", ".join(flagged["supplier_name"])
        text = (
            f"{len(flagged)} of {len(scorecard)} suppliers exceed at least one review threshold: {names}. "
            "The reasons differ, which is why they are not combined into a single score. "
        )
    else:
        text = "No supplier exceeds a review threshold in the current selection. "

    worst = scorecard.iloc[0]
    text += (
        f"{worst['supplier_name']} records the highest PPM at {worst['ppm']:,.0f} across "
        f"{int(worst['inspected']):,} inspected units. PPM is a volume-weighted measure, so a supplier with a "
        "small inspected quantity can show a high or low figure on very little evidence; the inspected column "
        "should always be read alongside it."
    )
    interpretation(text)
