"""Shared constants for the Supplier Quality Control Tower.

Keeping the fixed reference values in one place means the data generator, the
application and the tests all agree on things like the SPC constants and the
defect taxonomy.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

# Fixed seed so that the synthetic dataset is fully reproducible.
RANDOM_SEED = 2026

# ---------------------------------------------------------------------------
# SPC constants for an Individuals / Moving Range chart with a moving range of
# n = 2 consecutive observations. These are the standard published control
# chart constants, not arbitrary numbers:
#   d2   = 1.128  -> converts mean moving range to an estimate of sigma
#   E2   = 2.660  -> = 3 / d2, the individuals chart 3-sigma multiplier
#   D4   = 3.267  -> moving range chart upper limit multiplier
#   D3   = 0      -> moving range chart lower limit (a range cannot be negative)
# ---------------------------------------------------------------------------
D2_N2 = 1.128
E2_N2 = 2.660
D4_N2 = 3.267
D3_N2 = 0.0

DEFECT_CATEGORIES = [
    "Dimensional deviation",
    "Surface finish",
    "Burr",
    "Positional tolerance",
    "Material issue",
    "Assembly interface",
    "Visual defect",
]

SEVERITIES = ["Minor", "Major", "Critical"]

DETECTION_METHODS = [
    "Goods-in inspection",
    "In-process inspection",
    "Final inspection",
    "CMM inspection",
    "Assembly build check",
    "Test bench",
]

PROCESSES = [
    "CNC Turning",
    "CNC Milling",
    "Cylindrical Grinding",
    "Wire EDM",
    "Heat Treatment",
    "Surface Treatment",
    "Assembly",
]

# The component and supplier that carry the main engineering case study.
CASE_STUDY_COMPONENT = "CMP-101"
CASE_STUDY_SUPPLIER = "SUP-001"
CASE_STUDY_NCR = "NCR-2026-018"

# Fixed "as of" date for the dataset. Using a constant rather than today's date
# keeps overdue-action counts and test results reproducible.
REPORTING_DATE = "2026-08-01"

# Production window covered by the synthetic inspection data (Mondays to Fridays).
PRODUCTION_START = "2026-01-05"
PRODUCTION_WEEKS = 30

# Date the corrective action was implemented at the supplier, and the first
# delivery date of material produced under the revised control plan. The second
# of these is the "before/after" split point for verification.
CORRECTIVE_ACTION_IMPLEMENTED = "2026-05-15"
POST_CHANGE_START = "2026-05-18"

# The SPC baseline window. Control limits are calculated from this period only
# (a Phase I study) and then projected forward, which is what allows the later
# drift to appear as an out-of-control signal rather than being absorbed into
# wider limits.
BASELINE_START = "2026-01-05"
BASELINE_END = "2026-02-27"

# Named analysis windows for the case study. Keeping these explicit avoids
# comparing a mixed "before" population (stable + drifting) against a clean
# "after" population, which would overstate the improvement.
PHASE_WINDOWS = {
    "Baseline (stable)": ("2026-01-05", "2026-02-27"),
    "Drift period": ("2026-03-02", "2026-04-17"),
    "Excursion period": ("2026-04-20", "2026-05-15"),
    "Post-corrective action": ("2026-05-18", "2026-07-31"),
}

DISCLAIMER = (
    "All data in this application is synthetic and was generated for portfolio "
    "purposes. It does not represent any real company, supplier or production process."
)
