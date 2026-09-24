# CV and Interview Material

Wording for CV, application forms and interview. Everything here describes the project
accurately as a **portfolio engineering project on synthetic data**. Nothing claims
professional quality engineering experience.

---

## One-line CV version

> **Supplier Quality Engineering Control Tower** — Python/Streamlit portfolio project applying
> SPC, process capability, Pareto and structured root-cause analysis to a synthetic
> high-performance manufacturing supply chain, tracing one dimensional non-conformance from
> detection through to verified corrective action.

Shorter variant if space is tight:

> **Supplier Quality Control Tower** (Python, Streamlit) — SPC, Cp/Cpk, Pareto and root-cause
> analysis applied end to end on a synthetic manufacturing dataset.

---

## Two-bullet CV version

> - Built a supplier quality analysis tool in Python (pandas, SciPy, Plotly, Streamlit) over a
>   2,040-record synthetic inspection dataset, implementing Individuals/Moving-Range control
>   charts with Western Electric run rules, process capability (Cp, Cpk, Pp, Ppk) and Pareto
>   analysis, covered by 66 automated tests.
> - Investigated a simulated dimensional drift on a critical rotating component using 5 Whys and
>   Ishikawa analysis; the control chart detected the process shift **36 days before any part
>   breached the drawing tolerance**, and the corrective action was verified against
>   post-change data (Cpk 0.47 → 1.62) rather than assumed effective.

### Notes on why these are worded this way

- The 36-day figure is the strongest single number in the project and is calculated from the
  data, not asserted. It is worth leading with.
- "Verified rather than assumed effective" signals that I understand the verification step,
  which is the part most people skip.
- Naming the test count signals engineering rigour without claiming production experience.
- "Synthetic" appears in the first bullet so there is no ambiguity about what the data is.

---

## 60-second interview explanation

> I built a supplier quality control tower as a portfolio project — it's a Streamlit application
> over a synthetic dataset for a fictional high-performance powertrain supply chain, about two
> thousand inspection records across five suppliers.
>
> The core of it is one investigation followed all the way through. A critical rotating shaft
> has a journal diameter with a forty-micron tolerance. Over about ten weeks the process drifts
> upward and eventually parts go over the upper limit.
>
> What I think is the interesting part is the timing. I put an Individuals and Moving Range
> chart on that characteristic, with the control limits calculated from a stable baseline period
> and then held fixed. The chart signals a sustained shift on the sixteenth of March. The first
> part actually outside specification isn't until the twenty-first of April — thirty-six days
> later. So for five weeks every part was conforming and was being accepted at goods-in, and the
> process had already told you it had changed. That's the argument for monitoring a process
> rather than just inspecting what comes out of it.
>
> Capability pointed at the cause. Cp barely moved but Cpk collapsed from about 1.5 to 0.5,
> which says the spread was fine and the mean had moved — so I was looking for something that
> shifts a process steadily in one direction, which is tool wear.
>
> The root cause came out as an insert grade change released without re-validating tool life, so
> the control plan still had an inspection regime matched to the old insert. And the bit I'd
> actually want to talk about is that the first investigation got it wrong — it stopped at "the
> operator should adjust the offset more often", that action was implemented, and it was verified
> as not effective, which is why it got reopened.
>
> It's synthetic data, so I designed the problem to be findable. But I can defend every
> calculation in it.

**Delivery notes:** roughly 60–70 seconds at a normal pace. If they only want 30 seconds, stop
after the paragraph about the 36 days. If they want more, the failed first corrective action is
the richest thing to expand on.

---

## Technical discussion points

Ten likely questions with concise answers.

### 1. Why an Individuals chart rather than X-bar and R?

An X-bar and R chart needs rational subgroups — several parts measured under conditions you
believe are the same, so the within-subgroup range estimates short-term variation. Incoming
inspection here produces one measurement per part, so there is no subgroup to take a range
within. The Individuals chart with a moving range of consecutive pairs is the standard answer
to that. The trade-off is that it is less sensitive to small shifts than a subgrouped chart,
which is part of why the run rules matter so much here.

### 2. What is the difference between a control limit and a specification limit?

They come from completely different places and are never calculated from each other. A
specification limit comes from the drawing — it is what the design requires, and it would be
the same number if the part were made somewhere else or not made at all. A control limit is
calculated from the process data and describes what this process actually does when it is
behaving consistently. In this project the control limits were 24.9871 to 25.0138 while the
specification was 24.980 to 25.020 — the process was tighter than the tolerance, which is why
the chart could signal while every part was still conforming.

**Trap to avoid:** saying control limits are "three sigma of the data". They are three sigma of
the *short-term* variation, estimated from the moving range, not three times the standard
deviation of all the data. That distinction is exactly what made the drift detectable.

### 3. Why did you calculate limits from a baseline instead of all the data?

Because a control chart answers "has this process changed from how it was behaving?", and to
ask that you need limits that describe how it *was* behaving. I tested the alternative: fitting
limits to the whole period pulls the centre line from 25.00045 up to 25.00405, because the
drifting data drags it. The result is worse than just being less sensitive — the genuinely
stable baseline period starts tripping run rules, and the number of points beyond a control
limit drops from 30 to 18. You get false alarms on good data and you lose real signals.

### 4. Cp was still 1.2 during the excursion. Why did you call the process incapable?

