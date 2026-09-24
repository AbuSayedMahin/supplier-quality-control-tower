# Future Improvements

Ideas that came up while building the project and were deliberately **not** implemented,
because they sat outside the scope. The project was kept to what demonstrates quality
engineering reasoning rather than what demonstrates software features.

Recorded here so the thinking is not lost, and so it is clear these were decisions rather than
oversights.

---

## Quality engineering content that would genuinely add value

These are the ones I would do first if the project were extended, because they add engineering
substance rather than software.

**Measurement systems analysis (Gauge R&R).** The clearest gap in the project. A crossed Gauge
R&R study with operators, parts and trials, reporting repeatability, reproducibility, %R&R and
number of distinct categories. It belongs *before* the SPC analysis logically, since capability
figures are only as trustworthy as the measurement system behind them. Left out because doing
it properly means modelling operator and trial effects, which is a meaningful extension of the
data generator.

**Process FMEA on the case-study operation.** Severity, occurrence and detection ratings with
an action priority, linked to the control plan. It would connect naturally to the root cause
found here — the failure mode "diameter drifts with tool wear" would have a detection rating
that the missing in-process check makes worse.

**A control plan document for the critical characteristic.** The corrective action changes the
control plan, but the control plan itself is not modelled. Showing the before and after version
would make the corrective action more concrete.

**Non-normal capability methods.** Position, flatness and runout are one-sided or bounded and
are not normally distributed. Box-Cox transformation or a Weibull-based capability index would
be the correct treatment. Currently the project uses normal-based indices throughout and states
the assumption, which is honest but limited.

**Confidence intervals on Cp and Cpk.** Capability estimated from a sample has a confidence
interval that is wider than most people expect. Showing it would reinforce the point about
sample size that is currently only stated in a caveat.

**Cost of quality.** Scrap, rework, containment inspection hours and concession costs attached
to each NCR. It would let the Pareto be ranked by cost as well as by frequency and severity,
which is usually how prioritisation actually happens.

**8D report generation.** The investigation content already maps onto D1–D8. Rendering it as a
formatted 8D would be a small step and is the format most suppliers actually receive.

**Sampling plan analysis.** ISO 2859 / AQL sampling, and the arithmetic of what a given sample
plan can and cannot detect. Relevant because the case study hinges on detection.

## Software features deliberately excluded

Excluded because they add complexity without adding quality engineering evidence:

- Machine learning or predictive models for defect forecasting
- LLM integration or a natural-language query interface
- Authentication, user accounts or role-based access
- A production database — CSV files keep the data readable and reviewable
- REST API or ERP/MES integration
- Docker packaging
- Real-time data ingestion
- A custom frontend framework
- Multi-user collaboration or comment threads
- PDF export of reports
- Email or Teams alerting on threshold breaches

Any of these would have made the project larger. None would have made it better evidence of
quality engineering thinking.

## Data model extensions considered

- **Multiple characteristics per component.** Real parts have dozens. Modelling several would
  allow a genuine prioritisation exercise — deciding which characteristics justify SPC — which
  is itself a quality engineering skill. Left out to keep the analysis focused.
- **Batch and material traceability.** Batch IDs exist but are not used analytically. Tracing a
  non-conformance back through material heat would support a different class of investigation.
- **Operator and shift attribution.** Would enable a stratified analysis, but also risks
  encouraging "operator error" conclusions, which is the failure mode the root cause analysis in
  this project deliberately avoids.
- **Supplier audit records and scores.** Would make the supplier quality section more complete,
  but I have not conducted a supplier audit and modelling one would be guesswork.
- **A second, independent case study.** A second full investigation (the packaging/reference
  sample one is partially developed) would show the method generalising. The risk is diluting
  attention from the main case study.

## Known simplifications in the current build

Documented so they are not mistaken for errors:

- Each component carries exactly one critical characteristic.
- First pass yield is the complement of the defect rate, because each inspection record is a
  first-pass check. A multi-stage line would need rolled throughput yield.
- A unit with more than one problem is recorded under a single defect category.
- Repeat NCRs are defined as the same supplier, component and defect category. Other
  definitions (by root cause, by failure mode, within a rolling window) are equally defensible.
- Review thresholds (25,000 PPM, 92% on-time delivery, two repeat NCRs) are project conventions,
  not agreed supplier requirements.
- The reporting date is fixed at 2026-08-01 so that overdue counts and test results are
  reproducible.
