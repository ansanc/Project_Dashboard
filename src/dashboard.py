######################################################################
# dashboard.py
# Industry Monitoring Dashboard (Streamlit)
#
# Used in the monthly / quarterly meetings between the credit area and the
# credit risk area, to follow the behaviour of each sector and decide where
# to grow or slow the growth.
#
# It shows COLOURS (traffic lights), not scores, and explains each colour
# with its 3 pillars. It goes from the general picture to the details (5 pages):
#   1. Overview        -> all the sectors at once (click a sector in the table to zoom into it)
#   2. Sector zoom     -> one sector: why it has its colour + AI analysis
#                         (the AI is a complementary commentary, it does not change the colours)
#   3. Indicator data  -> the data behind the colours
#   4. ESG             -> ESG reporting of each sector + its physical / transition / governance risks
#   5. Methodology     -> how the colours are calculated
#
# It does NOT calculate anything new: it uses run_pipeline() of main.py
# and the settings of config.py.
#
# Before the first time: create the database with  uv run python src/database.py
# Run it from the Project_Dashboard folder with:
#     uv run streamlit run src/dashboard.py
# To stop it: Ctrl + C in the terminal
######################################################################

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

from config import (PROJECT_FOLDER, DATA_FILES, TARGET_SECTORS, SECTOR_COLORS,
                    INDICATORS_TO_ANALYSE, PILLARS, SCORE_INDICATORS, ESG_RISK_TO_LIGHT,
                    POINTS_PER_LIGHT, GREEN_IF_SCORE_AT_LEAST, AMBER_IF_SCORE_AT_LEAST,
                    NUMBER_OF_REDS_THAT_BLOCK_GREEN, CREDIT_SIGNAL,
                    AI_BASE_URL, AI_MODEL, AI_API_KEY_NAME, AI_LOG_FILE, ESG_SECTOR_RISKS)
from exploration import (convert_period_to_date, make_one_row_per_sector_and_period,
                         clean_esg, calculate_esg_answer_percentages)
from database import load_table
from main import run_pipeline


######################################################################
# PAGE SETUP
######################################################################

st.set_page_config(page_title="Industry Monitoring System", page_icon="📊", layout="wide")

# How each traffic light is shown in the dashboard
LIGHT_ICON = {"Green": "🟢", "Amber": "🟠", "Red": "🔴"}
LIGHT_COLOR = {"Green": "#2E8B57", "Amber": "#E69F00", "Red": "#D64545"}

# Traffic light -> number (to compare lights and draw the colour maps: the higher, the better)
LIGHT_NUMBER = {"Red": 0, "Amber": 1, "Green": 2}

# The indicators that come from the ESG report (they have no history)
ESG_INDICATORS = []
for indicator_name, indicator_settings in SCORE_INDICATORS.items():
    if indicator_settings["calculation"] == "esg":
        ESG_INDICATORS.append(indicator_name)


######################################################################
# LOAD THE RESULTS (same code as main.py)
######################################################################

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
df_esg_risk = results["df_esg_risk"]
clean_data = results["clean_data"]
filtered_data = results["filtered_data"]

# Quarters from the oldest to the newest
quarter_options = sorted(df_overall_results["Quarter"].unique(), key=convert_period_to_date)


######################################################################
# SMALL HELPERS
######################################################################

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


def quarter_text(quarter: str) -> str:
    """'2025 2Q' -> '2025 Q2' (only how it is shown, the data keeps '2025 2Q')."""
    year, quarter_number = quarter.split()
    return f"{year} Q{quarter_number[0]}"


def download_csv_button(df_to_download: pd.DataFrame, file_name: str) -> None:
    """Button to download a table as a CSV file (to take it to the committee)."""
    st.download_button("⬇️ Download CSV", df_to_download.to_csv(index=False).encode("utf-8"),
                       file_name=file_name, mime="text/csv", key=f"download_{file_name}")


def compare_lights(light_before, light_now) -> str:
    """Did the light get better, worse or stay the same?"""
    if pd.isna(light_before) or pd.isna(light_now):
        return "No data"
    if LIGHT_NUMBER[light_now] > LIGHT_NUMBER[light_before]:
        return "▲ Improved"
    elif LIGHT_NUMBER[light_now] < LIGHT_NUMBER[light_before]:
        return "▼ Deteriorated"
    else:
        return "= Same"


def count_quarters_with_same_light(lights_oldest_to_newest: list) -> int:
    """How many quarters in a row (ending in the last one) have the same light."""
    last_light = lights_oldest_to_newest[-1]
    number_of_quarters = 0
    for light in reversed(lights_oldest_to_newest):
        if light != last_light:
            break
        number_of_quarters = number_of_quarters + 1
    return number_of_quarters


