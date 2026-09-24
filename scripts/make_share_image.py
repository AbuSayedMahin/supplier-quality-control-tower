"""Generate a shareable, high-resolution image of the case-study control chart.

Run with:  python scripts/make_share_image.py

Produces assets/spc_control_chart.png at 2400x1350 (16:9, suitable for LinkedIn
and for embedding in the README). The chart is the single clearest artefact in
the project: it shows the process shift being detected well before any part fell
outside the drawing tolerance.

The image is generated from the same dataset and the same SPC code as the
application, so it cannot drift out of step with the analysis.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import BASELINE_END, BASELINE_START, CASE_STUDY_COMPONENT, CASE_STUDY_SUPPLIER, PROJECT_ROOT  # noqa: E402
from src.data_loader import load_data  # noqa: E402
from src.spc import build_imr_table, order_for_analysis  # noqa: E402

# Light theme reads better than dark on a LinkedIn feed.
SPEC = "#c62828"
CONTROL = "#ef6c00"
CENTRE = "#78909c"
SERIES = "#1565c0"
FLAG = "#c62828"
INK = "#1a2027"
MUTED = "#5f6b76"

# (label, start, end, fill, annotation position). The excursion band is narrow,
# so its neighbour is anchored to the right to stop the two labels colliding.
PHASE_BANDS = [
    ("Baseline &#8212; stable", "2026-01-05", "2026-02-27", "rgba(46,125,50,0.055)", "top left"),
    ("Drift &#8212; tool wear", "2026-03-02", "2026-04-17", "rgba(239,108,0,0.075)", "top left"),
    ("Excursion", "2026-04-20", "2026-05-15", "rgba(198,40,40,0.085)", "top left"),
    ("After corrective action", "2026-05-18", "2026-07-31", "rgba(21,101,192,0.055)", "top right"),
]


def build_figure() -> go.Figure:
    data = load_data()
    spec = data.component_spec(CASE_STUDY_COMPONENT)

    subset = order_for_analysis(
        data.inspections[
            (data.inspections["component_id"] == CASE_STUDY_COMPONENT)
            & (data.inspections["supplier_id"] == CASE_STUDY_SUPPLIER)
        ]
    )
    baseline_mask = (
        (subset["inspection_date"] >= BASELINE_START) & (subset["inspection_date"] <= BASELINE_END)
    ).reset_index(drop=True)
    imr, limits = build_imr_table(subset, baseline_mask=baseline_mask)

    first_signal = imr.loc[imr["any_rule"], "inspection_date"].min()
    first_oos = imr.loc[imr["in_spec"] == 0, "inspection_date"].min()
    lead_days = int((first_oos - first_signal).days)

    fig = go.Figure()

    # Phase bands -----------------------------------------------------------
    for label, start, end, colour, position in PHASE_BANDS:
        fig.add_vrect(
            x0=start, x1=end, fillcolor=colour, line_width=0, layer="below",
            annotation_text=label, annotation_position=position,
            annotation_font=dict(size=13.5, color=MUTED),
        )

    # Specification limits --------------------------------------------------
    for y, name in ((spec["usl"], "USL 25.020"), (spec["lsl"], "LSL 24.980")):
        fig.add_hline(y=y, line_color=SPEC, line_width=2.2)
        fig.add_annotation(xref="paper", x=1.0, y=y, text=f"<b>{name}</b>", showarrow=False,
                           xanchor="left", font=dict(size=13, color=SPEC))

    # Control limits --------------------------------------------------------
    for y, name in ((limits.ucl, f"UCL {limits.ucl:.4f}"), (limits.lcl, f"LCL {limits.lcl:.4f}")):
        fig.add_hline(y=y, line_color=CONTROL, line_width=1.8, line_dash="dash")
        fig.add_annotation(xref="paper", x=1.0, y=y, text=name, showarrow=False,
                           xanchor="left", font=dict(size=12, color=CONTROL))
    fig.add_hline(y=limits.center_line, line_color=CENTRE, line_width=1.4, line_dash="dot")
    fig.add_annotation(xref="paper", x=1.0, y=limits.center_line, text="CL", showarrow=False,
                       xanchor="left", font=dict(size=12, color=CENTRE))

    # The measurements ------------------------------------------------------
    fig.add_trace(go.Scatter(
        x=imr["inspection_date"], y=imr["measured_value"], mode="lines+markers",
        line=dict(color=SERIES, width=1.0), marker=dict(size=4.2, color=SERIES),
        name="Measured journal diameter", hoverinfo="skip",
    ))

    flagged = imr[imr["any_rule"]]
    fig.add_trace(go.Scatter(
        x=flagged["inspection_date"], y=flagged["measured_value"], mode="markers",
        marker=dict(size=9, color="rgba(0,0,0,0)", line=dict(color=FLAG, width=1.8)),
        name="Control rule violation", hoverinfo="skip",
    ))

    # The headline: the gap between signal and specification breach ----------
    y_top = spec["usl"] + 0.0042
    for x, colour in ((first_signal, CONTROL), (first_oos, SPEC)):
        fig.add_shape(type="line", x0=x, x1=x, y0=24.9775, y1=y_top,
                      line=dict(color=colour, width=1.6, dash="dot"))

    fig.add_annotation(
        x=first_signal, y=y_top, ax=first_oos, ay=y_top, xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=3, arrowsize=1, arrowwidth=2.4, arrowcolor=INK,
    )
    mid = first_signal + (first_oos - first_signal) / 2
    fig.add_annotation(
        x=mid, y=y_top + 0.0018, text=f"<b>{lead_days} days of warning</b>",
        showarrow=False, font=dict(size=17, color=INK),
    )
    fig.add_annotation(
        x=first_signal, y=24.9765, text=f"<b>SPC signals</b><br>{first_signal:%d %b}",
        showarrow=False, font=dict(size=12.5, color=CONTROL), align="center",
    )
    fig.add_annotation(
        x=first_oos, y=24.9765, text=f"<b>First part out of spec</b><br>{first_oos:%d %b}",
        showarrow=False, font=dict(size=12.5, color=SPEC), align="center",
    )

    fig.update_layout(
        template="plotly_white",
        title=dict(
            text=(
                "<b>The control chart flagged the shift "
                f"{lead_days} days before the first out-of-tolerance part</b>"
                "<br><span style='font-size:15px;color:#5f6b76'>"
                "Individuals chart &#8212; journal diameter on a critical rotating shaft, "
                "&#216;25.000 mm &#177;0.020. Every part in that window passed inspection."
                "</span>"
            ),
            x=0.012, xanchor="left", y=0.955, font=dict(size=25, color=INK),
        ),
        xaxis=dict(title="", tickfont=dict(size=13, color=MUTED), showgrid=False,
                   range=["2025-12-30", "2026-08-06"]),
        yaxis=dict(title=dict(text="Journal diameter (mm)", font=dict(size=14, color=MUTED)),
                   tickfont=dict(size=13, color=MUTED), gridcolor="rgba(0,0,0,0.055)",
                   range=[24.9735, spec["usl"] + 0.0088], tickformat=".3f"),
        legend=dict(orientation="h", yanchor="top", y=-0.10, xanchor="left", x=0,
                    font=dict(size=13, color=MUTED)),
        margin=dict(l=78, r=132, t=108, b=118),
        plot_bgcolor="white", paper_bgcolor="white",
    )

    fig.add_annotation(
        xref="paper", yref="paper", x=0, y=-0.195, xanchor="left", yanchor="top", showarrow=False,
        text=("Synthetic data generated for a portfolio project. Does not represent any real company, "
              "supplier or production process."),
        font=dict(size=12, color="#93a2ae"),
    )
    return fig


def main() -> None:
    out_dir = PROJECT_ROOT / "assets"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "spc_control_chart.png"

    fig = build_figure()
    fig.write_image(str(out_path), width=1200, height=675, scale=2)
    print(f"wrote {out_path}  (2400x1350)")


if __name__ == "__main__":
    main()
