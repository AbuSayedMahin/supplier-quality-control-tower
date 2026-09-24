"""Root cause analysis view - 5 Whys and Ishikawa."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts
from src.data_loader import QualityData
from src.investigations import INVESTIGATIONS, get_investigation

from .common import dataframe, interpretation, no_data, section_header


def _cause_detail(investigation, short_label: str) -> str:
    """Full wording for a fishbone cause, looked up by its short diagram label."""
    for items in investigation.fishbone.values():
        for label, detail in items:
            if label == short_label:
                return detail
    return short_label


def render(data: QualityData, full: QualityData) -> None:
    st.header("Root Cause Analysis")
    st.caption(
        "Structured investigation of selected non-conformances. The methods below organise thinking; they do "
        "not produce evidence on their own, so each conclusion is stated against what the data actually shows."
    )

    available = [n for n in INVESTIGATIONS if n in set(full.ncrs["ncr_id"])]
    if not available:
        no_data("No investigations are available.")
        return

    ncr_id = st.selectbox(
        "Investigation",
        available,
        format_func=lambda n: f"{n} - {full.ncrs.loc[full.ncrs['ncr_id'] == n, 'defect_category'].iloc[0]}",
    )
    investigation = get_investigation(ncr_id)
    record = full.ncrs[full.ncrs["ncr_id"] == ncr_id].iloc[0]

    st.markdown("**Problem statement**")
    st.error(investigation.problem_statement)

    meta = st.columns(4)
    meta[0].metric("Supplier", full.supplier_name(record["supplier_id"]))
    meta[1].metric("Component", record["component_id"])
    meta[2].metric("Severity", record["severity"])
    meta[3].metric("Detected by", record["detection_method"])

    tab_whys, tab_fish, tab_conclusion = st.tabs(["5 Whys", "Fishbone (Ishikawa)", "Conclusion and evidence"])

    # ------------------------------------------------------------------
    # 5 Whys
    # ------------------------------------------------------------------
    with tab_whys:
        section_header(
            "5 Whys",
            "Each answer is the question for the line below it. The chain stops when it reaches something that "
            "can actually be changed, which is usually a system or a decision rather than a person.",
        )

        st.markdown(f"**Problem:** {investigation.problem_statement}")
        for index, (question, answer) in enumerate(investigation.five_whys, start=1):
            with st.container(border=True):
                st.markdown(f"**Why {index}.** {question}")
                st.markdown(f"{answer}")

        st.success(f"**Root cause reached at why {len(investigation.five_whys)}:** {investigation.most_likely_root_cause}")

        st.caption(
            "Five is a convention, not a rule. The chain ends when the next answer would no longer be something "
            "within the organisation's control. Stopping too early produces an action against a symptom, which "
            "is what happened on the earlier NCR against this same trend."
        )

    # ------------------------------------------------------------------
    # Fishbone
    # ------------------------------------------------------------------
    with tab_fish:
        section_header(
            "Fishbone / Ishikawa",
            "Potential causes grouped under the six standard headings. Causes shown in red were supported by "
            "evidence; the rest were considered and remain unconfirmed.",
        )

        short_problem = investigation.problem_statement.split(".")[0]
        st.plotly_chart(
            charts.fishbone_figure(investigation.fishbone, short_problem, investigation.confirmed_causes),
            width='stretch',
        )

        st.markdown("**Causes in full**")
        rows = []
        for category, items in investigation.fishbone.items():
            for short_label, detail in items:
                rows.append(
                    {
                        "Category": category,
                        "Cause": short_label,
                        "Status": "Confirmed / most likely"
                        if short_label in investigation.confirmed_causes
                        else "Potential - not confirmed",
                        "Detail": detail,
                    }
                )
        dataframe(pd.DataFrame(rows))

        left, right = st.columns(2)
        with left:
            st.markdown("**Confirmed or most likely causes**")
            for cause in investigation.confirmed_causes:
                detail = _cause_detail(investigation, cause)
                st.markdown(f"- :red[**{cause}**] - {detail}")
        with right:
            st.markdown("**Considered and not supported**")
            if investigation.ruled_out:
                for name, reason in investigation.ruled_out:
                    with st.expander(name):
                        st.write(reason)
            else:
                st.caption("No branches were formally ruled out in this investigation.")

        st.caption(
            "Everything not marked as confirmed remains a potential cause. Recording what was ruled out, and "
            "why, is as much a part of the investigation as identifying what was confirmed."
        )

    # ------------------------------------------------------------------
    # Conclusion
    # ------------------------------------------------------------------
    with tab_conclusion:
        section_header("Most likely root cause")
        st.success(investigation.most_likely_root_cause)

        st.markdown("**Supporting evidence**")
        for item in investigation.evidence:
            st.markdown(f"- {item}")

        st.divider()
        section_header(
            "Containment, corrective action and preventive action",
            "Three different jobs. Confusing them is one of the most common weaknesses in a corrective action "
            "system.",
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Containment**")
            st.caption("Protects the downstream process and the customer from further affected material. Does "
                       "not change why the material was produced.")
            st.write(investigation.containment)
        with c2:
            st.markdown("**Corrective action**")
            st.caption("Removes the cause of the non-conformance that was detected, so that it does not happen "
                       "again in the same place.")
            st.write(investigation.corrective_action)
        with c3:
            st.markdown("**Preventive action**")
            st.caption("Reduces the likelihood of the same failure mode occurring elsewhere, where it has not "
                       "yet happened.")
            st.write(investigation.preventive_action)

        if investigation.verification:
            st.markdown("**Verification approach**")
            st.info(investigation.verification)

        if investigation.notes:
            st.divider()
            section_header("Investigation notes")
            for note in investigation.notes:
                st.warning(note)

    interpretation(
        "The conclusion above is presented as the most likely root cause on the available synthetic evidence, "
        "not as a proven fact. The distinction matters in practice: a corrective action is an investment made "
        "against a hypothesis, and the verification step exists precisely because that hypothesis might be "
        "wrong. In this dataset the first investigation into the same trend produced an action that was later "
        "verified as not effective, which is why the analysis was reopened and taken further.",
        title="Engineering interpretation",
    )
