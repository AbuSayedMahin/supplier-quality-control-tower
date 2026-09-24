"""Plotly chart builders.

The visual language is deliberately consistent across the application so that a
reader can tell at a glance what kind of line they are looking at:

    solid red        specification limit (what the design requires)
    dashed orange    control limit (what the process actually does)
    dotted grey      centre line / nominal
    red marker       point that violated a control rule

Confusing control limits with specification limits is the single most common
mistake in applied SPC, so they never share a colour or a line style here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

SPEC_COLOUR = "#c62828"
CONTROL_COLOUR = "#ef8f00"
CENTRE_COLOUR = "#607d8b"
SERIES_COLOUR = "#1565c0"
FLAG_COLOUR = "#c62828"
OK_COLOUR = "#2e7d32"

LAYOUT = dict(
    template="plotly_white",
    margin=dict(l=60, r=30, t=50, b=50),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def _hline(fig, y, colour, dash, text, row=None):
    kwargs = dict(
        y=y,
        line_color=colour,
        line_dash=dash,
        line_width=1.4,
        annotation_text=text,
        annotation_position="right",
        annotation_font_size=10,
        annotation_font_color=colour,
    )
    if row is not None:
        fig.add_hline(row=row, col=1, **kwargs)
    else:
        fig.add_hline(**kwargs)


def individuals_chart(imr: pd.DataFrame, limits, spec: dict, title: str, show_spec: bool = True) -> go.Figure:
    """Individuals chart with control limits, optional specification limits and rule flags."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=imr["inspection_date"],
            y=imr["measured_value"],
            mode="lines+markers",
            name="Measured value",
            line=dict(color=SERIES_COLOUR, width=1.2),
            marker=dict(size=4, color=SERIES_COLOUR),
            customdata=imr[["inspection_id", "batch_id"]].to_numpy(),
            hovertemplate="%{y:.4f} mm<br>%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
        )
    )

    flagged = imr[imr["any_rule"]]
    if len(flagged):
        fig.add_trace(
            go.Scatter(
                x=flagged["inspection_date"],
                y=flagged["measured_value"],
                mode="markers",
                name="Control rule violation",
                marker=dict(size=8, color=FLAG_COLOUR, symbol="circle-open", line=dict(width=2)),
                hovertemplate="%{y:.4f} mm - rule violation<extra></extra>",
            )
        )

    _hline(fig, limits.center_line, CENTRE_COLOUR, "dot", f"CL {limits.center_line:.4f}")
    _hline(fig, limits.ucl, CONTROL_COLOUR, "dash", f"UCL {limits.ucl:.4f}")
    _hline(fig, limits.lcl, CONTROL_COLOUR, "dash", f"LCL {limits.lcl:.4f}")

    if show_spec:
        _hline(fig, spec["usl"], SPEC_COLOUR, "solid", f"USL {spec['usl']:.3f}")
        _hline(fig, spec["lsl"], SPEC_COLOUR, "solid", f"LSL {spec['lsl']:.3f}")

    fig.update_layout(
        title=title,
        yaxis_title=f"{spec['characteristic']} ({spec['unit']})",
        xaxis_title="Inspection date",
        height=460,
        **LAYOUT,
    )
    return fig


def moving_range_chart(imr: pd.DataFrame, limits, title: str = "Moving Range chart") -> go.Figure:
    """Moving range chart - tracks part-to-part variation rather than level.

    The individuals chart answers "has the process moved?"; the moving range
    chart answers "has the process become more erratic?". A process can fail one
    without failing the other, which is why both are read together.
    """
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=imr["inspection_date"],
            y=imr["moving_range"],
            mode="lines+markers",
            name="Moving range",
            line=dict(color=SERIES_COLOUR, width=1.1),
            marker=dict(size=3.5, color=SERIES_COLOUR),
            hovertemplate="MR %{y:.4f}<extra></extra>",
        )
    )

    flagged = imr[imr["mr_out_of_control"]]
    if len(flagged):
        fig.add_trace(
            go.Scatter(
                x=flagged["inspection_date"],
                y=flagged["moving_range"],
                mode="markers",
                name="Above MR upper limit",
                marker=dict(size=8, color=FLAG_COLOUR, symbol="circle-open", line=dict(width=2)),
                hovertemplate="MR %{y:.4f} - above upper limit<extra></extra>",
            )
        )

    _hline(fig, limits.mr_center_line, CENTRE_COLOUR, "dot", f"MR-bar {limits.mr_center_line:.4f}")
    _hline(fig, limits.mr_ucl, CONTROL_COLOUR, "dash", f"UCL {limits.mr_ucl:.4f}")

    fig.update_layout(title=title, yaxis_title="Moving range", xaxis_title="Inspection date", height=300, **LAYOUT)
    return fig