Because Cp does not know where the process is sitting. It only compares the tolerance width to
six sigma, so it measures potential capability if the process were perfectly centred. Cpk
measures to the nearer specification limit, so it penalises being off centre. During the
excursion Cp was 1.17 but Cpk was 0.47, because the mean had moved to within about six microns
of the upper limit on a forty-micron tolerance. A Cpk below 1.0 means the process spread no
longer fits inside the tolerance at the position it is sitting, and five parts did go out.

The gap between them is the useful part. Cp holding while Cpk falls tells you it is a centring
problem, which is usually easier to fix than a variation problem.

### 5. How did you identify the root cause, and how do you know it is right?

Structurally, with 5 Whys and a fishbone, but the direction came from the data first. The
moving range chart stayed inside its limits while the individuals chart drifted, so part-to-part
variation was stable and the mean was moving. That rules out a lot — it is not the machine
losing repeatability, and it is not material scatter, because material varies batch to batch
and would produce noise rather than a one-directional trend. What shifts a mean steadily in one
direction is tool wear, or an offset that is not being corrected.

I do not know it is right, and I would not claim that. It is stated as the most likely root
cause on the available evidence. The reason I am comfortable acting on it is that the
corrective action was then verified against post-change data, and the earlier hypothesis on the
same problem was rejected that way.

### 6. How did you verify the corrective action?

Four independent lines of evidence, because any one of them alone is weak. The process mean
moved from 12.0 microns off nominal to 1.7 microns off nominal. Cpk went from 0.47 to 1.62.
Points beyond a control limit went from 30 to zero. And no further NCRs were raised on that
supplier, component and defect category.

Two things I was careful about. I plotted the post-change data against the *original* baseline
control limits, not against limits recalculated from itself — recalculating would guarantee the
points fell inside and would prove nothing. And I compared against the excursion period rather
than the whole pre-change period, because averaging the stable baseline in with the drift would
have understated the problem and overstated the improvement.

### 7. You have zero out-of-spec parts after the fix. Is the problem solved?

No, and I would not write it up that way. A zero count is not a zero rate. With no events in
154 parts, the one-sided 95% upper confidence bound on the true rate is about 1.9% — so the
data is consistent with a rate anywhere from zero up to roughly 19,000 PPM. The evidence
supports a real improvement, particularly taken with the capability and control chart evidence,
but it does not establish that the rate is zero.

I would also say eleven weeks is short. It is long enough to be persuasive but not long enough
to show the control holds through a tooling change, a new operator or a different material
batch.

### 8. Your chart still shows violations after the corrective action. Doesn't that undermine the result?

It looks that way until you check which rule. There are 31 flagged points out of 154, and none
of them is a point beyond a control limit — no rule 1, no rule 2. They are all run rules: four
of five points beyond one sigma, and eight consecutive on one side of the centre line. They
happen because the post-change mean sits about 0.29 sigma above the *original* baseline centre
line.

That is the chart working correctly. The process genuinely changed, so measuring it against
limits from the old process will keep producing run signals indefinitely. The right response is
to re-establish the limits on the revised process and monitor forward from there — the normal
move from a Phase I study to Phase II monitoring. Reopening the NCR would be wrong: there is no
drift, nothing outside a control limit, and nothing outside specification.

### 9. Why is there no overall supplier ranking score?

Because it would hide the thing you need to know. If you combine PPM, on-time delivery, open
NCRs and overdue actions into one number, a supplier with excellent delivery and a serious
quality problem can score the same as one with the reverse, and the weighting you pick to
combine them is arbitrary. The scorecard shows each measure separately with a named reason when
a threshold is exceeded.

There is a concrete example in the data. The case-study supplier sits *below* the PPM review
threshold, because its dimensional problem is diluted by a larger volume of conforming work on
another component. PPM alone would not have flagged it. It gets flagged by repeat NCRs and by
having a critical NCR.

### 10. What is the weakest part of this project?

The measurement system. There is no MSA study. I reasoned about the measurement branch of the
fishbone and ruled it out on the argument that gauge error would not produce a steady
one-directional trend, and that is a fair argument, but it is not the same as having done a
Gauge R&R. On a drift of 12 microns against a 40-micron tolerance, measurement variation is
well inside the range where it could contribute. In practice confirming the measurement system
is trustworthy would come *before* trusting any of the analysis built on it.

The second weakest part is that the data is synthetic, so the answer was designed to be
findable. Real data is noisier and competing explanations are harder to eliminate.

---

## Questions to ask them

Worth having a couple ready, and these are genuine:

1. How much of the quality engineering work is upstream — control plans, FMEA, capability
   studies at new part introduction — versus reacting to non-conformances that have already
   happened?
2. Where does SPC actually run: at the supplier, at goods-in, or in-house? And who reacts to it?
3. How is corrective action effectiveness verified, and how long is a typical verification
   window before an NCR is closed?

---

## What not to say

- Do not say the project gives me quality engineering experience. It gives me understanding of
  the methods.
- Do not present the synthetic data as if it were real, and do not let the F1-style framing
  imply any connection to a real team.
- Do not quote capability thresholds (1.33, 1.67) as if they were universal standards. They are
  widely used conventions; the real target comes from the customer specification.
- Do not claim the root cause is proven. It is the most likely cause on the available evidence.
