"""Statistical Process Control calculations.

This module implements an Individuals / Moving Range (I-MR) chart. An I-MR chart
is the appropriate choice here because inspection results arrive as single
measurements per part rather than as rational subgroups of several parts taken
under the same conditions, so there is no within-subgroup range to work with.

Two ideas in this module matter more than the code:

1.  Control limits are estimated from the SHORT-TERM variation between
    consecutive parts (the moving range), not from the overall spread of the
    data. That is what makes a control chart able to detect a slow drift: the
    drift inflates the overall spread but not the part-to-part range, so the
    points walk outside limits that stayed narrow.

2.  Control limits are calculated from a chosen BASELINE period and then held
    fixed and projected forward. This is the standard Phase I / Phase II
    approach. If limits were recalculated over all the data, the drift would
    widen the limits and partially hide the very signal being looked for.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import D2_N2, D3_N2, D4_N2, E2_N2


@dataclass
class ControlLimits:
    """Control limits for an I-MR chart, plus the sigma estimate behind them."""

    center_line: float
    ucl: float
    lcl: float
    mr_center_line: float
    mr_ucl: float
    mr_lcl: float
    sigma_within: float
    n_baseline: int
    # Sigma-zone boundaries on the individuals chart, used by the pattern rules.
    zones: dict = field(default_factory=dict)


def moving_ranges(values: np.ndarray) -> np.ndarray:
    """Absolute differences between consecutive observations.

    The first observation has no predecessor, so the returned array is one
    element shorter than the input.
    """
    values = np.asarray(values, dtype=float)
    if values.size < 2:
        return np.array([])
    return np.abs(np.diff(values))


def calculate_control_limits(baseline_values) -> ControlLimits:
    """Derive I-MR control limits from a baseline sample.

    sigma is estimated as MR-bar / d2 rather than as the sample standard
    deviation. d2 = 1.128 is the expected value of the range of two observations
    from a standard normal distribution, so dividing by it converts an average
    moving range back into an estimate of the process standard deviation.
    """
    values = np.asarray(baseline_values, dtype=float)
    values = values[~np.isnan(values)]
    if values.size < 2:
        raise ValueError("At least two observations are required to estimate control limits.")

    center_line = float(values.mean())
    mr = moving_ranges(values)
    mr_bar = float(mr.mean())

    # E2 = 3 / d2, so this is a genuine 3-sigma limit, not a rule of thumb.
    ucl = center_line + E2_N2 * mr_bar
    lcl = center_line - E2_N2 * mr_bar
    sigma_within = mr_bar / D2_N2 if mr_bar > 0 else 0.0

    zones = {
        "plus_1s": center_line + sigma_within,
        "plus_2s": center_line + 2 * sigma_within,
        "minus_1s": center_line - sigma_within,
        "minus_2s": center_line - 2 * sigma_within,
    }

    return ControlLimits(
        center_line=center_line,
        ucl=ucl,
        lcl=lcl,
        mr_center_line=mr_bar,
        mr_ucl=D4_N2 * mr_bar,
        mr_lcl=D3_N2 * mr_bar,
        sigma_within=sigma_within,
        n_baseline=int(values.size),
        zones=zones,
    )


# ---------------------------------------------------------------------------
# Pattern detection (Western Electric style rules)
#
# A point outside the control limits is only the most obvious signal. The
# supporting rules exist because a process can drift a long way before any
# single point crosses a limit, and a run of points on one side of the centre
# line is statistically very unlikely if the process is genuinely stable.
# ---------------------------------------------------------------------------

RULE_DESCRIPTIONS = {
    "rule_1": "1 point beyond 3 sigma (outside a control limit)",
    "rule_2": "2 out of 3 consecutive points beyond 2 sigma on the same side",
    "rule_3": "4 out of 5 consecutive points beyond 1 sigma on the same side",
    "rule_4": "8 consecutive points on the same side of the centre line",
}


def apply_control_rules(values, limits: ControlLimits) -> pd.DataFrame:
    """Flag each observation against four standard control chart rules.

    Returns a DataFrame with one boolean column per rule plus an ``any_rule``
    column. Every point that takes part in a violating pattern is flagged, not
    just the last point of the pattern, so the chart shows the whole run.
    """
    x = np.asarray(values, dtype=float)
    n = x.size
    flags = {name: np.zeros(n, dtype=bool) for name in RULE_DESCRIPTIONS}

    if n == 0:
        return pd.DataFrame(flags)

    cl = limits.center_line
    s = limits.sigma_within

    # Rule 1 - beyond the control limits.
    flags["rule_1"] = (x > limits.ucl) | (x < limits.lcl)

    if s > 0:
        above_2s = x > cl + 2 * s
        below_2s = x < cl - 2 * s
        above_1s = x > cl + s
        below_1s = x < cl - s

        # Rule 2 - 2 of any 3 consecutive points beyond 2 sigma, same side.
        for i in range(n - 2):
            window = slice(i, i + 3)
            for side in (above_2s, below_2s):
                if side[window].sum() >= 2:
                    flags["rule_2"][window] = np.where(side[window], True, flags["rule_2"][window])

        # Rule 3 - 4 of any 5 consecutive points beyond 1 sigma, same side.
        for i in range(n - 4):
            window = slice(i, i + 5)
            for side in (above_1s, below_1s):
                if side[window].sum() >= 4:
                    flags["rule_3"][window] = np.where(side[window], True, flags["rule_3"][window])

    # Rule 4 - 8 consecutive points on one side of the centre line. A sustained
    # run like this is the classic signature of a shifted process mean.
    above_cl = x > cl
    below_cl = x < cl
    for side in (above_cl, below_cl):
        run = 0
        for i in range(n):
            run = run + 1 if side[i] else 0
            if run >= 8:
                flags["rule_4"][i - run + 1 : i + 1] = True

    out = pd.DataFrame(flags)
    out["any_rule"] = out.any(axis=1)
    return out


def order_for_analysis(
    df: pd.DataFrame,
    date_col: str = "inspection_date",
    id_col: str = "inspection_id",
) -> pd.DataFrame:
    """Put inspection records into a single, deterministic production order.

    This matters more than it looks. A moving range is the difference between
    CONSECUTIVE parts, so the sequence is part of the calculation, not just
    presentation. Several parts share an inspection date, and sorting by date
    alone leaves their relative order undefined - pandas' default sort is not
    stable, so two sorts of the same data can interleave same-day records
    differently and produce a different MR-bar, different control limits and a
    different sigma estimate.

    Sorting by date and then by inspection ID with a stable sort fixes the
    order, because the IDs are issued in production sequence.
    """
    keys = [date_col] + ([id_col] if id_col in df.columns else [])
    return df.sort_values(keys, kind="mergesort").reset_index(drop=True)


def build_imr_table(
    df: pd.DataFrame,
    value_col: str = "measured_value",
    date_col: str = "inspection_date",
    baseline_mask: pd.Series | None = None,
) -> tuple[pd.DataFrame, ControlLimits]:
    """Assemble a plot-ready I-MR table with limits and rule violations.

    ``baseline_mask`` selects the Phase I period used to estimate the limits. If
    it is omitted the whole series is used, which is only appropriate when the
    process is believed to have been stable throughout. The mask is matched on
    position, so it must have been built from the same rows in the same order.
    """
    work = order_for_analysis(df, date_col=date_col).copy()
    values = work[value_col].to_numpy(dtype=float)

    if baseline_mask is None:
        baseline_values = values
    else:
        baseline_values = work.loc[baseline_mask.reindex(work.index, fill_value=False), value_col].to_numpy(
            dtype=float
        )
        if baseline_values.size < 2:
            baseline_values = values

    limits = calculate_control_limits(baseline_values)

    work["observation"] = np.arange(1, len(work) + 1)
    work["moving_range"] = np.concatenate([[np.nan], moving_ranges(values)])

    rules = apply_control_rules(values, limits)
    work = pd.concat([work, rules], axis=1)

    # The moving range chart has its own out-of-control condition: an unusually
    # large jump between consecutive parts indicates an abrupt change.
    work["mr_out_of_control"] = work["moving_range"] > limits.mr_ucl
    work["mr_out_of_control"] = work["mr_out_of_control"].fillna(False)

    return work, limits


def summarise_violations(imr: pd.DataFrame) -> pd.DataFrame:
    """Count how many observations trip each rule, for the interpretation text."""
    rows = []
    for rule, description in RULE_DESCRIPTIONS.items():
        if rule in imr.columns:
            rows.append(
                {
                    "Rule": rule.replace("_", " ").title(),
                    "Description": description,
                    "Points flagged": int(imr[rule].sum()),
                }
            )
    return pd.DataFrame(rows)