def pareto_chart(table: pd.DataFrame, title: str, threshold: float = 80.0) -> go.Figure:
    """Bars of frequency with a cumulative percentage line and a threshold marker."""
    category_col = table.columns[0]
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=table[category_col],
            y=table["count"],
            name="Non-conformances",
            marker_color=SERIES_COLOUR,
            hovertemplate="%{x}<br>%{y} occurrences<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=table[category_col],
            y=table["cumulative_percent"],
            name="Cumulative %",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color=SPEC_COLOUR, width=2),
            marker=dict(size=7),
            hovertemplate="%{x}<br>Cumulative %{y:.1f}%<extra></extra>",
        )
    )

    fig.add_hline(
        y=threshold,
        yref="y2",
        line_dash="dash",
        line_color=CENTRE_COLOUR,
        line_width=1.3,
        annotation_text=f"{threshold:.0f}% reference",
        annotation_position="right",
        annotation_font_size=10,
    )

    fig.update_layout(
        title=title,
        yaxis=dict(title="Number of non-conformances"),
        yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105], ticksuffix="%"),
        xaxis_title="Defect category",
        height=440,
        bargap=0.35,
        **LAYOUT,
    )
    return fig


def capability_histogram(values, result, title: str) -> go.Figure:
    """Histogram of measurements against the specification limits.

    A fitted normal curve is overlaid because the capability indices are built
    on that assumption. Showing the curve against the bars makes it possible to
    judge by eye whether the assumption is reasonable.
    """
    x = np.asarray(values, dtype=float)
    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=x,
            nbinsx=30,
            name="Measurements",
            marker_color=SERIES_COLOUR,
            opacity=0.75,
            histnorm="probability density",
            hovertemplate="%{x}<br>density %{y:.1f}<extra></extra>",
        )
    )

    if result.sigma_overall > 0:
        grid = np.linspace(min(x.min(), result.lsl) - 2 * result.sigma_overall,
                           max(x.max(), result.usl) + 2 * result.sigma_overall, 300)
        density = (1 / (result.sigma_overall * np.sqrt(2 * np.pi))) * np.exp(
            -0.5 * ((grid - result.mean) / result.sigma_overall) ** 2
        )
        fig.add_trace(
            go.Scatter(
                x=grid,
                y=density,
                mode="lines",
                name="Fitted normal curve",
                line=dict(color=CENTRE_COLOUR, width=2, dash="dot"),
                hoverinfo="skip",
            )
        )

    fig.add_vline(x=result.lsl, line_color=SPEC_COLOUR, line_width=1.6,
                  annotation_text=f"LSL {result.lsl:.3f}", annotation_position="top left", annotation_font_size=10)
    fig.add_vline(x=result.usl, line_color=SPEC_COLOUR, line_width=1.6,
                  annotation_text=f"USL {result.usl:.3f}", annotation_position="top right", annotation_font_size=10)
    fig.add_vline(x=result.nominal, line_color=CENTRE_COLOUR, line_dash="dot", line_width=1.3,
                  annotation_text="Nominal", annotation_position="bottom left", annotation_font_size=10)
    fig.add_vline(x=result.mean, line_color=OK_COLOUR, line_dash="dash", line_width=1.6,
                  annotation_text=f"Mean {result.mean:.4f}", annotation_position="bottom right", annotation_font_size=10)

    fig.update_layout(title=title, xaxis_title="Measured value", yaxis_title="Probability density",
                      height=430, showlegend=True, **LAYOUT)
    return fig


