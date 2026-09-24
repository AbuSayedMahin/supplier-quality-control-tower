"""Corrective and preventive action tracker."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import REPORTING_DATE
from src.data_loader import QualityData

from .common import dataframe, interpretation, no_data, section_header


def render(data: QualityData, full: QualityData) -> None:
    st.header("Corrective and Preventive Action")
    st.caption(
        "Tracks each action from the confirmed root cause through to verified effectiveness. An action is not "
        "finished when it is implemented; it is finished when evidence shows it worked."
    )

    actions = data.actions
    if not len(actions):
        no_data("No corrective actions match the current filter selection.")
        return

    as_of = pd.Timestamp(REPORTING_DATE)
    work = actions.copy()
    work["overdue"] = (~work["status"].isin(["Complete", "Closed"])) & (work["due_date"] < as_of)

    # ------------------------------------------------------------------
    # Definitions - short. The dashboard states them; the case study argues them.
    # ------------------------------------------------------------------
    with st.expander("Containment, corrective action, preventive action"):
        st.markdown(
            """
| | Purpose | Question it answers |
|---|---|---|
| **Containment** | Protect the downstream process and the customer from further affected material | What do we do about the parts that already exist? |
| **Corrective action** | Remove the cause of the non-conformance that was detected | Why did this happen, and what stops it happening here again? |
| **Preventive action** | Reduce the likelihood of the same failure mode arising where it has not yet happened | Where else could this go wrong for the same reason? |

Containment is usually fast and always temporary. If 100% inspection is still in place months later, the
corrective action has not worked.
"""
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    cols = st.columns(5)
    cols[0].metric("Actions", len(work))
    cols[1].metric("Complete", int((work["status"] == "Complete").sum()))
    cols[2].metric("In progress", int((work["status"] == "In progress").sum()))
    cols[3].metric("Overdue", int(work["overdue"].sum()),
                   help="Past the due date and not yet complete, as at the reporting date.")
    effective = work["verification_result"].str.startswith("Effective", na=False)
    cols[4].metric("Verified effective", int(effective.sum()))

    # ------------------------------------------------------------------
    # Tracker table
    # ------------------------------------------------------------------
    st.divider()
    section_header("Action tracker")

    show = st.radio("Show", ["All", "Open actions", "Overdue only"], horizontal=True, label_visibility="collapsed")
    view = work
    if show == "Open actions":
        view = work[work["status"] != "Complete"]
    elif show == "Overdue only":
        view = work[work["overdue"]]

    if not len(view):
        st.success("No actions match that selection.")
    else:
        table = view[["action_id", "ncr_id", "owner", "due_date", "status", "verification_result", "closure_date"]].copy()
        table["due_date"] = table["due_date"].dt.strftime("%Y-%m-%d")
        table["closure_date"] = table["closure_date"].dt.strftime("%Y-%m-%d").fillna("")
        table["verification_result"] = table["verification_result"].str.split(" - ").str[0]
        table["overdue"] = view["overdue"].map({True: "Yes", False: ""}).values
        table.columns = ["Action", "NCR", "Owner", "Due", "Status", "Verification", "Closed", "Overdue"]
        dataframe(table.sort_values("Due"))

    # ------------------------------------------------------------------
    # Detail
    # ------------------------------------------------------------------
    st.divider()
    section_header("Action detail")

    action_id = st.selectbox("Select an action", sorted(work["action_id"]))
    action = work[work["action_id"] == action_id].iloc[0]
    ncr = full.ncrs[full.ncrs["ncr_id"] == action["ncr_id"]]

    head = st.columns(4)
    head[0].metric("Action", action["action_id"])
    head[1].metric("Against NCR", action["ncr_id"])
    head[2].metric("Status", action["status"])
    head[3].metric("Due", f"{action['due_date']:%Y-%m-%d}")

    if action["overdue"]:
        st.warning(
            f"This action is past its due date of {action['due_date']:%Y-%m-%d} and is not yet complete. Until "
            "it is, the containment put in place is the only thing protecting the build."
        )

    if len(ncr):
        row = ncr.iloc[0]
        st.caption(
            f"{row['component_id']} - {full.component_name(row['component_id'])} from "
            f"{row['supplier_id']} - {full.supplier_name(row['supplier_id'])} | {row['defect_category']} | "
            f"{row['severity']}"
        )

    st.markdown("**Root cause**")
    st.write(action["root_cause"])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Immediate containment**")
        st.write(action["immediate_containment"])
    with c2:
        st.markdown("**Corrective action**")
        st.write(action["corrective_action"])
    with c3:
        st.markdown("**Preventive action**")
        st.write(action["preventive_action"])

    st.divider()
    st.markdown("**Verification**")
    v1, v2 = st.columns([1, 1])
    with v1:
        st.caption("Method")
        st.write(action["verification_method"])
    with v2:
        st.caption("Result")
        if str(action["verification_result"]).startswith("Effective"):
            st.success(action["verification_result"])
        elif str(action["verification_result"]).startswith("Not effective"):
            st.error(action["verification_result"])
        else:
            st.warning(action["verification_result"])

    st.caption(
        f"Owner: {action['owner']}"
        + (f" | Closed: {action['closure_date']:%Y-%m-%d}" if pd.notna(action["closure_date"]) else " | Not closed")
    )

    # ------------------------------------------------------------------
    # Interpretation
    # ------------------------------------------------------------------
    st.divider()
    not_effective = int(work["verification_result"].str.startswith("Not effective", na=False).sum())
    partial = int(work["verification_result"].str.startswith("Partially effective", na=False).sum())

    interpretation(
        f"Of {len(work)} corrective actions in this selection, {int(effective.sum())} were verified as effective, "
        f"{partial} as only partially effective and {not_effective} as not effective. "
        "Recording the actions that did not work is deliberate. A tracker in which every action is effective is "
        "usually a tracker with a weak verification step rather than a flawless process. The partially effective "
        "and ineffective entries here are each followed by a repeat non-conformance, which is what prompted the "
        "investigation to be reopened and taken deeper."
    )
