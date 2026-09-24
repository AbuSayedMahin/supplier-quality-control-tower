# Engineering Case Study: Dimensional Drift on a Critical Rotating Component

**Project:** Supplier Quality Engineering Control Tower
**Status:** Portfolio project built on entirely synthetic data
**Analysis period:** 5 January 2026 to 31 July 2026
**Reporting date:** 1 August 2026

> All suppliers, components, measurements and non-conformance records in this document are
> fictional. They were generated from a statistical model with a fixed random seed. Nothing
> here represents a real company, a real supplier or real production data.

---

## 1. Problem

Journal diameter on the High-Speed Rotating Shaft (CMP-101), supplied by Apex Precision
(SUP-001), drifted upward from nominal over a period of roughly ten weeks and eventually
produced parts above the upper specification limit.

The characteristic is a critical fit dimension on a rotating assembly:

| | |
|---|---|
| Characteristic | Journal Diameter |
| Nominal | 25.000 mm |
| Specification | 24.980 mm to 25.020 mm |
| Total tolerance | 0.040 mm |
| Process | CNC finish turning at the supplier |
| Detection point | Goods-in inspection |

Three non-conformance reports were raised against the same supplier, component and defect
category within five weeks:

| NCR | Raised | Severity | Content |
|---|---|---|---|
| NCR-2026-014 | 7 Apr 2026 | Major | Raised against a **trend**. No part was outside specification at the time; one measured 25.0193 mm, within 0.001 mm of the upper limit. |
| NCR-2026-018 | 27 Apr 2026 | Critical | Two shafts above 25.020 mm, measured 25.0207 mm and 25.0205 mm. |
| NCR-2026-021 | 15 May 2026 | Major | Three further parts above the limit, all caught by the containment inspection put in place under NCR-2026-018. |

## 2. Approach

The investigation followed the sequence the dashboard is built around:

```
data -> detection -> analysis -> root cause -> containment
     -> corrective action -> verification -> closure
```

Each step narrowed the question. The control tower identified *where* to look, the Pareto
identified *what kind* of problem it was, SPC identified *when* it started and *what shape*
it had, capability quantified *how bad* it was, and only then did the investigation move on
to *why*.

That order matters. Starting at "why" without establishing the shape of the problem is how
investigations end up chasing plausible-sounding causes that the data does not support.

## 3. Data

| File | Records | Content |
|---|---|---|
| `suppliers.csv` | 5 | Supplier master data and on-time delivery |
| `components.csv` | 6 | Component master data with one critical characteristic each |
| `inspections.csv` | 2,040 | Individual inspection measurements over 30 production weeks |
| `ncrs.csv` | 32 | Non-conformance reports with full workflow status |
| `corrective_actions.csv` | 21 | Corrective and preventive actions with verification evidence |

Overall across the whole dataset: 51 non-conforming units in 2,040 inspected, a defect rate
of 2.50% (25,000 PPM) and a first pass yield of 97.50%.

Dimensional non-conformances are not invented separately from the measurements. A part is
recorded as dimensionally non-conforming because its measured value falls outside the
specification limits, which keeps the analysis and the records consistent with each other.
Non-dimensional defects such as burrs, surface finish and visual findings are drawn at
supplier-specific rates.

For the case-study characteristic, 420 measurements were taken across the period. The
underlying process model moves through four phases: a stable baseline, a drift as a finish
turning tool wears, an excursion where the mean sits close to the upper limit, and a return
toward nominal after corrective action.

## 4. Pareto findings

At supply-base level the Pareto does **not** point at the problem. Across all suppliers and
components, dimensional deviation is only the sixth largest of seven defect categories by
frequency (5 of 51 records). Visual defect and surface finish are larger.

That is not a flaw in the method; it is the method working correctly. A Pareto across
unrelated processes mixes several independent problems together and averages them. Two things
recovered the signal:

1. **The severity cross-check.** Splitting each category by severity showed that dimensional
   deviation, despite low frequency, was the category carrying critical-severity records. A
   frequency-only Pareto would have deprioritised exactly the thing that mattered most.
2. **Narrowing the scope.** Filtered to CMP-101 at Apex Precision, dimensional deviation
   accounts for 5 of 7 recorded non-conformances for that combination.

The practical conclusion is that a Pareto is a tool for narrowing, not a diagnosis, and that
ranking by frequency alone is not sufficient when severity varies widely between categories.

## 5. SPC findings

An Individuals and Moving Range (I-MR) chart was used because inspection produces a single
measurement per part rather than rational subgroups, so there is no within-subgroup range to
work from.

Control limits were estimated from the stable baseline period (5 January to 27 February) and
then held fixed and projected forward. This is a Phase I / Phase II approach. Sigma was
estimated from the average moving range rather than the overall standard deviation:

