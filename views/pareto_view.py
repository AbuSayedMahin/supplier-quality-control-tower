"""Pareto analysis of recorded non-conformances."""

from __future__ import annotations

import streamlit as st

from src import charts
from src.data_loader import QualityData
from src.quality_metrics import pareto_interpretation, pareto_table, vital_few

from .common import dataframe, interpretation, no_data, section_header


def render(data: QualityData, full: QualityData) -> None:
    st.header("Pareto Analysis")
    st.caption(
        "Ranks defect categories by how often they occur, so that improvement effort can be directed at the "
        "categories that account for most of the recorded non-conformance."
    )

    defects = data.inspections[data.inspections["defect_flag"] == 1]
    if not len(defects):
        no_data("No non-conformances are recorded for the current filter selection.")
        return

    source = st.radio(
        "Analyse",
        ["Inspection findings", "Non-conformance reports"],
        horizontal=True,
        help=(
            "Inspection findings count every non-conforming unit detected. NCRs count formally raised reports, "
            "which is a smaller number because several findings of the same condition are usually raised as one "
            "NCR. The two views answer different questions and will not agree."
        ),
    )

    if source == "Inspection findings":
        frame = defects
        unit_label = "non-conforming units"
    else:
        frame = data.ncrs
        unit_label = "NCRs"
        if not len(frame):
            no_data("No NCRs match the current filter selection.")
            return

    threshold = st.slider("Cumulative reference line (%)", 50, 95, 80, step=5)

    table = pareto_table(frame, "defect_category")
    st.plotly_chart(
        charts.pareto_chart(table, f"Defect Pareto - {unit_label}", threshold=float(threshold)),
        width='stretch',
    )

    display = table.copy()
    display.columns = ["Defect category", "Count", "Cumulative count", "% of total", "Cumulative %"]
    display["% of total"] = display["% of total"].round(1)
    display["Cumulative %"] = display["Cumulative %"].round(1)
    dataframe(display)

    interpretation(pareto_interpretation(table, threshold=float(threshold)))

    # ------------------------------------------------------------------
    # Severity cross-check
    #
    # A frequency Pareto can point at a category that is common but harmless.
    # Splitting the leading categories by severity is a cheap guard against
    # chasing the wrong thing.
    # ------------------------------------------------------------------
    st.divider()
    section_header(
        "Severity cross-check",
        "Frequency alone can be misleading. This splits each category by severity so a common but low-impact "
        "category is not mistaken for the most important problem.",
    )

    if "severity" in frame.columns:
        severity = (
            frame[frame["severity"].astype(str) != ""]
            .groupby(["defect_category", "severity"])
            .size()
            .unstack(fill_value=0)
        )
        for level in ["Minor", "Major", "Critical"]:
            if level not in severity.columns:
                severity[level] = 0
        severity = severity[["Minor", "Major", "Critical"]]
        severity["Total"] = severity.sum(axis=1)
        severity = severity.sort_values("Total", ascending=False).reset_index()
        severity.columns = ["Defect category", "Minor", "Major", "Critical", "Total"]
        dataframe(severity)

        leading = vital_few(table, float(threshold))
        critical_heavy = severity[(severity["Critical"] > 0) & (~severity["Defect category"].isin(leading))]
        if len(critical_heavy):
            names = ", ".join(critical_heavy["Defect category"])
            st.warning(
                f"{names} falls outside the leading categories by frequency but includes critical-severity "
                "records. Categories like this are worth reviewing separately rather than being deprioritised "
                "on count alone."
            )

    # ------------------------------------------------------------------
    # Drill-down
    # ------------------------------------------------------------------
    st.divider()
    section_header(
        "Drill-down",
        "A Pareto across the whole supply base mixes several unrelated processes together. Narrowing to one "
        "supplier or component is usually where the analysis becomes actionable.",
    )

    col1, col2 = st.columns(2)
    with col1:
        by_supplier = (
            frame.groupby(["supplier_id", "defect_category"]).size().reset_index(name="count")
        )
        by_supplier["supplier"] = by_supplier["supplier_id"].map(full.label_map("supplier"))
        pivot = by_supplier.pivot_table(
            index="defect_category", columns="supplier_id", values="count", fill_value=0
        ).reset_index()
        pivot.rename(columns={"defect_category": "Defect category"}, inplace=True)
        st.markdown("**Defect category by supplier**")
        dataframe(pivot)

    with col2:
        by_component = (
            frame.groupby(["component_id", "defect_category"]).size().reset_index(name="count")
        )
        pivot_c = by_component.pivot_table(
            index="defect_category", columns="component_id", values="count", fill_value=0
        ).reset_index()
        pivot_c.rename(columns={"defect_category": "Defect category"}, inplace=True)
        st.markdown("**Defect category by component**")
        dataframe(pivot_c)

    st.caption(
        "Use the sidebar filters to narrow to a single supplier or component and the Pareto above will "
        "recalculate. This is the step that turns a supply-base summary into an investigation."
    )
