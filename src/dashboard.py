######################################################################
# dashboard.py
# Industry Monitoring Dashboard (Streamlit)
#
# It does NOT calculate anything new: it uses the same code as main.py
# (run_pipeline) and the settings of config.py, and only shows the results.
#
# Before the first time: create the database with  uv run python src/database.py
# Run it from the Project_Dashboard folder with:
#     uv run streamlit run src/dashboard.py


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import (TARGET_SECTORS, SECTOR_COLORS, PILLARS, SCORE_INDICATORS,
                    INDICATORS_TO_ANALYSE, POINTS_PER_LIGHT,
                    GREEN_IF_SCORE_AT_LEAST, AMBER_IF_SCORE_AT_LEAST, NUMBER_OF_REDS_THAT_BLOCK_GREEN)
from exploration import convert_period_to_date, make_one_row_per_sector_and_period
from main import run_pipeline


######################################################################
# PAGE SETUP


st.set_page_config(page_title="Industry Monitoring System", page_icon="📊", layout="wide")

# How each traffic light is shown in the dashboard
LIGHT_ICON = {"Green": "🟢", "Amber": "🟠", "Red": "🔴"}
LIGHT_COLOR = {"Green": "#2E8B57", "Amber": "#E69F00", "Red": "#D64545"}


######################################################################
# LOAD THE RESULTS (same code as main.py)


@st.cache_resource(show_spinner="Preparing industry monitoring data...")
def load_results() -> dict:
    """Run the pipeline of main.py ONCE and keep the results in memory.
    (st.cache_resource = it is not run again every time you click a filter)"""
    return run_pipeline()


try:
    results = load_results()
except Exception as error:
    st.error("The data could not be loaded. Did you create the database with database.py?")
    st.exception(error)
    st.stop()

df_overall_results = results["df_overall_results"]
df_indicator_results = results["df_indicator_results"]
df_pillar_results = results["df_pillar_results"]
clean_data = results["clean_data"]
filtered_data = results["filtered_data"]


######################################################################
# SMALL HELPERS

def light_text(light) -> str:
    """'Green' -> '🟢 Green'. No light -> 'No data'."""
    if pd.isna(light):
        return "No data"
    return f"{LIGHT_ICON[light]} {light}"


def value_text(value) -> str:
    """Number with 2 decimals, or 'No data'."""
    if pd.isna(value):
        return "No data"
    return f"{value:,.2f}"


def make_gdp_share_table() -> pd.DataFrame:
    """% of each target sector in the total GDP: sector value / total GDP value * 100."""
    df_gdp = clean_data["gdp"]
    total_row = df_gdp[df_gdp["Sectors"] == INDICATORS_TO_ANALYSE["gdp"]["total_row"]]

    df_share = filtered_data["gdp"].copy()
    if total_row.empty:
        return df_share.iloc[0:0]          # no total row -> empty table
    for period in df_share.columns[1:]:
        df_share[period] = df_share[period] / total_row[period].values[0] * 100
    return df_share


######################################################################
# TITLE AND SHORT GUIDE
######################################################################

st.title("📊 Industry Monitoring System")
st.caption("A traffic-light dashboard for monitoring industry strength, deterioration and elevated risk.")

with st.expander("How to read this dashboard", expanded=False):
    st.markdown(
        """
        - **🟢 Green** = relatively healthy based on the project's scoring rules.
        - **🟠 Amber** = watch closely; some indicators are weaker or mixed.
        - **🔴 Red** = elevated risk based on the project's thresholds.
        - The **overall score** combines the indicators using their weights.
        - Use the sidebar to change the **industry** and the **quarter**.
        - The lower sections explain **why** an industry received its status.
        """
    )


######################################################################
# SIDEBAR FILTERS
######################################################################

# Quarters from the oldest to the newest
quarter_options = sorted(df_overall_results["Quarter"].unique(), key=convert_period_to_date)

st.sidebar.header("Dashboard filters")
selected_sector = st.sidebar.selectbox("Industry sector", TARGET_SECTORS, index=0)
selected_quarter = st.sidebar.selectbox("Assessment quarter", quarter_options,
                                        index=len(quarter_options) - 1)   # latest quarter

st.sidebar.divider()
if st.sidebar.button("Reload data"):
    # Use it after changing the data files or config.py
    st.cache_resource.clear()
    st.rerun()


######################################################################
# 1. SELECTED SECTOR + QUARTER
######################################################################

is_this_sector = df_overall_results["Sectors"] == selected_sector
is_this_quarter = df_overall_results["Quarter"] == selected_quarter
selected_rows = df_overall_results[is_this_sector & is_this_quarter]

if selected_rows.empty:
    st.warning("No overall assessment is available for this sector and quarter.")
    st.stop()

selected_row = selected_rows.iloc[0]

st.subheader(f"{selected_sector} — {selected_quarter}")