```
MR-bar  = 0.00503
sigma   = MR-bar / d2 = 0.00503 / 1.128 = 0.00446
CL      = 25.00045
UCL     = CL + 2.660 x MR-bar = 25.01383
LCL     = CL - 2.660 x MR-bar = 24.98706
```

Results across the 420 observations:

| | |
|---|---|
| First control rule violation | 16 March 2026 |
| First part outside specification | 21 April 2026 |
| **Warning lead time** | **36 days** |
| Observations violating a control rule | 153 of 420 |
| Points beyond a control limit during drift and excursion | 30 |
| Moving range exceedances | 5 |

**The single most important finding in this project is the 36-day gap.** The control chart
signalled a sustained shift more than five weeks before any part actually breached the drawing
tolerance. During that period every part produced was conforming and was being accepted at
goods-in. Inspection alone would not have raised anything; the process itself had already
announced that it had changed.

The pattern also carried diagnostic information. The violations were dominated by run rules —
sustained runs above the centre line — rather than by isolated extreme points, and the moving
range chart stayed broadly within its upper limit. Part-to-part variation was stable while the
average moved. That is the signature of a shifting process centre, not of a machine losing
repeatability, and it narrowed the list of plausible causes considerably before any of them
were examined.

The importance of the baseline was tested directly. When control limits are fitted to the
whole period instead, the centre line is dragged upward from 25.00045 to 25.00405 by the
drifting data. The consequence is not that the drift is merely less visible: the genuinely
stable baseline period starts tripping run rules, and the number of points beyond a control
limit falls from 30 to 18. Fitting limits to data from a process that has already changed
produces false alarms on good data and hides real signals.

## 6. Capability findings

Capability was calculated separately for each phase, because calculating it across a period
containing a process change averages two different processes together and describes neither.

| Phase | n | Mean | Offset from nominal | Sigma (within) | Cp | Cpk | Ppk | Out of spec |
|---|---|---|---|---|---|---|---|---|
| Baseline (stable) | 112 | 25.0005 | +0.0005 | 0.00446 | 1.49 | 1.46 | 1.52 | 0 |
| Drift period | 98 | 25.0072 | +0.0072 | 0.00478 | 1.39 | 0.89 | 0.80 | 0 |
| Excursion period | 56 | 25.0120 | +0.0120 | 0.00569 | 1.17 | 0.47 | 0.49 | 5 |
| Post-corrective action | 154 | 25.0017 | +0.0017 | 0.00376 | 1.78 | 1.62 | 1.47 | 0 |

The diagnostic pattern is the divergence between Cp and Cpk. Between baseline and excursion,
Cp fell only from 1.49 to 1.17 while Cpk collapsed from 1.46 to 0.47. The process spread
barely changed; what changed was where the process was sitting. Cp ignores centring, Cpk does
not, and the gap between them is a direct measure of how far off centre the process has moved.

That distinction is what turned the investigation toward causes that shift a mean steadily in
one direction — tool wear, an uncorrected offset, thermal growth — and away from causes that
would widen the spread, such as machine repeatability or material variation.

The gap between Cpk and Ppk during the drift period (0.89 against 0.80) carries the same
message from a different direction. Cpk uses short-term variation between consecutive parts;
Ppk uses the spread across the whole period. When a process is drifting, the overall spread is
inflated by the movement while the part-to-part range is not, so the two indices separate. A
Cpk that is comfortably higher than Ppk is itself evidence of instability.

All capability figures are reported with the caveat that capability indices assume a stable
process. During the drift and excursion the process was not stable, so those values describe
the period that was measured rather than predicting future output. Guideline bands (1.33,
1.67) are stated as widely used industry conventions rather than universal requirements.

## 7. Root-cause investigation

### 5 Whys

| | Question | Answer |
|---|---|---|
| 1 | Why were journal diameters recorded above the upper specification limit? | The machined diameter had drifted steadily upward over successive batches until parts exceeded 25.020 mm. |
| 2 | Why did the diameter drift upward? | The finish turning insert wore progressively, the depth of cut reduced, and more material was left on the diameter. No offset correction was applied between batches to compensate. |
| 3 | Why was no offset correction applied between batches? | The operator only adjusted the offset when a first-off inspection failed, rather than on a planned basis linked to tool life. |
| 4 | Why was the offset only adjusted on a first-off failure? | The control plan specified first-off and last-off inspection only. It contained no in-process check and no rule requiring an offset correction at a defined tool life point. |
| 5 | Why did the control plan not contain a tool-life-based rule? | A finish turning insert grade change was introduced in February and the tool life for the new grade was never re-validated. The control plan still reflected the wear behaviour of the previous insert. |

