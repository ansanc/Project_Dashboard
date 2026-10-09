# %%
"""
Industry Monitoring Dashboard
=============================

Place this file in the same ``src/`` folder as ``AllCode.py``.
Run from the project root with:

    uv run streamlit run src/industry_monitoring_streamlit.py

The dashboard deliberately keeps data preparation and scoring inside AllCode.py.
It imports the final tables produced there and focuses only on presentation,
filtering, comparison and drill-down analysis.
"""

from pathlib import Path
import importlib.util

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# %%
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

# %%
# -----------------------------------------------------------------------------
# LOAD THE EXISTING ANALYSIS ENGINE
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Preparing industry monitoring data...")
def load_analysis_engine():
    """
    Run AllCode.py once and keep its final dataframes in memory.

    AllCode.py currently calls Plotly ``.show(renderer='browser')``. That is useful
    in a notebook/script, but not inside Streamlit, so browser display is disabled
    only while the file is being imported. The HTML-writing logic in AllCode.py is
    left unchanged.
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

# %%
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


def light_background(value):
    """Simple background colors for traffic-light cells in a dataframe."""
    if value == "Green":
        return "background-color: #DFF3E5; color: #175C34; font-weight: 600"
    if value == "Amber":
        return "background-color: #FFF0CC; color: #7A5200; font-weight: 600"
    if value == "Red":
        return "background-color: #FADDDD; color: #8D2222; font-weight: 600"
    return ""


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

# %%
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
        - Use the sidebar to change the **industry** and **quarter**.
        - The lower sections explain **why** an industry received its status.
        """
    )

# %%
# -----------------------------------------------------------------------------
# SIDEBAR FILTERS
# -----------------------------------------------------------------------------
quarter_options = sorted(overall["Quarter"].dropna().astype(str).unique(), key=period_sort_key)

st.sidebar.header("Dashboard filters")
selected_sector = st.sidebar.selectbox(
    "Industry sector",
    TARGET_SECTORS,
    index=0,
)

selected_quarter = st.sidebar.selectbox(
    "Assessment quarter",
    quarter_options,
    index=len(quarter_options) - 1,
)

st.sidebar.divider()
st.sidebar.caption(
    "Tip: start from the latest quarter, then move to the score history and "
    "indicator drill-down if you want to understand what changed."
)

# %%
# -----------------------------------------------------------------------------
# SELECTED SECTOR + QUARTER OVERVIEW
# -----------------------------------------------------------------------------
selected_overall = overall[
    (overall["Sectors"] == selected_sector)
    & (overall["Quarter"].astype(str) == selected_quarter)
]

if selected_overall.empty:
    st.warning("No overall assessment is available for this sector and quarter.")
    st.stop()

selected_overall_row = selected_overall.iloc[0]
selected_light = selected_overall_row["Final light"]
selected_score = selected_overall_row["Score"]
selected_coverage = selected_overall_row["Data coverage %"]
selected_reds = int(selected_overall_row["Red indicators"])
selected_warning = selected_overall_row["Warning"]

st.subheader(f"{selected_sector} — {selected_quarter}")

kpi_cols = st.columns(4)
kpi_cols[0].metric("Overall status", status_text(selected_light))
kpi_cols[1].metric(
    "Industry score",
    "No data" if pd.isna(selected_score) else f"{selected_score:.1f} / 100",
)
kpi_cols[2].metric("Red indicators", f"{selected_reds}")
kpi_cols[3].metric("Data coverage", f"{selected_coverage:.0f}%")

if isinstance(selected_warning, str) and selected_warning.strip():
    st.warning(selected_warning)
elif selected_light == "Red":
    st.error("The selected industry is currently classified as Red.")
elif selected_light == "Amber":
    st.info("The selected industry is currently Amber and should be monitored closely.")
else:
    st.success("The selected industry is currently Green under the project's scoring rules.")

# %%
# -----------------------------------------------------------------------------
# MARKET / INDUSTRY SNAPSHOT FOR THE SELECTED QUARTER
# -----------------------------------------------------------------------------
st.subheader("Industry snapshot")
st.caption("Compare all monitored sectors for the same assessment quarter.")

snapshot = overall[overall["Quarter"].astype(str) == selected_quarter][
    ["Sectors", "Score", "Final light", "Red indicators", "Data coverage %"]
].copy()

snapshot = snapshot.rename(
    columns={
        "Sectors": "Industry",
        "Score": "Score",
        "Final light": "Status",
        "Red indicators": "Red indicators",
        "Data coverage %": "Coverage %",
    }
)

snapshot["Status display"] = snapshot["Status"].apply(status_text)
snapshot = snapshot.sort_values("Score", ascending=False, na_position="last")

chart_snapshot = snapshot.dropna(subset=["Score"]).copy()
if not chart_snapshot.empty:
    snapshot_fig = px.bar(
        chart_snapshot,
        x="Score",
        y="Industry",
        orientation="h",
        color="Status",
        color_discrete_map=STATUS_COLOR,
        range_x=[0, 100],
        text="Score",
        title=f"Overall industry scores — {selected_quarter}",
    )
    snapshot_fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    snapshot_fig.update_layout(
        template="plotly_white",
        legend_title="Status",
        yaxis={"categoryorder": "total ascending"},
        margin=dict(l=10, r=40, t=55, b=10),
    )
    st.plotly_chart(snapshot_fig, width="stretch")

st.dataframe(
    snapshot[["Industry", "Score", "Status display", "Red indicators", "Coverage %"]],
    hide_index=True,
    width="stretch",
)

