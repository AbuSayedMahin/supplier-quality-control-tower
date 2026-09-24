"""Process capability view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts
from src.capability import calculate_capability, capability_guideline, capability_is_trustworthy
from src.config import BASELINE_END, BASELINE_START, CASE_STUDY_COMPONENT, CASE_STUDY_SUPPLIER, PHASE_WINDOWS
from src.data_loader import QualityData
from src.spc import build_imr_table, order_for_analysis

from .common import caveats, dataframe, interpretation, no_data, section_header


def _default_index(options: list, preferred: str) -> int:
    return options.index(preferred) if preferred in options else 0


def render(data: QualityData, full: QualityData) -> None:
    st.header("Process Capability")
    st.caption(
        "Compares what the process produces against what the drawing allows. Capability describes a stable "
        "process; if the process is not stable the indices describe the period measured rather than predicting "
        "future output."
    )

    if not len(data.inspections):
        no_data()
        return

    col1, col2, col3 = st.columns([1, 1, 1.2])
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

    with col3:
        window_options = ["All data in current filter"] + list(PHASE_WINDOWS)
        window = st.selectbox(
            "Analysis window",
            window_options,
            help=(
                "Capability calculated across a period that contains a process change is an average of two "
                "different processes and describes neither. Selecting a single phase gives a meaningful answer."
            ),
        )

    subset = order_for_analysis(
        data.inspections[
            (data.inspections["component_id"] == component_id)
            & (data.inspections["supplier_id"] == supplier_id)
        ]
    )

    if window != "All data in current filter":
        start, end = PHASE_WINDOWS[window]
        subset = subset[(subset["inspection_date"] >= start) & (subset["inspection_date"] <= end)]

    if len(subset) < 10:
        no_data(f"Only {len(subset)} measurements in this selection. That is too few for a capability study.")
        return

    spec = full.component_spec(component_id)
    result = calculate_capability(
        subset["measured_value"], lsl=spec["lsl"], usl=spec["usl"], nominal=spec["nominal"]
    )

    # Stability check, because capability is only interpretable for a stable process.
    baseline_mask = (
        (subset["inspection_date"] >= BASELINE_START) & (subset["inspection_date"] <= BASELINE_END)
    ).reset_index(drop=True)
    imr, _ = build_imr_table(subset, baseline_mask=baseline_mask if baseline_mask.any() else None)
    unstable = bool(imr["any_rule"].any())

    # ------------------------------------------------------------------
    # Indices
    # ------------------------------------------------------------------
    m = st.columns(5)
    m[0].metric("n", f"{result.n:,}")
    m[1].metric("Mean", f"{result.mean:.5f}")
    m[2].metric("Sigma (within)", f"{result.sigma_within:.5f}",
                help="Short-term variation estimated from the average moving range.")
    m[3].metric("Cp", f"{result.cp:.2f}", help="Tolerance width divided by six sigma. Ignores centring.")
    m[4].metric("Cpk", f"{result.cpk:.2f}", help="Distance from the mean to the nearer limit, over three sigma.")

    m2 = st.columns(5)
    m2[0].metric("Cpu", f"{result.cpu:.2f}", help="Capability against the upper limit only.")
    m2[1].metric("Cpl", f"{result.cpl:.2f}", help="Capability against the lower limit only.")
    m2[2].metric("Sigma (overall)", f"{result.sigma_overall:.5f}",
                 help="Standard deviation of all the data, including any drift across the period.")
    m2[3].metric("Pp", f"{result.pp:.2f}", help="As Cp but using the overall standard deviation.")
    m2[4].metric("Ppk", f"{result.ppk:.2f}", help="As Cpk but using the overall standard deviation.")

    st.plotly_chart(
        charts.capability_histogram(
            subset["measured_value"],
            result,
            f"{spec['characteristic']} distribution - {full.component_name(component_id)} "
            f"from {full.supplier_name(supplier_id)}",
        ),
        width='stretch',
    )

    # ------------------------------------------------------------------
    # Supporting numbers
    # ------------------------------------------------------------------
    left, right = st.columns(2)
    with left:
        st.markdown("**Process position**")
        dataframe(
            pd.DataFrame(
                {
                    "Measure": [
                        "Nominal", "Process mean", "Offset from nominal", "Offset as % of tolerance",
                        "Process spread (6 sigma within)", "Tolerance band", "Tolerance consumed",
                    ],
                    "Value": [
                        f"{result.nominal:.4f} {spec['unit']}",
                        f"{result.mean:.5f} {spec['unit']}",
                        f"{result.centering_offset:+.5f} {spec['unit']}",
                        f"{result.centering_offset_pct:+.1f}%",
                        f"{6 * result.sigma_within:.5f} {spec['unit']}",
                        f"{result.usl - result.lsl:.4f} {spec['unit']}",
                        f"{result.tolerance_used_pct:.1f}%",
                    ],
                }
            )
        )

    with right:
        st.markdown("**Out-of-specification output**")
        dataframe(
            pd.DataFrame(
                {
                    "Measure": [
                        "Observed out of specification", "Observed PPM", "Predicted PPM (normal model)",
                        f"Normality test ({result.normality_test})", "Process stable over window",
                    ],
                    "Value": [
                        f"{result.observed_out_of_spec} of {result.n}",
                        f"{result.observed_out_of_spec_ppm:,.0f}",
                        f"{result.predicted_out_of_spec_ppm:,.0f}",
                        f"p = {result.normality_p_value:.4f}",
                        "No - control rule violations present" if unstable else "No violations detected",
                    ],
                }
            )
        )
        st.caption(
            "Predicted PPM comes from fitting a normal distribution to the data. It is a model output, not a "
            "count, and it can differ substantially from the observed figure when the distribution is skewed or "
            "the process was not stable."
        )

    # ------------------------------------------------------------------
    # Interpretation
    # ------------------------------------------------------------------
    lines = [capability_guideline(result.cpk)]

    gap = result.cp - result.cpk
    if gap > 0.15:
        lines.append(
            f"Cp is {result.cp:.2f} but Cpk is only {result.cpk:.2f}. The spread of the process would fit inside "
            f"the tolerance, but the mean sits {result.centering_offset:+.4f} {spec['unit']} from nominal, which "
            "is what pulls Cpk down. This is a centring problem rather than a variation problem, and centring is "
            "usually the easier of the two to correct."
        )
    else:
        lines.append(
            f"Cp ({result.cp:.2f}) and Cpk ({result.cpk:.2f}) are close, so the process is reasonably well "
            "centred within the tolerance. Any improvement from here would have to come from reducing variation "
            "rather than from moving the mean."
        )

    ppk_gap = result.cpk - result.ppk
    if abs(ppk_gap) > 0.15:
        lines.append(
            f"Cpk ({result.cpk:.2f}) and Ppk ({result.ppk:.2f}) differ noticeably. Cpk uses short-term variation "
            "between consecutive parts while Ppk uses the spread of the whole period, so a gap of this size "
            "indicates that the process moved over the window rather than holding one steady position."
        )

    interpretation(" ".join(lines))

    caveats(capability_is_trustworthy(unstable, result.normality_p_value, result.n))

    with st.expander("How these indices were calculated"):
        st.markdown(
            f"""
