"""Root cause investigation content for selected NCRs.

The 5 Whys chains and fishbone diagrams are authored rather than generated. A
root cause analysis is an argument, and an argument has to be written by
somebody who can defend each step.

Two conventions are applied throughout:

*   Every "why" answers the answer above it, not the original problem. A chain
    where each line restates the symptom differently is the most common way
    5 Whys is done badly.
*   Potential causes and confirmed causes are held in separate fields. A
    fishbone is a list of hypotheses; only some of them survive contact with
    evidence, and the ones that did not are still worth recording because they
    show what was ruled out and why.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Investigation:
    ncr_id: str
    problem_statement: str
    five_whys: list
    fishbone: dict
    confirmed_causes: list
    ruled_out: list
    most_likely_root_cause: str
    evidence: list
    containment: str
    corrective_action: str
    preventive_action: str
    verification: str = ""
    notes: list = field(default_factory=list)


INVESTIGATIONS = {
    "NCR-2026-018": Investigation(
        ncr_id="NCR-2026-018",
        problem_statement=(
            "Journal diameter on the High-Speed Rotating Shaft (CMP-101) from Apex Precision (SUP-001) "
            "drifted upward from nominal between March and May 2026 and produced parts above the 25.020 mm "
            "upper specification limit."
        ),
        five_whys=[
            (
                "Why were journal diameters recorded above the upper specification limit?",
                "Because the machined diameter had drifted steadily upward over successive batches until "
                "individual parts exceeded 25.020 mm.",
            ),
            (
                "Why did the machined diameter drift upward?",
                "Because the finish turning insert wore progressively, the depth of cut reduced, and more "
                "material was left on the diameter. No tool offset correction was applied between batches to "
                "compensate for that wear.",
            ),
            (
                "Why was no offset correction applied between batches?",
                "Because the operator only adjusted the tool offset when a first-off inspection failed, rather "
                "than on a planned basis linked to how far the tool had run.",
            ),
            (
                "Why was the offset only adjusted on a first-off failure?",
                "Because the control plan for the finish turning operation specified first-off and last-off "
                "inspection only. It contained no in-process check and no rule requiring an offset correction at "
                "a defined tool life point.",
            ),
            (
                "Why did the control plan not contain a tool-life-based rule?",
                "Because a finish turning insert grade change was introduced in February and the tool life for "
                "the new grade was never re-validated. The control plan still reflected the wear behaviour of "
                "the previous insert, under which the existing first-off and last-off regime had been adequate.",
            ),
        ],
        fishbone={
            "Man": [
                ("Offset set by judgement",
                 "Tool offset correction applied on operator judgement rather than to a defined rule."),
                ("No briefing on new insert",
                 "Operators were not briefed on the different wear behaviour of the new insert grade."),
            ],
            "Machine": [
                ("Turret repeatability",
                 "Lathe turret repeatability. Checked during the investigation and found within specification."),
                ("Spindle thermal growth",
                 "Spindle thermal growth during long production runs could move the achieved diameter."),
            ],
            "Method": [
                ("No in-process check",
                 "The control plan specifies first-off and last-off inspection only. There is no in-process "
                 "check capable of detecting a mid-batch drift."),
                ("No tool-life offset rule",
                 "No rule requiring a tool offset correction at a defined tool life point on the finish "
                 "turning operation."),
                ("Change not re-validated",
                 "The February insert grade change was released without re-validating tool life or reviewing "
                 "the control plan."),
            ],
            "Material": [
                ("Bar stock hardness",
                 "Bar stock hardness variation between material heats affecting tool wear rate."),
                ("Stock removal allowance",
                 "Variation in the stock allowance left by the preceding operation."),
            ],
            "Measurement": [
                ("Gauge calibration",
                 "Goods-in air gauge calibration. Checked during the investigation and in date throughout."),
                ("Gauge R&R not re-assessed",
                 "Gauge repeatability and reproducibility on the journal diameter had not been formally "
                 "re-assessed for this characteristic."),
            ],
            "Environment": [
                ("Shop temperature",
                 "Shop-floor temperature variation affecting both the part and the machine."),
                ("Coolant temperature",
                 "Coolant temperature stability across a production shift."),
            ],
        },
        confirmed_causes=[
            "No in-process check",
            "No tool-life offset rule",
            "Change not re-validated",
        ],
        ruled_out=[
            (
                "Measurement system error",
                "The goods-in air gauge was within calibration throughout the period, and a sample of suspect "
                "parts was re-measured on an independent gauge with agreement to within 0.001 mm. A measurement "
                "problem would also not produce a steady one-directional trend.",
            ),
            (
                "Material hardness variation",
                "The drift is monotonic across many separate material batches. Batch-to-batch hardness variation "
                "would be expected to produce scatter rather than a sustained one-way trend.",
            ),
            (
                "Machine capability",
                "The moving range chart shows part-to-part variation staying broadly stable while the mean moved. "
                "That is the signature of a shifting process centre, not of a machine losing repeatability.",
            ),
        ],
        most_likely_root_cause=(
            "Most likely root cause based on the available synthetic evidence: a finish turning insert grade "
            "change was released in February 2026 without re-validating tool life or reviewing the control plan. "
            "The existing first-off and last-off inspection regime was matched to the previous insert's wear "
            "rate, so with the new grade the diameter drifted between offset corrections with no in-process "
            "check capable of detecting it."
        ),
        evidence=[
            "The individuals chart shows a sustained run above the centre line beginning in the week commencing "
            "9 March 2026, well before any part fell outside specification on 21 April 2026.",
            "The moving range chart stays broadly within its upper limit through the same period, indicating a "
            "shift in process centre rather than a loss of part-to-part consistency.",
            "Cp remains reasonable through the drift period while Cpk falls sharply. That gap is characteristic "
            "of a process whose spread is acceptable but whose centre has moved.",
            "The drift is one-directional and coincides with the February insert grade change recorded in the "
            "supplier's change log.",
            "The second-source supplier for the same component over the same period shows no equivalent trend, "
            "which points to something specific to this supplier's process rather than to the design or material.",
        ],
        containment=(
            "Two suspect batches quarantined at goods-in and returned to the supplier. 100% inspection of journal "
            "diameter introduced on all incoming shafts and at supplier final inspection. Stock on hand "
            "re-measured and segregated. Containment protects the build from further affected material but does "
            "not change why the material was produced that way."
        ),
        corrective_action=(
            "Supplier reverted to the validated insert grade and re-established the tool life limit for the "
            "finish turning operation. The control plan was updated to require an in-process journal diameter "
            "check every fifth part and a tool offset correction at a defined cumulative part count. This removes "
            "the cause of the non-conformance that was detected."
        ),
        preventive_action=(
            "The change control procedure was extended so that any tooling or consumable change affecting a "
            "critical characteristic requires tool life re-validation and a control plan review before release. "
            "The same review was applied to the other critical rotating characteristics supplied by this "
            "supplier, and SPC monitoring with a documented reaction plan was introduced at the supplier for the "
            "journal diameter. This reduces the likelihood of the same failure mode arising elsewhere."
        ),
        verification=(
            "Verified on eleven weeks of post-change inspection data using an individuals and moving range chart "
            "against the original baseline limits, a capability study over the same period, and a check for "
            "repeat NCR activity on the same supplier, component and defect category."
        ),
        notes=[
            "NCR-2026-014 was raised three weeks earlier against the same trend. The corrective action taken at "
            "that point asked the supplier to tighten the offset correction frequency, but did not ask why the "
            "existing frequency had stopped working. That action was verified as NOT effective, and the "
            "investigation was reopened at a deeper level. The first investigation stopped at the third why.",
            "NCR-2026-021 covers further non-conforming parts found by the containment inspection before the "
            "corrective action took effect. It is closed against the same corrective action rather than a "
            "separate one, so that the verification evidence stays in one place.",
        ],
    ),
    "NCR-2026-010": Investigation(
        ncr_id="NCR-2026-010",
        problem_statement=(
            "Burrs on oil gallery port edges of the Oil Pump Body (CMP-106) from Velocity Manufacturing "
            "(SUP-004) recurred after a corrective action had already been raised and closed against the same "
            "condition under NCR-2026-003."
        ),
        five_whys=[
            (
                "Why were burrs present on the port edges again?",
                "Because the edge condition produced at the supplier no longer matched the condition that had "
                "been agreed as acceptable.",
            ),
            (
                "Why did the edge condition no longer match what was agreed?",
                "Because the operators were comparing parts against a physical reference sample that had itself "
                "been damaged in handling.",
            ),
            (
                "Why was a damaged reference sample still in use?",
                "Because the sample was not identified, controlled or subject to any replacement interval.",
            ),
            (
                "Why was the reference sample not under control?",
                "Because the original corrective action created a physical acceptance standard without bringing "
                "it into the document control system.",
            ),
            (
                "Why did the corrective action not cover control of the standard it created?",
                "Because the effectiveness check for the original action only looked at whether parts conformed "
                "in the following two batches. It did not test whether the control introduced would survive over "
                "time.",
            ),
        ],
        fishbone={
            "Man": [
                ("Operator interpretation",
                 "What counts as an acceptable edge varies between individual operators."),
            ],
            "Machine": [
                ("Deburring tool condition", "Condition and wear of the hand deburring tool."),
                ("Manual, no fixture", "The operation is manual with no fixture to make it repeatable."),
            ],
            "Method": [
                ("Sample not controlled",
                 "The physical reference sample used as the acceptance standard was not under document control."),
                ("No replacement interval",
                 "No defined replacement interval or condition check for physical acceptance standards."),
                ("Shallow effectiveness check",
                 "The effectiveness check on the original corrective action looked only at short-term "
                 "conformance, not at whether the control introduced would hold over time."),
            ],
            "Material": [
                ("Material ductility", "Material ductility affecting how readily a burr forms."),
            ],
            "Measurement": [
                ("Visual comparison only",
                 "Acceptance is by visual comparison only. No measurable edge break is specified on the drawing."),
            ],
            "Environment": [
                ("Station lighting", "Lighting at the deburring station affecting what the operator can see."),
            ],
        },
        confirmed_causes=[
            "Sample not controlled",
            "No replacement interval",
        ],
        ruled_out=[
            (
                "Material change",
                "Material certificates across the affected batches show no change in specification or supplier.",
            ),
        ],
        most_likely_root_cause=(
            "Most likely root cause based on the available synthetic evidence: the original corrective action "
            "introduced a physical reference sample as the acceptance standard but did not place it under "
            "document control. Once the sample degraded, the accepted edge condition drifted with it."
        ),
        evidence=[
            "The recurrence is on the same component, supplier and defect category as NCR-2026-003, which is the "
            "definition of a repeat non-conformance used throughout this project.",
            "The reference sample in use at the supplier was found to be damaged on inspection.",
            "No change in material specification, tooling or operator was recorded between the two occurrences.",
        ],
        containment="Affected batch sorted and deburred at goods-in before release to stores.",
        corrective_action=(
            "Reference samples brought under document control with an identification number, a defined "
            "replacement interval and a recorded issue date."
        ),
        preventive_action=(
            "Controlled reference samples introduced for all visual and edge-condition acceptance criteria at "
            "this supplier, so the same failure mode cannot recur on other characteristics."
        ),
        verification=(
            "Visual inspection against the controlled sample across four consecutive batches, with no burr "
            "findings recorded."
        ),
        notes=[
            "This NCR is included as a second worked example because it shows a different and very common "
            "failure pattern: the corrective action was reasonable, but the effectiveness check was too shallow "
            "and too short to detect that the control introduced would not hold."
        ],
    ),
}


def available_investigations() -> list:
    return list(INVESTIGATIONS)


def get_investigation(ncr_id: str) -> Investigation | None:
    return INVESTIGATIONS.get(ncr_id)
