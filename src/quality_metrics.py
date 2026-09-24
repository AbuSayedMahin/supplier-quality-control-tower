"""Quality KPI calculations and Pareto analysis.

Every metric here is deliberately defined in code rather than assumed, because
the definition is the part that gets challenged in a review. Where a metric has
more than one common definition in industry, the choice made for this project is
stated in the docstring.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Core rate metrics
# ---------------------------------------------------------------------------

def defect_rate(defects: int, inspected: int) -> float:
    """Proportion of inspected units that were found non-conforming.

    Note this counts non-conforming UNITS, not individual defects. A unit with
    two separate problems on it is one non-conforming unit. That keeps the
    metric consistent with yield, which is also unit-based.
    """
    if inspected <= 0:
        return float("nan")
    return defects / inspected


def ppm(defects: int, inspected: int) -> float:
    """Defective parts per million.

    PPM is just the defect rate scaled by one million. It is used in supplier
    quality because defect rates at a decent supplier are small decimals that
    are awkward to compare, whereas "3,400 PPM versus 900 PPM" reads clearly.
    """
    rate = defect_rate(defects, inspected)
    return rate * 1_000_000 if not np.isnan(rate) else float("nan")


def first_pass_yield(defects: int, inspected: int) -> float:
    """Proportion of units that passed inspection first time, as a percentage.

    In this project each inspection record is a first-pass check on a unit, so
    FPY is the complement of the defect rate. In a multi-stage production line
    the rolled throughput yield would be the product of the FPY at each stage,
    which is a stricter and usually much lower figure.
    """
    rate = defect_rate(defects, inspected)
    return (1 - rate) * 100 if not np.isnan(rate) else float("nan")


@dataclass
class QualitySummary:
    inspected: int
    defects: int
    defect_rate_pct: float
    ppm: float
    fpy_pct: float
    open_ncrs: int
    closed_ncrs: int
    repeat_ncrs: int
    overdue_actions: int
    suppliers: int
    components: int

    def as_dict(self) -> dict:
        return asdict(self)


def summarise_quality(
    inspections: pd.DataFrame,
    ncrs: pd.DataFrame,
    actions: pd.DataFrame | None = None,
    as_of: pd.Timestamp | None = None,
) -> QualitySummary:
    """Roll a filtered dataset up into the headline control tower figures."""
    inspected = int(len(inspections))
    defects = int(inspections["defect_flag"].sum()) if inspected else 0

    open_ncrs = int((ncrs["closure_status"] != "Closed").sum()) if len(ncrs) else 0
    closed_ncrs = int((ncrs["closure_status"] == "Closed").sum()) if len(ncrs) else 0
    repeat = int(ncrs["is_repeat"].sum()) if len(ncrs) and "is_repeat" in ncrs else 0

    overdue = 0
    if actions is not None and len(actions):
        overdue = int(count_overdue_actions(actions, as_of=as_of))

    return QualitySummary(
        inspected=inspected,
        defects=defects,
        defect_rate_pct=defect_rate(defects, inspected) * 100 if inspected else float("nan"),
        ppm=ppm(defects, inspected),
        fpy_pct=first_pass_yield(defects, inspected),
        open_ncrs=open_ncrs,
        closed_ncrs=closed_ncrs,
        repeat_ncrs=repeat,
        overdue_actions=overdue,
        suppliers=int(inspections["supplier_id"].nunique()) if inspected else 0,
        components=int(inspections["component_id"].nunique()) if inspected else 0,
    )


# ---------------------------------------------------------------------------
# NCR derived fields
# ---------------------------------------------------------------------------

def flag_repeat_ncrs(ncrs: pd.DataFrame) -> pd.Series:
    """Mark an NCR as a repeat when the same problem has already been raised.

    Definition used here: an NCR is a repeat if an EARLIER NCR exists with the
    same supplier, component and defect category. The first occurrence is not a
    repeat; every subsequent occurrence is.

    Repeat NCRs matter more than the raw NCR count. A high NCR count can simply
    mean detection is working well. A high REPEAT count means corrective action
    is not removing causes, which is a different and more serious problem.
    """
    work = ncrs.sort_values("date_raised").copy()
    key = work["supplier_id"] + "|" + work["component_id"] + "|" + work["defect_category"]
    is_repeat = key.groupby(key).cumcount() > 0
    return is_repeat.reindex(ncrs.index)


def count_overdue_actions(actions: pd.DataFrame, as_of: pd.Timestamp | None = None) -> int:
    """Corrective actions past their due date that are not yet complete.

    An action that was completed after its due date is late but not currently
    overdue, so it is not counted here. It is still visible in the tracker.
    """
    if not len(actions):
        return 0
    as_of = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.today().normalize()
    not_complete = ~actions["status"].isin(["Complete", "Closed"])
    past_due = pd.to_datetime(actions["due_date"]) < as_of
    return int((not_complete & past_due).sum())


# ---------------------------------------------------------------------------
# Pareto analysis
# ---------------------------------------------------------------------------

def pareto_table(df: pd.DataFrame, category_col: str, value_col: str | None = None) -> pd.DataFrame:
    """Build a Pareto table: counts sorted descending with a cumulative share.

    The Pareto principle is an observation, not a law. The point of the chart is
    not to prove an 80/20 split exists but to rank contributors so that effort
    goes where it removes the most non-conformance.
    """
    if not len(df):
        return pd.DataFrame(columns=[category_col, "count", "cumulative_count", "percent", "cumulative_percent"])

    if value_col is None:
        counts = df.groupby(category_col).size().rename("count")
    else:
        counts = df.groupby(category_col)[value_col].sum().rename("count")

    table = counts.sort_values(ascending=False).reset_index()
    total = table["count"].sum()
    table["cumulative_count"] = table["count"].cumsum()
    table["percent"] = 100 * table["count"] / total if total else 0.0
    table["cumulative_percent"] = 100 * table["cumulative_count"] / total if total else 0.0
    return table


def vital_few(table: pd.DataFrame, threshold: float = 80.0) -> list[str]:
    """Categories that together make up the first ``threshold`` percent of counts.

    The category that crosses the threshold is included, otherwise the returned
    group would account for less than the threshold it is named after.
    """
    if not len(table):
        return []
    category_col = table.columns[0]
    crossed = table["cumulative_percent"] >= threshold
    if crossed.any():
        cutoff = int(crossed.idxmax()) + 1
    else:
        cutoff = len(table)
    return table[category_col].head(cutoff).tolist()


def pareto_interpretation(table: pd.DataFrame, threshold: float = 80.0) -> str:
    """Plain, non-inflated wording describing what the Pareto shows."""
    if not len(table):
        return "No non-conformances are recorded for the current filter selection."

    category_col = table.columns[0]
    few = vital_few(table, threshold)
    share = float(table.loc[table[category_col].isin(few), "percent"].sum())
    top = table.iloc[0]

    return (
        f"{len(few)} of the {len(table)} recorded defect categories account for "
        f"{share:.1f}% of non-conformances in the current selection. The largest single "
        f"contributor is '{top[category_col]}' at {int(top['count'])} occurrences "
        f"({top['percent']:.1f}%). On this evidence, investigation effort directed at the "
        "leading categories would address the majority of recorded non-conformance. This "
        "ranking reflects frequency only; categories with lower counts but higher severity "
        "or cost may still warrant separate attention."
    )


# ---------------------------------------------------------------------------
# Supplier scorecard
# ---------------------------------------------------------------------------

def supplier_scorecard(
    inspections: pd.DataFrame,
    ncrs: pd.DataFrame,
    actions: pd.DataFrame,
    suppliers: pd.DataFrame,
    as_of: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Per-supplier quality performance.

    Deliberately NOT reduced to a single ranking score. Combining PPM, delivery
    and open actions into one number hides which of them is the problem, and the
    weighting used would be arbitrary. The engineer reading this needs to see
    where a supplier needs attention, not a league table position.
    """
    rows = []
    as_of = pd.Timestamp(as_of) if as_of is not None else pd.Timestamp.today().normalize()

    for supplier_id, meta in suppliers.set_index("supplier_id").iterrows():
        insp = inspections[inspections["supplier_id"] == supplier_id]
        sup_ncrs = ncrs[ncrs["supplier_id"] == supplier_id]
        ncr_ids = set(sup_ncrs["ncr_id"])
        sup_actions = actions[actions["ncr_id"].isin(ncr_ids)]

        inspected = int(len(insp))
        defects = int(insp["defect_flag"].sum()) if inspected else 0

        rows.append(
            {
                "supplier_id": supplier_id,
                "supplier_name": meta["supplier_name"],
                "category": meta["category"],
                "inspected": inspected,
                "defects": defects,
                "defect_rate_pct": defect_rate(defects, inspected) * 100 if inspected else np.nan,
                "ppm": ppm(defects, inspected),
                "fpy_pct": first_pass_yield(defects, inspected),
                "total_ncrs": int(len(sup_ncrs)),
                "open_ncrs": int((sup_ncrs["closure_status"] != "Closed").sum()) if len(sup_ncrs) else 0,
                "repeat_ncrs": int(sup_ncrs["is_repeat"].sum()) if len(sup_ncrs) and "is_repeat" in sup_ncrs else 0,
                "critical_ncrs": int((sup_ncrs["severity"] == "Critical").sum()) if len(sup_ncrs) else 0,
                "overdue_actions": count_overdue_actions(sup_actions, as_of=as_of),
                "on_time_delivery_pct": float(meta["on_time_delivery_pct"]),
            }
        )

    return pd.DataFrame(rows)


