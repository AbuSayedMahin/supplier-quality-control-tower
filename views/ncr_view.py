"""Non-conformance report register and detail view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import REPORTING_DATE
from src.data_loader import QualityData

from .common import dataframe, interpretation, no_data, section_header, status_badge

WORKFLOW = [
    ("Containment", "containment_status"),
    ("Root cause", "root_cause_status"),
    ("Corrective action", "corrective_action_status"),
    ("Verification", "verification_status"),
    ("Closure", "closure_status"),
]


def render(data: QualityData, full: QualityData) -> None:
    st.header("Non-Conformance Reports")
    st.caption(
        "An NCR records a product or process that does not meet a specified requirement, and tracks it through "
        "containment, investigation, corrective action, verification and closure."
    )

    ncrs = data.ncrs
    if not len(ncrs):
        no_data("No NCRs match the current filter selection.")
        return

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------
    status_filter = st.radio(
        "Show", ["All", "Open only", "Closed only", "Repeats only"], horizontal=True, label_visibility="collapsed"
    )
    view = ncrs
    if status_filter == "Open only":
        view = ncrs[ncrs["closure_status"] != "Closed"]
    elif status_filter == "Closed only":
        view = ncrs[ncrs["closure_status"] == "Closed"]
    elif status_filter == "Repeats only":
        view = ncrs[ncrs["is_repeat"]]

    if not len(view):
        no_data("No NCRs match that status selection.")
        return

    register = view[
        [
            "ncr_id", "date_raised", "supplier_id", "component_id", "process", "defect_category",
            "quantity_affected", "severity", "detection_method", "closure_status", "is_repeat",
        ]
    ].copy()
    register["date_raised"] = register["date_raised"].dt.strftime("%Y-%m-%d")
    register["is_repeat"] = register["is_repeat"].map({True: "Yes", False: ""})
    register.columns = [
        "NCR", "Raised", "Supplier", "Component", "Process", "Defect category",
        "Qty", "Severity", "Detected by", "Status", "Repeat",
    ]
    dataframe(register.sort_values("Raised", ascending=False))

    st.divider()

    # ------------------------------------------------------------------
    # Detail
    # ------------------------------------------------------------------
    section_header("NCR detail")
    ncr_id = st.selectbox("Select an NCR", sorted(view["ncr_id"]), index=0)
    record = ncrs[ncrs["ncr_id"] == ncr_id].iloc[0]

    head = st.columns(4)
    head[0].metric("NCR", record["ncr_id"])
    head[1].metric("Severity", record["severity"])
    head[2].metric("Quantity affected", int(record["quantity_affected"]))
    head[3].metric("Days open" if record["closure_status"] != "Closed" else "Days to close",
                   int(record["days_open"]))

    left, right = st.columns([1.3, 1])
    with left:
        st.markdown("**Description**")
        st.write(record["description"])

        st.markdown("**Record**")
        detail = pd.DataFrame(
            {
                "Field": ["Date raised", "Supplier", "Component", "Process", "Defect category",
                          "Detection method", "Repeat occurrence", "Closure date"],
                "Value": [
                    record["date_raised"].strftime("%Y-%m-%d"),
                    f"{record['supplier_id']} - {full.supplier_name(record['supplier_id'])}",
                    f"{record['component_id']} - {full.component_name(record['component_id'])}",
                    record["process"],
                    record["defect_category"],
                    record["detection_method"],
                    "Yes - same supplier, component and defect category previously recorded"
                    if record["is_repeat"] else "No",
                    record["closure_date"].strftime("%Y-%m-%d") if pd.notna(record["closure_date"]) else "Not closed",
                ],
            }
        )
        dataframe(detail)

    with right:
        st.markdown("**Workflow status**")
        for label, column in WORKFLOW:
            st.markdown(f"{label}: {status_badge(str(record[column]))}")

        st.caption(
            "An NCR is only closed after the corrective action has been verified as effective, or where a formal "
            "corrective action was judged not to be required and the parts were dispositioned. Closing on the "
            "strength of an action being completed, without checking that it worked, is how repeat "
            "non-conformances are created."
        )

    # ------------------------------------------------------------------
    # Linked corrective actions
    # ------------------------------------------------------------------
    linked = full.actions[full.actions["ncr_id"] == ncr_id]
    if len(linked):
        st.markdown("**Linked corrective action**")
        for _, action in linked.iterrows():
            with st.expander(f"{action['action_id']} - {action['status']}", expanded=True):
                st.markdown(f"**Root cause**  \n{action['root_cause']}")
                st.markdown(f"**Containment**  \n{action['immediate_containment']}")
                st.markdown(f"**Corrective action**  \n{action['corrective_action']}")
                st.markdown(f"**Preventive action**  \n{action['preventive_action']}")
                st.markdown(f"**Verification method**  \n{action['verification_method']}")
                st.markdown(f"**Verification result**  \n{action['verification_result']}")
                st.caption(
                    f"Owner: {action['owner']} | Due: {action['due_date']:%Y-%m-%d} | "
                    f"Closed: {action['closure_date']:%Y-%m-%d}"
                    if pd.notna(action["closure_date"])
                    else f"Owner: {action['owner']} | Due: {action['due_date']:%Y-%m-%d} | Not closed"
                )
    elif record["corrective_action_status"] == "Not required":
        st.info(
            "No formal corrective action was raised. The non-conformance was contained and the parts "
            "dispositioned. Not every NCR justifies a corrective action; a low-severity, first-occurrence issue "
            "can reasonably be closed this way, and raising a CAPA against every record produces paperwork "
            "rather than improvement."
        )

    # ------------------------------------------------------------------
    # Register summary
    # ------------------------------------------------------------------
    st.divider()
    section_header("Register summary")

    summary_cols = st.columns(4)
    summary_cols[0].metric("Total NCRs", len(ncrs))
    summary_cols[1].metric("Open", int((ncrs["closure_status"] != "Closed").sum()))
    summary_cols[2].metric("Repeats", int(ncrs["is_repeat"].sum()))
    closed = ncrs[ncrs["closure_status"] == "Closed"]
    summary_cols[3].metric(
        "Median days to close", f"{closed['days_open'].median():.0f}" if len(closed) else "-"
    )

    by_category = (
        ncrs.groupby(["defect_category"])
        .agg(total=("ncr_id", "size"), repeats=("is_repeat", "sum"),
             open_count=("closure_status", lambda s: int((s != "Closed").sum())))
        .reset_index()
        .sort_values("total", ascending=False)
    )
    by_category.columns = ["Defect category", "NCRs", "Repeats", "Open"]
    dataframe(by_category)

    repeat_count = int(ncrs["is_repeat"].sum())
    interpretation(
        f"{len(ncrs)} NCRs are recorded in the current selection, of which {repeat_count} are repeats of a "
        f"supplier, component and defect category combination that had already been raised. "
        + (
            "Repeat activity concentrated in a small number of categories usually means the earlier corrective "
            "action addressed the symptom rather than the cause, or that its effectiveness check was too short "
            "to detect that the control introduced would not hold."
            if repeat_count
            else "No repeat activity is present, which is consistent with corrective actions having removed the "
            "causes they were raised against, at least over the period measured."
        )
        + f" Status as at the reporting date of {REPORTING_DATE}."
    )