kpi_columns = st.columns(4)
kpi_columns[0].metric("Overall status", light_text(selected_row["Final light"]))
kpi_columns[1].metric("Industry score", value_text(selected_row["Score"]) + " / 100")
kpi_columns[2].metric("Red indicators", int(selected_row["Red indicators"]))
kpi_columns[3].metric("Data coverage", f"{selected_row['Data coverage %']:.0f}%")

if selected_row["Warning"] != "":
    st.warning(selected_row["Warning"])
elif selected_row["Final light"] == "Red":
    st.error("The selected industry is currently classified as Red.")
elif selected_row["Final light"] == "Amber":
    st.info("The selected industry is currently Amber and should be monitored closely.")
else:
    st.success("The selected industry is currently Green under the project's scoring rules.")


######################################################################
# 2. ALL THE SECTORS IN THE SELECTED QUARTER
######################################################################

st.subheader("Industry snapshot")
st.caption("Compare all the sectors in the same quarter.")

df_snapshot = df_overall_results[df_overall_results["Quarter"] == selected_quarter].copy()
df_snapshot = df_snapshot.sort_values("Score", ascending=False)

snapshot_chart = px.bar(
    df_snapshot.dropna(subset=["Score"]),
    x="Score", y="Sectors", orientation="h",
    color="Final light", color_discrete_map=LIGHT_COLOR,
    range_x=[0, 100], text="Score",
    title=f"Overall score by industry — {selected_quarter}",
    labels={"Sectors": "Industry", "Final light": "Status"},
)
snapshot_chart.update_traces(texttemplate="%{text:.1f}", textposition="outside")
snapshot_chart.update_layout(template="plotly_white", yaxis={"categoryorder": "total ascending"})
st.plotly_chart(snapshot_chart, width="stretch")

df_snapshot_table = pd.DataFrame({
    "Industry": df_snapshot["Sectors"],
    "Score": df_snapshot["Score"],
    "Status": df_snapshot["Final light"].apply(light_text),
    "Red indicators": df_snapshot["Red indicators"],
    "Coverage %": df_snapshot["Data coverage %"],
})
st.dataframe(df_snapshot_table, hide_index=True, width="stretch")


######################################################################
# 3. SCORE HISTORY OF THE SELECTED SECTOR
######################################################################

st.subheader("Score history")
st.caption("Is the selected industry improving, stable or getting worse?")

df_history = df_overall_results[df_overall_results["Sectors"] == selected_sector]

history_chart = go.Figure()
history_chart.add_trace(go.Scatter(
    x=df_history["Quarter"], y=df_history["Score"],
    mode="lines+markers", line=dict(width=3), marker=dict(size=8),
    customdata=df_history[["Final light", "Data coverage %"]],
    hovertemplate="<b>%{x}</b><br>Score: %{y:.1f}<br>Status: %{customdata[0]}"
                  "<br>Coverage: %{customdata[1]:.0f}%<extra></extra>",
))
history_chart.add_hline(y=GREEN_IF_SCORE_AT_LEAST, line_dash="dash",
                        annotation_text=f"Green from {GREEN_IF_SCORE_AT_LEAST}")
history_chart.add_hline(y=AMBER_IF_SCORE_AT_LEAST, line_dash="dash",
                        annotation_text=f"Amber from {AMBER_IF_SCORE_AT_LEAST}")
history_chart.update_layout(template="plotly_white", yaxis_title="Score (0-100)",
                            xaxis_title="Quarter", yaxis_range=[0, 100], showlegend=False)
st.plotly_chart(history_chart, width="stretch")


######################################################################
# 4. WHAT IS DRIVING THE SCORE? (the 5 indicators)
######################################################################

st.subheader("What is driving the score?")
st.caption("Which indicators are helping or hurting the industry.")

is_this_sector = df_indicator_results["Sectors"] == selected_sector
is_this_quarter = df_indicator_results["Quarter"] == selected_quarter
df_selected_indicators = df_indicator_results[is_this_sector & is_this_quarter]

df_indicator_table = pd.DataFrame({
    "Pillar": df_selected_indicators["Pillar"],
    "Indicator": df_selected_indicators["Label"],
    "Value": df_selected_indicators["Value"].apply(value_text),
    "Data period": df_selected_indicators["Value period"],
    "Status": df_selected_indicators["Light"].apply(light_text),
    "Weight": df_selected_indicators["Weight"],
    "Points earned": df_selected_indicators["Points"],
})
st.dataframe(df_indicator_table, hide_index=True, width="stretch")


######################################################################
# 5. RISK PILLARS (W1, W2, W3)
######################################################################

st.subheader("Risk pillars")

is_this_sector = df_pillar_results["Sectors"] == selected_sector
is_this_quarter = df_pillar_results["Quarter"] == selected_quarter
df_selected_pillars = df_pillar_results[is_this_sector & is_this_quarter]

pillar_chart = px.bar(
    df_selected_pillars,
    x="Pillar name", y="Score",
    color="Light", color_discrete_map=LIGHT_COLOR,
    range_y=[0, 100], text="Score",
    title="Pillar scores",
    labels={"Pillar name": "Risk pillar", "Light": "Status"},
)
pillar_chart.update_traces(texttemplate="%{text:.1f}", textposition="outside")
pillar_chart.update_layout(template="plotly_white")
st.plotly_chart(pillar_chart, width="stretch")

df_pillar_table = pd.DataFrame({
    "Pillar": df_selected_pillars["Pillar name"],
    "Score": df_selected_pillars["Score"],
    "Status": df_selected_pillars["Light"].apply(light_text),
    "Coverage %": df_selected_pillars["Data coverage %"],
})
st.dataframe(df_pillar_table, hide_index=True, width="stretch")


######################################################################
# 6. INDICATOR DRILL-DOWN (the data behind the score)
######################################################################

st.subheader("Indicator drill-down")
st.caption("The underlying data. Business Expectations is shown for context, "
           "it is not part of the score.")

# Indicator name shown in the list -> its filtered table
drill_down_tables = {}
for indicator_name, indicator_settings in INDICATORS_TO_ANALYSE.items():
    drill_down_tables[indicator_settings["title"]] = filtered_data[indicator_name]
drill_down_tables["GDP share of total (%)"] = make_gdp_share_table()

left_column, right_column = st.columns([1, 2])

with left_column:
    selected_indicator = st.selectbox("Monitoring indicator", list(drill_down_tables.keys()))
    compared_sectors = st.multiselect("Industries to compare", TARGET_SECTORS, default=[selected_sector])

with right_column:
    if len(compared_sectors) == 0:
        st.info("Select at least one industry to display the trend.")
    else:
        df_trend = make_one_row_per_sector_and_period(drill_down_tables[selected_indicator])
        df_trend = df_trend[df_trend["Sectors"].isin(compared_sectors)].dropna(subset=["Value"])

        trend_chart = px.line(
            df_trend, x="Date", y="Value", color="Sectors",
            markers=True, color_discrete_map=SECTOR_COLORS,
            hover_data={"Period": True, "Date": False},
            title=f"{selected_indicator}: trend",
            labels={"Sectors": "Industry", "Value": selected_indicator, "Date": "Period"},
        )
        trend_chart.update_layout(template="plotly_white", hovermode="x unified")
        st.plotly_chart(trend_chart, width="stretch")


######################################################################
# 7. SCORING METHODOLOGY (taken from config.py)
######################################################################

with st.expander("Scoring methodology and thresholds", expanded=False):
    st.markdown(
        f"""
        **Overall score bands**
        - Green: score **≥ {GREEN_IF_SCORE_AT_LEAST}**
        - Amber: score **{AMBER_IF_SCORE_AT_LEAST} to < {GREEN_IF_SCORE_AT_LEAST}**
        - Red: score **< {AMBER_IF_SCORE_AT_LEAST}**

        **Indicator points**
        - Green earns **{POINTS_PER_LIGHT['Green']:.0%}** of the indicator's weight.
        - Amber earns **{POINTS_PER_LIGHT['Amber']:.0%}** of the indicator's weight.
        - Red earns **{POINTS_PER_LIGHT['Red']:.0%}** of the indicator's weight.

        **Override rule**
        - With **{NUMBER_OF_REDS_THAT_BLOCK_GREEN} or more Red indicators**, an industry can't be Green (maximum Amber).
        - With **1 Red indicator**, it can stay Green but a warning is shown.
        """
    )

    methodology_rows = []
    for indicator_name, indicator_settings in SCORE_INDICATORS.items():
        if indicator_settings["calculation"] == "esg":
            green_text, amber_text, red_text = "Low ESG risk", "Medium ESG risk", "High ESG risk"
        else:
            green_symbol = "≥" if indicator_settings["green_includes_limit"] else ">"
            green_text = f"{green_symbol} {indicator_settings['green_from']}"
            amber_text = f"≥ {indicator_settings['amber_from']} and below Green"
            red_text = f"< {indicator_settings['amber_from']}"

        methodology_rows.append({
            "Indicator": indicator_settings["label"],
            "Pillar": PILLARS[indicator_settings["pillar"]],
            "Weight": indicator_settings["weight"],
            "Green": green_text,
            "Amber": amber_text,
            "Red": red_text,
        })

    st.dataframe(pd.DataFrame(methodology_rows), hide_index=True, width="stretch")
    st.caption("When some indicator has no data, the score is calculated only with the indicators "
               "that have data. Always read the Data coverage % together with the score.")


######################################################################
# 8. TECHNICAL VIEW (all the result rows)
######################################################################

with st.expander("Technical data view", expanded=False):
    st.write("Overall results")
    st.dataframe(df_overall_results, width="stretch")
    st.write("Indicator results")
    st.dataframe(df_indicator_results, width="stretch")
    st.write("Pillar results")
    st.dataframe(df_pillar_results, width="stretch")