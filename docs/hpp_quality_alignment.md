# Quality Engineering Theme Alignment

A personal preparation document. It maps what this project actually contains onto the themes
that come up in high-performance powertrain and motorsport quality engineering roles, so that
I can talk about the project in the right language without overstating what it is.

> This is a portfolio project on synthetic data. It is evidence that I understand the methods
> and can apply them, not evidence of professional quality engineering experience.

---

## How to use this document

For each theme: what the theme means, what the project demonstrates, and — importantly — what
it does **not** demonstrate. The third column is the one that keeps me honest in an interview.
Being able to say clearly where a project stops is more convincing than claiming it covers
everything.

---

## 1. Non-conformance management

**What the theme means.** Recording product or process that does not meet a specified
requirement, containing it, investigating it, and closing it out with evidence. The discipline
is in the workflow, not in the paperwork.

**What the project demonstrates.**
- 32 NCR records with a full workflow: containment, root cause, corrective action,
  verification, closure.
- Status logic enforced in code and asserted in tests: an NCR cannot be closed without
  verification; corrective action cannot start before root cause is confirmed; verification
  cannot precede a completed action.
- A deliberate "not required" path for low-severity, first-occurrence issues that were
  contained and dispositioned without a formal CAPA. Not every NCR justifies one, and forcing
  a CAPA onto every record produces paperwork rather than improvement.
- Repeat NCR tracking, defined as the same supplier, component and defect category recurring.

**What it does not demonstrate.** Writing an NCR under time pressure with a line waiting, or
negotiating a disposition with a design authority. The records here are authored, not raised
in anger.

## 2. Root-cause analysis

**What the theme means.** Getting past the symptom to something that can actually be changed,
and being able to defend the conclusion.

**What the project demonstrates.**
- A 5 Whys chain where each answer is genuinely the question for the line below it, ending at a
  systemic cause (change control and control plan), not at "the operator should have been more
  careful".
- A fishbone across Man / Machine / Method / Material / Measurement / Environment that separates
  **potential** causes from **confirmed** causes, and records what was ruled out and why.
- A conclusion phrased as "most likely root cause on the available evidence" rather than as
  established fact.
- An investigation that was done badly first, stopped at the third why, produced a reasonable
  action, and was caught by verification. This is the part I would actually lead with.

**What it does not demonstrate.** Physical confirmation. In reality the insert grade change
would be verified against supplier change records, and tool wear would be measured. Here the
evidence is statistical and circumstantial.

## 3. Statistical analysis and SPC

**What the theme means.** Using data to tell the difference between a process that is behaving
normally and one that has changed.

**What the project demonstrates.**
- Individuals / Moving Range chart, chosen and justified: single measurements per part, no
  rational subgroups available.
- Sigma estimated from MR-bar / d2 rather than the sample standard deviation, with the reason
  explained — short-term variation is what makes a chart sensitive to drift.
- Phase I / Phase II handling: limits estimated from a stable baseline and held fixed.
- Four Western Electric style rules implemented, not just the "point outside the limits" rule.
- A demonstrated, measurable result: the chart signalled the shift **36 days** before the first
  part breached the drawing tolerance.
- A demonstration of what goes wrong when limits are fitted to drifting data: the stable
  baseline starts tripping run rules and real signals are lost.

**What it does not demonstrate.** Running SPC live on a shop floor, setting up a reaction plan
that operators will actually follow, or dealing with charts that nobody looks at.

## 4. Process capability

**What the theme means.** Knowing whether a process can hold a tolerance, and knowing when that
question is even answerable.

**What the project demonstrates.**
- Cp, Cpk, Cpu, Cpl, Pp and Ppk calculated and displayed together, with the within/overall sigma
  distinction explained.
- Capability calculated **per phase** rather than across a period containing a process change.
- The Cp / Cpk divergence used diagnostically, not just reported: Cp barely moved while Cpk
  collapsed, which identified a centring problem and redirected the investigation.
- The Cpk / Ppk gap used as evidence of instability.
- Explicit caveats: stability, normality (with a Shapiro-Wilk result shown), and sample size.
- Guideline bands stated as industry conventions, with the point made that the real target comes
  from the customer specification.

**What it does not demonstrate.** Negotiating a capability requirement with a customer, or
dealing with characteristics whose distribution is genuinely not normal (position, flatness,
runout — all one-sided or bounded).

## 5. Supplier quality

**What the theme means.** Managing quality at the supplier rather than inspecting it in on
arrival.

**What the project demonstrates.**
- A five-supplier scorecard covering PPM, defect rate, FPY, open NCRs, repeat NCRs, critical
  NCRs, overdue actions and on-time delivery.
