# charts.py — PamojaData Visualization Engine
# All charts and visual components used across the platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import io


# ── COLOUR PALETTE ────────────────────────────────────────────────────────────
COLORS = {
    'primary': '#1A3C5E',
    'secondary': '#2E6DA4',
    'accent': '#1A8A7A',
    'met': '#2ECC71',
    'on_track': '#F39C12',
    'off_track': '#E74C3C',
    'background': '#F4F6F9',
    'white': '#FFFFFF'
}


def status_color(status):
    if 'Met' in status or 'Exceeded' in status:
        return COLORS['met']
    elif 'On Track' in status:
        return COLORS['on_track']
    else:
        return COLORS['off_track']


# ── SECTOR PERFORMANCE BAR CHART ──────────────────────────────────────────────
def sector_bar_chart(sector_summary, sector_col):
    """
    Interactive Plotly bar chart showing sector performance.
    """
    colors = [
        COLORS['met'] if v >= 100
        else COLORS['on_track'] if v >= 80
        else COLORS['off_track']
        for v in sector_summary['% Achievement']
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=sector_summary[sector_col],
        y=sector_summary['% Achievement'],
        marker_color=colors,
        text=[f"{v:.1f}%" for v in sector_summary['% Achievement']],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Achievement: %{y:.1f}%<extra></extra>'
    ))

    fig.add_hline(y=100, line_dash="dash", line_color=COLORS['primary'],
                  annotation_text="100% Target", annotation_position="right")
    fig.add_hline(y=80, line_dash="dot", line_color=COLORS['on_track'],
                  annotation_text="80% Threshold", annotation_position="right")

    fig.update_layout(
        title=dict(text='Sector Performance Overview', font=dict(size=16, color=COLORS['primary'])),
        xaxis_title='Sector',
        yaxis_title='% Achievement',
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['white'],
        yaxis=dict(range=[0, max(sector_summary['% Achievement'].max() + 20, 120)]),
        showlegend=False,
        height=400
    )
    return fig


# ── TREND LINE CHART ──────────────────────────────────────────────────────────
def trend_line_chart(trend_df, period_col, sector_col):
    """
    Interactive multi-line chart showing achievement trends across periods.
    """
    fig = px.line(
        trend_df,
        x=period_col,
        y='% Achievement',
        color=sector_col,
        markers=True,
        title='Achievement Trends by Sector',
        labels={'% Achievement': '% Achievement', period_col: 'Reporting Period'}
    )

    fig.add_hline(y=100, line_dash="dash", line_color=COLORS['primary'],
                  annotation_text="100% Target")
    fig.add_hline(y=80, line_dash="dot", line_color=COLORS['on_track'],
                  annotation_text="80% Threshold")

    fig.update_layout(
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['white'],
        height=400,
        legend=dict(orientation='h', yanchor='bottom', y=1.02)
    )
    return fig


# ── INDICATOR STATUS DONUT CHART ──────────────────────────────────────────────
def status_donut_chart(overall_summary):
    """
    Donut chart showing proportion of indicators by status.
    """
    labels = ['Met/Exceeded', 'On Track', 'Off Track']
    values = [
        overall_summary['met'],
        overall_summary['on_track'],
        overall_summary['off_track']
    ]
    colors = [COLORS['met'], COLORS['on_track'], COLORS['off_track']]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker_colors=colors,
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>'
    )])

    fig.update_layout(
        title=dict(text='Indicator Status Distribution',
                   font=dict(size=16, color=COLORS['primary'])),
        annotations=[dict(
            text=f"{overall_summary['overall_achievement']}%",
            x=0.5, y=0.5,
            font=dict(size=22, color=COLORS['primary'], family='Arial Black'),
            showarrow=False
        )],
        showlegend=True,
        height=350,
        paper_bgcolor=COLORS['white']
    )
    return fig