### Fishbone

Causes were grouped under Man, Machine, Method, Material, Measurement and Environment.
Confirmed causes were all under **Method**:

- Control plan specifies first-off and last-off inspection only, with no in-process check
- No tool-life-based offset correction rule for the finish turning operation
- Insert grade change released without tool life re-validation

Branches considered and **not supported**, with the reason recorded:

| Branch | Why it was not supported |
|---|---|
| Measurement system error | The goods-in gauge was in calibration throughout, and suspect parts re-measured on an independent gauge agreed to within 0.001 mm. A measurement fault would also not produce a steady one-directional trend. |
| Material hardness variation | The drift is monotonic across many separate material batches. Batch-to-batch variation would produce scatter, not a sustained one-way trend. |
| Machine capability | The moving range chart shows part-to-part variation staying stable while the mean moved, which is a centre shift rather than a loss of repeatability. |

### Most likely root cause

> A finish turning insert grade change was released in February 2026 without re-validating
> tool life or reviewing the control plan. The existing first-off and last-off inspection
> regime had been matched to the previous insert's wear rate, so with the new grade the
> diameter drifted between offset corrections and no in-process check existed to detect it.

This is stated as the most likely root cause on the available synthetic evidence, not as a
proven fact. A root cause analysis produces a hypothesis strong enough to act on. The
verification step exists precisely because that hypothesis can be wrong.

### The first investigation was wrong

NCR-2026-014 had been raised three weeks earlier against the same trend. The corrective action
taken then (CA-014) asked the supplier to tighten the tool offset correction frequency. That
is an action against the **third** why: it treats the offset practice as the cause rather than
asking why the existing practice had stopped being adequate.

CA-014 was verified as **not effective**. The mean continued to rise and parts subsequently
went out of specification. The investigation was reopened and taken deeper.

This is preserved deliberately in the dataset. An investigation that stops too early produces
an action that is reasonable, cheap and wrong, and the only reason that gets discovered is
that effectiveness is checked against data rather than assumed.

## 8. Corrective action

The three actions are deliberately separated, because they answer different questions.

**Containment** — *what do we do about the parts that already exist?*
Two suspect batches quarantined at goods-in and returned. 100% inspection of journal diameter
on all incoming shafts and at supplier final inspection. Stock on hand re-measured and
segregated. Containment protects the build but does not change why the material was produced
that way, and it is expensive: 100% inspection on every incoming shaft. It also worked — the
three further non-conforming parts recorded under NCR-2026-021 were all caught by it.

**Corrective action** — *why did this happen, and what stops it happening here again?*
Supplier reverted to the validated insert grade and re-established the tool life limit for the
finish turning operation. Control plan updated to require an in-process journal diameter check
every fifth part and a tool offset correction at a defined cumulative part count.

**Preventive action** — *where else could this go wrong for the same reason?*
Change control procedure extended so that any tooling or consumable change affecting a
critical characteristic requires tool life re-validation and a control plan review before
release. The same review was applied to the other critical rotating characteristics from this
supplier, and SPC monitoring with a documented reaction plan was introduced at the supplier
for the journal diameter.

The corrective action addresses the fifth why, not the first. An action aimed at the first why
would have been to rework the parts, which fixes nothing. An action aimed at the third why had
already been tried and had already failed.

Implemented 15 May 2026. First delivery of material produced under the revised control plan
arrived 18 May 2026.

## 9. Verification

Effectiveness was assessed on eleven weeks of post-change data (154 measurements), compared
against the **excursion period** rather than against the whole pre-change period. Averaging
the stable baseline together with the drift would understate the problem and therefore
overstate the improvement.

| Measure | Excursion period | Post-corrective action |
|---|---|---|
| Observations | 56 | 154 |
| Process mean | 25.01204 mm | 25.00173 mm |
| Offset from nominal | +0.01204 mm | +0.00173 mm |
| Sigma (within) | 0.00569 | 0.00376 |
| Cp | 1.17 | 1.78 |
| Cpk | 0.47 | 1.62 |
| Ppk | 0.49 | 1.47 |
| Parts outside specification | 5 | 0 |
| Points beyond a control limit | 30 | 0 |

Post-change data was plotted against the **original baseline control limits**, not against
limits recalculated from itself. Recalculating would guarantee that the points fell inside and
would prove nothing.

A Welch two-sample t-test on the difference in means returns t = -12.93, p ≈ 3e-21. This is
recorded as a supporting check rather than as the primary evidence: the control chart and the
capability indices describe the process, whereas a t-test only tests a single summary
statistic.

Four independent lines of evidence point the same way: the position of the mean, the
capability index, the absence of points beyond a control limit, and the absence of further
NCRs on the same supplier, component and defect category. That consistency is what makes it
reasonable to call the action effective.

### Two things the verification does *not* claim

**Zero out of specification is not a zero rate.** With no events observed in 154 parts, the
one-sided 95% upper confidence bound on the true non-conformance rate is approximately 1.93%
(19,265 PPM). The evidence supports a real improvement; it does not establish that the rate is
zero.

**The chart is not completely clean.** 31 of the 154 post-change observations still trip a run
rule. None is a point beyond a control limit and none is a rule 1 or rule 2 violation; they
are all run rules, caused by the post-change mean sitting about 0.29 sigma above the
*original* baseline centre line. That is correct chart behaviour, not a fault. The process
really has changed, so measuring it against limits derived from the old process will keep
producing run signals. The right response is to re-establish the control limits on the revised
process and monitor forward — the normal transition from a Phase I study to Phase II
monitoring — not to reopen the NCR.

## 10. Closure

NCR-2026-018 was raised on 27 April 2026, the corrective action was implemented on 15 May
2026, and the NCR was closed on 26 June 2026 — 42 days after implementation and 60 days after
it was raised.

That 42-day gap is the verification period. Closing on the implementation date would have
recorded that something was done, not that it worked. Six weeks of post-change data was needed
before the control chart and the capability study could support a conclusion.

All three related NCRs were closed only after verification status reached "Verified".

## 11. Engineering reflection

**The control chart earned its place before the specification was breached.** The single
finding I would lead with is the 36-day warning lead time. It is the concrete argument for
monitoring a process rather than only inspecting its output, and it is measurable rather than
rhetorical.

**Cp and Cpk together were more informative than either alone.** The divergence between them
was not just a number that got worse; it was a pointer toward a specific class of cause. That
changed what the investigation looked at.

**The failed first corrective action is the most instructive part of the dataset.** It is easy
to build a case study where the analysis is correct first time. Including an investigation
that stopped at the third why, produced a reasonable action, and was caught only by
verification, demonstrates why the verification step exists at all.

**Frequency-based prioritisation nearly buried the problem.** Dimensional deviation was sixth
of seven by count. Without the severity cross-check and without narrowing the scope, a purely
frequency-driven approach would have directed effort at visual defects while a critical
rotating characteristic drifted toward its tolerance limit.

**Root causes that are systems, not people, are the ones worth finding.** The chain could have
stopped at "the operator did not adjust the offset often enough". That reads like a cause and
is actionable, which makes it dangerous. The control plan and the change control procedure are
what actually failed, and they are what a corrective action can fix permanently.

## 12. Limitations

This is a portfolio project built on synthetic data. The following are genuine limitations,
not disclaimers:

1. **The data is generated, so the answer was designed to be findable.** The drift was put into
   the process model deliberately. Real data is noisier, the signal is weaker, and competing
   explanations are harder to eliminate.

2. **One characteristic per component.** Real parts carry dozens of controlled characteristics,
   and real supplier quality work involves deciding which of them matter. That prioritisation
   step is absent here.

3. **No measurement system analysis.** Gauge R&R is discussed and the measurement branch of the
   fishbone was reasoned about, but no MSA study was performed. In practice, confirming the
   measurement system before trusting the data would come first. A drift of 0.012 mm on a 0.040
   mm tolerance is well within the range where gauge error could contribute.

4. **Normality is assumed for predicted PPM.** A Shapiro-Wilk test is reported alongside it, but
   the model-based out-of-specification prediction should be read as a model output, not a
   count. The observed count is the more reliable figure.

5. **Defect rates are higher than a mature programme would accept.** 25,000 PPM overall was
   chosen so that the analysis has something to work with across a six-month window. A
   high-performance powertrain programme would target very much lower, and would treat these
   figures as a serious supply-base problem rather than a baseline.

6. **The root cause is asserted, not investigated physically.** In reality the insert grade
   change would be confirmed against the supplier's change records, tool life would be measured,
   and the wear rate would be characterised. Here the evidence is statistical and circumstantial.

7. **Eleven weeks is a short verification window.** It is enough to be persuasive but not enough
   to confirm the control holds through a tooling change, a new operator or a different material
   batch. The honest statement is that the action is effective on the evidence available so far.

8. **Repeat NCR definition is a project convention.** "Same supplier, component and defect
   category" is defensible and is applied consistently, but other organisations define repeats
   differently — by root cause, by failure mode, or within a rolling time window.

9. **Thresholds are chosen, not agreed.** The 25,000 PPM review threshold and the 92% on-time
   delivery threshold are project conventions. In a real programme these would come from the
   quality agreement with each supplier.