def make_light_map(df_light_table: pd.DataFrame, title: str, show_text: bool = False,
                   x_title: str = "Quarter") -> go.Figure:
    """Grid of coloured squares. df_light_table: 'Green' / 'Amber' / 'Red' in each cell
    (rows = sectors, pillars or indicators | columns = quarters or pillars)."""
    df_numbers = df_light_table.replace(LIGHT_NUMBER).astype(float)   # Red 0 | Amber 1 | Green 2
    df_text = df_light_table.fillna("No data")

    # Write the light inside each square? (only when there are few squares)
    if show_text:
        text_inside_squares = "%{text}"
    else:
        text_inside_squares = None

    light_map = go.Figure(go.Heatmap(
        z=df_numbers.values,
        x=list(df_light_table.columns),
        y=list(df_light_table.index),
        zmin=0, zmax=2,
        colorscale=[[0, LIGHT_COLOR["Red"]], [0.5, LIGHT_COLOR["Amber"]], [1, LIGHT_COLOR["Green"]]],
        text=df_text.values,
        texttemplate=text_inside_squares,
        hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
        showscale=False,
        xgap=3, ygap=3,     # white space between the squares
    ))
    light_map.update_layout(template="plotly_white", title=title,
                            height=120 + 45 * len(df_light_table.index),
                            xaxis_title=x_title,
                            yaxis={"autorange": "reversed"})   # first row on top
    return light_map


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
# AI LAYER (only used in the Sector zoom) - based on Week 10
#   Deterministic pipeline (main.py) -> colours | LLM -> commentary | Committee -> decides
#   1. System prompt -> persona + guardrails (what the AI must NOT do)
#   2. User prompt   -> the current view + its data + the output format
#   3. Ask AI        -> one call to OpenRouter
#   4. Log           -> every AI run is written in log/ai_runs.log (never the API key)
# Same structure as the class demos (week9_streamlit_demo.py, week10_openrouter_demo.py)
# The API key is NOT in the code:
#   Local (our laptops)               -> .env file  -> os.getenv()
#   Cloud (Streamlit Community Cloud) -> st.secrets -> st.secrets.get()
######################################################################

# 1. SYSTEM PROMPT: persona + guardrails
AI_SYSTEM_PROMPT = """You are a senior credit risk analyst at a bank in Singapore.
You write for the monthly / quarterly committee between the credit area and the credit risk area.
The readers are senior analysts, managers and vice presidents of credit and risk:
be concise and professional, do not explain basic concepts.

Hard limits:
- Use only the data you receive for the sector analysis. No unsupported causal claims.
- Do not mention or estimate numeric scores: talk about the traffic lights.
- No pricing, underwriting or individual customer decisions. Comment only at sector level:
  the credit signal comes from the model and the committee takes the decision.
- You have no live internet access: never invent headlines, dates, figures, quotes or sources.
- ESG reporting comes from the latest report only (no history): do not describe ESG trends.
- Always state the limitations of your analysis.
Return only the final assessment: no reasoning, no task analysis, no description of the format."""

# 2. USER PROMPT FORMAT: what we want back
AI_OUTPUT_FORMAT = """Please provide a professional 3-paragraph assessment summarize (maximum 200 words).
Start each paragraph with its title in bold:
1. **Key strengths & vulnerabilities**: what is driving the traffic light of the sector.
2. **Outlook & risk commentary**: key macro or financial risks suggested by the indicator
   traffic lights and their change since the previous quarter, and what it means for the
   credit signal.
3. **Sector current trends**: general trends of this sector in Singapore and important worldwide
   tendencies (not about the indicators). Describe well-known structural trends only.
End with one line starting with **Limitation:**"""


def build_ai_prompt(current_view_text: str, df_quarter_indicators: pd.DataFrame,
                    df_previous_indicators: pd.DataFrame) -> str:
    """User prompt: the current view + the indicators of the sector + the output format."""
    prompt = "Current view: " + current_view_text + "\n\nIndicators:\n"

    for _, indicator_row in df_quarter_indicators.iterrows():
        pillar_name = PILLARS[indicator_row["Pillar"]]

        if indicator_row["Indicator"] in ESG_INDICATORS:
            if pd.isna(indicator_row["Value"]):
                esg_text = "no ESG data for this sector (counted as High risk)"
            else:
                esg_text = f"{indicator_row['Value']}% of the top companies report ESG fully"
            prompt += (f"- {indicator_row['Label']} ({pillar_name}): light {indicator_row['Light']}, "
                       f"{esg_text} (latest report, no history)\n")
        else:
            # Light of the same indicator in the previous quarter (if there is one)
            previous_row = df_previous_indicators[df_previous_indicators["Indicator"] == indicator_row["Indicator"]]
            if previous_row.empty:
                previous_light = "no previous quarter"
            else:
                previous_light = previous_row["Light"].iloc[0]
            prompt += (f"- {indicator_row['Label']} ({pillar_name}): light {indicator_row['Light']} "
                       f"(previous quarter: {previous_light}), value {indicator_row['Value']} "
                       f"(data of {indicator_row['Value period']})\n")

    return prompt + "\n" + AI_OUTPUT_FORMAT


def get_ai_api_key() -> str | None:
    """API key of OpenRouter. None if it is not found.
    1. Local: the .env file of the project folder (OPENROUTER_API_KEY=...)
    2. Cloud: Streamlit Secrets (only used if the app is published online)"""
    load_dotenv(PROJECT_FOLDER / ".env")
    api_key = os.getenv(AI_API_KEY_NAME)
    if api_key:
        return api_key
    try:
        return st.secrets.get(AI_API_KEY_NAME)
    except Exception:          # no secrets.toml file (normal when running locally)
        return None


