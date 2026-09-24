"""Statistical process control view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts
from src.config import BASELINE_END, BASELINE_START, CASE_STUDY_COMPONENT, CASE_STUDY_SUPPLIER
from src.data_loader import QualityData
from src.spc import build_imr_table, order_for_analysis, summarise_violations

from .common import dataframe, interpretation, no_data, section_header


def _default_index(options: list, preferred: str) -> int:
    return options.index(preferred) if preferred in options else 0


def render(data: QualityData, full: QualityData) -> None:
    st.header("Statistical Process Control")
    st.caption(
        "Individuals and Moving Range chart for a single critical characteristic. An I-MR chart is used because "
        "inspection produces one measurement per part rather than rational subgroups."
    )

    if not len(data.inspections):
        no_data()
        return

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------
    col1, col2 = st.columns(2)
    components = sorted(data.inspections["component_id"].unique())
    with col1:
        component_id = st.selectbox(
            "Component",
            components,
            index=_default_index(components, CASE_STUDY_COMPONENT),
            format_func=lambda c: full.label_map("component").get(c, c),
        )

    supplier_options = sorted(
        data.inspections.loc[data.inspections["component_id"] == component_id, "supplier_id"].unique()
    )
    with col2:
        supplier_id = st.selectbox(
            "Supplier",
            supplier_options,
            index=_default_index(supplier_options, CASE_STUDY_SUPPLIER),
            format_func=lambda s: full.label_map("supplier").get(s, s),
        )

    subset = order_for_analysis(
        data.inspections[
            (data.inspections["component_id"] == component_id)
            & (data.inspections["supplier_id"] == supplier_id)
        ]
    )

    if len(subset) < 10:
        no_data(
            f"Only {len(subset)} measurements available for this combination. A control chart needs a reasonable "
            "run of data before its limits mean anything."
        )
        return

    spec = full.component_spec(component_id)

    # ------------------------------------------------------------------
    # Baseline selection for the control limits
    # ------------------------------------------------------------------
    st.markdown("**Control limit basis**")
    basis = st.radio(
        "Control limit basis",
        ["Baseline period (recommended)", "All displayed data"],
        horizontal=True,
        label_visibility="collapsed",
        help=(
            "Control limits describe how a process behaves when it is stable, so they should be estimated from "
            "a period when it was stable and then held fixed. Estimating them from all the data lets a later "
            "drift widen the limits and hide the signal it was meant to detect."
        ),
    )

    if basis.startswith("Baseline"):
        baseline_start, baseline_end = st.select_slider(
            "Baseline window",
            options=sorted(subset["inspection_date"].dt.date.unique()),
            value=(
                max(pd.Timestamp(BASELINE_START).date(), subset["inspection_date"].min().date()),
                min(pd.Timestamp(BASELINE_END).date(), subset["inspection_date"].max().date()),
            ),
        )
        baseline_mask = (
            subset["inspection_date"].dt.date >= baseline_start
        ) & (subset["inspection_date"].dt.date <= baseline_end)
        baseline_mask = baseline_mask.reset_index(drop=True)
        basis_note = (
            f"Limits estimated from {baseline_start} to {baseline_end} and projected across the full period."
        )
    else:
        baseline_mask = None
        basis_note = "Limits estimated from every displayed observation."

    imr, limits = build_imr_table(subset, baseline_mask=baseline_mask)

    show_spec = st.checkbox(
        "Show specification limits on the individuals chart",
        value=True,
        help=(
            "Specification limits and control limits are different things and are never calculated from each "
            "other. They are shown together here only because the comparison between them is informative."
        ),
    )

    st.plotly_chart(
        charts.individuals_chart(
            imr,
            limits,
            spec,
            f"Individuals chart - {spec['characteristic']} on {full.component_name(component_id)} "
            f"from {full.supplier_name(supplier_id)}",
            show_spec=show_spec,
        ),
        width='stretch',
    )
    st.plotly_chart(charts.moving_range_chart(imr, limits), width='stretch')
    st.caption(basis_note)

    # ------------------------------------------------------------------
    # Limits table - the control vs specification distinction made explicit
    # ------------------------------------------------------------------
    st.divider()
    section_header("Control limits and specification limits")

    left, right = st.columns(2)
    with left:
        st.markdown("**Control limits** - what this process actually does")
        st.caption(
            "Calculated from the data using the average moving range between consecutive parts. They describe "
            "the voice of the process. Nothing about the drawing or the customer enters this calculation."
        )
        dataframe(
            pd.DataFrame(
                {
                    "Statistic": ["Centre line (X-bar)", "Upper control limit", "Lower control limit",
                                  "Sigma (within, MR-bar / d2)", "Mean moving range", "Baseline observations"],
                    "Value": [
                        f"{limits.center_line:.5f}",
                        f"{limits.ucl:.5f}",
                        f"{limits.lcl:.5f}",
                        f"{limits.sigma_within:.5f}",
                        f"{limits.mr_center_line:.5f}",
                        f"{limits.n_baseline}",
                    ],
                }
            )
        )

    with right:
        st.markdown("**Specification limits** - what the design requires")
        st.caption(
            "Taken from the drawing. They are fixed by the engineering requirement and would be identical if "
            "the part were made on a different machine, by a different supplier, or not at all."
        )
        dataframe(
            pd.DataFrame(
                {
                    "Statistic": ["Nominal", "Upper specification limit", "Lower specification limit",
                                  "Total tolerance", "Criticality"],
                    "Value": [
                        f"{spec['nominal']:.3f} {spec['unit']}",
                        f"{spec['usl']:.3f} {spec['unit']}",
                        f"{spec['lsl']:.3f} {spec['unit']}",
                        f"{spec['usl'] - spec['lsl']:.3f} {spec['unit']}",
                        str(spec["criticality"]),
                    ],
                }
            )
        )

    # ------------------------------------------------------------------
    # Rule violations
    # ------------------------------------------------------------------
    st.divider()
    section_header(
        "Control rule violations",
        "A point outside a control limit is only the most obvious signal. The supporting run rules detect a "
        "process that has shifted but has not yet produced an extreme individual value.",
    )

    violations = summarise_violations(imr)
    dataframe(violations)

    flagged = imr[imr["any_rule"]]
    total_flagged = int(len(flagged))
    out_of_spec = int((imr["in_spec"] == 0).sum())

    metrics = st.columns(4)
    metrics[0].metric("Observations", f"{len(imr):,}")
    metrics[1].metric("Points violating a control rule", f"{total_flagged:,}")
    metrics[2].metric("Points outside specification", f"{out_of_spec:,}")
    metrics[3].metric(
        "Moving range exceedances", f"{int(imr['mr_out_of_control'].sum()):,}",
        help="Jumps between consecutive parts larger than the moving range upper limit.",
    )

    # ------------------------------------------------------------------
    # Interpretation
    # ------------------------------------------------------------------
    lines = []
    if total_flagged == 0:
        lines.append(
            "No control rule violations are present in this selection. On this evidence the process behaved "
            "consistently over the period shown, which is the condition that has to hold before a capability "
            "index can be interpreted as describing future output."
        )
    else:
        first_flag = flagged["inspection_date"].min()
        lines.append(
            f"{total_flagged} of {len(imr):,} observations violate at least one control rule, the first on "
            f"{first_flag:%d %B %Y}. That is evidence of special-cause variation: something changed in the "
            "process rather than the normal random variation continuing."
        )
        if out_of_spec:
            first_oos = imr.loc[imr["in_spec"] == 0, "inspection_date"].min()
            gap = (first_oos - first_flag).days
            if gap > 0:
                lines.append(
                    f"The first part outside specification was not recorded until {first_oos:%d %B %Y}, "
                    f"{gap} days after the first control rule violation. The control chart therefore signalled "
                    "the change well before the specification was breached, which is the practical argument for "
                    "monitoring a process rather than only inspecting its output."
                )
        else:
            lines.append(
                "No part in this selection fell outside specification. A process can be out of control while "
                "still producing conforming parts; that is a warning, not an all-clear, because the process is "
                "no longer predictable."
            )

        if imr["mr_out_of_control"].sum() == 0:
            lines.append(
                "The moving range chart shows no exceedances, so part-to-part variation stayed broadly stable "
                "while the average moved. That pattern points to a shift in the process centre rather than a "
                "loss of machine consistency."
            )

    interpretation(" ".join(lines))

    with st.expander("How these limits were calculated"):
        st.markdown(
            f"""
Sigma is estimated from the average moving range rather than from the standard deviation of all the data:

- Mean moving range (MR-bar) = `{limits.mr_center_line:.5f}`
- Sigma = MR-bar / d2 = `{limits.mr_center_line:.5f}` / `1.128` = `{limits.sigma_within:.5f}`
- UCL = X-bar + 2.660 x MR-bar = `{limits.center_line:.5f}` + 2.660 x `{limits.mr_center_line:.5f}` = `{limits.ucl:.5f}`
- LCL = X-bar - 2.660 x MR-bar = `{limits.lcl:.5f}`
- Moving range UCL = 3.267 x MR-bar = `{limits.mr_ucl:.5f}`

The constant 2.660 is 3 / d2, so these are genuine three-sigma limits. Using the moving range is what makes the
chart sensitive to drift: a slow shift inflates the overall standard deviation but leaves the difference between
consecutive parts largely unchanged, so limits built from the moving range stay narrow and the drifting points
walk outside them.
"""
        )