def trend_chart(trend: pd.DataFrame, value_col: str, title: str, y_title: str,
                reference_date=None, reference_label: str = "") -> go.Figure:
    """Weekly quality trend line, optionally marked with an event date."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=trend["week"],
            y=trend[value_col],
            mode="lines+markers",
            name=y_title,
            line=dict(color=SERIES_COLOUR, width=2),
            marker=dict(size=5),
            hovertemplate="w/c %{x|%d %b %Y}<br>%{y:.2f}<extra></extra>",
        )
    )
    if reference_date is not None:
        fig.add_vline(
            x=pd.Timestamp(reference_date).to_pydatetime(),
            line_color=SPEC_COLOUR,
            line_dash="dash",
            line_width=1.5,
            annotation_text=reference_label,
            annotation_position="top left",
            annotation_font_size=10,
        )
    fig.update_layout(title=title, xaxis_title="Week commencing", yaxis_title=y_title, height=360, **LAYOUT)
    return fig


def grouped_bar(df: pd.DataFrame, x: str, y: str, title: str, y_title: str, colour: str = SERIES_COLOUR,
                reference: float | None = None, reference_label: str = "") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df[x], y=df[y], marker_color=colour, hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>"))
    if reference is not None:
        fig.add_hline(y=reference, line_dash="dash", line_color=SPEC_COLOUR, line_width=1.3,
                      annotation_text=reference_label, annotation_position="right", annotation_font_size=10)
    fig.update_layout(title=title, yaxis_title=y_title, xaxis_title="", height=380, bargap=0.4, **LAYOUT)
    return fig


def before_after_chart(comparison: pd.DataFrame, value_col: str, title: str, y_title: str) -> go.Figure:
    colours = [SPEC_COLOUR, OK_COLOUR]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=comparison["period"],
            y=comparison[value_col],
            marker_color=colours[: len(comparison)],
            text=[f"{v:,.2f}" for v in comparison[value_col]],
            textposition="outside",
            hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(title=title, yaxis_title=y_title, xaxis_title="", height=350, bargap=0.5,
                      showlegend=False, **LAYOUT)
    return fig


def fishbone_figure(causes: dict, problem: str, confirmed: list) -> go.Figure:
    """Draw an Ishikawa diagram as an annotated figure.

    ``causes`` maps each category to a list of (short_label, full_text) pairs.
    Only the short label is drawn, because a diagram with full sentences on
    every bone becomes unreadable; the full wording is listed beneath the chart
    in the application.

    Confirmed or most likely causes are drawn in red and bold; everything else
    is a potential cause drawn in grey. Keeping that distinction visible matters:
    a fishbone is a structured list of hypotheses, and presenting every branch as
    though it were established fact is how investigations go wrong.
    """
    fig = go.Figure()
    categories = list(causes)

    spine_end = 27.0
    bone_rise = 3.4
    bone_run = 2.2

    fig.add_trace(
        go.Scatter(x=[0, spine_end], y=[0, 0], mode="lines",
                   line=dict(color="#78909c", width=3), hoverinfo="skip", showlegend=False)
    )
    # Arrowhead into the problem statement.
    fig.add_annotation(x=spine_end, y=0, ax=spine_end - 1.6, ay=0, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=2, arrowsize=1.3, arrowwidth=3, arrowcolor="#78909c")
    fig.add_annotation(x=spine_end + 0.5, y=0, text=f"<b>{problem}</b>", showarrow=False,
                       xanchor="left", yanchor="middle", font=dict(size=11, color=SPEC_COLOUR),
                       align="left", width=190)

    top = [c for i, c in enumerate(categories) if i % 2 == 0]
    bottom = [c for i, c in enumerate(categories) if i % 2 == 1]

    for group, direction in ((top, 1), (bottom, -1)):
        # Offset the two rows so the bones interleave rather than line up.
        start = 5.0 if direction > 0 else 9.0
        step = 8.0
        for j, category in enumerate(group):
            base_x = start + j * step
            tip_x = base_x + bone_run
            tip_y = direction * bone_rise

            fig.add_trace(
                go.Scatter(x=[base_x, tip_x], y=[0, tip_y], mode="lines",
                           line=dict(color="#90a4ae", width=2), hoverinfo="skip", showlegend=False)
            )
            fig.add_annotation(
                x=tip_x, y=tip_y + direction * 0.45, text=f"<b>{category}</b>", showarrow=False,
                font=dict(size=12, color="#37474f"), xanchor="center",
            )

            for k, (short, _full) in enumerate(causes[category]):
                is_confirmed = short in confirmed
                cy = direction * (0.95 + 0.95 * k)
                # Sit the label just outboard of the bone at that height.
                cx = base_x + bone_run * (abs(cy) / bone_rise) + 0.3
                fig.add_annotation(
                    x=cx,
                    y=cy,
                    text=f"<b>{short}</b>" if is_confirmed else short,
                    showarrow=False,
                    xanchor="left",
                    yanchor="middle",
                    align="left",
                    font=dict(size=10, color=(SPEC_COLOUR if is_confirmed else "#607d8b")),
                    width=185,
                )

    fig.update_layout(
        template="plotly_white",
        xaxis=dict(visible=False, range=[-0.5, spine_end + 7.0]),
        yaxis=dict(visible=False, range=[-4.9, 4.9]),
        height=540,
        margin=dict(l=10, r=10, t=20, b=20),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
