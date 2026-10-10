
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

import os
from pathlib import Path
import importlib.util

from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Load environment variables from .env file
load_dotenv()

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
# OPENROUTER AI CLIENT SETUP & HELPER FUNCTION
# -----------------------------------------------------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

@st.cache_data(show_spinner=False)
def generate_ai_sector_commentary(sector_name, quarter, score, status, red_count, warning_text, indicator_data_dict):
    """
    Call OpenRouter API to generate an executive risk analyst commentary for a specific sector.
    Cached per sector, quarter, and score state to minimize unnecessary API calls.
    """
    if not OPENROUTER_API_KEY:
        return "⚠️ OpenRouter API Key not found. Please set `OPENROUTER_API_KEY` in your `.env` file to enable AI Commentary."

    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )

        indicators_summary = "\n".join([f"- {k}: {v}" for k, v in indicator_data_dict.items()])

        prompt = f"""
You are an expert actuarial and financial risk analyst evaluating industry sector health in Singapore.
Provide a concise executive commentary for the following industry assessment:

- Sector: {sector_name}
- Assessment Quarter: {quarter}
- Overall Risk Score: {score:.1f} / 100
- Traffic-Light Status: {status}
- Number of Red Indicators: {red_count}
- Safety Warnings/Overrides: {warning_text if warning_text else 'None'}

Key Indicator Results:
{indicators_summary}

Please provide a professional 3-paragraph assessment:
1. Key Strengths & Vulnerabilities: Briefly analyze what driven this score and status.
2. Outlook & Risk Commentary: Highlight key macro or financial risks based on the indicator traffic lights.
3. Recommended Action Items: Concise, actionable recommendations for industry stakeholders/risk managers.

Keep the tone concise, professional, and directly actionable.
"""

        response = client.chat.completions.create(
            model="nvidia/nemotron-3-ultra-550b-a55b:free", # You can also use openai/gpt-4o-mini or meta-llama/llama-3.1-80b-instruct
            messages=[
                {"role": "system", "content": "You are a senior financial risk analyst producing executive reports."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=5000,
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ Unable to generate AI commentary: {str(e)}"

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
        "GDP Share": engine.df_GDP_Share_filtered,
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
# SIDEBAR FILTERS
# -----------------------------------------------------------------------------
quarter_options = sorted(overall["Quarter"].dropna().astype(str).unique(), key=period_sort_key)
latest_quarter = quarter_options[-1]

if "quarter_selector_key" not in st.session_state:
    st.session_state.quarter_selector_key = latest_quarter

def reset_quarter_callback():
    st.session_state.quarter_selector_key = latest_quarter

st.sidebar.header("⚙️ Dashboard Controls")

with st.sidebar.expander("📅 Assessment Quarter Filter", expanded=True):
    selected_quarter = st.sidebar.selectbox(
        "Assessment Quarter",
        quarter_options,
        key="quarter_selector_key",
        help="Select the quarter to evaluate risk across all industries."
    )

    st.sidebar.button(
        "🔄 Reset to Latest Quarter", 
        on_click=reset_quarter_callback,
        help="Reset the Assessment Quarter back to the most recent period."
    )

st.sidebar.caption(
    "Tip: Select an Assessment Quarter to update market risk scores and indicators."
)

# Initialize Session State for Active View Page
if "active_sector_detail" not in st.session_state:
    st.session_state.active_sector_detail = None

# =============================================================================
# VIEW 1: FULL-PAGE SECTOR DETAIL PAGE (SHOWS WHEN A SECTOR BUTTON IS CLICKED)
# =============================================================================
if st.session_state.active_sector_detail:
    selected_sector = st.session_state.active_sector_detail

    # Header and Navigation Bar
    col_nav_title, col_nav_btn = st.columns([4, 1])
    with col_nav_title:
        st.title(f"🏢 Sector Analysis: {selected_sector}")
        st.caption(f"Comprehensive risk drill-down and indicator performance evaluation for {selected_quarter}.")
    with col_nav_btn:
        st.write("") # Padding
        if st.button("⬅️ Back to Market Overview", type="primary", key="btn_back_main"):
            st.session_state.active_sector_detail = None
            st.rerun()

    st.divider()

    selected_overall = overall[
        (overall["Sectors"] == selected_sector)
        & (overall["Quarter"].astype(str) == selected_quarter)
    ]

    if selected_overall.empty:
        st.warning(f"No overall assessment data available for {selected_sector} in {selected_quarter}.")
    else:
        selected_overall_row = selected_overall.iloc[0]
        selected_light = selected_overall_row["Final light"]
        selected_score = selected_overall_row["Score"]
        selected_coverage = selected_overall_row["Data coverage %"]
        selected_reds = int(selected_overall_row["Red indicators"])
        selected_warning = selected_overall_row["Warning"]

        # ---------------------------------------------------------------------
        # SECTION 1: OVERALL STATUS, INDUSTRY SCORE, RED INDICATOR, DATA COVERAGE
        # ---------------------------------------------------------------------
        st.markdown("### 1️⃣ Sector KPI Summary")
        sec_kpi = st.columns(4)
        sec_kpi[0].metric("Overall Status", status_text(selected_light))
        sec_kpi[1].metric("Industry Score", f"{selected_score:.1f} / 100" if pd.notna(selected_score) else "No data")
        sec_kpi[2].metric("Red Indicators", f"{selected_reds}")
        sec_kpi[3].metric("Data Coverage", f"{selected_coverage:.0f}%")

        if isinstance(selected_warning, str) and selected_warning.strip():
            st.warning(selected_warning)

        st.divider()

        # ---------------------------------------------------------------------
        # SECTION 2: INDICATOR SCORECARD
        # ---------------------------------------------------------------------
        st.markdown("### 2️⃣ Indicator Scorecard")
        st.caption("Detailed breakdown of raw values, traffic lights, assigned weights, and points earned.")

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

        # ---------------------------------------------------------------------
        # SECTION 3: SCORE HISTORY / SCORE TRAJECTORY
        # ---------------------------------------------------------------------
        st.markdown("### 3️⃣ Score History & Trajectory")
        st.caption("Overall historical risk score trajectory over time.")

        history = overall[overall["Sectors"] == selected_sector].copy()
        history["Quarter"] = history["Quarter"].astype(str)
        history = history.sort_values("Quarter", key=lambda s: s.map(period_sort_key))

        history_fig = go.Figure()
        history_fig.add_trace(
            go.Scatter(
                x=history["Quarter"],
                y=history["Score"],
                mode="lines+markers",
                name="Overall Score",
                line=dict(width=3, color=STATUS_COLOR.get(selected_light, "#2a78d6")),
                marker=dict(size=8),
                customdata=history[["Final light", "Data coverage %"]],
                hovertemplate=(
                    "<b>%{x}</b><br>Score: %{y:.1f}<br>"
                    "Status: %{customdata[0]}<br>Coverage: %{customdata[1]:.0f}%<extra></extra>"
                ),
            )
        )
        history_fig.add_hrect(y0=75, y1=100, opacity=0.08, line_width=0, fillcolor="green", annotation_text="Green Band (≥75)")
        history_fig.add_hrect(y0=40, y1=75, opacity=0.05, line_width=0, fillcolor="orange", annotation_text="Amber Band (40-74)")
        history_fig.add_hrect(y0=0, y1=40, opacity=0.04, line_width=0, fillcolor="red", annotation_text="Red Band (<40)")
        history_fig.update_layout(
            template="plotly_white",
            yaxis_title="Overall Score (0–100)",
            xaxis_title="Quarter",
            yaxis_range=[0, 100],
            showlegend=False,
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(history_fig, width="stretch", key=f"full_page_history_{selected_sector}")

        st.divider()

        # ---------------------------------------------------------------------
        # SECTION 4: RISK PILLAR PERFORMANCE
        # ---------------------------------------------------------------------
        st.markdown("### 4️⃣ Risk Pillar Performance")
        st.caption("Pillar breakdown across Economic Performance (W1), Financial Health (W2), and Workforce/Operational Risk (W3).")

        selected_pillars = pillars[
            (pillars["Sectors"] == selected_sector)
            & (pillars["Quarter"].astype(str) == selected_quarter)
        ].copy()

        p_cols = st.columns(3)
        for p_idx, (p_id, p_name) in enumerate(PILLARS.items()):
            p_data = selected_pillars[selected_pillars["Pillar"] == p_id]
            with p_cols[p_idx]:
                with st.container(border=True):
                    st.markdown(f"#### {p_id}: {p_name}")
                    if p_data.empty or pd.isna(p_data.iloc[0]["Score"]):
                        st.write("No pillar data available.")
                    else:
                        p_row = p_data.iloc[0]
                        st.metric("Pillar Score", f"{p_row['Score']:.1f} / 100", status_text(p_row['Light']))
                        
                        fig_p = px.bar(
                            p_data,
                            x="Pillar name",
                            y="Score",
                            color="Light",
                            color_discrete_map=STATUS_COLOR,
                            range_y=[0, 100],
                            text="Score"
                        )
                        fig_p.update_traces(texttemplate="%{text:.1f}", textposition="outside")
                        fig_p.update_layout(template="plotly_white", showlegend=False, margin=dict(l=5, r=5, t=10, b=5), height=200)
                        st.plotly_chart(fig_p, width="stretch", key=f"pillar_chart_{p_id}_{selected_sector}")

        st.divider()

        # ---------------------------------------------------------------------
        # SECTION 5: INDIVIDUAL INDICATOR PERFORMANCE GRAPHS
        # ---------------------------------------------------------------------
        st.markdown("### 5️⃣ Individual Indicator Performance Graphs")
        st.caption("Historical performance trajectory for each core scoring indicator.")

        sector_indicators = indicators[indicators["Sectors"] == selected_sector].copy()
        sector_indicators["Quarter"] = sector_indicators["Quarter"].astype(str)
        sector_indicators = sector_indicators.sort_values("Quarter", key=lambda s: s.map(period_sort_key))

        ind_grid_col1, ind_grid_col2 = st.columns(2)
        unique_ind_keys = list(SCORE_INDICATORS.keys())

        # Construct dictionary of indicators for OpenRouter Prompt
        current_indicator_dict = {}

        for ind_idx, ind_key in enumerate(unique_ind_keys):
            ind_info = SCORE_INDICATORS[ind_key]
            ind_label = ind_info["label"]
            ind_history = sector_indicators[sector_indicators["Indicator"] == ind_key].dropna(subset=["Value"])

            if not ind_history.empty:
                latest_val = ind_history.iloc[-1]["Value"]
                latest_light = ind_history.iloc[-1]["Light"]
                current_indicator_dict[ind_label] = f"{latest_val:.2f} ({latest_light})"

            target_col = ind_grid_col1 if ind_idx % 2 == 0 else ind_grid_col2

            with target_col:
                with st.container(border=True):
                    st.markdown(f"##### 📊 {ind_label}")
                    st.caption(f"Pillar: {PILLARS[ind_info['pillar']]} | Weight: {ind_info['weight']}%")

                    if ind_history.empty:
                        st.info("No historical raw data available for this indicator.")
                    else:
                        fig_ind = px.line(
                            ind_history,
                            x="Quarter",
                            y="Value",
                            markers=True,
                            title=f"{ind_label} Trend",
                            labels={"Value": "Indicator Value", "Quarter": "Quarter"},
                        )
                        fig_ind.update_traces(line_color=engine.SECTOR_COLORS.get(selected_sector, "#2a78d6"), line_width=2, marker_size=6)
                        fig_ind.update_layout(
                            template="plotly_white",
                            margin=dict(l=10, r=10, t=30, b=10),
                            height=250,
                        )
                        st.plotly_chart(fig_ind, width="stretch", key=f"ind_graph_{ind_key}_{selected_sector}")

        st.divider()

        # ---------------------------------------------------------------------
        # NEW SECTION 6: AI RISK ANALYST COMMENTARY (OPENROUTER INTEGRATION)
        # ---------------------------------------------------------------------
        st.markdown("### 🤖 AI Risk Analyst Commentary")
        st.caption("Automated executive analysis generated via OpenRouter LLM.")

        with st.container(border=True):
            if st.button("✨ Generate / Refresh AI Commentary", key=f"btn_ai_{selected_sector}"):
                with st.spinner("Analyzing sector data via OpenRouter AI..."):
                    commentary = generate_ai_sector_commentary(
                        sector_name=selected_sector,
                        quarter=selected_quarter,
                        score=selected_score,
                        status=selected_light,
                        red_count=selected_reds,
                        warning_text=selected_warning,
                        indicator_data_dict=current_indicator_dict
                    )
                    st.session_state[f"ai_commentary_{selected_sector}_{selected_quarter}"] = commentary

            # Display generated commentary if present in session state
            commentary_key = f"ai_commentary_{selected_sector}_{selected_quarter}"
            if commentary_key in st.session_state:
                st.markdown(st.session_state[commentary_key])
            else:
                st.info("Click the **✨ Generate / Refresh AI Commentary** button above to generate a tailored executive summary for this sector.")

    st.divider()
    if st.button("⬅️ Return to Overall Market Summary", type="primary", key="btn_back_bottom"):
        st.session_state.active_sector_detail = None
        st.rerun()

# =============================================================================
# VIEW 2: MAIN OVERALL MARKET SUMMARY PAGE
# =============================================================================
else:
    st.title("📊 Industry Monitoring System")
    st.caption("A simple traffic-light dashboard for monitoring industry strength, deterioration and elevated risk.")

    with st.expander("How to read this dashboard", expanded=False):
        st.markdown(
            """
            - **🟢 Green** = relatively healthy based on the project's scoring rules.
            - **🟠 Amber** = watch closely; some indicators are weaker or mixed.
            - **🔴 Red** = elevated risk based on the project's thresholds.
            - The **overall score** combines the indicators using their assigned weights.
            - Click any **Sector Deep-Dive Button** to switch to that industry's full detail page.
            - Use the **left sidebar** to adjust the assessment quarter.
            """
        )

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

    # -------------------------------------------------------------------------
    # 1. SECTOR DEEP-DIVE BUTTONS (SWITCHES TO FULL SECTOR PAGE)
    # -------------------------------------------------------------------------
    st.markdown("### 🏢 Sector Deep-Dive Actions")
    st.caption("Click a sector button below to switch to that sector's full analysis page.")

    btn_cols = st.columns(len(TARGET_SECTORS))

    for idx, sector in enumerate(TARGET_SECTORS):
        sector_overall = quarter_overall[quarter_overall["Sectors"] == sector]
        status_icon = "⚪"
        if not sector_overall.empty:
            status_light = sector_overall.iloc[0]["Final light"]
            status_icon = STATUS_ICON.get(status_light, "⚪")
        
        if btn_cols[idx].button(f"{status_icon} {sector}", key=f"btn_sector_{sector}", use_container_width=True):
            st.session_state.active_sector_detail = sector
            st.rerun()

    st.divider()

    # -------------------------------------------------------------------------
    # 2. INDUSTRY RISK SCORING HORIZONTAL BAR CHART & 3. TRAFFIC-LIGHT HEATMAP
    # -------------------------------------------------------------------------
    col_bar, col_heatmap = st.columns([1, 1])

    with col_bar:
        st.markdown("### 📊 Industry Risk Score Ranking")
        st.caption(f"Overall sector score ranking for {selected_quarter}.")
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

    with col_heatmap:
        st.markdown("### 🚦 Historical Traffic-Light Heatmap")
        st.caption("Historical sector scores color-coded by final traffic-light status.")

        pivot_scores = overall.pivot(index="Sectors", columns="Quarter", values="Score")
        pivot_lights = overall.pivot(index="Sectors", columns="Quarter", values="Final light")

        ordered_quarters = sorted([str(q) for q in pivot_scores.columns], key=period_sort_key)
        pivot_scores = pivot_scores.reindex(index=TARGET_SECTORS, columns=ordered_quarters)
        pivot_lights = pivot_lights.reindex(index=TARGET_SECTORS, columns=ordered_quarters)

        light_map = {"Green": 1, "Amber": 0.5, "Red": 0}
        numeric_lights = pivot_lights.replace(light_map)

        fig_heatmap = px.imshow(
            numeric_lights,
            labels=dict(x="Quarter", y="Industry", color="Traffic Light"),
            x=ordered_quarters,
            y=TARGET_SECTORS,
            color_continuous_scale=[[0, "#D64545"], [0.5, "#E69F00"], [1, "#2E8B57"]],
            text_auto=False,
        )

        for i, sector in enumerate(TARGET_SECTORS):
            for j, qtr in enumerate(ordered_quarters):
                score_val = pivot_scores.loc[sector, qtr]
                text_val = f"{score_val:.1f}" if pd.notna(score_val) else "-"
                fig_heatmap.add_annotation(
                    x=qtr, y=sector, text=text_val,
                    showarrow=False, font=dict(color="white", size=11, family="sans-serif")
                )

        fig_heatmap.update_layout(
            template="plotly_white",
            coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig_heatmap, width="stretch", key="overall_traffic_light_heatmap")

    st.divider()

    # -------------------------------------------------------------------------
    # 4. CROSS-INDUSTRY STATUS MATRIX
    # -------------------------------------------------------------------------
    st.markdown("### 📋 Cross-Industry Status Matrix")
    st.caption(f"Full breakdown of scores, traffic light status, and active warnings ({selected_quarter}).")

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

    st.divider()

    # -------------------------------------------------------------------------
    # 5. HISTORICAL INDICATOR DRILL-DOWN (INDICATOR TABS + COMPACT FILTERS)
    # -------------------------------------------------------------------------
    st.markdown("### 🔍 Historical Indicator Drill-Down")
    st.caption("Compare underlying macro indicators across target industries over adjustable time horizons.")

    indicator_names = [
        "Real GDP",
        "GDP Share",
        "Gross Operating Surplus",
        "Labour Productivity",
        "Equity Ratio",
        "Business Expectations",
    ]

    # Indicator Tabs
    ind_tabs = st.tabs([f"📈 {name}" for name in indicator_names])

    for ind_tab, selected_metric in zip(ind_tabs, indicator_names):
        with ind_tab:
            col_ctrl, col_graph = st.columns([1, 3])

            with col_ctrl:
                st.markdown("#### ⚙️ Filters")
                
                compared_sectors = st.multiselect(
                    "Filter Industries",
                    TARGET_SECTORS,
                    default=TARGET_SECTORS,
                    key=f"sectors_{selected_metric}",
                    help="Select industries to include in the plot."
                )

                num_years = st.slider(
                    "Years of History",
                    min_value=1,
                    max_value=10,
                    value=5,
                    step=1,
                    key=f"years_slider_{selected_metric}",
                    help="Adjust how many recent years of data to view."
                )

            with col_graph:
                if not compared_sectors:
                    st.info("Select at least one industry to display the historical line chart.")
                else:
                    trend_df = get_trend_dataframe(selected_metric)
                    
                    # Filter by Selected Sectors
                    trend_df = trend_df[trend_df["Sectors"].isin(compared_sectors)].copy()

                    # Filter by Selected Number of Years
                    if not trend_df.empty:
                        trend_df["Year"] = trend_df["Period"].astype(str).str.extract(r'(\d{4})').astype(float)
                        max_year = trend_df["Year"].max()
                        if pd.notna(max_year):
                            min_year_cutoff = max_year - num_years + 1
                            trend_df = trend_df[trend_df["Year"] >= min_year_cutoff]

                    if trend_df.empty:
                        st.warning("No data available for the selected time window and sectors.")
                    else:
                        trend_fig = px.line(
                            trend_df,
                            x="Period",
                            y="Value",
                            color="Sectors",
                            markers=True,
                            color_discrete_map=engine.SECTOR_COLORS,
                            title=f"{selected_metric} Historical Trend (Last {num_years} Years)",
                            labels={"Sectors": "Industry", "Value": selected_metric},
                        )
                        trend_fig.update_layout(
                            template="plotly_white",
                            hovermode="x unified",
                            legend_title="Industry",
                            margin=dict(l=10, r=10, t=40, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        )
                        st.plotly_chart(trend_fig, width="stretch", key=f"indicator_trend_tab_{selected_metric}")

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