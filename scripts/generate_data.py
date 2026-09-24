"""Generate the synthetic dataset for the Supplier Quality Control Tower.

Run with:  python scripts/generate_data.py

Everything produced here is synthetic. The numbers are drawn from statistical
models chosen to tell a believable manufacturing story, not copied or derived
from any real company, supplier or process.

The design intent of the dataset
--------------------------------
Inspection measurements are generated from a normal distribution whose mean and
standard deviation vary by component, supplier and, for the case-study part, by
time. The case-study characteristic (journal diameter on CMP-101 from SUP-001)
moves through four phases:

    1. Baseline      - centred on nominal, capable, stable
    2. Drift         - mean walks upward as a finish turning tool wears
    3. Excursion     - mean sits close to the upper limit, parts start failing
    4. Post-change   - mean returns near nominal after corrective action

Non-conformances then fall out of the measurements rather than being invented
separately: a part is dimensionally non-conforming because its measured value is
outside the specification limits, which keeps the dataset self-consistent.
Non-dimensional defects (burrs, finish, visual) are drawn independently at
supplier-specific rates.

NCR and corrective action records are authored by hand rather than randomised,
because their value is in the engineering narrative and in the status logic
being coherent, which random generation would not produce.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DATA_DIR, PRODUCTION_START, PRODUCTION_WEEKS, RANDOM_SEED  # noqa: E402

rng = np.random.default_rng(RANDOM_SEED)


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

SUPPLIERS = [
    {
        "supplier_id": "SUP-001",
        "supplier_name": "Apex Precision",
        "category": "Precision turning and grinding",
        "location": "United Kingdom",
        "approval_status": "Approved",
        "on_time_delivery_pct": 96.4,
        "years_supplying": 6,
    },
    {
        "supplier_id": "SUP-002",
        "supplier_name": "Vector Machining",
        "category": "Multi-axis milling",
        "location": "United Kingdom",
        "approval_status": "Approved",
        "on_time_delivery_pct": 93.1,
        "years_supplying": 4,
    },
    {
        "supplier_id": "SUP-003",
        "supplier_name": "Orion Components",
        "category": "Castings and machined housings",
        "location": "Italy",
        "approval_status": "Approved - under review",
        "on_time_delivery_pct": 89.7,
        "years_supplying": 3,
    },
    {
        "supplier_id": "SUP-004",
        "supplier_name": "Velocity Manufacturing",
        "category": "Machining and sub-assembly",
        "location": "Germany",
        "approval_status": "Approved",
        "on_time_delivery_pct": 94.8,
        "years_supplying": 5,
    },
    {
        "supplier_id": "SUP-005",
        "supplier_name": "Nova Engineering",
        "category": "Precision grinding and finishing",
        "location": "United Kingdom",
        "approval_status": "Approved",
        "on_time_delivery_pct": 97.2,
        "years_supplying": 8,
    },
]

# Each component carries ONE critical characteristic that is measured at
# inspection. Real parts have many; restricting to one keeps the analysis
# focused and is stated as a limitation in the documentation.
COMPONENTS = [
    {
        "component_id": "CMP-101",
        "component_name": "High-Speed Rotating Shaft",
        "assembly": "Turbocharger rotor group",
        "characteristic": "Journal Diameter",
        "nominal": 25.000,
        "lsl": 24.980,
        "usl": 25.020,
        "unit": "mm",
        "process": "CNC Turning",
        "criticality": "Critical",
    },
    {
        "component_id": "CMP-102",
        "component_name": "Turbine Housing",
        "assembly": "Turbocharger hot side",
        "characteristic": "Bore Diameter",
        "nominal": 60.000,
        "lsl": 59.950,
        "usl": 60.050,
        "unit": "mm",
        "process": "CNC Milling",
        "criticality": "Major",
    },
    {
        "component_id": "CMP-103",
        "component_name": "Compressor Impeller",
        "assembly": "Turbocharger cold side",
        "characteristic": "Hub Thickness",
        "nominal": 8.000,
        "lsl": 7.970,
        "usl": 8.030,
        "unit": "mm",
        "process": "CNC Milling",
        "criticality": "Critical",
    },
    {
        "component_id": "CMP-104",
        "component_name": "Bearing Carrier",
        "assembly": "Turbocharger centre housing",
        "characteristic": "Bore Diameter",
        "nominal": 42.000,
        "lsl": 41.975,
        "usl": 42.025,
        "unit": "mm",
        "process": "Cylindrical Grinding",
        "criticality": "Critical",
    },
    {
        "component_id": "CMP-105",
        "component_name": "Gear Shaft Spline",
        "assembly": "Auxiliary drive",
        "characteristic": "Pitch Diameter",
        "nominal": 18.000,
        "lsl": 17.985,
        "usl": 18.015,
        "unit": "mm",
        "process": "Cylindrical Grinding",
        "criticality": "Major",
    },
    {
        "component_id": "CMP-106",
        "component_name": "Oil Pump Body",
        "assembly": "Lubrication system",
        "characteristic": "Oil Port Position",
        "nominal": 12.000,
        "lsl": 11.960,
        "usl": 12.040,
        "unit": "mm",
        "process": "CNC Milling",
        "criticality": "Major",
    },
]

# (component, supplier) -> parts inspected per production week, plus the
# baseline process mean and standard deviation for that combination.
SUPPLY_ROUTES = [
    {"component_id": "CMP-101", "supplier_id": "SUP-001", "per_week": 14, "mean": 25.0005, "sd": 0.0044},
    {"component_id": "CMP-101", "supplier_id": "SUP-002", "per_week": 3, "mean": 25.0010, "sd": 0.0050},
    {"component_id": "CMP-102", "supplier_id": "SUP-003", "per_week": 9, "mean": 60.0040, "sd": 0.0140},
    {"component_id": "CMP-103", "supplier_id": "SUP-002", "per_week": 8, "mean": 7.9985, "sd": 0.0078},
    {"component_id": "CMP-104", "supplier_id": "SUP-004", "per_week": 8, "mean": 42.0010, "sd": 0.0068},
    {"component_id": "CMP-104", "supplier_id": "SUP-001", "per_week": 4, "mean": 42.0000, "sd": 0.0055},
    {"component_id": "CMP-105", "supplier_id": "SUP-005", "per_week": 9, "mean": 18.0005, "sd": 0.0040},
    {"component_id": "CMP-106", "supplier_id": "SUP-004", "per_week": 7, "mean": 12.0020, "sd": 0.0115},
    {"component_id": "CMP-106", "supplier_id": "SUP-003", "per_week": 6, "mean": 11.9980, "sd": 0.0120},
]

# Rate and mix of defects that a dimensional measurement cannot capture, such as
# burrs, finish and visual problems. Rates are per inspected part.
NON_DIMENSIONAL_DEFECTS = {
    "SUP-001": (
        0.011,
        {
            "Surface finish": 0.34,
            "Burr": 0.30,
            "Visual defect": 0.18,
            "Assembly interface": 0.08,
            "Material issue": 0.06,
            "Positional tolerance": 0.04,
        },
    ),
    "SUP-002": (
        0.026,
        {
            "Surface finish": 0.38,
            "Burr": 0.26,
            "Visual defect": 0.14,
            "Assembly interface": 0.09,
            "Material issue": 0.07,
            "Positional tolerance": 0.06,
        },
    ),
    "SUP-003": (
        0.040,
        {
            "Material issue": 0.28,
            "Surface finish": 0.20,
            "Visual defect": 0.20,
            "Burr": 0.14,
            "Positional tolerance": 0.10,
            "Assembly interface": 0.08,
        },
    ),
    "SUP-004": (
        0.020,
        {
            "Burr": 0.30,
            "Surface finish": 0.22,
            "Assembly interface": 0.18,
            "Visual defect": 0.14,
            "Positional tolerance": 0.10,
            "Material issue": 0.06,
        },
    ),
    "SUP-005": (
        0.013,
        {
            "Surface finish": 0.29,
            "Visual defect": 0.26,
            "Burr": 0.21,
            "Material issue": 0.10,
            "Assembly interface": 0.08,
            "Positional tolerance": 0.06,
        },
    ),
}

SEVERITY_MIX = {
    "Dimensional deviation": {"Minor": 0.05, "Major": 0.70, "Critical": 0.25},
    "Positional tolerance": {"Minor": 0.25, "Major": 0.65, "Critical": 0.10},
    "Material issue": {"Minor": 0.20, "Major": 0.65, "Critical": 0.15},
    "Assembly interface": {"Minor": 0.25, "Major": 0.65, "Critical": 0.10},
    "Surface finish": {"Minor": 0.70, "Major": 0.28, "Critical": 0.02},
    "Burr": {"Minor": 0.85, "Major": 0.15, "Critical": 0.00},
    "Visual defect": {"Minor": 0.92, "Major": 0.08, "Critical": 0.00},
}

DETECTION_MIX = {
    "Dimensional deviation": {"Goods-in inspection": 0.55, "CMM inspection": 0.30, "In-process inspection": 0.15},
    "Positional tolerance": {"CMM inspection": 0.70, "Goods-in inspection": 0.30},
    "Material issue": {"Goods-in inspection": 0.55, "In-process inspection": 0.30, "Final inspection": 0.15},
    "Assembly interface": {"Assembly build check": 0.70, "Goods-in inspection": 0.20, "Test bench": 0.10},
    "Surface finish": {"Goods-in inspection": 0.65, "Final inspection": 0.35},
    "Burr": {"Goods-in inspection": 0.70, "Final inspection": 0.30},
    "Visual defect": {"Goods-in inspection": 0.80, "Final inspection": 0.20},
}


def weighted_choice(mapping: dict) -> str:
    keys = list(mapping)
    weights = np.array([mapping[k] for k in keys], dtype=float)
    weights = weights / weights.sum()
    return str(rng.choice(keys, p=weights))


# ---------------------------------------------------------------------------
# Case-study process model
# ---------------------------------------------------------------------------

def case_study_parameters(week: int, base_mean: float, base_sd: float) -> tuple[float, float]:
    """Process mean and standard deviation for CMP-101 at SUP-001 in a given week.

    Weeks 0-7    baseline: centred, capable, stable.
    Weeks 8-14   drift: the mean walks upward as the finish turning insert wears
                 and no offset correction is applied between batches. Variation
                 also grows slightly because wear is not perfectly linear.
    Weeks 15-18  excursion: the mean sits close to the upper specification limit,
                 so a meaningful share of parts now falls outside it.
    Weeks 19-29  post-change: the revised control plan brings the mean back near
                 nominal with variation slightly better than baseline, because
                 the in-process check also catches smaller deviations.
    """
    if week <= 7:
        return base_mean, base_sd

    if week <= 14:
        # Linear ramp across the drift period. By the end of it the mean sits
        # about two thirds of the way from nominal to the upper limit, which is
        # enough for the control chart to react well before parts fail.
        progress = (week - 7) / 7.0
        return base_mean + progress * 0.0126, base_sd + progress * 0.0013

    if week <= 18:
        progress = (week - 14) / 4.0
        return 25.0131 + progress * 0.0008, 0.0057 + progress * 0.0005

    return 25.0015, 0.0042


# ---------------------------------------------------------------------------
# Inspection generation
# ---------------------------------------------------------------------------

def generate_inspections() -> pd.DataFrame:
    components = {c["component_id"]: c for c in COMPONENTS}
    start = pd.Timestamp(PRODUCTION_START)
    records = []
    counter = 1

    for week in range(PRODUCTION_WEEKS):
        week_start = start + pd.Timedelta(days=7 * week)

        for route in SUPPLY_ROUTES:
            comp = components[route["component_id"]]
            supplier_id = route["supplier_id"]

            if route["component_id"] == "CMP-101" and supplier_id == "SUP-001":
                mean, sd = case_study_parameters(week, route["mean"], route["sd"])
            else:
                # Small week-to-week wobble in the mean so that stable processes
                # still look like real processes rather than pure noise around a
                # fixed constant.
                mean = route["mean"] + rng.normal(0, route["sd"] * 0.18)
                sd = route["sd"] * rng.uniform(0.92, 1.10)

            n = route["per_week"]
            batch_id = f"B-{route['component_id'][-3:]}-{supplier_id[-3:]}-W{week + 1:02d}"

            for i in range(n):
                # Spread the week's parts across Monday to Friday.
                day_offset = int(np.floor(i * 5 / n))
                date = week_start + pd.Timedelta(days=day_offset)

                measured = float(rng.normal(mean, sd))
                measured = round(measured, 4)

                out_of_spec = measured > comp["usl"] or measured < comp["lsl"]

                defect_category = ""
                if out_of_spec:
                    # A position characteristic that fails is a positional
                    # tolerance non-conformance; a size characteristic that
                    # fails is a dimensional deviation.
                    defect_category = (
                        "Positional tolerance" if "Position" in comp["characteristic"] else "Dimensional deviation"
                    )
                else:
                    rate, mix = NON_DIMENSIONAL_DEFECTS[supplier_id]
                    if rng.random() < rate:
                        defect_category = weighted_choice(mix)

                defect_flag = int(bool(defect_category))
                severity = weighted_choice(SEVERITY_MIX[defect_category]) if defect_flag else ""
                detection = (
                    weighted_choice(DETECTION_MIX[defect_category]) if defect_flag else "Goods-in inspection"
                )

                records.append(
                    {
                        "inspection_id": f"INS-{counter:05d}",
                        "inspection_date": date.strftime("%Y-%m-%d"),
                        "supplier_id": supplier_id,
                        "component_id": comp["component_id"],
                        "process": comp["process"],
                        "characteristic": comp["characteristic"],
                        "nominal": comp["nominal"],
                        "lsl": comp["lsl"],
                        "usl": comp["usl"],
                        "unit": comp["unit"],
                        "measured_value": measured,
                        "in_spec": int(not out_of_spec),
                        "defect_flag": defect_flag,
                        "defect_category": defect_category,
                        "severity": severity,
                        "detection_method": detection,
                        "batch_id": batch_id,
                    }
                )
                counter += 1

    df = pd.DataFrame(records)
    return df.sort_values(["inspection_date", "inspection_id"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Non-conformance reports
#
# Status vocabulary used throughout:
#   containment_status        Not started / In progress / Complete
#   root_cause_status         Not started / Under investigation / Confirmed
#   corrective_action_status  Not started / Not required / In progress / Complete
#   verification_status       Not started / In progress / Verified / Not applicable
#   closure_status            Open / Closed
#
# "Not required" is a deliberate option. Not every non-conformance justifies a
# formal corrective action: a low-severity, first-occurrence issue can be
# contained and dispositioned without one. Forcing a CAPA onto every NCR is a
# common way for a quality system to generate paperwork instead of improvement.
# ---------------------------------------------------------------------------

NCRS = [
    ("NCR-2026-001", "2026-01-09", "SUP-003", "CMP-102", "CNC Milling", "Material issue",
     "Porosity observed on the machined bore face of turbine housing castings during goods-in inspection.",
     6, "Major", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-02-13"),
    ("NCR-2026-002", "2026-01-16", "SUP-002", "CMP-103", "CNC Milling", "Surface finish",
     "Hub face surface roughness measured above the drawing requirement on three impellers.",
     3, "Minor", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-02-20"),
    ("NCR-2026-003", "2026-01-27", "SUP-004", "CMP-106", "CNC Milling", "Burr",
     "Burrs present on oil gallery port edges following final machining.",
     11, "Minor", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-03-06"),
    ("NCR-2026-004", "2026-02-04", "SUP-003", "CMP-106", "CNC Milling", "Positional tolerance",
     "Oil port position outside positional tolerance on two bodies, identified during CMM inspection.",
     2, "Major", "CMM inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-03-13"),
    ("NCR-2026-005", "2026-02-10", "SUP-005", "CMP-105", "Cylindrical Grinding", "Surface finish",
     "Grinding chatter marks visible on the spline pitch diameter.",
     4, "Minor", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-03-20"),
    ("NCR-2026-006", "2026-02-17", "SUP-002", "CMP-103", "CNC Milling", "Surface finish",
     "Repeat occurrence of hub face roughness above the drawing requirement following NCR-2026-002.",
     5, "Major", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-04-02"),
    ("NCR-2026-007", "2026-02-25", "SUP-004", "CMP-104", "Cylindrical Grinding", "Dimensional deviation",
     "Bearing carrier bore diameter measured below the lower specification limit on one part.",
     1, "Major", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-04-10"),
    ("NCR-2026-008", "2026-03-03", "SUP-003", "CMP-102", "CNC Milling", "Material issue",
     "Casting inclusion found in the bore wall after rough machining.",
     4, "Major", "In-process inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-04-17"),
    ("NCR-2026-009", "2026-03-10", "SUP-001", "CMP-104", "Cylindrical Grinding", "Burr",
     "Light burr on the bore entry chamfer across one carrier batch. Sorted and deburred at goods-in.",
     7, "Minor", "Goods-in inspection", "Complete", "Confirmed", "Not required", "Not applicable", "Closed",
     "2026-03-24"),
    ("NCR-2026-010", "2026-03-17", "SUP-004", "CMP-106", "CNC Milling", "Burr",
     "Burrs on port edges recurring after the corrective action raised against NCR-2026-003.",
     9, "Major", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-05-01"),
    ("NCR-2026-011", "2026-03-24", "SUP-002", "CMP-101", "CNC Turning", "Surface finish",
     "Journal surface finish marginally above the drawing requirement on second-source shafts.",
     2, "Minor", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-05-08"),
    ("NCR-2026-012", "2026-03-31", "SUP-005", "CMP-105", "Cylindrical Grinding", "Visual defect",
     "Handling marks on spline flanks noted at goods-in. Parts cleaned and re-presented.",
     6, "Minor", "Goods-in inspection", "Complete", "Confirmed", "Not required", "Not applicable", "Closed",
     "2026-04-14"),
    ("NCR-2026-013", "2026-04-02", "SUP-003", "CMP-102", "CNC Milling", "Dimensional deviation",
     "Housing bore diameter above the upper specification limit on one housing.",
     1, "Major", "CMM inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-05-22"),
    ("NCR-2026-014", "2026-04-07", "SUP-001", "CMP-101", "CNC Turning", "Dimensional deviation",
     "Journal diameter measurements trending toward the upper specification limit across successive "
     "deliveries. One part measured 25.0193 mm, within 0.001 mm of the upper limit. No part had yet been "
     "recorded outside specification, so this NCR was raised against the process trend rather than against "
     "non-conforming parts.",
     2, "Major", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-06-05"),
    ("NCR-2026-015", "2026-04-14", "SUP-004", "CMP-104", "Cylindrical Grinding", "Assembly interface",
     "Carrier-to-housing interface interference reported during trial build.",
     3, "Major", "Assembly build check", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-05-29"),
    ("NCR-2026-016", "2026-04-20", "SUP-002", "CMP-103", "CNC Milling", "Burr",
     "Burr on the impeller blade root radius. Deburred and re-inspected at goods-in.",
     4, "Minor", "Goods-in inspection", "Complete", "Confirmed", "Not required", "Not applicable", "Closed",
     "2026-05-05"),
    ("NCR-2026-017", "2026-04-23", "SUP-003", "CMP-106", "CNC Milling", "Material issue",
     "Isolated surface porosity on the oil pump body mounting face. Parts rejected and replaced.",
     3, "Minor", "Goods-in inspection", "Complete", "Confirmed", "Not required", "Not applicable", "Closed",
     "2026-05-11"),
    ("NCR-2026-018", "2026-04-27", "SUP-001", "CMP-101", "CNC Turning", "Dimensional deviation",
     "Journal diameter above the upper specification limit of 25.020 mm on two shafts inspected on 21 and 22 "
     "April (25.0207 mm and 25.0205 mm). The individuals control chart for this characteristic shows a "
     "sustained upward shift beginning in early March, so the finding is treated as a process condition "
     "affecting the whole population rather than as two isolated parts.",
     2, "Critical", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-06-26"),
    ("NCR-2026-019", "2026-05-01", "SUP-005", "CMP-105", "Cylindrical Grinding", "Surface finish",
     "Grinding burn indication on two spline journals, repeat of the condition raised in NCR-2026-005.",
     2, "Major", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-06-19"),
    ("NCR-2026-020", "2026-05-05", "SUP-004", "CMP-106", "CNC Milling", "Positional tolerance",
     "Oil port position outside tolerance on one body. Part rejected, remaining batch 100% checked and accepted.",
     1, "Minor", "CMM inspection", "Complete", "Confirmed", "Not required", "Not applicable", "Closed",
     "2026-05-19"),
    ("NCR-2026-021", "2026-05-15", "SUP-001", "CMP-101", "CNC Turning", "Dimensional deviation",
     "Three further journal diameters above the upper specification limit, inspected on 5, 12 and 14 May, on "
     "material produced before the revised control plan took effect. All three were detected by the 100% "
     "containment inspection introduced under NCR-2026-018. Raised separately to keep the affected batches "
     "traceable and to record that containment was working as intended.",
     3, "Major", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-06-26"),
    ("NCR-2026-022", "2026-05-19", "SUP-003", "CMP-102", "CNC Milling", "Visual defect",
     "Cosmetic scoring on the external housing face. Accepted under concession, supplier notified.",
     8, "Minor", "Goods-in inspection", "Complete", "Confirmed", "Not required", "Not applicable", "Closed",
     "2026-06-02"),
    ("NCR-2026-023", "2026-05-26", "SUP-002", "CMP-103", "CNC Milling", "Dimensional deviation",
     "Hub thickness measured below the lower specification limit on one impeller.",
     1, "Major", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-07-10"),
    ("NCR-2026-024", "2026-06-02", "SUP-004", "CMP-104", "Cylindrical Grinding", "Burr",
     "Burr at the bore exit across one carrier batch. Deburred and re-inspected.",
     5, "Minor", "Goods-in inspection", "Complete", "Confirmed", "Not required", "Not applicable", "Closed",
     "2026-06-16"),
    ("NCR-2026-025", "2026-06-09", "SUP-003", "CMP-102", "CNC Milling", "Material issue",
     "Third occurrence of casting porosity on this component within the reporting period. Escalated to a "
     "supplier corrective action request.",
     5, "Major", "Goods-in inspection", "Complete", "Confirmed", "In progress", "Not started", "Open", ""),
    ("NCR-2026-026", "2026-06-16", "SUP-005", "CMP-105", "Cylindrical Grinding", "Visual defect",
     "Handling damage on spline flanks, second occurrence following NCR-2026-012. Packaging method reviewed.",
     4, "Minor", "Goods-in inspection", "Complete", "Confirmed", "Complete", "Verified", "Closed", "2026-07-24"),
    ("NCR-2026-027", "2026-06-23", "SUP-002", "CMP-101", "CNC Turning", "Surface finish",
     "Journal surface finish above requirement on second-source shafts, repeat of NCR-2026-011.",
     3, "Major", "Goods-in inspection", "Complete", "Confirmed", "In progress", "Not started", "Open", ""),
    ("NCR-2026-028", "2026-06-30", "SUP-004", "CMP-106", "CNC Milling", "Assembly interface",
     "Oil pump body mounting face flatness causing a gasket seating concern at build.",
     2, "Major", "Assembly build check", "Complete", "Confirmed", "In progress", "Not started", "Open", ""),
    ("NCR-2026-029", "2026-07-07", "SUP-003", "CMP-106", "CNC Milling", "Visual defect",
     "Machining witness marks on a visible face. Accepted under concession, no functional impact identified.",
     7, "Minor", "Goods-in inspection", "Complete", "Confirmed", "Not required", "Not applicable", "Closed",
     "2026-07-20"),
    ("NCR-2026-030", "2026-07-14", "SUP-001", "CMP-104", "Cylindrical Grinding", "Surface finish",
     "Bore surface finish above the drawing requirement on two carriers. Investigation ongoing.",
     2, "Minor", "Goods-in inspection", "Complete", "Under investigation", "Not started", "Not started", "Open", ""),
    ("NCR-2026-031", "2026-07-21", "SUP-002", "CMP-103", "CNC Milling", "Surface finish",
     "Hub face roughness above the drawing requirement, third occurrence of this condition. Investigation ongoing.",
     4, "Major", "Goods-in inspection", "Complete", "Under investigation", "Not started", "Not started", "Open", ""),
    ("NCR-2026-032", "2026-07-29", "SUP-004", "CMP-104", "Cylindrical Grinding", "Dimensional deviation",
     "Carrier bore diameter above the upper specification limit on one part. Containment in progress.",
     1, "Major", "CMM inspection", "In progress", "Not started", "Not started", "Not started", "Open", ""),
]

NCR_COLUMNS = [
    "ncr_id", "date_raised", "supplier_id", "component_id", "process", "defect_category",
    "description", "quantity_affected", "severity", "detection_method", "containment_status",
    "root_cause_status", "corrective_action_status", "verification_status", "closure_status", "closure_date",
]


# ---------------------------------------------------------------------------
# Corrective actions
# ---------------------------------------------------------------------------

CORRECTIVE_ACTIONS = [
    (
        "CA-001", "NCR-2026-001",
        "Casting gate design allowed gas entrapment near the bore face, producing subsurface porosity that was "
        "only revealed once machining removed the skin.",
        "Batch quarantined at goods-in and returned to supplier. Remaining stock 100% inspected after rough machining.",
        "Supplier revised the gating and venting arrangement for the bore region and re-qualified the pattern.",
        "Porosity inspection added to the supplier's final inspection routine for all castings from this pattern family.",
        "A. Reed (Supplier Quality Engineer)", "2026-02-06", "Complete",
        "Inspection of the next three delivered batches after rough machining.",
        "Effective - no porosity findings in the three batches following implementation.", "2026-02-13",
    ),
    (
        "CA-002", "NCR-2026-002",
        "Cutting tool used for the hub face had exceeded its intended life, degrading the achieved surface finish.",
        "Affected impellers segregated and returned for refinishing.",
        "Tool change interval for the hub face operation reduced and recorded on the setup sheet.",
        "Tool life monitoring added to the operator check sheet for the milling cell.",
        "M. Okoro (Manufacturing Engineer)", "2026-02-13", "Complete",
        "Surface roughness measurement on 10 parts from the following two deliveries.",
        "Effective at the time of verification - all measured parts within the drawing requirement.", "2026-02-20",
    ),
    (
        "CA-003", "NCR-2026-003",
        "Manual deburring of the port edges was inconsistent between operators and no defined edge condition was "
        "specified on the drawing note.",
        "Batch sorted and deburred at goods-in before release to stores.",
        "Deburring operation defined with a specified edge break and a reference sample provided to the operators.",
        "Edge condition added to the inspection check sheet for all ported bodies.",
        "J. Lindqvist (Quality Inspection Lead)", "2026-02-27", "Complete",
        "Visual inspection against the reference sample on the next two batches.",
        "Partially effective - improvement seen but the condition recurred, see NCR-2026-010.", "2026-03-06",
    ),
    (
        "CA-004", "NCR-2026-004",
        "Fixture locating pin wear allowed part rotation during the port drilling operation.",
        "Two affected bodies rejected. Remaining batch 100% CMM checked.",
        "Locating pins replaced and a wear check added to the fixture maintenance schedule.",
        "Fixture wear checks extended to the other two drilling fixtures used for this family.",
        "M. Okoro (Manufacturing Engineer)", "2026-03-06", "Complete",
        "CMM check of port position on the following two batches.",
        "Effective - all checked positions within tolerance.", "2026-03-13",
    ),
    (
        "CA-005", "NCR-2026-005",
        "Grinding wheel dressing interval was too long for the wheel grade in use, allowing the wheel to load and "
        "produce chatter.",
        "Affected parts returned for regrinding.",
        "Wheel dressing interval shortened and specified on the operation sheet.",
        "Dressing interval reviewed for the other grinding operations on the same machine.",
        "T. Fenwick (Manufacturing Engineering)", "2026-03-13", "Complete",
        "Surface finish measurement on the next two deliveries.",
        "Partially effective - finish improved but a related grinding burn condition later occurred, see NCR-2026-019.",
        "2026-03-20",
    ),
    (
        "CA-006", "NCR-2026-006",
        "The reduced tool change interval from CA-002 was recorded on the setup sheet but not built into the "
        "machine's tool life counter, so it depended on the operator remembering it.",
        "Affected impellers segregated and returned for refinishing.",
        "Tool life limit programmed into the machine controller so the tool change is prompted automatically.",
        "Controller-based tool life limits applied to the other finish operations in the cell.",
        "M. Okoro (Manufacturing Engineer)", "2026-03-20", "Complete",
        "Surface roughness on 10 parts per delivery for three consecutive deliveries.",
        "Effective at the time of verification - no findings across the three deliveries checked.", "2026-04-02",
    ),
    (
        "CA-007", "NCR-2026-007",
        "Grinding wheel offset was corrected in the wrong direction after a wheel change, producing an undersized bore.",
        "Part rejected. Remaining batch 100% inspected before release.",
        "Offset correction after a wheel change made a two-person verified step on the setup sheet.",
        "First-off approval requirement introduced after every wheel change on critical bore operations.",
        "T. Fenwick (Manufacturing Engineering)", "2026-03-27", "Complete",
        "Bore diameter check on the first-off part after the next three wheel changes.",
        "Effective - all first-off parts within tolerance.", "2026-04-10",
    ),
    (
        "CA-008", "NCR-2026-008",
        "Melt handling practice allowed slag carryover into the pour for one heat, producing inclusions.",
        "Batch held at the supplier and re-inspected after rough machining.",
        "Pouring procedure updated with a defined skimming step and a hold time before pouring.",
        "Melt handling procedure reviewed with the foundry and applied to all heats for this alloy.",
        "A. Reed (Supplier Quality Engineer)", "2026-04-10", "Complete",
        "Ultrasonic and visual inspection after rough machining on the next four batches.",
        "Partially effective - no inclusions found in the four batches checked, but porosity recurred later on "
        "the same component, see NCR-2026-025.", "2026-04-17",
    ),
    (
        "CA-010", "NCR-2026-010",
        "The reference sample provided under CA-003 was not controlled, and the sample in use at the supplier had "
        "been damaged, so the accepted edge condition had drifted.",
        "Batch sorted and deburred at goods-in.",
        "Reference samples brought under document control with a defined replacement interval and identification.",
        "Controlled reference samples introduced for all visual and edge-condition acceptance criteria at this supplier.",
        "J. Lindqvist (Quality Inspection Lead)", "2026-04-17", "Complete",
        "Visual inspection against the controlled sample on four consecutive batches.",
        "Effective - no burr findings across the four batches following implementation.", "2026-05-01",
    ),
    (
        "CA-011", "NCR-2026-011",
        "Finish turning feed rate at the second-source supplier was set from a generic process sheet rather than "
        "the part-specific parameters.",
        "Two affected shafts rejected and replaced.",
        "Part-specific finish turning parameters issued to the supplier and recorded in their process sheet.",
        "Process parameter records reviewed for the other parts supplied by this second source.",
        "A. Reed (Supplier Quality Engineer)", "2026-04-24", "Complete",
        "Surface finish measurement on all shafts in the next two deliveries.",
        "Partially effective - condition improved but recurred later, see NCR-2026-027.", "2026-05-08",
    ),
    (
        "CA-013", "NCR-2026-013",
        "Boring bar deflection under a worn insert produced an oversized bore on the last part of the run.",
        "Part rejected. Remaining housings 100% CMM checked.",
        "Insert change point defined by part count for the boring operation and added to the control plan.",
        "Insert life defined by part count for the other bored features on this component.",
        "M. Okoro (Manufacturing Engineer)", "2026-05-08", "Complete",
        "CMM bore measurement on all housings in the next three deliveries.",
        "Effective - all measured bores within tolerance.", "2026-05-22",
    ),
    (
        "CA-014", "NCR-2026-014",
        "Initial assessment attributed the upward trend to normal tool wear within the existing offset correction "
        "practice. This was later shown to be incomplete, see CA-018.",
        "Journal diameter recorded and trended on every incoming shaft rather than on a sample.",
        "Supplier asked to tighten the tool offset correction frequency for the finish turning operation.",
        "Trend review of the journal diameter added to the weekly incoming quality review.",
        "A. Reed (Supplier Quality Engineer)", "2026-04-24", "Complete",
        "Review of journal diameter trend over the following three weeks.",
        "Not effective - the mean continued to rise and parts subsequently fell outside specification, leading to "
        "NCR-2026-018. The investigation was reopened at a deeper level.", "2026-06-05",
    ),
    (
        "CA-015", "NCR-2026-015",
        "Carrier outer diameter was at the top of its tolerance while the mating housing bore was at the bottom of "
        "its own, producing an interference at the tolerance stack extreme.",
        "Three affected assemblies held and the carriers replaced from an alternative batch.",
        "Tolerance stack for the interface reviewed and the carrier outer diameter target moved to mid-tolerance.",
        "Interface tolerance stacks reviewed for the other two press-fit joints in the centre housing.",
        "T. Fenwick (Manufacturing Engineering)", "2026-05-22", "Complete",
        "Measured fit check on ten assemblies at build.",
        "Effective - all ten assemblies within the intended interference range.", "2026-05-29",
    ),
    (
        "CA-018", "NCR-2026-018",
        "A finish turning insert grade change was introduced in February without re-validating tool life. The "
        "control plan still specified first-off and last-off inspection only, based on the previous insert's wear "
        "behaviour, so progressive wear moved the journal diameter toward the upper specification limit between "
        "offset corrections and no in-process check existed to detect it.",
        "Two suspect batches quarantined at goods-in and returned to the supplier. 100% inspection of journal "
        "diameter introduced on all incoming shafts and at supplier final inspection. Stock on hand re-measured "
        "and segregated.",
        "Supplier reverted to the validated insert grade and re-established the tool life limit for the finish "
        "turning operation. Control plan updated to require an in-process journal diameter check every fifth part "
        "and a tool offset correction at a defined cumulative part count.",
        "Change control procedure extended so that any tooling or consumable change affecting a critical "
        "characteristic requires tool life re-validation and a control plan review before release. The same review "
        "was applied to the other critical rotating characteristics from this supplier, and SPC monitoring with a "
        "documented reaction plan was introduced at the supplier for the journal diameter.",
        "A. Reed (Supplier Quality Engineer)", "2026-05-15", "Complete",
        "Individuals and moving range chart plus a capability study on eleven weeks of post-change inspection "
        "data, compared against the pre-change period, together with a review of repeat NCR activity for the same "
        "supplier, component and defect category.",
        "Effective - see the verification analysis in the application for the measured before and after values.",
        "2026-06-26",
    ),
    (
        "CA-019", "NCR-2026-019",
        "Coolant concentration had fallen below the specified range, reducing heat removal during grinding and "
        "producing localised burn.",
        "Two affected parts rejected. Remaining stock etch-inspected for burn.",
        "Coolant concentration check added to the daily machine start-up routine with a recorded reading.",
        "Daily coolant checks introduced across all grinding machines at the supplier.",
        "T. Fenwick (Manufacturing Engineering)", "2026-06-05", "Complete",
        "Etch inspection of a sample from each of the next three deliveries.",
        "Effective - no burn indications in the three deliveries checked.", "2026-06-19",
    ),
    (
        "CA-021", "NCR-2026-021",
        "Same root cause as NCR-2026-018. This NCR covers the additional material produced before the corrective "
        "action took effect and is closed against the same corrective action.",
        "Affected batches quarantined and returned. 100% inspection maintained until the corrective action was verified.",
        "Covered by CA-018. No separate corrective action raised, as raising a second action against the same cause "
        "would fragment the verification evidence.",
        "Covered by CA-018.",
        "A. Reed (Supplier Quality Engineer)", "2026-05-15", "Complete",
        "Verified together with CA-018 using the post-change control chart and capability study.",
        "Effective - no further dimensional non-conformances on this component and supplier after the change.",
        "2026-06-26",
    ),
    (
        "CA-023", "NCR-2026-023",
        "Hub thickness was machined to the low side of tolerance following a fixture shim change that was not "
        "re-qualified with a first-off measurement.",
        "Affected impeller rejected. Remaining batch 100% inspected.",
        "First-off measurement required and recorded after any fixture shim or packing change.",
        "First-off requirement after fixture changes applied to all critical thickness features in the cell.",
        "M. Okoro (Manufacturing Engineer)", "2026-06-26", "Complete",
        "First-off records audited for the next four production runs.",
        "Effective - first-off measurements recorded and within tolerance on all four runs.", "2026-07-10",
    ),
    (
        "CA-025", "NCR-2026-025",
        "Porosity has now occurred three times on this component from the same pattern. The earlier gating change "
        "under CA-001 addressed the bore region only, and the current findings are at a different location, so the "
        "pattern is being re-assessed as a whole.",
        "Batch quarantined. 100% inspection after rough machining maintained on all deliveries of this component.",
        "Full pattern and gating review with the supplier's foundry, including a solidification assessment. Work in "
        "progress at the reporting date.",
        "Pending completion of the pattern review. A supplier process audit has been scheduled.",
        "A. Reed (Supplier Quality Engineer)", "2026-07-17", "In progress",
        "Inspection after rough machining on five consecutive batches once the revised pattern is released.",
        "Not yet verified - corrective action not complete at the reporting date and now past its due date.", "",
    ),
    (
        "CA-026", "NCR-2026-026",
        "Parts were transported in a returnable container without individual separation, allowing flank-to-flank "
        "contact in transit.",
        "Affected parts cleaned, re-inspected and accepted.",
        "Packaging specification updated to require individual part separators in the returnable container.",
        "Packaging specifications reviewed for the other ground components from this supplier.",
        "J. Lindqvist (Quality Inspection Lead)", "2026-07-14", "Complete",
        "Visual inspection at goods-in on three consecutive deliveries in the revised packaging.",
        "Effective - no handling damage found in the three deliveries checked.", "2026-07-24",
    ),
    (
        "CA-027", "NCR-2026-027",
        "The part-specific turning parameters issued under CA-011 were applied to one machine at the supplier but "
        "the part was subsequently run on a second machine that still held the generic parameters.",
        "Affected shafts rejected. 100% surface finish inspection applied at goods-in.",
        "Part-specific parameters loaded and verified on all machines capable of running the part. Work in progress "
        "at the reporting date.",
        "Pending completion. Intended action is a check that process parameters are controlled per part rather than "
        "per machine at this supplier.",
        "A. Reed (Supplier Quality Engineer)", "2026-07-31", "In progress",
        "Surface finish measurement on all shafts from the next three deliveries, recording which machine produced them.",
        "Not yet verified - corrective action not complete at the reporting date and now past its due date.", "",
    ),
    (
        "CA-028", "NCR-2026-028",
        "Mounting face flatness is not currently a controlled characteristic on the drawing, so it was never "
        "measured at inspection despite affecting gasket seating.",
        "Affected bodies held at build. Flatness measured on all bodies in stock.",
        "Flatness added as a controlled characteristic with a defined tolerance, and added to the control plan and "
        "inspection routine. Drawing change in progress at the reporting date.",
        "Review of other gasket-sealed faces across the lubrication system to confirm flatness is specified where "
        "it affects function.",
        "T. Fenwick (Manufacturing Engineering)", "2026-08-21", "In progress",
        "Flatness measurement on all bodies from the first three deliveries after the drawing change is released.",
        "Not yet verified - corrective action in progress and not yet due.", "",
    ),
]

CA_COLUMNS = [
    "action_id", "ncr_id", "root_cause", "immediate_containment", "corrective_action", "preventive_action",
    "owner", "due_date", "status", "verification_method", "verification_result", "closure_date",
]


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    suppliers = pd.DataFrame(SUPPLIERS)
    components = pd.DataFrame(COMPONENTS)
    inspections = generate_inspections()
    ncrs = pd.DataFrame(NCRS, columns=NCR_COLUMNS)
    actions = pd.DataFrame(CORRECTIVE_ACTIONS, columns=CA_COLUMNS)

    suppliers.to_csv(DATA_DIR / "suppliers.csv", index=False)
    components.to_csv(DATA_DIR / "components.csv", index=False)
    inspections.to_csv(DATA_DIR / "inspections.csv", index=False)
    ncrs.to_csv(DATA_DIR / "ncrs.csv", index=False)
    actions.to_csv(DATA_DIR / "corrective_actions.csv", index=False)

    defects = int(inspections["defect_flag"].sum())
    total = len(inspections)
    print(f"suppliers.csv           {len(suppliers):>6} rows")
    print(f"components.csv          {len(components):>6} rows")
    print(f"inspections.csv         {total:>6} rows")
    print(f"ncrs.csv                {len(ncrs):>6} rows")
    print(f"corrective_actions.csv  {len(actions):>6} rows")
    print()
    print(f"Defects: {defects} / {total} = {100 * defects / total:.2f}%  ({1e6 * defects / total:,.0f} PPM)")


if __name__ == "__main__":
    main()