# ── GEOGRAPHIC PERFORMANCE MAP (SIMPLE BAR) ───────────────────────────────────
def location_bar_chart(location_df, location_col):
    """
    Horizontal bar chart showing performance by location/region.
    """
    location_df = location_df.sort_values('% Achievement', ascending=True)
    colors = [
        COLORS['met'] if v >= 100
        else COLORS['on_track'] if v >= 80
        else COLORS['off_track']
        for v in location_df['% Achievement']
    ]

    fig = go.Figure(go.Bar(
        x=location_df['% Achievement'],
        y=location_df[location_col],
        orientation='h',
        marker_color=colors,
        text=[f"{v:.1f}%" for v in location_df['% Achievement']],
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Achievement: %{x:.1f}%<extra></extra>'
    ))

    fig.add_vline(x=100, line_dash="dash", line_color=COLORS['primary'])
    fig.add_vline(x=80, line_dash="dot", line_color=COLORS['on_track'])

    fig.update_layout(
        title=dict(text='Performance by Region/Location',
                   font=dict(size=16, color=COLORS['primary'])),
        xaxis_title='% Achievement',
        yaxis_title='Location',
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['white'],
        height=max(300, len(location_df) * 50),
        showlegend=False
    )
    return fig


# ── RISK GAUGE CHART ──────────────────────────────────────────────────────────
def risk_gauge(risk_summary):
    """
    Gauge chart showing overall programme risk level.
    """
    total = risk_summary['total']
    high_pct = (risk_summary['high_risk'] / total * 100) if total > 0 else 0

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=high_pct,
        title={'text': "High Risk Indicators %", 'font': {'size': 14}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': COLORS['off_track']},
            'steps': [
                {'range': [0, 30], 'color': COLORS['met']},
                {'range': [30, 60], 'color': COLORS['on_track']},
                {'range': [60, 100], 'color': '#FADBD8'}
            ],
            'threshold': {
                'line': {'color': COLORS['primary'], 'width': 3},
                'thickness': 0.75,
                'value': 30
            }
        }
    ))

    fig.update_layout(
        height=280,
        paper_bgcolor=COLORS['white']
    )
    return fig


# ── FEATURE IMPORTANCE CHART ──────────────────────────────────────────────────
def feature_importance_chart(importance_df):
    """
    Horizontal bar chart showing ML model feature importance.
    """
    fig = px.bar(
        importance_df,
        x='Importance',
        y='Feature',
        orientation='h',
        title='What Drives Indicator Risk? (ML Insights)',
        color='Importance',
        color_continuous_scale=['#A8D5E2', '#1A3C5E']
    )

    fig.update_layout(
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['white'],
        height=300,
        showlegend=False
    )
    return fig


# ── STATIC MATPLOTLIB CHART FOR WORD EXPORT ───────────────────────────────────
def sector_chart_for_export(sector_summary, sector_col):
    """
    Static Matplotlib chart saved to buffer for Word document export.
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(COLORS['background'])
    ax.set_facecolor(COLORS['background'])

    sectors = sector_summary[sector_col]
    achievements = sector_summary['% Achievement']
    colors = [
        COLORS['met'] if v >= 100
        else COLORS['on_track'] if v >= 80
        else COLORS['off_track']
        for v in achievements
    ]

    bars = ax.bar(sectors, achievements, color=colors, width=0.5,
                  edgecolor='white', linewidth=1.5)

    ax.axhline(y=100, color=COLORS['primary'], linestyle='--',
               linewidth=1.2, alpha=0.7, label='100% Target')
    ax.axhline(y=80, color=COLORS['on_track'], linestyle=':',
               linewidth=1.2, alpha=0.7, label='80% Threshold')

    for bar, val in zip(bars, achievements):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1.5,
                f'{val:.1f}%', ha='center', va='bottom',
                fontsize=10, fontweight='bold', color=COLORS['primary'])

    ax.set_ylim(0, max(achievements.max() + 20, 120))
    ax.set_xlabel('Programme Sector', fontsize=11, color=COLORS['primary'])
    ax.set_ylabel('% Achievement', fontsize=11, color=COLORS['primary'])
    ax.set_title('Sector Performance Overview', fontsize=14,
                 fontweight='bold', color=COLORS['primary'], pad=15)

    legend_patches = [
        mpatches.Patch(color=COLORS['met'], label='Met/Exceeded (≥100%)'),
        mpatches.Patch(color=COLORS['on_track'], label='On Track (80-99%)'),
        mpatches.Patch(color=COLORS['off_track'], label='Off Track (<80%)')
    ]
    ax.legend(handles=legend_patches, loc='upper right', fontsize=9)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf