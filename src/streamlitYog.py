"""
Industry Monitoring Dashboard
=============================

Place this file in the same ``src/`` folder as ``AllCode.py``.
Run from the project root with:

    uv run streamlit run src/stremlit.py

The dashboard keeps data preparation and scoring inside AllCode.py.
It imports the final tables produced there and focuses on presentation,
filtering, comparison and drill-down analysis.
"""

from pathlib import Path
import importlib.util

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# -----------------------------------------------------------------------------
# PAGE SETUP
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Industry Monitoring System",
    page_icon="📊",
    layout="wide",
)

SRC_FOLDER = Path(__file__).resolve().parent
ALL_CODE_PATH = SRC_FOLDER / "AllCode.py"

STATUS_ICON = {
    "Green": "🟢",
    "Amber": "🟠",
    "Red": "🔴",
}

STATUS_COLOR = {
    "Green": "#2E8B57",
    "Amber": "#E69F00",
    "Red": "#D64545",
}

# -----------------------------------------------------------------------------
# LOAD THE EXISTING ANALYSIS ENGINE
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Preparing industry monitoring data...")
def load_analysis_engine():
    """
    Run AllCode.py once and keep its final dataframes in memory.
    """
    if not ALL_CODE_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {ALL_CODE_PATH.name}. Put this Streamlit file in the "
            "same src/ folder as AllCode.py."
        )

    original_plotly_show = pio.show
    pio.show = lambda *args, **kwargs: None

    try:
        spec = importlib.util.spec_from_file_location("industry_analysis_engine", ALL_CODE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        pio.show = original_plotly_show

    return module


try:
    engine = load_analysis_engine()
except Exception as exc:
    st.error("The analysis engine could not be loaded.")
    st.exception(exc)
    st.stop()


# Make copies because Streamlit filters should not modify the original objects.
overall = engine.df_overall_results.copy()
indicators = engine.df_indicator_results.copy()
pillars = engine.df_pillar_results.copy()

TARGET_SECTORS = list(engine.TARGET_SECTORS)
PILLARS = dict(engine.PILLARS)
SCORE_INDICATORS = dict(engine.SCORE_INDICATORS)

# -----------------------------------------------------------------------------
# SMALL HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def status_text(light):
    """Turn 'Green' into '🟢 Green', etc."""
    if pd.isna(light):
        return "⚪ No data"
    return f"{STATUS_ICON.get(light, '⚪')} {light}"


def period_sort_key(period):
    """Sort labels such as '2025 2Q' and '2025' in time order."""
    text = str(period).strip()
    parts = text.split()

    try:
        year = int(parts[0])
    except (ValueError, IndexError):
        return (0, 0, text)

    subperiod = 0
    if len(parts) > 1 and parts[1].endswith("Q"):
        try:
            subperiod = int(parts[1][:-1])
        except ValueError:
            subperiod = 0

    return (year, subperiod, text)


def format_value(value):
    """Readable value for the indicator table."""
    if pd.isna(value):
        return "No data"
    return f"{value:,.2f}"


def get_trend_dataframe(metric_name):
    """Return one long-format dataframe for the selected raw monitoring metric."""
    metric_sources = {
        "Real GDP": engine.df_GDP_Growth_filtered,
        "GDP share of total": engine.df_GDP_Share_filtered,
        "Gross Operating Surplus": engine.df_GrossOperatingSurplusGrowth_filtered,
        "Labour Productivity": engine.df_LabourProductivity_filtered,
        "Equity Ratio": engine.df_EquityRatio_filtered,
        "Business Expectations": engine.df_Business_Expectations_filtered,
    }

    source = metric_sources[metric_name].copy()
    long_df = source.melt(id_vars="Sectors", var_name="Period", value_name="Value")
    long_df = long_df.dropna(subset=["Value"])

    ordered_periods = sorted(long_df["Period"].astype(str).unique(), key=period_sort_key)
    long_df["Period"] = pd.Categorical(
        long_df["Period"].astype(str),
        categories=ordered_periods,
        ordered=True,
    )
    return long_df.sort_values(["Period", "Sectors"])

# -----------------------------------------------------------------------------
# TITLE AND SHORT USER GUIDE
# -----------------------------------------------------------------------------
st.title("📊 Industry Monitoring System")
st.caption(
    "A simple traffic-light dashboard for monitoring industry strength, "
    "deterioration and elevated risk."
)

with st.expander("How to read this dashboard", expanded=False):
    st.markdown(
        """
        - **🟢 Green** = relatively healthy based on the project's scoring rules.
        - **🟠 Amber** = watch closely; some indicators are weaker or mixed.
        - **🔴 Red** = elevated risk based on the project's thresholds.
        - The **overall score** combines the indicators using their assigned weights.
        - Use the **left sidebar** to filter global assessment quarters and indicator drill-downs.
        - Use the **top tabs** to switch between Market Overview and Industry Drill-Downs.
        """
    )

# -----------------------------------------------------------------------------
# SIDEBAR FILTERS (GLOBAL CONTROLS WITH WORKING RESET BUTTON)
# -----------------------------------------------------------------------------
quarter_options = sorted(overall["Quarter"].dropna().astype(str).unique(), key=period_sort_key)
latest_quarter = quarter_options[-1]

# Initialize Session State key directly bound to widget
if "quarter_selector_key" not in st.session_state:
    st.session_state.quarter_selector_key = latest_quarter

def reset_quarter_callback():
    st.session_state.quarter_selector_key = latest_quarter

st.sidebar.header("⚙️ Global Assessment Filters")

selected_quarter = st.sidebar.selectbox(
    "Assessment Quarter",
    quarter_options,
    key="quarter_selector_key",
    help="Select the quarter to evaluate risk across all industries."
)

# Reset Quarter Button using callback
st.sidebar.button(
    "🔄 Reset to Latest Quarter", 
    on_click=reset_quarter_callback,
    help="Reset the Assessment Quarter back to the most recent period."
)

st.sidebar.divider()
st.sidebar.header("🔍 Indicator Drill-Down Filters")

selected_metric = st.sidebar.selectbox(
    "Monitoring Indicator",
    [
        "Real GDP",
        "GDP share of total",
        "Gross Operating Surplus",
        "Labour Productivity",
        "Equity Ratio",
        "Business Expectations",
    ],
    help="Select an indicator to view across all industry drill-down tabs."
)

compared_sectors = st.sidebar.multiselect(
    "Industries to Compare",
    TARGET_SECTORS,
    default=TARGET_SECTORS,
    help="Select which industries to plot in the historical trend chart."
)

st.sidebar.divider()
st.sidebar.caption(
    "Tip: Adjust filters in the sidebar to update cross-industry calculations "
    "and indicator trend charts globally."
)

# -----------------------------------------------------------------------------
# TOP NAVIGATION TABS (ALL SECTORS + INDIVIDUAL INDUSTRIES)
# -----------------------------------------------------------------------------
tab_titles = ["🌐 Overall Market Summary"] + [f"🏢 {sector}" for sector in TARGET_SECTORS]
tabs = st.tabs(tab_titles)

# =============================================================================
# TAB 1: OVERALL MARKET SUMMARY
# =============================================================================
with tabs[0]:
    st.subheader(f"🌐 Overall Market Risk Summary — {selected_quarter}")

    quarter_overall = overall[overall["Quarter"].astype(str) == selected_quarter].copy()

    # KPI Summary Row
    green_count = (quarter_overall["Final light"] == "Green").sum()
    amber_count = (quarter_overall["Final light"] == "Amber").sum()
    red_count = (quarter_overall["Final light"] == "Red").sum()
    avg_score = quarter_overall["Score"].mean()

    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Low Risk Industries (Green)", f"{green_count} / {len(TARGET_SECTORS)}")
    kpi_cols[1].metric("Moderate Risk (Amber)", f"{amber_count} / {len(TARGET_SECTORS)}")
    kpi_cols[2].metric("High Risk (Red)", f"{red_count} / {len(TARGET_SECTORS)}")
    kpi_cols[3].metric("Average Market Score", f"{avg_score:.1f} / 100" if pd.notna(avg_score) else "No data")

    st.divider()

    # Main Visualizations Row
    col_chart1, col_chart2 = st.columns([1, 1])

    with col_chart1:
        st.markdown("#### 📊 Industry Risk Score Ranking")
        snapshot_df = quarter_overall.sort_values("Score", ascending=True)

        fig_scores = px.bar(
            snapshot_df,
            x="Score",
            y="Sectors",
            orientation="h",
            color="Final light",
            color_discrete_map=STATUS_COLOR,
            range_x=[0, 100],
            text="Score",
            labels={"Sectors": "Industry", "Score": "Overall Score", "Final light": "Status"},
        )
        fig_scores.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig_scores.update_layout(
            template="plotly_white",
            legend_title="Status",
            margin=dict(l=10, r=30, t=20, b=10),
        )
        st.plotly_chart(fig_scores, width="stretch", key="overall_scores_bar")

    with col_chart2:
        st.markdown("#### 📈 Multi-Sector Historical Score Trajectory")
        all_history = overall.copy()
        all_history["Quarter"] = all_history["Quarter"].astype(str)
        all_history = all_history.sort_values("Quarter", key=lambda s: s.map(period_sort_key))

        fig_history = px.line(
            all_history,
            x="Quarter",
            y="Score",
            color="Sectors",
            markers=True,
            color_discrete_map=engine.SECTOR_COLORS,
            labels={"Sectors": "Industry", "Score": "Score (0–100)"},
        )
        fig_history.add_hrect(y0=75, y1=100, opacity=0.06, line_width=0, fillcolor="green")
        fig_history.add_hrect(y0=40, y1=75, opacity=0.04, line_width=0, fillcolor="orange")
        fig_history.add_hrect(y0=0, y1=40, opacity=0.03, line_width=0, fillcolor="red")
        fig_history.update_layout(
            template="plotly_white",
            hovermode="x unified",
            yaxis_range=[0, 100],
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig_history, width="stretch", key="overall_history_line")

    st.divider()

    # Detailed Table & Alerts
    st.markdown("#### 📋 Cross-Industry Status Matrix")

    summary_table = quarter_overall[
        ["Sectors", "Score", "Final light", "Red indicators", "Warning", "Data coverage %"]
    ].copy()

    summary_table["Status"] = summary_table["Final light"].apply(status_text)
    summary_table = summary_table.rename(
        columns={
            "Sectors": "Industry",
            "Score": "Overall Score",
            "Red indicators": "Red Indicators",
            "Warning": "Active Warnings / Overrides",
            "Data coverage %": "Coverage %",
        }
    )

    summary_table = summary_table.sort_values("Overall Score", ascending=False)

    st.dataframe(
        summary_table[["Industry", "Overall Score", "Status", "Red Indicators", "Active Warnings / Overrides", "Coverage %"]],
        hide_index=True,
        width="stretch",
        column_config={
            "Overall Score": st.column_config.NumberColumn(format="%.1f"),
            "Coverage %": st.column_config.NumberColumn(format="%.0f%%"),
        },
    )

# =============================================================================
# TABS 2+: INDIVIDUAL SECTOR DRILL-DOWNS
# =============================================================================
for tab, selected_sector in zip(tabs[1:], TARGET_SECTORS):
    with tab:
        selected_overall = overall[
            (overall["Sectors"] == selected_sector)
            & (overall["Quarter"].astype(str) == selected_quarter)
        ]

        if selected_overall.empty:
            st.warning(f"No overall assessment is available for {selected_sector} in {selected_quarter}.")
            continue

        selected_overall_row = selected_overall.iloc[0]
        selected_light = selected_overall_row["Final light"]
        selected_score = selected_overall_row["Score"]
        selected_coverage = selected_overall_row["Data coverage %"]
        selected_reds = int(selected_overall_row["Red indicators"])
        selected_warning = selected_overall_row["Warning"]

        st.subheader(f"{selected_sector} — {selected_quarter} Assessment")

        kpi_cols = st.columns(4)
        kpi_cols[0].metric("Overall Status", status_text(selected_light))
        kpi_cols[1].metric(
            "Industry Score",
            "No data" if pd.isna(selected_score) else f"{selected_score:.1f} / 100",
        )
        kpi_cols[2].metric("Red Indicators", f"{selected_reds}")
        kpi_cols[3].metric("Data Coverage", f"{selected_coverage:.0f}%")

        if isinstance(selected_warning, str) and selected_warning.strip():
            st.warning(selected_warning)
        elif selected_light == "Red":
            st.error(f"{selected_sector} is currently classified as RED (Elevated Risk).")
        elif selected_light == "Amber":
            st.info(f"{selected_sector} is currently AMBER and requires monitoring.")
        else:
            st.success(f"{selected_sector} is currently GREEN under scoring rules.")

        st.divider()

        # SCORE HISTORY & PILLAR BREAKDOWN
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("#### 📈 Score History")
            st.caption("Historical performance trajectory over time.")

            history = overall[overall["Sectors"] == selected_sector].copy()
            history["Quarter"] = history["Quarter"].astype(str)
            history = history.sort_values("Quarter", key=lambda s: s.map(period_sort_key))

            history_fig = go.Figure()
            history_fig.add_trace(
                go.Scatter(
                    x=history["Quarter"],
                    y=history["Score"],
                    mode="lines+markers",
                    name="Overall score",
                    line=dict(width=3, color=STATUS_COLOR.get(selected_light, "#2a78d6")),
                    marker=dict(size=8),
                    customdata=history[["Final light", "Data coverage %"]],
                    hovertemplate=(
                        "<b>%{x}</b><br>Score: %{y:.1f}<br>"
                        "Status: %{customdata[0]}<br>Coverage: %{customdata[1]:.0f}%<extra></extra>"
                    ),
                )
            )
            history_fig.add_hrect(y0=75, y1=100, opacity=0.08, line_width=0, fillcolor="green")
            history_fig.add_hrect(y0=40, y1=75, opacity=0.05, line_width=0, fillcolor="orange")
            history_fig.add_hrect(y0=0, y1=40, opacity=0.04, line_width=0, fillcolor="red")
            history_fig.add_hline(y=75, line_dash="dash", annotation_text="Green (75+)")
            history_fig.add_hline(y=40, line_dash="dash", annotation_text="Amber (40+)")
            history_fig.update_layout(
                template="plotly_white",
                yaxis_title="Score (0–100)",
                xaxis_title="Quarter",
                yaxis_range=[0, 100],
                showlegend=False,
                margin=dict(l=10, r=10, t=20, b=10),
            )
            st.plotly_chart(history_fig, width="stretch", key=f"score_history_{selected_sector}")

        with col_right:
            st.markdown("#### 🛡️ Risk Pillars Breakdown")
            st.caption("Pillar performance breakdown for this industry.")

            selected_pillars = pillars[
                (pillars["Sectors"] == selected_sector)
                & (pillars["Quarter"].astype(str) == selected_quarter)
            ].copy()

            pillar_fig = px.bar(
                selected_pillars,
                x="Pillar name",
                y="Score",
                color="Light",
                color_discrete_map=STATUS_COLOR,
                range_y=[0, 100],
                text="Score",
                labels={"Pillar name": "Risk Pillar", "Score": "Score", "Light": "Status"},
            )
            pillar_fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            pillar_fig.update_layout(template="plotly_white", legend_title="Status", margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(pillar_fig, width="stretch", key=f"pillar_breakdown_{selected_sector}")

        st.divider()

        # INDICATOR SCORECARD TABLE
        st.markdown("### 📋 Indicator Scorecard")
        st.caption("Detailed view of raw values, traffic lights, and assigned weights.")

        selected_indicator_rows = indicators[
            (indicators["Sectors"] == selected_sector)
            & (indicators["Quarter"].astype(str) == selected_quarter)
        ].copy()

        selected_indicator_rows["Status"] = selected_indicator_rows["Light"].apply(status_text)
        selected_indicator_rows["Value shown"] = selected_indicator_rows["Value"].apply(format_value)

        indicator_table = selected_indicator_rows[
            ["Pillar", "Label", "Value shown", "Value period", "Status", "Weight", "Points"]
        ].rename(
            columns={
                "Pillar": "Pillar",
                "Label": "Indicator",
                "Value shown": "Raw Value",
                "Value period": "Data Period",
                "Weight": "Weight %",
                "Points": "Points Earned",
            }
        )

        st.dataframe(
            indicator_table,
            hide_index=True,
            width="stretch",
            column_config={
                "Weight %": st.column_config.NumberColumn(format="%.0f%%"),
                "Points Earned": st.column_config.NumberColumn(format="%.1f"),
            },
        )

        st.divider()

        # FULL-WIDTH HISTORICAL INDICATOR DRILL-DOWN (SIDEBAR CONTROLLED)
        st.markdown(f"### 🔍 Historical Indicator Drill-Down: {selected_metric}")
        st.caption("Controlled globally from the left-hand sidebar.")

        if not compared_sectors:
            st.info("Select at least one industry in the sidebar to display the trend.")
        else:
            trend_df = get_trend_dataframe(selected_metric)
            trend_df = trend_df[trend_df["Sectors"].isin(compared_sectors)]

            trend_fig = px.line(
                trend_df,
                x="Period",
                y="Value",
                color="Sectors",
                markers=True,
                color_discrete_map=engine.SECTOR_COLORS,
                title=f"{selected_metric} Historical Trend",
                labels={"Sectors": "Industry", "Value": selected_metric},
            )
            trend_fig.update_layout(
                template="plotly_white",
                hovermode="x unified",
                legend_title="Industry",
                margin=dict(l=10, r=10, t=40, b=10),
            )
            st.plotly_chart(trend_fig, width="stretch", key=f"indicator_trend_{selected_sector}")

# -----------------------------------------------------------------------------
# METHODOLOGY & TECHNICAL DATA EXPANDERS
# -----------------------------------------------------------------------------
with st.expander("📖 Scoring Methodology & Thresholds", expanded=False):
    st.markdown(
        """
        **Overall Score Bands**
        - Green: Score **≥ 75**
        - Amber: Score **40 to < 75**
        - Red: Score **< 40**

        **Indicator Points**
        - Green earns **100%** of that indicator's weight.
        - Amber earns **50%** of that indicator's weight.
        - Red earns **0%** of that indicator's weight.

        **Override Rule**
        - If an industry would otherwise be Green but has **2 or more Red indicators**, the final status is capped at Amber.
        - If it has **1 Red indicator**, it can remain Green but a warning is shown.
        """
    )

    methodology_rows = []
    for indicator_name, settings in SCORE_INDICATORS.items():
        row = {
            "Indicator": settings["label"],
            "Pillar": PILLARS[settings["pillar"]],
            "Weight %": settings["weight"],
            "Calculation": settings["calculation"],
        }

        if settings["calculation"] == "esg":
            row["Green"] = "Low ESG risk"
            row["Amber"] = "Medium ESG risk"
            row["Red"] = "High ESG risk"
        else:
            green_symbol = "≥" if settings.get("green_includes_limit", False) else ">"
            row["Green"] = f"{green_symbol} {settings['green_from']}"
            row["Amber"] = f"≥ {settings['amber_from']} and below Green"
            row["Red"] = f"< {settings['amber_from']}"

        methodology_rows.append(row)

    methodology_df = pd.DataFrame(methodology_rows)
    st.dataframe(methodology_df, hide_index=True, width="stretch")

with st.expander("🛠️ Technical Data View", expanded=False):
    st.write("Overall Result Table")
    st.dataframe(overall, width="stretch")

    st.write("Indicator Results Table")
    st.dataframe(indicators, width="stretch")

    st.write("Pillar Results Table")
    st.dataframe(pillars, width="stretch")