def attention_flags(scorecard: pd.DataFrame, ppm_threshold: float = 20_000) -> pd.DataFrame:
    """Add a short, explicit reason column describing why a supplier stands out.

    The thresholds here are project conventions chosen so the dashboard has
    something concrete to react to. In a real programme they would come from the
    quality agreement with each supplier.
    """
    reasons = []
    for _, row in scorecard.iterrows():
        flags = []
        if row["ppm"] > ppm_threshold:
            flags.append(f"PPM above {ppm_threshold:,.0f}")
        if row["repeat_ncrs"] >= 2:
            flags.append(f"{int(row['repeat_ncrs'])} repeat NCRs")
        if row["overdue_actions"] > 0:
            flags.append(f"{int(row['overdue_actions'])} overdue corrective action(s)")
        if row["critical_ncrs"] > 0:
            flags.append(f"{int(row['critical_ncrs'])} critical NCR(s)")
        if row["on_time_delivery_pct"] < 92:
            flags.append(f"on-time delivery {row['on_time_delivery_pct']:.1f}%")
        reasons.append("; ".join(flags) if flags else "No threshold exceeded")

    out = scorecard.copy()
    out["attention_required"] = reasons
    return out


# ---------------------------------------------------------------------------
# Trend helpers
# ---------------------------------------------------------------------------

