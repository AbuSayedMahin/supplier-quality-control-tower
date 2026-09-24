"""Process capability calculations.

Capability answers a different question from a control chart. A control chart
asks "is this process consistent over time?". Capability asks "given how this
process behaves, does its output fit inside the drawing tolerance?".

The order matters: capability indices are only meaningful for a process that is
already stable, because an unstable process does not have a single mean and
standard deviation to describe. That caveat is carried through the return value
of :func:`calculate_capability` so the application can display it rather than
quietly reporting a number that does not mean what it appears to mean.

Two families of index are calculated:

*   Cp / Cpk use a SHORT-TERM (within) sigma estimated from the moving range.
    These describe what the process is capable of when it is behaving
    consistently - sometimes called potential capability.
*   Pp / Ppk use the overall sample standard deviation, which includes any
    drift or shift across the period. These describe what the process actually
    delivered - sometimes called performance.

A large gap between Cpk and Ppk is itself evidence of instability.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
from scipy import stats

from .config import D2_N2
from .spc import moving_ranges


@dataclass
class CapabilityResult:
    n: int
    mean: float
    sigma_within: float
    sigma_overall: float
    lsl: float
    usl: float
    nominal: float
    cp: float
    cpk: float
    cpu: float
    cpl: float
    pp: float
    ppk: float
    # Fraction of the tolerance band consumed by the process spread.
    tolerance_used_pct: float
    # Distance of the process mean from nominal, in units and as a % of tolerance.
    centering_offset: float
    centering_offset_pct: float
    observed_out_of_spec: int
    observed_out_of_spec_ppm: float
    predicted_out_of_spec_ppm: float
    normality_p_value: float
    normality_test: str

    def as_dict(self) -> dict:
        return asdict(self)


def _safe_div(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator and denominator > 0 else float("nan")


def calculate_capability(values, lsl: float, usl: float, nominal: float | None = None) -> CapabilityResult:
    """Calculate Cp, Cpk, Pp and Ppk for a set of measurements.

    Formulae
    --------
    Cp  = (USL - LSL) / (6 * sigma_within)
        How wide the tolerance is compared with the process spread. It ignores
        where the process is centred, so a badly centred process can still have
        a flattering Cp.

    Cpk = min( (USL - mean) / (3 * sigma_within), (mean - LSL) / (3 * sigma_within) )
        The same comparison but measured to the NEAREST specification limit, so
        it penalises a process that has drifted off centre. Cpk can never
        exceed Cp; they are equal only when the process is perfectly centred.

    Pp / Ppk are identical in form but use the overall standard deviation.
    """
    x = np.asarray(values, dtype=float)
    x = x[~np.isnan(x)]
    n = int(x.size)
    if n < 2:
        raise ValueError("At least two measurements are required for a capability study.")

    mean = float(x.mean())
    # ddof=1 - this is a sample drawn from an ongoing process, not a whole population.
    sigma_overall = float(x.std(ddof=1))

    mr = moving_ranges(x)
    mr_bar = float(mr.mean()) if mr.size else 0.0
    sigma_within = mr_bar / D2_N2 if mr_bar > 0 else sigma_overall

    tolerance = usl - lsl
    nominal = float(nominal) if nominal is not None else (usl + lsl) / 2.0

    cp = _safe_div(tolerance, 6 * sigma_within)
    cpu = _safe_div(usl - mean, 3 * sigma_within)
    cpl = _safe_div(mean - lsl, 3 * sigma_within)
    cpk = float(np.nanmin([cpu, cpl]))

    pp = _safe_div(tolerance, 6 * sigma_overall)
    ppu = _safe_div(usl - mean, 3 * sigma_overall)
    ppl = _safe_div(mean - lsl, 3 * sigma_overall)
    ppk = float(np.nanmin([ppu, ppl]))

    observed_oos = int(((x > usl) | (x < lsl)).sum())

    # Predicted out-of-spec assumes the measurements are normally distributed.
    # It is a model output, not a count, and is labelled as such in the app.
    if sigma_overall > 0:
        tail_high = 1 - stats.norm.cdf(usl, loc=mean, scale=sigma_overall)
        tail_low = stats.norm.cdf(lsl, loc=mean, scale=sigma_overall)
        predicted_ppm = float((tail_high + tail_low) * 1_000_000)
    else:
        predicted_ppm = 0.0

    # Shapiro-Wilk is a reasonable general normality test for samples of this
    # size. It is reported so the normality assumption behind the predicted PPM
    # is visible rather than hidden.
    if 3 <= n <= 5000:
        _, p_value = stats.shapiro(x)
        test_name = "Shapiro-Wilk"
    else:
        _, p_value = stats.normaltest(x)
        test_name = "D'Agostino-Pearson"

    return CapabilityResult(
        n=n,
        mean=mean,
        sigma_within=float(sigma_within),
        sigma_overall=sigma_overall,
        lsl=float(lsl),
        usl=float(usl),
        nominal=nominal,
        cp=cp,
        cpk=cpk,
        cpu=cpu,
        cpl=cpl,
        pp=pp,
        ppk=ppk,
        tolerance_used_pct=float(100 * (6 * sigma_within) / tolerance) if tolerance > 0 else float("nan"),
        centering_offset=float(mean - nominal),
        centering_offset_pct=float(100 * (mean - nominal) / tolerance) if tolerance > 0 else float("nan"),
        observed_out_of_spec=observed_oos,
        observed_out_of_spec_ppm=float(1_000_000 * observed_oos / n),
        predicted_out_of_spec_ppm=predicted_ppm,
        normality_p_value=float(p_value),
        normality_test=test_name,
    )


def capability_guideline(cpk: float) -> str:
    """Describe a Cpk against commonly quoted guideline values.

    These thresholds are widely used industry conventions, not standards that
    apply everywhere. The wording deliberately presents them as guidelines and
    points back to the customer or drawing requirement.
    """
    if np.isnan(cpk):
        return "Cpk could not be calculated for this selection."
    if cpk < 1.00:
        band = (
            "below 1.00 - the process spread does not fit inside the tolerance, so a "
            "measurable proportion of output is expected to fall outside specification."
        )
    elif cpk < 1.33:
        band = (
            "between 1.00 and 1.33 - the output nominally fits the tolerance but with "
            "little margin, so a small shift would start producing non-conforming parts."
        )
    elif cpk < 1.67:
        band = (
            "between 1.33 and 1.67 - commonly treated as an acceptable level for an "
            "established process in many manufacturing sectors."
        )
    else:
        band = (
            "at or above 1.67 - a level often expected for safety-critical or "
            "high-consequence characteristics."
        )
    return (
        f"Cpk is {cpk:.2f}, which is {band} These bands are widely used industry "
        "guidelines rather than universal requirements; the applicable target should "
        "come from the customer specification or quality agreement for the characteristic."
    )


def capability_is_trustworthy(has_out_of_control_points: bool, normality_p: float, n: int) -> list[str]:
    """Return the caveats that apply to a capability result.

    Reporting Cp and Cpk without checking these is one of the most common ways
    capability analysis is misused.
    """
    caveats = []
    if has_out_of_control_points:
        caveats.append(
            "The control chart for this selection shows out-of-control signals. Capability "
            "indices assume a stable process, so these values describe the period that was "
            "measured rather than a predictable future state."
        )
    if normality_p < 0.05:
        caveats.append(
            f"The normality test returns p = {normality_p:.4f}, so the assumption of a normal "
            "distribution is not well supported. The predicted out-of-specification PPM should "
            "be treated with caution; the observed count is the more reliable figure."
        )
    if n < 30:
        caveats.append(
            f"Only {n} measurements are included. Capability estimates from small samples carry "
            "wide confidence intervals and can move considerably as more data is collected."
        )
    return caveats
