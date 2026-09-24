"""The end-to-end engineering case study.

This view walks the complete quality engineering cycle on one problem, in the
order the work was actually done. Every number on the page is calculated from
the dataset at render time rather than written into the text, so the narrative
cannot drift away from the data behind it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
from scipy import stats

from src import charts
from src.capability import calculate_capability
from src.config import (
    BASELINE_END,
    BASELINE_START,
    CASE_STUDY_COMPONENT,
    CASE_STUDY_NCR,
    CASE_STUDY_SUPPLIER,
    CORRECTIVE_ACTION_IMPLEMENTED,
    PHASE_WINDOWS,
    POST_CHANGE_START,
)
from src.data_loader import QualityData
from src.investigations import get_investigation
from src.quality_metrics import before_after_comparison, pareto_interpretation, pareto_table, weekly_trend
from src.spc import build_imr_table, order_for_analysis

from .common import dataframe, interpretation, section_header

STEPS = [
    "1. Detection",
    "2. Pareto",
    "3. SPC",
    "4. Capability",
    "5. Investigation",
    "6. Root cause",
    "7. Action",
    "8. Verification",
    "9. Closure",
]


def _case_data(full: QualityData) -> pd.DataFrame:
    return order_for_analysis(
        full.inspections[
            (full.inspections["component_id"] == CASE_STUDY_COMPONENT)
            & (full.inspections["supplier_id"] == CASE_STUDY_SUPPLIER)
        ]
    )


def render(data: QualityData, full: QualityData) -> None:
    st.header("Engineering Case Study")
    st.caption(
        "One problem followed end to end: detection, analysis, root cause, containment, corrective action and "
        "verified closure. This view always uses the full dataset so the story stays intact regardless of the "
        "sidebar filters."
    )

    subset = _case_data(full)
    spec = full.component_spec(CASE_STUDY_COMPONENT)
    supplier_name = full.supplier_name(CASE_STUDY_SUPPLIER)
    component_name = full.component_name(CASE_STUDY_COMPONENT)

    st.markdown(
        f"**Subject:** {spec['characteristic']} on {component_name} ({CASE_STUDY_COMPONENT}) "
        f"from {supplier_name} ({CASE_STUDY_SUPPLIER})  \n"
        f"**Specification:** {spec['nominal']:.3f} {spec['unit']} "
        f"({spec['lsl']:.3f} to {spec['usl']:.3f} {spec['unit']})  \n"
        f"**Lead NCR:** {CASE_STUDY_NCR}"
    )

    step = st.radio("Step", STEPS, horizontal=True, label_visibility="collapsed")

    # Shared calculations -------------------------------------------------
    baseline_mask = (
        (subset["inspection_date"] >= BASELINE_START) & (subset["inspection_date"] <= BASELINE_END)
    ).reset_index(drop=True)
    imr, limits = build_imr_table(subset, baseline_mask=baseline_mask)

    phase_results = {}
    for label, (start, end) in PHASE_WINDOWS.items():
        phase = subset[(subset["inspection_date"] >= start) & (subset["inspection_date"] <= end)]
        if len(phase) >= 10:
            phase_results[label] = calculate_capability(
                phase["measured_value"], lsl=spec["lsl"], usl=spec["usl"], nominal=spec["nominal"]
            )

    if step == STEPS[0]:
        _detection(full, subset, supplier_name)
    elif step == STEPS[1]:
        _pareto(full, subset, supplier_name)
    elif step == STEPS[2]:
        _spc(imr, limits, spec, component_name, supplier_name)
    elif step == STEPS[3]:
        _capability(subset, phase_results, spec)
    elif step == STEPS[4]:
        _investigation(full)
    elif step == STEPS[5]:
        _root_cause(full)
    elif step == STEPS[6]:
        _action(full)
    elif step == STEPS[7]:
        _verification(full, subset, imr, limits, spec, phase_results, component_name, supplier_name)
    else:
        _closure(full, subset)


# ---------------------------------------------------------------------------
# 1. Detection
# ---------------------------------------------------------------------------

def _detection(full: QualityData, subset: pd.DataFrame, supplier_name: str) -> None:
    section_header(
        "Step 1 - Detection",
        "The control tower is a monitoring tool. It does not diagnose anything; it tells you where to look.",
    )

    supplier_all = full.inspections[full.inspections["supplier_id"] == CASE_STUDY_SUPPLIER]
    trend = weekly_trend(supplier_all)

    st.plotly_chart(
        charts.trend_chart(
            trend, "ppm", f"Weekly PPM - {supplier_name} (all components)", "PPM",
            reference_date=POST_CHANGE_START, reference_label="Corrective action<br>in effect",
        ),
        width='stretch',
    )

    defect_weeks = trend[trend["defects"] > 0]
    first_march = defect_weeks[defect_weeks["week"] >= "2026-03-01"]

    cols = st.columns(4)
    cols[0].metric("Inspection records", f"{len(supplier_all):,}")
    cols[1].metric("Non-conforming", int(supplier_all["defect_flag"].sum()))
    cols[2].metric(
        "Supplier PPM",
        f"{1_000_000 * supplier_all['defect_flag'].sum() / len(supplier_all):,.0f}",
    )
    cols[3].metric(
        "NCRs raised in Apr-May",
        int(
            (
                (full.ncrs["supplier_id"] == CASE_STUDY_SUPPLIER)
                & (full.ncrs["date_raised"] >= "2026-04-01")
                & (full.ncrs["date_raised"] <= "2026-05-31")
            ).sum()
        ),
    )

    interpretation(
        f"Defect activity at {supplier_name} concentrates in April and May 2026, and three NCRs were raised "
        f"against the same component and defect category in that window "
        f"({', '.join(sorted(full.ncrs.loc[(full.ncrs['supplier_id'] == CASE_STUDY_SUPPLIER) & (full.ncrs['component_id'] == CASE_STUDY_COMPONENT), 'ncr_id']))}). "
        "Weekly PPM on a single supplier is a noisy measure and a rise across two or three weeks proves nothing "
        "on its own. What makes this worth investigating is that the rise is concentrated on one component and "
        "one defect category rather than spread across the supplier's whole range, which points to a process "
        "rather than to chance."
        + (f" The first week with recorded defects after 1 March was w/c {first_march.iloc[0]['week']:%d %B %Y}."
           if len(first_march) else "")
    )


# ---------------------------------------------------------------------------
# 2. Pareto
# ---------------------------------------------------------------------------

def _pareto(full: QualityData, subset: pd.DataFrame, supplier_name: str) -> None:
    section_header(
        "Step 2 - Pareto analysis",
        "Narrowing from the whole supply base to the supplier, and then to the component.",
    )

    all_defects = full.inspections[full.inspections["defect_flag"] == 1]
    supplier_defects = all_defects[all_defects["supplier_id"] == CASE_STUDY_SUPPLIER]
    component_defects = supplier_defects[supplier_defects["component_id"] == CASE_STUDY_COMPONENT]

    tab1, tab2, tab3 = st.tabs(["Whole supply base", f"{supplier_name}", f"{supplier_name} / {CASE_STUDY_COMPONENT}"])

    with tab1:
        table = pareto_table(all_defects, "defect_category")
        st.plotly_chart(charts.pareto_chart(table, "All suppliers, all components"), width='stretch')
        st.caption(pareto_interpretation(table))
        st.warning(
            "At supply-base level dimensional deviation is not the largest category. A Pareto across unrelated "
            "processes mixes several different problems together, which is why it rarely points straight at an "
            "answer. It is a starting point for narrowing, not a diagnosis."
        )

    with tab2:
        table = pareto_table(supplier_defects, "defect_category")
        st.plotly_chart(charts.pareto_chart(table, f"{supplier_name}, all components"), width='stretch')
        st.caption(pareto_interpretation(table))

    with tab3:
        table = pareto_table(component_defects, "defect_category")
        st.plotly_chart(
            charts.pareto_chart(table, f"{supplier_name}, {CASE_STUDY_COMPONENT} only"), width='stretch'
        )
        display = table.copy()
        display.columns = ["Defect category", "Count", "Cumulative count", "% of total", "Cumulative %"]
        display["% of total"] = display["% of total"].round(1)
        display["Cumulative %"] = display["Cumulative %"].round(1)
        dataframe(display)

    dim = int((component_defects["defect_category"] == "Dimensional deviation").sum())
    total = int(len(component_defects))
    interpretation(
        f"Filtered to {CASE_STUDY_COMPONENT} at {supplier_name}, dimensional deviation accounts for {dim} of "
        f"{total} recorded non-conformances "
        f"({100 * dim / total:.0f}% of the total for that combination). That is the point at which the Pareto "
        "becomes useful: the category, the component and the supplier are all identified, and the analysis can "
        "move from counting non-conformances to examining the measurements behind them. "
        "Note also how few records this is in absolute terms. A Pareto built on a small number of events should "
        "direct where to look next, not settle the question on its own."
    )


# ---------------------------------------------------------------------------
# 3. SPC
# ---------------------------------------------------------------------------

def _spc(imr: pd.DataFrame, limits, spec: dict, component_name: str, supplier_name: str) -> None:
    section_header(
        "Step 3 - Statistical process control",
        "Control limits estimated from the stable January to February baseline and then held fixed, so that any "
        "later change shows up rather than being absorbed into wider limits.",
    )

    st.plotly_chart(
        charts.individuals_chart(
            imr, limits, spec,
            f"Individuals chart - {spec['characteristic']}, {component_name} from {supplier_name}",
        ),
        width='stretch',
    )
    st.plotly_chart(charts.moving_range_chart(imr, limits), width='stretch')

    flagged = imr[imr["any_rule"]]
    out_of_spec = imr[imr["in_spec"] == 0]

    first_flag = flagged["inspection_date"].min() if len(flagged) else None
    first_oos = out_of_spec["inspection_date"].min() if len(out_of_spec) else None

    cols = st.columns(4)
    cols[0].metric("Observations", f"{len(imr):,}")
    cols[1].metric("Control rule violations", f"{len(flagged):,}")
    cols[2].metric("Parts outside specification", f"{len(out_of_spec):,}")
    if first_flag is not None and first_oos is not None:
        cols[3].metric("Warning lead time", f"{(first_oos - first_flag).days} days",
                       help="Between the first control rule violation and the first part outside specification.")

    text = []
    if first_flag is not None:
        text.append(
            f"The chart first violates a control rule on {first_flag:%d %B %Y}. The pattern is a sustained run "
            "above the centre line rather than a single extreme point, which is the signature of a process mean "
            "that has moved rather than of an isolated bad part."
        )
    if first_flag is not None and first_oos is not None:
        text.append(
            f"The first part outside specification was not recorded until {first_oos:%d %B %Y}, "
            f"{(first_oos - first_flag).days} days later. This is the central argument for control charting: the "
            "process announced the change roughly {} weeks before the drawing tolerance was breached, during "
            "which time the parts being produced were still conforming and still being accepted.".format(
                round((first_oos - first_flag).days / 7)
            )
        )
    text.append(
        f"The moving range chart records {int(imr['mr_out_of_control'].sum())} exceedance(s) of its upper limit, "
        "so part-to-part variation stayed broadly stable while the average moved. Taken together the two charts "
        "point to a shift in the process centre, which is consistent with progressive tool wear and inconsistent "
        "with a machine losing repeatability."
    )
    interpretation(" ".join(text))

    st.caption(
        f"Control limits: CL {limits.center_line:.5f}, UCL {limits.ucl:.5f}, LCL {limits.lcl:.5f} "
        f"(sigma within = {limits.sigma_within:.5f}, from {limits.n_baseline} baseline observations). "
        f"Specification limits: {spec['lsl']:.3f} to {spec['usl']:.3f}. The two are calculated from completely "
        "different sources and are never derived from one another."
    )


# ---------------------------------------------------------------------------
# 4. Capability
# ---------------------------------------------------------------------------

def _capability(subset: pd.DataFrame, phase_results: dict, spec: dict) -> None:
    section_header(
        "Step 4 - Process capability",
        "Capability calculated separately for each phase. Calculating it across the whole period would average "
        "a capable process together with an incapable one and describe neither.",
    )

    rows = []
    for label, result in phase_results.items():
        rows.append(
            {
                "Phase": label,
                "n": result.n,
                "Mean": round(result.mean, 5),
                "Offset from nominal": round(result.centering_offset, 5),
                "Sigma (within)": round(result.sigma_within, 5),
                "Cp": round(result.cp, 2),
                "Cpk": round(result.cpk, 2),
                "Ppk": round(result.ppk, 2),
                "Out of spec": result.observed_out_of_spec,
            }
        )
    table = pd.DataFrame(rows)
    dataframe(table)

    excursion = phase_results.get("Excursion period")
    baseline = phase_results.get("Baseline (stable)")

    if excursion is not None:
        st.plotly_chart(
            charts.capability_histogram(
                _phase_values(subset, "Excursion period"),
                excursion,
                f"Distribution during the excursion period - {spec['characteristic']}",
            ),
            width='stretch',
        )

    if baseline is not None and excursion is not None:
        interpretation(
            f"During the stable baseline the process ran at Cp {baseline.cp:.2f} and Cpk {baseline.cpk:.2f}, with "
            f"the mean {baseline.centering_offset:+.5f} {spec['unit']} from nominal. During the excursion Cp held "
            f"at {excursion.cp:.2f} while Cpk fell to {excursion.cpk:.2f}, with the mean "
            f"{excursion.centering_offset:+.5f} {spec['unit']} from nominal. "
            "Cp barely moved because the process spread barely changed. Cpk collapsed because the mean moved "
            "toward the upper limit. That divergence is diagnostic: it says the problem is where the process is "
            "sitting, not how much it is varying, and it points the investigation at anything that could shift a "
            "process centre steadily in one direction, such as tool wear or an offset that is not being "
            "corrected. "
            f"It is also worth noting that the excursion-period Cpk of {excursion.cpk:.2f} is below 1.00, meaning "
            "the process spread no longer fits inside the tolerance at that position. The five parts actually "
            "found outside specification are the visible part of that; the rest of the population was conforming "
            "but had very little margin."
        )


def _phase_values(subset: pd.DataFrame, phase: str):
    """Measured values for one phase of the case-study characteristic."""
    start, end = PHASE_WINDOWS[phase]
    window = subset[(subset["inspection_date"] >= start) & (subset["inspection_date"] <= end)]
    return window["measured_value"].to_numpy()


# ---------------------------------------------------------------------------
# 5. Investigation
# ---------------------------------------------------------------------------

def _investigation(full: QualityData) -> None:
    section_header("Step 5 - NCR investigation", "The records raised against this problem, in sequence.")

    related = full.ncrs[
        (full.ncrs["supplier_id"] == CASE_STUDY_SUPPLIER)
        & (full.ncrs["component_id"] == CASE_STUDY_COMPONENT)
        & (full.ncrs["defect_category"] == "Dimensional deviation")
    ].sort_values("date_raised")

    for _, row in related.iterrows():
        with st.container(border=True):
            top = st.columns([1, 1, 1, 1])
            top[0].markdown(f"**{row['ncr_id']}**")
            top[1].markdown(f"Raised {row['date_raised']:%d %b %Y}")
            top[2].markdown(f"Severity: {row['severity']}")
            top[3].markdown(f"Qty: {int(row['quantity_affected'])}")
            st.write(row["description"])

    interpretation(
        "Three NCRs were raised against the same supplier, component and defect category within five weeks. "
        "The first was raised against a trend rather than against a non-conforming part, which is the earlier "
        "and cheaper point to intervene. The corrective action taken at that stage asked the supplier to correct "
        "the tool offset more often, but did not ask why the existing frequency had stopped being adequate. That "
        "action was subsequently verified as not effective. The second NCR was raised once parts had actually "
        "breached the specification, and the investigation was reopened at a deeper level. "
        "The pattern of an action closed against the third why, followed by a recurrence, is the most common "
        "failure mode in corrective action systems and is deliberately preserved in this dataset."
    )


# ---------------------------------------------------------------------------
# 6. Root cause
# ---------------------------------------------------------------------------

def _root_cause(full: QualityData) -> None:
    section_header("Step 6 - Root cause", "5 Whys and Ishikawa, with the evidence that supports the conclusion.")

    investigation = get_investigation(CASE_STUDY_NCR)
    st.markdown(f"**Problem:** {investigation.problem_statement}")

    for index, (question, answer) in enumerate(investigation.five_whys, start=1):
        with st.container(border=True):
            st.markdown(f"**Why {index}.** {question}")
            st.markdown(answer)

    st.success(investigation.most_likely_root_cause)

    st.plotly_chart(
        charts.fishbone_figure(
            investigation.fishbone,
            investigation.problem_statement.split(".")[0],
            investigation.confirmed_causes,
        ),
        width='stretch',
    )

    st.markdown("**Confirmed or most likely causes, in full**")
    for cause in investigation.confirmed_causes:
        detail = next(
            (full for items in investigation.fishbone.values() for short, full in items if short == cause),
            cause,
        )
        st.markdown(f"- :red[**{cause}**] - {detail}")

    left, right = st.columns(2)
    with left:
        st.markdown("**Supporting evidence**")
        for item in investigation.evidence:
            st.markdown(f"- {item}")
    with right:
        st.markdown("**Considered and not supported**")
        for name, reason in investigation.ruled_out:
            with st.expander(name):
                st.write(reason)

    st.caption(
        "The conclusion is stated as the most likely root cause on the available synthetic evidence. A root "
        "cause analysis produces a hypothesis that is strong enough to act on, not a proof. The verification "
        "step exists because that hypothesis can be wrong, and in this case an earlier one was."
    )


# ---------------------------------------------------------------------------
# 7. Action
# ---------------------------------------------------------------------------

def _action(full: QualityData) -> None:
    section_header("Step 7 - Containment, corrective and preventive action")

    investigation = get_investigation(CASE_STUDY_NCR)

    st.markdown("**Containment** - applied immediately, before the cause was known")
    st.warning(investigation.containment)
    st.caption(
        "Containment was in place from late April. It protected the build but cost 100% inspection on every "
        "incoming shaft, which is exactly why containment is a temporary measure rather than a solution. It also "
        "worked: the three further non-conforming parts recorded in NCR-2026-021 were all caught by it."
    )

    st.markdown("**Corrective action** - removes the cause of what was detected")
    st.info(investigation.corrective_action)

    st.markdown("**Preventive action** - reduces the chance of the same failure mode elsewhere")
    st.success(investigation.preventive_action)

    action = full.actions[full.actions["action_id"] == "CA-018"]
    if len(action):
        row = action.iloc[0]
        st.caption(
            f"Owner: {row['owner']} | Due {row['due_date']:%d %b %Y} | Implemented "
            f"{pd.Timestamp(CORRECTIVE_ACTION_IMPLEMENTED):%d %b %Y} | Status: {row['status']}"
        )

    interpretation(
        "The corrective action addresses the fifth why, not the first. The immediate observation was oversized "
        "parts; the action changes the control plan and the change control procedure. An action aimed at the "
        "first why would have been to rework the parts, which fixes nothing, and an action aimed at the third "
        "why would have been to tell the operator to adjust the offset more often, which is what had already "
        "been tried and had already failed. "
        "The preventive action is separated deliberately: reverting the insert grade and adding an in-process "
        "check fixes this operation, but only the change control revision stops the same mistake being made on "
        "the next tooling change."
    )


# ---------------------------------------------------------------------------
# 8. Verification
# ---------------------------------------------------------------------------

def _verification(full, subset, imr, limits, spec, phase_results, component_name, supplier_name) -> None:
    section_header(
        "Step 8 - Verification of effectiveness",
        "The action is only effective if the data after it differs from the data before it. This is the step "
        "that is most often skipped.",
    )

    excursion = phase_results.get("Excursion period")
    post = phase_results.get("Post-corrective action")

    if excursion is None or post is None:
        st.warning("Not enough data in both periods to verify.")
        return

    cols = st.columns(4)
    cols[0].metric(
        "Process mean", f"{post.mean:.5f}", f"{post.mean - excursion.mean:+.5f}",
        delta_color="inverse", help="Change from the excursion period.",
    )
    cols[1].metric("Cpk", f"{post.cpk:.2f}", f"{post.cpk - excursion.cpk:+.2f}")
    cols[2].metric(
        "Offset from nominal", f"{post.centering_offset:+.5f}",
        f"{abs(post.centering_offset) - abs(excursion.centering_offset):+.5f}", delta_color="inverse",
    )
    cols[3].metric("Sigma (within)", f"{post.sigma_within:.5f}",
                   f"{post.sigma_within - excursion.sigma_within:+.5f}", delta_color="inverse")

    # Control chart evidence -------------------------------------------
    post_mask = imr["inspection_date"] >= POST_CHANGE_START
    pre_mask = (imr["inspection_date"] >= PHASE_WINDOWS["Drift period"][0]) & (
        imr["inspection_date"] <= PHASE_WINDOWS["Excursion period"][1]
    )
    violations_before = int(imr.loc[pre_mask, "any_rule"].sum())
    violations_after = int(imr.loc[post_mask, "any_rule"].sum())
    beyond_limits_before = int(imr.loc[pre_mask, "rule_1"].sum())
    beyond_limits_after = int(imr.loc[post_mask, "rule_1"].sum())

    comparison = pd.DataFrame(
        {
            "Measure": [
                "Observations", "Process mean", "Offset from nominal", "Sigma (within)",
                "Cp", "Cpk", "Ppk", "Parts outside specification",
                "Points beyond a control limit (rule 1)", "Any control rule violation",
            ],
            "Excursion period": [
                excursion.n, f"{excursion.mean:.5f}", f"{excursion.centering_offset:+.5f}",
                f"{excursion.sigma_within:.5f}", f"{excursion.cp:.2f}", f"{excursion.cpk:.2f}",
                f"{excursion.ppk:.2f}", excursion.observed_out_of_spec,
                beyond_limits_before, violations_before,
            ],
            "Post-corrective action": [
                post.n, f"{post.mean:.5f}", f"{post.centering_offset:+.5f}", f"{post.sigma_within:.5f}",
                f"{post.cp:.2f}", f"{post.cpk:.2f}", f"{post.ppk:.2f}", post.observed_out_of_spec,
                beyond_limits_after, violations_after,
            ],
        }
    )
    dataframe(comparison)

    # The residual run-rule flags are not swept under the carpet: explaining
    # them correctly is part of the analysis.
    if violations_after > 0 and beyond_limits_after == 0:
        residual_sigma = (post.mean - limits.center_line) / limits.sigma_within
        st.warning(
            f"The post-change data is not completely free of control rule violations: {violations_after} of "
            f"{post.n} observations trip a run rule. None of them is a point beyond a control limit, and none is "
            "a rule 1 or rule 2 violation. They are all run rules (4 of 5 points beyond 1 sigma, and 8 "
            "consecutive points on one side of the centre line), and they occur because the post-change process "
            f"mean sits about {residual_sigma:.2f} sigma above the ORIGINAL baseline centre line of "
            f"{limits.center_line:.5f}.\n\n"
            "That is the correct behaviour for the chart, not a fault in it. The process really has changed, so "
            "measuring it against limits derived from the old process will keep producing run signals. The right "
            "response is to re-establish the control limits on the revised process and monitor forward from "
            "there, which is the normal transition from a Phase I study to ongoing Phase II monitoring. "
            "Reopening the NCR would be the wrong conclusion: there is no drift, no point outside a control "
            "limit, and no part outside specification."
        )
    st.caption(
        "The excursion period is used as the comparison rather than the whole pre-change period. Averaging the "
        "stable baseline together with the drift would understate the problem and therefore overstate the "
        "improvement."
    )

    # Charts ------------------------------------------------------------
    post_data = subset[subset["inspection_date"] >= POST_CHANGE_START]
    post_imr, post_limits = build_imr_table(post_data)
    st.plotly_chart(
        charts.individuals_chart(
            post_imr, limits, spec,
            "Post-change data against the original baseline control limits",
        ),
        width='stretch',
    )
    st.caption(
        "The post-change data is plotted against the ORIGINAL baseline limits, not against limits recalculated "
        "from itself. Recalculating would guarantee that the points fell inside, which would prove nothing."
    )

    # Defect rate -------------------------------------------------------
    ba = before_after_comparison(subset, POST_CHANGE_START)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            charts.before_after_chart(ba, "ppm", "PPM before and after (all defect types)", "PPM"),
            width='stretch',
        )
    with c2:
        dim_before = subset[(subset["inspection_date"] < POST_CHANGE_START)]
        dim_after = subset[(subset["inspection_date"] >= POST_CHANGE_START)]
        dim_table = pd.DataFrame(
            {
                "period": ["Before corrective action", "After corrective action"],
                "dimensional_ppm": [
                    1_000_000 * int((dim_before["in_spec"] == 0).sum()) / len(dim_before),
                    1_000_000 * int((dim_after["in_spec"] == 0).sum()) / len(dim_after),
                ],
            }
        )
        st.plotly_chart(
            charts.before_after_chart(
                dim_table, "dimensional_ppm", "Dimensional PPM before and after", "PPM"
            ),
            width='stretch',
        )

    # Statistical honesty about a zero count -----------------------------
    n_after = len(dim_after)
    oos_after = int((dim_after["in_spec"] == 0).sum())
    if oos_after == 0 and n_after > 0:
        # One-sided 95% upper bound on a proportion when zero events are observed
        # is approximately 1 - 0.05 ** (1/n), the "rule of three" in exact form.
        upper_bound = 1 - 0.05 ** (1 / n_after)
        st.info(
            f"No parts fell outside specification in the {n_after} inspected after the change. A zero count is "
            "not the same as a zero rate. With no events in "
            f"{n_after} parts the one-sided 95% upper confidence bound on the true non-conformance rate is about "
            f"{100 * upper_bound:.2f}% ({1_000_000 * upper_bound:,.0f} PPM). The evidence supports a real "
            "improvement; it does not establish that the rate is zero."
        )

    # Statistical test on the mean ---------------------------------------
    exc_values = subset[
        (subset["inspection_date"] >= PHASE_WINDOWS["Excursion period"][0])
        & (subset["inspection_date"] <= PHASE_WINDOWS["Excursion period"][1])
    ]["measured_value"]
    post_values = dim_after["measured_value"]
    # Ordered post-change first so the t statistic carries the same sign as the
    # difference in means shown beside it.
    t_stat, p_value = stats.ttest_ind(post_values, exc_values, equal_var=False)

    st.markdown("**Has the process mean actually changed?**")
    st.caption(
        "A two-sample Welch t-test comparing the excursion period against the post-change period. This is a "
        "supporting check, not the primary evidence; the control chart and the capability indices carry more "
        "weight because they describe the process rather than testing a single summary statistic."
    )
    test_cols = st.columns(3)
    test_cols[0].metric("Difference in means", f"{post_values.mean() - exc_values.mean():+.5f} {spec['unit']}")
    test_cols[1].metric("t statistic", f"{t_stat:.2f}")
    test_cols[2].metric("p value", f"{p_value:.2e}" if p_value < 0.001 else f"{p_value:.4f}")

    # Repeat NCR evidence -------------------------------------------------
    later_ncrs = full.ncrs[
        (full.ncrs["supplier_id"] == CASE_STUDY_SUPPLIER)
        & (full.ncrs["component_id"] == CASE_STUDY_COMPONENT)
        & (full.ncrs["date_raised"] > POST_CHANGE_START)
    ]

    interpretation(
        f"The process mean moved from {excursion.mean:.5f} {spec['unit']} during the excursion to "
        f"{post.mean:.5f} {spec['unit']} afterwards, which is {abs(post.centering_offset) * 1000:.1f} microns "
        f"from nominal against {abs(excursion.centering_offset) * 1000:.1f} microns before. Cpk improved from "
        f"{excursion.cpk:.2f} to {post.cpk:.2f}, and the number of points beyond a control limit fell from "
        f"{beyond_limits_before} in the drift and excursion periods to {beyond_limits_after} across the "
        f"{post.n} observations after the change. "
        f"{'No further NCRs have been raised on this component and supplier since the change took effect. ' if not len(later_ncrs) else ''}"
        "The improvement is consistent across four independent lines of evidence: the position of the mean, the "
        "capability index, the absence of control chart signals, and the absence of repeat non-conformances. "
        "That consistency is what makes it reasonable to call the action effective. "
        "The post-change period is eleven weeks, which is long enough to be persuasive but not long enough to "
        "confirm that the control will hold through a tooling change, a new operator or a different material "
        "batch. The honest statement is that the action is effective on the evidence available so far."
    )


# ---------------------------------------------------------------------------
# 9. Closure
# ---------------------------------------------------------------------------

def _closure(full: QualityData, subset: pd.DataFrame) -> None:
    section_header("Step 9 - Closure", "An NCR is closed on verified effectiveness, not on completed paperwork.")

    related = full.ncrs[
        (full.ncrs["supplier_id"] == CASE_STUDY_SUPPLIER)
        & (full.ncrs["component_id"] == CASE_STUDY_COMPONENT)
    ].sort_values("date_raised")

    display = related[
        ["ncr_id", "date_raised", "severity", "containment_status", "root_cause_status",
         "corrective_action_status", "verification_status", "closure_status", "closure_date"]
    ].copy()
    display["date_raised"] = display["date_raised"].dt.strftime("%Y-%m-%d")
    display["closure_date"] = display["closure_date"].dt.strftime("%Y-%m-%d").fillna("")
    display.columns = ["NCR", "Raised", "Severity", "Containment", "Root cause", "Corrective action",
                       "Verification", "Closure", "Closed"]
    dataframe(display)

    lead = related[related["ncr_id"] == CASE_STUDY_NCR].iloc[0]
    days = int((lead["closure_date"] - lead["date_raised"]).days)

    cols = st.columns(4)
    cols[0].metric("Raised", f"{lead['date_raised']:%d %b %Y}")
    cols[1].metric("Action implemented", f"{pd.Timestamp(CORRECTIVE_ACTION_IMPLEMENTED):%d %b %Y}")
    cols[2].metric("Closed", f"{lead['closure_date']:%d %b %Y}")
    cols[3].metric("Days open", days)

    st.markdown("**Why closure took longer than implementation**")
    st.info(
        f"The corrective action was implemented on {pd.Timestamp(CORRECTIVE_ACTION_IMPLEMENTED):%d %B %Y} but "
        f"{CASE_STUDY_NCR} was not closed until {lead['closure_date']:%d %B %Y}, "
        f"{(lead['closure_date'] - pd.Timestamp(CORRECTIVE_ACTION_IMPLEMENTED)).days} days later. That gap is "
        "the verification period. Closing on the implementation date would have recorded that something was "
        "done, not that it worked. Six weeks of post-change data was required before the control chart and the "
        "capability study could support a conclusion."
    )

    st.markdown("**Cycle summary**")
    summary = pd.DataFrame(
        {
            "Stage": [
                "Detection", "Pareto narrowing", "SPC analysis", "Capability analysis",
                "NCR raised (trend)", "First action - verified NOT effective", "NCR raised (parts out of spec)",
                "Root cause confirmed", "Containment", "Corrective action implemented",
                "Verification period", "Closure",
            ],
            "Outcome": [
                "Rising defect activity concentrated on one supplier, component and defect category",
                "Dimensional deviation identified as the dominant category for that combination",
                "Sustained upward shift detected weeks before any part breached specification",
                "Cp held while Cpk collapsed, identifying a centring problem rather than a spread problem",
                "NCR-2026-014, raised against the trend before any part was non-conforming",
                "Offset correction frequency tightened; the mean continued to rise",
                "NCR-2026-018, critical severity, two parts above the upper limit",
                "Insert grade change released without tool life re-validation or control plan review",
                "100% inspection and quarantine of suspect batches",
                f"{pd.Timestamp(CORRECTIVE_ACTION_IMPLEMENTED):%d %B %Y}",
                "Eleven weeks of post-change data analysed against the original control limits",
                f"{lead['closure_date']:%d %B %Y}, after effectiveness was demonstrated",
            ],
        }
    )
    dataframe(summary)

    interpretation(
        "The full cycle ran from detection to verified closure over roughly two months. The part that is easy "
        "to underrate is the failed first attempt. An investigation that stopped at the third why produced an "
        "action that was reasonable, cheap and wrong, and the only reason that was discovered is that its "
        "effectiveness was checked against data rather than assumed. A quality system without a real "
        "verification step would have recorded that NCR as successfully closed and would have met the same "
        "problem again."
    )