# 3. ASK THE AI
# st.cache_data = if the same prompt was already sent, reuse the answer and do NOT call
# the API again (professor's instruction 4: avoid unnecessary repeated calls)
@st.cache_data(show_spinner=False)
def ask_ai(user_prompt: str, _api_key: str) -> tuple[str, str]:
    """One call to OpenRouter. Returns (answer, name of the model that answered)."""
    client = OpenAI(base_url=AI_BASE_URL, api_key=_api_key)
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,                                # low = less random answers
        max_tokens=800,                                 # enough for ~350 words
        extra_body={"reasoning": {"enabled": False}},   # only the final answer
    )
    ai_summary = response.choices[0].message.content
    if not ai_summary:
        raise ValueError("The model returned an empty answer")
    return ai_summary, response.model


# 4. LOG EVERY AI RUN (one log file, never the API key)
@st.cache_resource
def configure_ai_logging() -> int:
    """Add log/ai_runs.log to loguru ONCE (cache_resource = not again on every click)."""
    AI_LOG_FILE.parent.mkdir(exist_ok=True)
    return logger.add(AI_LOG_FILE, rotation="10 MB",
                      format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")


######################################################################
# TITLE + SIDEBAR FILTERS (quarter + sectors: they are used in every tab)
######################################################################

st.title("📊 Industry Monitoring System")
st.caption("Singapore industries · Traffic-light monitoring for the credit and credit risk committee. "
           "Start with the Overview and zoom in with the next tabs.")

# Default filters the first time the page opens: latest quarter + all the sectors
if "selected_quarter" not in st.session_state:
    st.session_state["selected_quarter"] = quarter_options[-1]
if "selected_sectors" not in st.session_state:
    st.session_state["selected_sectors"] = TARGET_SECTORS


def reset_filters() -> None:
    """Button 'Reset': back to the latest quarter and all the sectors."""
    st.session_state["selected_quarter"] = quarter_options[-1]
    st.session_state["selected_sectors"] = TARGET_SECTORS


st.sidebar.header("Filters")
selected_quarter = st.sidebar.selectbox("Assessment quarter", quarter_options, key="selected_quarter",
                                        format_func=quarter_text)
selected_sectors = st.sidebar.multiselect("Sectors", TARGET_SECTORS, key="selected_sectors")
position_of_quarter = quarter_options.index(selected_quarter)

# The quarter before the selected one (None if the selected one is the first)
if position_of_quarter > 0:
    previous_quarter = quarter_options[position_of_quarter - 1]
else:
    previous_quarter = None

st.sidebar.button("🔄 Reset to latest quarter and all sectors", on_click=reset_filters)
st.sidebar.caption("Tip: select an Assessment quarter and the Sectors to update "
                   "the traffic lights, pillars and indicators in every tab.")

st.sidebar.divider()
st.sidebar.caption("🟢 Green = Grow · 🟠 Amber = Grow selectively · 🔴 Red = Slow growth. "
                   "Model signals to support the discussion, not automatic decisions.")
if st.sidebar.button("Reload data"):
    # Use it after changing the data files or config.py
    st.cache_resource.clear()
    st.rerun()

if len(selected_sectors) == 0:
    st.info("Select at least one sector in the left sidebar.")
    st.stop()

# The sector shown in "Sector zoom" (it must be one of the sectors of the filter)
if st.session_state.get("zoom_sector") not in selected_sectors:
    st.session_state["zoom_sector"] = selected_sectors[0]


def open_clicked_sector() -> None:
    """When a row of the committee table is clicked: open that sector in 'Sector zoom'.
    (it runs BEFORE the page is drawn again, so it can change the page and the sector)"""
    clicked_rows = st.session_state["committee_table"].selection.rows
    if len(clicked_rows) > 0:
        clicked_sector = st.session_state["committee_table_order"][clicked_rows[0]]
        st.session_state["zoom_sector"] = clicked_sector
        st.session_state["page"] = "Sector zoom"


# Pages (like tabs, but they can be opened from the code when a sector is clicked)
PAGES = ["Overview", "Sector zoom", "Indicator data", "ESG", "Methodology"]
selected_page = st.radio("Page", PAGES, horizontal=True, key="page", label_visibility="collapsed")
st.divider()


######################################################################
# TAB 1. OVERVIEW: all the sectors at once
######################################################################

if selected_page == "Overview":
    df_quarter = df_overall_results[df_overall_results["Quarter"] == selected_quarter]
    df_quarter = df_quarter[df_quarter["Sectors"].isin(selected_sectors)]
    df_quarter_pillars = df_pillar_results[df_pillar_results["Quarter"] == selected_quarter]

    # 1.1 How many sectors in each colour
    st.subheader(f"All industries — {selected_quarter}")
    count_columns = st.columns(3)
    for column, light in zip(count_columns, ["Green", "Amber", "Red"]):
        number_of_sectors = (df_quarter["Final light"] == light).sum()
        column.metric(f"{LIGHT_ICON[light]} {light} · {CREDIT_SIGNAL[light]}",
                      f"{number_of_sectors} of {len(selected_sectors)} sectors")

    # 1.2 Committee table: one row per sector (Red first = needs attention first)
    st.markdown("**Committee summary**")
    df_previous = df_overall_results[df_overall_results["Quarter"] == previous_quarter]

    summary_rows = []
    for sector in selected_sectors:
        sector_row = df_quarter[df_quarter["Sectors"] == sector].iloc[0]
        final_light = sector_row["Final light"]

        if previous_quarter is None:
            change = "First quarter"
        else:
            light_before = df_previous[df_previous["Sectors"] == sector]["Final light"].iloc[0]
            change = compare_lights(light_before, final_light)

        summary_row = {
            "Industry": sector,
            "Traffic light": light_text(final_light),
            "vs previous quarter": change,
        }
        for pillar, pillar_name in PILLARS.items():
            is_this_sector = df_quarter_pillars["Sectors"] == sector
            is_this_pillar = df_quarter_pillars["Pillar"] == pillar
            pillar_light = df_quarter_pillars[is_this_sector & is_this_pillar]["Light"].iloc[0]
            summary_row[f"{pillar} {pillar_name}"] = light_text(pillar_light)
        summary_row["Red indicators"] = int(sector_row["Red indicators"])
        summary_row["Order"] = LIGHT_NUMBER.get(final_light, -1)      # only to sort the table
        summary_rows.append(summary_row)

    df_summary = pd.DataFrame(summary_rows).sort_values("Order").drop(columns="Order")
    st.caption("👆 Click a row to zoom into that sector.")
    st.session_state["committee_table_order"] = list(df_summary["Industry"])   # order of the rows
    st.dataframe(df_summary, hide_index=True, width="stretch", key="committee_table",
                 on_select=open_clicked_sector, selection_mode="single-row")
    download_csv_button(df_summary, f"committee_summary_{selected_quarter}.csv")

    # 1.3 Colour of every sector in every quarter + colour of each pillar this quarter
    left_column, right_column = st.columns([3, 2])

    with left_column:
        df_light_table = df_overall_results.pivot(index="Sectors", columns="Quarter", values="Final light")
        df_light_table = df_light_table.reindex(index=selected_sectors, columns=quarter_options)
        st.plotly_chart(make_light_map(df_light_table, "Traffic light over time"), width="stretch")

    with right_column:
        df_pillar_lights = df_quarter_pillars.pivot(index="Sectors", columns="Pillar name", values="Light")
        df_pillar_lights = df_pillar_lights.reindex(index=selected_sectors, columns=list(PILLARS.values()))
        st.plotly_chart(make_light_map(df_pillar_lights, f"Pillars — {selected_quarter}", show_text=True,
                                       x_title="Pillar"),
                        width="stretch")

    st.caption("Click a sector in the table, or go to **Sector zoom**, to see why it has its colour.")


######################################################################
# TAB 2. SECTOR ZOOM: one sector, why it has its colour
######################################################################

if selected_page == "Sector zoom":
    selected_sector = st.selectbox("Industry sector", selected_sectors, key="zoom_sector")

    df_sector_overall = df_overall_results[df_overall_results["Sectors"] == selected_sector]
    df_sector_pillars = df_pillar_results[df_pillar_results["Sectors"] == selected_sector]
    df_sector_indicators = df_indicator_results[df_indicator_results["Sectors"] == selected_sector]
    selected_row = df_sector_overall[df_sector_overall["Quarter"] == selected_quarter].iloc[0]
    final_light = selected_row["Final light"]

    # 2.1 Headline
    st.subheader(f"{selected_sector} — {selected_quarter}")
    lights_until_now = list(df_sector_overall["Final light"])[: position_of_quarter + 1]
    quarters_same_light = count_quarters_with_same_light(lights_until_now)

    headline_columns = st.columns(5)
    headline_columns[0].metric("Traffic light", light_text(final_light))
    headline_columns[1].metric("Credit signal", CREDIT_SIGNAL.get(final_light, "No data"))
    headline_columns[2].metric("Same colour for", f"{quarters_same_light} quarter(s)")
    headline_columns[3].metric("Red indicators", int(selected_row["Red indicators"]))
    headline_columns[4].metric("Data coverage", f"{selected_row['Data coverage %']:.0f}%")

    if selected_row["Data coverage %"] < 100:
        st.info("Some indicators have no data for this quarter: the colour was calculated "
                "only with the indicators that have data.")

    if selected_row["Warning"] != "":
        st.warning(selected_row["Warning"])

    # 2.2 Why this colour? The 3 pillars and their indicators
    st.markdown("**Why this colour? The 3 pillars**")
    df_quarter_indicators = df_sector_indicators[df_sector_indicators["Quarter"] == selected_quarter]
    pillar_columns = st.columns(len(PILLARS))

    for column, (pillar, pillar_name) in zip(pillar_columns, PILLARS.items()):
        is_this_quarter = df_sector_pillars["Quarter"] == selected_quarter
        is_this_pillar = df_sector_pillars["Pillar"] == pillar
        pillar_light = df_sector_pillars[is_this_quarter & is_this_pillar]["Light"].iloc[0]

        with column.container(border=True):
            st.markdown(f"**{pillar} · {pillar_name}**")
            st.markdown(f"### {light_text(pillar_light)}")

            df_pillar_indicators = df_quarter_indicators[df_quarter_indicators["Pillar"] == pillar]
            for _, indicator_row in df_pillar_indicators.iterrows():
                if indicator_row["Indicator"] in ESG_INDICATORS:
                    if pd.isna(indicator_row["Value"]):
                        detail = "no ESG data (counted as High risk)"
                    else:
                        detail = f"{indicator_row['Value']:.0f}% of top companies report fully"
                    detail = detail + " · *latest report, not quarterly*"
                else:
                    # All the score indicators are percentages (see their labels in config.py)
                    detail = f"{value_text(indicator_row['Value'])}% ({indicator_row['Value period']})"
                st.markdown(f"{light_text(indicator_row['Light'])} — **{indicator_row['Label']}**: {detail}")

    # 2.3 How the colours moved: overall, pillars and indicators over time
    history_rows = {"Overall": df_sector_overall.set_index("Quarter")["Final light"]}
    for pillar, pillar_name in PILLARS.items():
        df_one_pillar = df_sector_pillars[df_sector_pillars["Pillar"] == pillar]
        history_rows[f"{pillar} {pillar_name}"] = df_one_pillar.set_index("Quarter")["Light"]
    for indicator_name, indicator_settings in SCORE_INDICATORS.items():
        if indicator_name in ESG_INDICATORS:
            continue          # ESG has no history (only the latest report)
        df_one_indicator = df_sector_indicators[df_sector_indicators["Indicator"] == indicator_name]
        history_rows[indicator_settings["label"]] = df_one_indicator.set_index("Quarter")["Light"]

    df_history = pd.DataFrame(history_rows).T.reindex(columns=quarter_options)
    st.plotly_chart(make_light_map(df_history, "How the colours moved"), width="stretch")
    st.caption("ESG reporting is not in this map: it comes from the latest ESG report only "
               "(no history), so the same ESG colour is used in every quarter.")

    # 2.4 How the values of each indicator moved (each point coloured with its traffic light)
    st.markdown(f"**How the indicator values of {selected_sector} moved**")
    st.caption("Each point is the value of the quarter, coloured with its traffic light "
               "(🟢 Green · 🟠 Amber · 🔴 Red · grey = no data). Dashed lines are the limits: "
               "above the green line = Green, between the two lines = Amber, below the amber line = Red. "
               "ESG is not shown: it has no history.")
    trend_columns = st.columns(2)
    position_in_grid = 0
    for indicator_name, indicator_settings in SCORE_INDICATORS.items():
        if indicator_name in ESG_INDICATORS:
            continue
        df_one_indicator = df_sector_indicators[df_sector_indicators["Indicator"] == indicator_name]

        # Name of the y axis: growth indicators vs ratios
        if indicator_settings["calculation"] == "yearly_growth":
            y_axis_title = "Growth vs same quarter of last year (%)"
        else:
            y_axis_title = indicator_settings["label"]

        # Colour of each point = traffic light of that quarter
        point_colors = []
        for light in df_one_indicator["Light"]:
            point_colors.append(LIGHT_COLOR.get(light, "#9E9E9E"))      # grey = no data

        indicator_chart = px.line(
            df_one_indicator, x="Quarter", y="Value", markers=True,
            title=f"{indicator_settings['label']} — {selected_sector}",
            labels={"Value": y_axis_title, "Quarter": "Quarter"},
        )
        indicator_chart.update_traces(line_color="#1F3A68", marker={"size": 10, "color": point_colors})

        # Dashed lines with the limits of the traffic light (with their label)
        green_from = indicator_settings["green_from"]
        amber_from = indicator_settings["amber_from"]
        indicator_chart.add_hline(y=green_from, line_dash="dash", line_color=LIGHT_COLOR["Green"],
                                  annotation_text=f"Green from {green_from}%",
                                  annotation_position="top left")
        indicator_chart.add_hline(y=amber_from, line_dash="dash", line_color=LIGHT_COLOR["Amber"],
                                  annotation_text=f"Amber from {amber_from}%",
                                  annotation_position="bottom left")

        # Make sure the values AND the two limits are always visible
        values_and_limits = list(df_one_indicator["Value"].dropna()) + [green_from, amber_from]
        lowest = min(values_and_limits)
        highest = max(values_and_limits)
        margin = (highest - lowest) * 0.15 + 1
        indicator_chart.update_yaxes(range=[lowest - margin, highest + margin])
        indicator_chart.update_layout(template="plotly_white", height=320)

        trend_columns[position_in_grid % 2].plotly_chart(indicator_chart, width="stretch")
        position_in_grid = position_in_grid + 1

    # 2.5 AI analysis (complementary)
    st.divider()
    st.markdown("**AI analysis (complementary)**")
    st.caption(f"Written by an AI model through OpenRouter ({AI_MODEL}) from the colours above. "
               "It has no live internet access: the sector context is general knowledge, "
               "check it against current news before using it.")

    # The current view in plain English (it goes to the AI and to the log)
    current_view_text = (f"Sector: {selected_sector} (Singapore) | Quarter: {selected_quarter} | "
                         f"Traffic light: {final_light} | Credit signal: {CREDIT_SIGNAL.get(final_light)}")
    df_quarter_sector_pillars = df_sector_pillars[df_sector_pillars["Quarter"] == selected_quarter]
    for _, pillar_row in df_quarter_sector_pillars.iterrows():
        current_view_text += f" | {pillar_row['Pillar']} {pillar_row['Pillar name']}: {pillar_row['Light']}"
    if selected_row["Warning"] != "":
        current_view_text += f" | Warning: {selected_row['Warning']}"

    # Answers already generated are kept while the dashboard is open
    if "ai_answers" not in st.session_state:
        st.session_state["ai_answers"] = {}

    ai_api_key = get_ai_api_key()
    if ai_api_key is None:
        st.info(f"To use the AI analysis, add {AI_API_KEY_NAME}=your-key to the .env file "
                "of the project folder and refresh the page.")

    elif st.button(f"Generate AI analysis for {selected_sector} — {selected_quarter}"):
        configure_ai_logging()
        logger.info("action=ai_analysis_button_clicked | current_view_text={}", current_view_text)

        df_previous_indicators = df_sector_indicators[df_sector_indicators["Quarter"] == previous_quarter]
        user_prompt = build_ai_prompt(current_view_text, df_quarter_indicators, df_previous_indicators)

        try:
            with st.spinner("Writing the analysis..."):
                ai_summary, model_used = ask_ai(user_prompt, ai_api_key)
        except Exception as error:
            logger.error("status=failed | error_type={} | error={}", type(error).__name__, error)
            st.error("The AI analysis could not be generated. Check the API key and try again.")
        else:
            logger.info("status=success | model={} | ai_summary={}", model_used, ai_summary)
            st.session_state["ai_answers"][current_view_text] = {
                "ai_summary": ai_summary, "model": model_used, "prompt": user_prompt}

    if current_view_text in st.session_state["ai_answers"]:
        saved_answer = st.session_state["ai_answers"][current_view_text]
        with st.container(border=True):
            st.markdown(saved_answer["ai_summary"])
        st.caption(f"Model used: {saved_answer['model']} · AI commentary: verify before using it.")
        with st.expander("See what was sent to the AI"):
            st.text(AI_SYSTEM_PROMPT + "\n\n" + saved_answer["prompt"])


######################################################################
# TAB 3. INDICATOR DATA: the data behind the colours
######################################################################

if selected_page == "Indicator data":
    st.caption("The underlying data. Business Expectations is shown for context, it does not "
               "change the colours. ESG reporting has no history: only the latest report.")

    # Indicator name shown in the list -> its filtered table
    drill_down_tables = {}
    for indicator_name, indicator_settings in INDICATORS_TO_ANALYSE.items():
        drill_down_tables[indicator_settings["title"]] = filtered_data[indicator_name]
    drill_down_tables["GDP share of total (%)"] = make_gdp_share_table()

    # Unit of each indicator (shown in the axis and in the tables)
    drill_down_units = {}
    for indicator_name, indicator_settings in INDICATORS_TO_ANALYSE.items():
        drill_down_units[indicator_settings["title"]] = indicator_settings["unit"]
    drill_down_units["GDP share of total (%)"] = "% of total GDP"
    esg_option = "ESG reporting (latest report)"
    indicator_options = list(drill_down_tables.keys()) + [esg_option]

    selected_indicator = st.selectbox("Monitoring indicator", indicator_options)

    if selected_indicator == esg_option:
        # ESG: one picture of today, compared between sectors (no trend)
        df_esg_chart = df_esg_risk[df_esg_risk["Sector"].isin(selected_sectors)].copy()
        df_esg_chart["Light"] = df_esg_chart["risk_score"].map(ESG_RISK_TO_LIGHT)
        esg_chart = px.bar(
            df_esg_chart, x="Sector", y="ESG reporting compliance",
            color="Light", color_discrete_map=LIGHT_COLOR, range_y=[0, 100],
            title="Top companies with full ESG reporting (%) — latest report",
            labels={"ESG reporting compliance": "% of companies", "Sector": "Industry"},
        )
        esg_chart.update_layout(template="plotly_white")
        st.plotly_chart(esg_chart, width="stretch")
        st.caption("Sectors without a bar have no ESG data and are counted as High risk.")

    else:
        unit = drill_down_units[selected_indicator]
        filter_columns = st.columns(2)
        years_of_history = filter_columns[0].select_slider("Years of history", options=[1, 3, 5, 10, "All"],
                                                           value=5)
        chart_type = filter_columns[1].radio("Chart type", ["Line", "Bars"], horizontal=True)

        df_trend = make_one_row_per_sector_and_period(drill_down_tables[selected_indicator])
        df_trend = df_trend[df_trend["Sectors"].isin(selected_sectors)].dropna(subset=["Value"])
        if years_of_history != "All" and not df_trend.empty:
            first_year_to_show = df_trend["Date"].dt.year.max() - years_of_history + 1
            df_trend = df_trend[df_trend["Date"].dt.year >= first_year_to_show]

        if chart_type == "Line":
            trend_chart = px.line(
                df_trend, x="Date", y="Value", color="Sectors",
                markers=True, color_discrete_map=SECTOR_COLORS,
                hover_data={"Period": True, "Date": False},
                title=f"{selected_indicator}: trend",
                labels={"Sectors": "Industry", "Value": unit, "Date": "Period"},
            )
        else:
            trend_chart = px.bar(
                df_trend, x="Period", y="Value", color="Sectors", barmode="group",
                color_discrete_map=SECTOR_COLORS,
                title=f"{selected_indicator}: trend",
                labels={"Sectors": "Industry", "Value": unit, "Period": "Period"},
            )
        trend_chart.update_layout(template="plotly_white", hovermode="x unified")
        st.plotly_chart(trend_chart, width="stretch")

        # Latest value available for each sector
        st.markdown("**Latest data available by sector**")
        df_latest = df_trend.sort_values("Date").groupby("Sectors").tail(1)
        df_latest = df_latest[["Sectors", "Period", "Value"]].rename(
            columns={"Sectors": "Industry", "Value": f"Value ({unit})"})
        st.dataframe(df_latest, hide_index=True, width="stretch")

    with st.expander("See the data table"):
        if selected_indicator == esg_option:
            df_table = df_esg_risk[df_esg_risk["Sector"].isin(selected_sectors)]
            st.caption("Unit: % of the top companies with full ESG reporting")
        else:
            df_table = drill_down_tables[selected_indicator]
            df_table = df_table[df_table["Sectors"].isin(selected_sectors)]
            st.caption(f"Unit: {drill_down_units[selected_indicator]}")
        st.dataframe(df_table, hide_index=True, width="stretch")
        download_csv_button(df_table, f"{selected_indicator}.csv")


######################################################################
# TAB 4. ESG: reporting of each sector + the ESG risks of the sector
######################################################################

if selected_page == "ESG":
    st.subheader("ESG reporting — latest report")
    st.caption("The ESG file has no history: it is one picture of today of the top companies "
               "of each sector. The same ESG colour is used in every quarter.")

    # 4.1 How the top companies of each sector report ESG (% Yes / Partially / No)
    df_esg_answers = calculate_esg_answer_percentages(clean_esg(load_table(DATA_FILES["esg"]["table_name"])))
    df_esg_answers = df_esg_answers.reset_index()
    df_esg_answers = df_esg_answers.rename(columns={df_esg_answers.columns[0]: "Sector"})
    df_esg_answers = df_esg_answers[df_esg_answers["Sector"].isin(selected_sectors)]
    df_esg_long = df_esg_answers.melt(id_vars="Sector", var_name="Answer", value_name="% of companies")

    esg_answers_chart = px.bar(
        df_esg_long, x="% of companies", y="Sector", color="Answer", orientation="h",
        color_discrete_map={"Yes": "#1F3A68", "Partially": "#6F8FBF", "No": "#C9D3E3"},
        title="Do the top companies report ESG?",
        labels={"Sector": "Industry"},
    )
    esg_answers_chart.update_layout(template="plotly_white", barmode="stack")
    st.plotly_chart(esg_answers_chart, width="stretch")

    missing_esg_sectors = []
    for sector in selected_sectors:
        if sector not in list(df_esg_answers["Sector"]):
            missing_esg_sectors.append(sector)
    if len(missing_esg_sectors) > 0:
        st.caption(f"No ESG data for: {', '.join(missing_esg_sectors)} -> counted as High risk.")

    # 4.2 ESG risk profile of each sector (texts in config.py)
    st.subheader("ESG risks the sectors tend to have")
    st.caption("General tendencies of each sector in Singapore, not an assessment of each company.")

    for sector in selected_sectors:
        esg_row = df_esg_risk[df_esg_risk["Sector"] == sector].iloc[0]
        esg_light = ESG_RISK_TO_LIGHT[esg_row["risk_score"]]

        with st.expander(f"{sector} · ESG reporting risk: {light_text(esg_light)}"):
            if sector not in ESG_SECTOR_RISKS:
                st.info("Add the ESG profile of this sector in ESG_SECTOR_RISKS (config.py).")
                continue
            risk_columns = st.columns(3)
            for column, risk_type in zip(risk_columns, ["Physical", "Transition", "Governance"]):
                column.markdown(f"**{risk_type} risk**")
                column.markdown(ESG_SECTOR_RISKS[sector][risk_type])

            # Official sources of the texts above
            source_links = []
            for source_name, source_url in ESG_SECTOR_RISKS[sector]["Sources"]:
                source_links.append(f"[{source_name}]({source_url})")
            st.caption("Sources: " + " · ".join(source_links))

    # 4.3 Why it is good that companies publish ESG / TCFD / TNFD reports
    st.subheader("Why ESG, TCFD and TNFD reports matter for credit")
    st.markdown(
        """
        - **TCFD → ISSB (IFRS S2)**: the ISSB Standards fully incorporate the TCFD recommendations, and the
          IFRS Foundation took over monitoring of TCFD from 2024. The company explains its climate
          **governance, strategy, risk management, metrics and targets**: for credit, it shows whether
          management knows its climate risks, its emissions and its transition plan.
        - **TNFD**: the same type of disclosure for **nature** (water, land, biodiversity), with the LEAP
          approach (Locate, Evaluate, Assess, Prepare). Relevant for sectors that depend on water and
          natural resources.
        - **Singapore (ACRA / SGX RegCo, Aug 2025)**: all listed companies report Scope 1 and 2 emissions
          from FY2025. STI companies report full ISSB-based climate disclosures from FY2025 (Scope 3 from
          FY2026); other listed companies from FY2028 (market cap ≥ S$1 billion) or FY2030; large
          non-listed companies from FY2030.
        - **For the bank (MAS Guidelines on Environmental Risk Management)**: banks are expected to assess
          the environmental risk of their customers, with enhanced due diligence and engagement for
          higher-risk sectors. A good report gives the data for that assessment, makes companies
          comparable and is an early signal of how prepared they are for the transition.
        - **No report** is an information gap, not proof of bad performance. That is why the model
          treats it conservatively (as High risk).
        """
    )
    st.caption(
        "Sources: "
        "[IFRS - ISSB and TCFD](https://www.ifrs.org/sustainability/tcfd/) · "
        "[TNFD - LEAP approach](https://tnfd.global/publication/additional-guidance-on-assessment-of-nature-related-issues-the-leap-approach/) · "
        "[ACRA - Climate reporting timelines](https://www.acra.gov.sg/news-events/news-announcements/887/) · "
        "[MAS - Environmental Risk Management Guidelines](https://www.mas.gov.sg/regulation/guidelines/guidelines-on-environmental-risk-management)"
    )


######################################################################
# TAB 5. METHODOLOGY (taken from config.py)
######################################################################

if selected_page == "Methodology":
    st.markdown(
        f"""
        **How the colours work**
        - Each **indicator** gets a colour with its own limits (table below).
        - Each **pillar** (W1, W2, W3) and the **sector** get a colour from their indicators:
          Green earns {POINTS_PER_LIGHT['Green']:.0%} of the indicator's weight,
          Amber {POINTS_PER_LIGHT['Amber']:.0%} and Red {POINTS_PER_LIGHT['Red']:.0%}.
          The result (0-100) gives Green from {GREEN_IF_SCORE_AT_LEAST}, Amber from
          {AMBER_IF_SCORE_AT_LEAST}, and Red below {AMBER_IF_SCORE_AT_LEAST}.
        - With **{NUMBER_OF_REDS_THAT_BLOCK_GREEN} or more Red indicators**, a sector can't be Green
          (maximum Amber). With **1 Red indicator** it can stay Green, with a warning.
        - If an indicator has no data, the colour is calculated with the indicators that have data.

        **Credit signal of each colour** (a starting point for the committee, not a decision)
        - 🟢 Green → {CREDIT_SIGNAL['Green']} · 🟠 Amber → {CREDIT_SIGNAL['Amber']} · 🔴 Red → {CREDIT_SIGNAL['Red']}

        **ESG reporting** comes from the latest ESG report of the top companies of each sector.
        It has no history, so the same ESG colour is used in every quarter. Sectors without ESG
        data are counted as High risk.

        **AI analysis** is a complementary commentary written by an AI model through OpenRouter.
        It does not change the colours and has no live internet access.
        """
    )

    methodology_rows = []
    for indicator_name, indicator_settings in SCORE_INDICATORS.items():
        if indicator_settings["calculation"] == "esg":
            green_text, amber_text, red_text = "Low ESG risk", "Medium ESG risk", "High ESG risk"
        else:
            if indicator_settings["green_includes_limit"]:
                green_symbol = "≥"
            else:
                green_symbol = ">"
            green_text = f"{green_symbol} {indicator_settings['green_from']}"
            amber_text = f"≥ {indicator_settings['amber_from']} and below Green"
            red_text = f"< {indicator_settings['amber_from']}"

        methodology_rows.append({
            "Indicator": indicator_settings["label"],
            "Pillar": f"{indicator_settings['pillar']} {PILLARS[indicator_settings['pillar']]}",
            "Weight": indicator_settings["weight"],
            "Green": green_text,
            "Amber": amber_text,
            "Red": red_text,
        })
    st.dataframe(pd.DataFrame(methodology_rows), hide_index=True, width="stretch")

    with st.expander("Technical data view (for auditing a colour)"):
        st.write("Overall results")
        st.dataframe(df_overall_results, width="stretch")
        download_csv_button(df_overall_results, "overall_results.csv")
        st.write("Pillar results")
        st.dataframe(df_pillar_results, width="stretch")
        download_csv_button(df_pillar_results, "pillar_results.csv")
        st.write("Indicator results")
        st.dataframe(df_indicator_results, width="stretch")
        download_csv_button(df_indicator_results, "indicator_results.csv")