- A deliberate refusal to produce a single overall ranking score, with the reasoning stated:
  combining PPM, delivery and open actions into one number hides which of them is the problem
  and the weighting would be arbitrary.
- Attention flags that name the specific threshold exceeded rather than a colour.
- A worked example of why PPM alone is insufficient: the case-study supplier sits *below* the
  PPM review threshold because its problem is diluted by higher-volume conforming work. It was
  flagged by repeat NCRs and a critical NCR instead.
- Corrective action driven back into the supplier's control plan and change control procedure,
  not just into incoming inspection.

**What it does not demonstrate.** Supplier audits, supplier development visits, escalation
conversations, PPAP or first article submission review. I have not done these and the project
does not pretend otherwise.

## 6. Continuous improvement

**What the theme means.** Changing something and being able to show it worked.

**What the project demonstrates.**
- A full problem → analysis → action → verification cycle with measured before and after.
- Preventive action separated from corrective action and applied across other characteristics.
- Verification against data, with the honest statement that a zero count is not a zero rate and
  a confidence bound quoted.
- An improvement that is believable rather than miraculous: Cpk 0.47 to 1.62, mean from 12.0
  microns off nominal to 1.7 microns off nominal.

**What it does not demonstrate.** Sustaining an improvement over a year, or the organisational
work of getting people to keep doing the new thing.

## 7. Manufacturing understanding

**What the theme means.** Knowing enough about how parts are made to have a sensible opinion
about why they came out wrong.

**What the project demonstrates.**
- A failure mechanism that is physically coherent: finish turning insert wear reduces depth of
  cut, leaves more material, and moves a diameter upward — one-directional, progressive, and
  consistent with the chart pattern observed.
- Recognition that a shift in the mean and an increase in spread have different physical causes.
- Process, characteristic and detection method modelled per component.

**Where this comes from.** My manufacturing placement gave me exposure to production support
and manufacturing processes. The specific turning scenario here is constructed for the project,
not drawn from that experience.

## 8. Data-driven engineering decisions

**What the theme means.** Deciding on evidence, and being clear about how strong the evidence is.

**What the project demonstrates.**
- Every number in the application is calculated at render time from the dataset rather than
  written into the narrative, so the text cannot drift away from the data.
- 66 automated tests, including tests that assert the case-study claims hold: that SPC signals
  before the specification is breached, that Cpk collapses while Cp holds, and that no
  dimensional non-conformance occurs after the corrective action.
- Uncertainty stated where it exists: confidence bound on a zero count, normality test result
  beside the model-based PPM, sample size caveats.

## 9. Inspection and detection

**What the theme means.** Knowing what inspection can and cannot do.

**What the project demonstrates.**
- Detection methods recorded per non-conformance (goods-in, CMM, in-process, assembly build
  check, test bench).
- The central argument that inspection is detection and SPC is closer to prevention, evidenced
  by the 36-day lead time.
- 100% inspection used as containment and explicitly framed as temporary and expensive.

## 10. Quality KPIs

**What the theme means.** Measuring the right things and knowing what each measure hides.

**What the project demonstrates.**
- PPM, defect rate, FPY, open/closed NCRs, repeat NCRs, overdue actions — each with its
  definition stated in code.
- The point that FPY here is the complement of the defect rate because each record is a
  first-pass check, and that rolled throughput yield across several stages would be stricter.
- Repeat NCR count argued as more informative than raw NCR count, because a high NCR count can
  simply mean detection is working well.
- PPM described as volume-weighted, with the inspected quantity always shown beside it.

---

## Three things I would say if asked "what did you learn?"

1. **The control chart is worth more than the inspection result.** The measurable version of
   this is the 36-day gap between the first control rule violation and the first out-of-spec
   part. Every part made in that window was conforming and was accepted.

2. **Cp and Cpk disagreeing is information, not noise.** The gap between them told me the
   problem was where the process was sitting rather than how much it was varying, which changed
   what I looked for.

3. **Verification is the step that makes the rest of it real.** The first corrective action in
   this project was sensible and wrong. Nothing except checking it against data would have
   found that.

## What I would need to learn on the job

Honest gaps, worth naming before someone else does:

- Measurement systems analysis in practice — Gauge R&R studies, bias and linearity.
- APQP and PPAP as they are actually run, including first article inspection.
- FMEA facilitation with a cross-functional team, rather than FMEA as a document.
- Supplier audits and supplier development.
- Working within a controlled QMS, with change control and document control as constraints
  rather than as concepts.
- Non-normal capability methods for one-sided and geometric characteristics.