# %%
# -----------------------------------------------------------------------------
# SCORE HISTORY
# -----------------------------------------------------------------------------
st.subheader("Score history")
st.caption("See whether the selected industry is improving, stable or deteriorating over time.")

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
        line=dict(width=3),
        marker=dict(size=8),
        customdata=history[["Final light", "Data coverage %"]],
        hovertemplate=(
            "<b>%{x}</b><br>Score: %{y:.1f}<br>"
            "Status: %{customdata[0]}<br>Coverage: %{customdata[1]:.0f}%<extra></extra>"
        ),
    )
)
history_fig.add_hrect(y0=75, y1=100, opacity=0.08, line_width=0)
history_fig.add_hrect(y0=40, y1=75, opacity=0.05, line_width=0)
history_fig.add_hrect(y0=0, y1=40, opacity=0.04, line_width=0)
history_fig.add_hline(y=75, line_dash="dash", annotation_text="Green threshold: 75")
history_fig.add_hline(y=40, line_dash="dash", annotation_text="Amber threshold: 40")
history_fig.update_layout(
    template="plotly_white",
    yaxis_title="Score (0–100)",
    xaxis_title="Quarter",
    yaxis_range=[0, 100],
    showlegend=False,
    margin=dict(l=10, r=10, t=20, b=10),
)
st.plotly_chart(history_fig, width="stretch")

# %%
# -----------------------------------------------------------------------------
# WHY DID THE SECTOR RECEIVE THIS SCORE?
# -----------------------------------------------------------------------------
st.subheader("What is driving the score?")
st.caption("This is the fastest way to see which indicators are helping or hurting the industry.")

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
        "Value shown": "Value",
        "Value period": "Data period",
        "Weight": "Weight %",
        "Points": "Points earned",
    }
)

st.dataframe(
    indicator_table,
    hide_index=True,
    width="stretch",
    column_config={
        "Weight %": st.column_config.NumberColumn(format="%.0f"),
        "Points earned": st.column_config.NumberColumn(format="%.1f"),
    },
)

# %%
# -----------------------------------------------------------------------------
# PILLAR VIEW
# -----------------------------------------------------------------------------
st.subheader("Risk pillars")
selected_pillars = pillars[
    (pillars["Sectors"] == selected_sector)
    & (pillars["Quarter"].astype(str) == selected_quarter)
].copy()

selected_pillars["Status display"] = selected_pillars["Light"].apply(status_text)

pillar_fig = px.bar(
    selected_pillars,
    x="Pillar name",
    y="Score",
    color="Light",
    color_discrete_map=STATUS_COLOR,
    range_y=[0, 100],
    text="Score",
    title="Pillar scores",
    labels={"Pillar name": "Risk pillar", "Score": "Score", "Light": "Status"},
)
pillar_fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
pillar_fig.update_layout(template="plotly_white", legend_title="Status")
st.plotly_chart(pillar_fig, width="stretch")

pillar_table = selected_pillars[
    ["Pillar name", "Score", "Status display", "Data coverage %"]
].rename(
    columns={
        "Pillar name": "Pillar",
        "Status display": "Status",
        "Data coverage %": "Coverage %",
    }
)
st.dataframe(pillar_table, hide_index=True, width="stretch")

# %%
# -----------------------------------------------------------------------------
# RAW INDICATOR DRILL-DOWN
# -----------------------------------------------------------------------------
st.subheader("Indicator drill-down")
st.caption(
    "Explore the underlying monitoring data. Business Expectations is included here "
    "for context even though it is not currently part of the final score."
)

trend_col1, trend_col2 = st.columns([1, 2])

with trend_col1:
    selected_metric = st.selectbox(
        "Monitoring indicator",
        [
            "Real GDP",
            "GDP share of total",
            "Gross Operating Surplus",
            "Labour Productivity",
            "Equity Ratio",
            "Business Expectations",
        ],
    )

    compared_sectors = st.multiselect(
        "Industries to compare",
        TARGET_SECTORS,
        default=[selected_sector],
    )

with trend_col2:
    if not compared_sectors:
        st.info("Select at least one industry to display the trend.")
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
            title=f"{selected_metric} trend",
            labels={"Sectors": "Industry", "Value": selected_metric},
        )
        trend_fig.update_layout(
            template="plotly_white",
            hovermode="x unified",
            legend_title="Industry",
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(trend_fig, width="stretch")

# %%
# -----------------------------------------------------------------------------
# SCORING METHODOLOGY - TRANSPARENT BUT KEPT OUT OF THE MAIN VIEW
# -----------------------------------------------------------------------------
with st.expander("Scoring methodology and thresholds", expanded=False):
    st.markdown(
        """
        **Overall score bands**
        - Green: score **≥ 75**
        - Amber: score **40 to < 75**
        - Red: score **< 40**

        **Indicator points**
        - Green earns **100%** of that indicator's weight.
        - Amber earns **50%** of that indicator's weight.
        - Red earns **0%** of that indicator's weight.

        **Override rule**
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

    st.caption(
        "Important: when some indicator data is missing, the current scoring code "
        "rescales the points using only indicators with available data. Always read "
        "the Data coverage % together with the score."
    )

# %%
# -----------------------------------------------------------------------------
# OPTIONAL TECHNICAL VIEW FOR TEAM / MARKING
# -----------------------------------------------------------------------------
with st.expander("Technical data view", expanded=False):
    st.write("Overall result rows")
    st.dataframe(overall, width="stretch")

    st.write("Indicator result rows")
    st.dataframe(indicators, width="stretch")

    st.write("Pillar result rows")
    st.dataframe(pillars, width="stretch")