```
Cp  = (USL - LSL) / (6 x sigma_within)
    = ({result.usl:.3f} - {result.lsl:.3f}) / (6 x {result.sigma_within:.5f})
    = {result.cp:.3f}

Cpu = (USL - mean) / (3 x sigma_within) = ({result.usl:.3f} - {result.mean:.5f}) / (3 x {result.sigma_within:.5f}) = {result.cpu:.3f}
Cpl = (mean - LSL) / (3 x sigma_within) = ({result.mean:.5f} - {result.lsl:.3f}) / (3 x {result.sigma_within:.5f}) = {result.cpl:.3f}

Cpk = min(Cpu, Cpl) = {result.cpk:.3f}
```

`sigma_within` is estimated from the average moving range (MR-bar / 1.128), which captures short-term
part-to-part variation. `sigma_overall` is the sample standard deviation and includes any drift across the
period; it is what Pp and Ppk are built from.

Cpk can never be larger than Cp. They are equal only when the process mean sits exactly halfway between the
two specification limits.
"""
        )

    # ------------------------------------------------------------------
    # Phase comparison
    # ------------------------------------------------------------------
    st.divider()
    section_header(
        "Capability by phase",
        "The same characteristic measured over each phase of the period, so the effect of the process change is "
        "visible rather than averaged away.",
    )

    all_subset = data.inspections[
        (data.inspections["component_id"] == component_id)
        & (data.inspections["supplier_id"] == supplier_id)
    ]
    rows = []
    for label, (start, end) in PHASE_WINDOWS.items():
        phase = all_subset[(all_subset["inspection_date"] >= start) & (all_subset["inspection_date"] <= end)]
        if len(phase) < 10:
            continue
        phase_result = calculate_capability(
            phase["measured_value"], lsl=spec["lsl"], usl=spec["usl"], nominal=spec["nominal"]
        )
        rows.append(
            {
                "Phase": label,
                "n": phase_result.n,
                "Mean": round(phase_result.mean, 5),
                "Sigma (within)": round(phase_result.sigma_within, 5),
                "Cp": round(phase_result.cp, 2),
                "Cpk": round(phase_result.cpk, 2),
                "Ppk": round(phase_result.ppk, 2),
                "Out of spec": phase_result.observed_out_of_spec,
            }
        )

    if rows:
        dataframe(pd.DataFrame(rows))
    else:
        st.caption("Not enough data in each phase for this component and supplier combination.")