def weekly_trend(inspections: pd.DataFrame, date_col: str = "inspection_date") -> pd.DataFrame:
    """Weekly inspected volume, defect count, defect rate, PPM and FPY."""
    if not len(inspections):
        return pd.DataFrame(columns=["week", "inspected", "defects", "defect_rate_pct", "ppm", "fpy_pct"])

    work = inspections.copy()
    work[date_col] = pd.to_datetime(work[date_col])
    work["week"] = work[date_col].dt.to_period("W").dt.start_time

    grouped = work.groupby("week").agg(inspected=("defect_flag", "size"), defects=("defect_flag", "sum")).reset_index()
    grouped["defect_rate_pct"] = 100 * grouped["defects"] / grouped["inspected"]
    grouped["ppm"] = 1_000_000 * grouped["defects"] / grouped["inspected"]
    grouped["fpy_pct"] = 100 - grouped["defect_rate_pct"]
    return grouped


def before_after_comparison(
    inspections: pd.DataFrame,
    split_date: str,
    date_col: str = "inspection_date",
) -> pd.DataFrame:
    """Compare quality metrics either side of a corrective action date.

    This is the verification step. A corrective action is not effective because
    somebody signed a form; it is effective because the data after the change is
    measurably different from the data before it.
    """
    work = inspections.copy()
    work[date_col] = pd.to_datetime(work[date_col])
    split = pd.Timestamp(split_date)

    periods = {
        "Before corrective action": work[work[date_col] < split],
        "After corrective action": work[work[date_col] >= split],
    }

    rows = []
    for label, subset in periods.items():
        inspected = int(len(subset))
        defects = int(subset["defect_flag"].sum()) if inspected else 0
        rows.append(
            {
                "period": label,
                "inspected": inspected,
                "defects": defects,
                "defect_rate_pct": defect_rate(defects, inspected) * 100 if inspected else np.nan,
                "ppm": ppm(defects, inspected),
                "fpy_pct": first_pass_yield(defects, inspected),
            }
        )
    return pd.DataFrame(rows)
