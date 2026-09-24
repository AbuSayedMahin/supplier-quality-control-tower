"""Supplier Quality Engineering Control Tower.

A portfolio engineering project demonstrating applied quality engineering methods
on a synthetic dataset from a fictional high-performance powertrain supply chain.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import DATA_DIR, DEFECT_CATEGORIES, DISCLAIMER, REPORTING_DATE, SEVERITIES
from src.data_loader import FilterState, apply_filters, load_data
from views import (
    capa_view,
    capability_view,
    case_study_view,
    control_tower,
    ncr_view,
    pareto_view,
    rca_view,
    scorecard_view,
    spc_view,
)

st.set_page_config(
    page_title="Supplier Quality Control Tower",
    page_icon="assets/favicon.png" if (DATA_DIR.parent / "assets" / "favicon.png").exists() else ":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = {
    "Control Tower": control_tower,
    "Pareto Analysis": pareto_view,
    "Statistical Process Control": spc_view,
    "Process Capability": capability_view,
    "Non-Conformance Reports": ncr_view,
    "Root Cause Analysis": rca_view,
    "Corrective Action": capa_view,
    "Supplier Scorecard": scorecard_view,
    "Engineering Case Study": case_study_view,
}

# Pages that analyse one specific process end to end and are not meant to be
# reshaped by the sidebar filters.
UNFILTERED_PAGES = {"Engineering Case Study", "Root Cause Analysis"}


@st.cache_data(show_spinner="Loading quality data...")
def _load():
    return load_data()


def _missing_data_message() -> None:
    st.error(
        "The data files were not found. Generate the synthetic dataset first:\n\n"
        "```\npython scripts/generate_data.py\n```"
    )


def main() -> None:
    if not (DATA_DIR / "inspections.csv").exists():
        _missing_data_message()
        return

    data = _load()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------
    with st.sidebar:
        st.title("Supplier Quality")
        st.caption("Control Tower")

        page_name = st.radio("Section", list(PAGES), label_visibility="collapsed")

        st.divider()
        st.subheader("Filters")

        if page_name in UNFILTERED_PAGES:
            st.caption(
                "This section follows one investigation end to end and always uses the full dataset, so the "
                "filters below do not apply to it."
            )

        supplier_labels = data.label_map("supplier")
        component_labels = data.label_map("component")

        suppliers = st.multiselect(
            "Supplier",
            list(data.suppliers["supplier_id"]),
            default=list(data.suppliers["supplier_id"]),
            format_func=lambda s: supplier_labels.get(s, s),
        )
        components = st.multiselect(
            "Component",
            list(data.components["component_id"]),
            default=list(data.components["component_id"]),
            format_func=lambda c: component_labels.get(c, c),
        )

        min_date = data.inspections["inspection_date"].min().date()
        max_date = data.inspections["inspection_date"].max().date()
        date_range = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            date_from, date_to = (pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))
        else:
            date_from, date_to = pd.Timestamp(min_date), pd.Timestamp(max_date)

        defect_categories = st.multiselect(
            "Defect category",
            DEFECT_CATEGORIES,
            default=[],
            help="Leave empty to include all categories. Selecting a category restricts the view to "
            "non-conforming records only.",
        )
        severities = st.multiselect("Severity", SEVERITIES, default=[])

        if not suppliers or not components:
            st.warning("Select at least one supplier and one component.")

        st.divider()
        st.caption(f"Reporting date: {REPORTING_DATE}")
        st.caption(f"{len(data.inspections):,} inspection records | {len(data.ncrs)} NCRs | {len(data.actions)} actions")

        if st.button("Reset filters", width='stretch'):
            st.rerun()

    # ------------------------------------------------------------------
    # Main area
    # ------------------------------------------------------------------
    st.caption(f":grey[SYNTHETIC DATA - PORTFOLIO PROJECT] {DISCLAIMER}")

    if not suppliers or not components:
        st.warning("Select at least one supplier and one component to continue.")
        return

    state = FilterState(
        suppliers=suppliers,
        components=components,
        date_from=date_from,
        date_to=date_to,
        defect_categories=defect_categories,
        severities=severities,
    )
    filtered = apply_filters(data, state)

    if page_name not in UNFILTERED_PAGES and not state.is_default(data):
        st.caption(
            f":orange[Filters active] - {len(filtered.inspections):,} of {len(data.inspections):,} inspection "
            f"records and {len(filtered.ncrs)} of {len(data.ncrs)} NCRs in scope."
        )

    PAGES[page_name].render(filtered, data)

    st.divider()
    st.caption(
        "Portfolio engineering project. All suppliers, components, measurements and non-conformance records are "
        "fictional and were generated from a statistical model with a fixed random seed. The reasoning behind "
        "each method choice is set out in docs/engineering_case_study.md."
    )


if __name__ == "__main__":
    main()
