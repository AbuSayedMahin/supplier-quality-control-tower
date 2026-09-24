"""Small shared presentation helpers.

Engineering interpretation text in this application is kept short and
conservative on purpose. The dashboard states a finding and its caveat; the
full argument belongs in the case study, not on the page.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def kpi_row(items: list, columns: int = 5) -> None:
    """Render KPI tiles. Each item is (label, value, help_text)."""
    for start in range(0, len(items), columns):
        chunk = items[start : start + columns]
        cols = st.columns(len(chunk))
        for col, (label, value, help_text) in zip(cols, chunk):
            col.metric(label, value, help=help_text)


def interpretation(text: str, title: str = "Engineering interpretation") -> None:
    """A consistently styled interpretation block."""
    st.markdown(f"**{title}**")
    st.info(text)


def caveats(items: list, title: str = "Assumptions and caveats") -> None:
    if not items:
        return
    with st.expander(title, expanded=False):
        for item in items:
            st.markdown(f"- {item}")


def section_header(title: str, subtitle: str = "") -> None:
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)


def no_data(message: str = "No records match the current filter selection.") -> None:
    st.warning(message)


def fmt(value, spec: str = ",.0f", dash: str = "-") -> str:
    """Format a number, returning a dash rather than 'nan' for missing values."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return dash
    return format(value, spec)


def status_badge(status: str) -> str:
    """Return a coloured marker for a workflow status."""
    complete = {"Complete", "Closed", "Verified", "Confirmed", "Effective"}
    progress = {"In progress", "Under investigation"}
    if status in complete:
        return f":green[{status}]"
    if status in progress:
        return f":orange[{status}]"
    if status in {"Not required", "Not applicable"}:
        return f":grey[{status}]"
    return f":red[{status}]"


def dataframe(df: pd.DataFrame, **kwargs) -> None:
    st.dataframe(df, width='stretch', hide_index=True, **kwargs)
