"""Industry Monitoring System — Streamlit UI using the existing AllCode.py engine.

Place in src/ beside AllCode.py. Run from repository root:
    uv run streamlit run src/industry_monitoring_dashboard.py

Your repository must also contain the seven original data files in data/.
The analysis and traffic-light rules remain in AllCode.py.
"""
from pathlib import Path
import importlib.util
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

st.set_page_config(page_title="Industry Monitoring System", page_icon="📊", layout="wide")
ROOT = Path(__file__).resolve().parent.parent
ENGINE_PATH = Path(__file__).resolve().parent / "AllCode.py"
DATA_DIR = ROOT / "data"
COLORS = {"Green": "#22956A", "Amber": "#E5A232", "Red": "#D75A58"}
ICONS = {"Green": "🟢", "Amber": "🟠", "Red": "🔴"}
PAGES = ["Overview", "Industry Deep Dive", "Indicator Explorer", "Methodology & Data"]
RAW_METRICS = {
    "Real GDP": ("df_GDP_Growth_filtered", "Million chained 2015 dollars"),
    "GDP share of total": ("df_GDP_Share_filtered", "% of GDP"),
    "Gross Operating Surplus": ("df_GrossOperatingSurplusGrowth_filtered", "Million dollars"),
    "Labour Productivity": ("df_LabourProductivity_filtered", "Value added per worker"),
    "Equity Ratio": ("df_EquityRatio_filtered", "%"),
    "Business Expectations": ("df_Business_Expectations_filtered", "Net weighted balance (%)"),
}


def sort_period(period):
    """Convert e.g. '2025 2Q' to sortable year-quarter tuple."""
    parts = str(period).split()
    try:
        year = int(parts[0])
        quarter = int(parts[1][:-1]) if len(parts) > 1 and parts[1].endswith("Q") else 0
        return year, quarter
    except (ValueError, IndexError):
        return 0, 0


def pretty_period(period):
    pieces = str(period).split()
    return f"{pieces[0]} Q{pieces[1][:-1]}" if len(pieces) > 1 and pieces[1].endswith("Q") else str(period)


def status(light):
    return f"{ICONS.get(str(light), '⚪')} {light}" if pd.notna(light) else "⚪ No data"


def fmt_num(value, digits=1):
    return f"{value:,.{digits}f}" if pd.notna(value) else "No data"


def clean_plot(fig, height=390):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=12, r=20, t=40, b=20),
                      legend_title_text="", hovermode="closest")
    return fig


@st.cache_resource(show_spinner="Loading the industry risk assessment...")
def get_engine():
    """Use exactly the existing analysis engine, with browser charts suppressed."""
    if not ENGINE_PATH.is_file():
        raise FileNotFoundError(f"AllCode.py must be in the same folder as this file: {ENGINE_PATH.parent}")
    if not DATA_DIR.is_dir():
        raise FileNotFoundError(f"Data folder missing: {DATA_DIR}")
    # AllCode.py generates a SQLite database in data/; do not silently create a missing data folder.
    original_show = pio.show
    pio.show = lambda *args, **kwargs: None
    try:
        spec = importlib.util.spec_from_file_location("industry_analysis_dashboard_backend", ENGINE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        pio.show = original_show
    required = ("df_overall_results", "df_indicator_results", "df_pillar_results", "TARGET_SECTORS", "SCORE_INDICATORS")
    for name in required:
        if not hasattr(module, name):
            raise AttributeError(f"AllCode.py is missing expected output: {name}")
    return module


try:
    eng = get_engine()
except Exception as error:
    st.error("Could not load AllCode.py and its source data.")
    st.exception(error)
    st.info("Make sure both Python files are in src/, the seven source CSV/XLSX files are in data/, and the dependencies are installed.")
    st.stop()

overall = eng.df_overall_results.copy()
indicators = eng.df_indicator_results.copy()
pillars = eng.df_pillar_results.copy()
sectors = list(eng.TARGET_SECTORS)
quarters = sorted(overall["Quarter"].dropna().astype(str).unique().tolist(), key=sort_period)
if not quarters:
    st.error("No assessment quarters are available from AllCode.py.")
    st.stop()
for frame in (overall, indicators, pillars):
    frame["Quarter"] = frame["Quarter"].astype(str)

if "page" not in st.session_state:
    st.session_state.page = PAGES[0]
if "sector" not in st.session_state or st.session_state.sector not in sectors:
    st.session_state.sector = sectors[0]
if "quarter" not in st.session_state or st.session_state.quarter not in quarters:
    st.session_state.quarter = quarters[-1]
if "trend_years" not in st.session_state:
    st.session_state.trend_years = 5


def open_sector(sector):
    st.session_state.sector = sector
    st.session_state.page = "Industry Deep Dive"


# ------------------------- Sidebar: context-dependent filters -------------------------
st.sidebar.title("📊 Industry Monitor")
st.sidebar.caption("Navigate between the analysis views")
st.sidebar.radio("Pages", PAGES, key="page", label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.subheader("Filters")
st.sidebar.selectbox("Assessment quarter", quarters, format_func=pretty_period, key="quarter")

if st.session_state.page == "Industry Deep Dive":
    st.sidebar.selectbox("Industry", sectors, key="sector")
elif st.session_state.page == "Indicator Explorer":
    st.sidebar.selectbox("Indicator", list(RAW_METRICS), key="raw_metric")
    if "explorer_sectors" not in st.session_state:
        st.session_state.explorer_sectors = sectors.copy()
    st.sidebar.multiselect("Compare industries", sectors, key="explorer_sectors")
    st.sidebar.select_slider("Historical period", options=[1, 3, 5, 10, "All"], key="trend_years")
elif st.session_state.page == "Overview":
    st.sidebar.caption("All monitored industries remain visible on the overview.")
else:
    st.sidebar.caption("Methodology reflects the team's existing scoring settings.")
st.sidebar.divider()
st.sidebar.caption("Assessment: Green = relatively strong; Amber = watch; Red = elevated risk. These are model classifications, not investment advice.")

st.title("Industry Monitoring System")
st.caption("Singapore industries | Economic, financial and operational indicators | Risk signals based on the team's predefined scoring model")
selected_quarter = st.session_state.quarter
snapshot = overall[overall["Quarter"] == selected_quarter].copy()
snapshot["Status"] = snapshot["Final light"].map(status)
snapshot["Rank"] = snapshot["Score"].rank(ascending=False, method="min")
snapshot = snapshot.sort_values("Score", ascending=False, na_position="last")

# ------------------------- Page 1: overview (ALL industries) -------------------------
if st.session_state.page == "Overview":
    st.subheader(f"Industry overview · {pretty_period(selected_quarter)}")
    st.write("See which sectors may require attention before investigating the underlying drivers.")
    c1, c2, c3, c4 = st.columns(4)
    count_green = (snapshot["Final light"] == "Green").sum()
    count_amber = (snapshot["Final light"] == "Amber").sum()
    count_red = (snapshot["Final light"] == "Red").sum()
    c1.metric("🟢 Green industries", int(count_green))
    c2.metric("🟠 Amber industries", int(count_amber))
    c3.metric("🔴 Red industries", int(count_red))
    c4.metric("Industries monitored", len(snapshot))
    st.markdown("#### Which industries need attention?")
    left, right = st.columns([1.5, 1], gap="large")
    with left:
        scored = snapshot.dropna(subset=["Score"])
        if not scored.empty:
            fig = px.bar(scored, x="Score", y="Sectors", color="Final light", orientation="h",
                         text="Score", range_x=[0, 110], color_discrete_map=COLORS,
                         labels={"Sectors": "Industry", "Score": "Score (0–100)", "Final light": "Status"})
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(clean_plot(fig, 370), use_container_width=True)
        else:
            st.info("No numerical scores are available for this quarter.")
    with right:
        st.write("**Select an industry to investigate**")
        for sector in sectors:
            record = snapshot[snapshot["Sectors"] == sector]
            label = f"{sector}  ·  {status(record.iloc[0]['Final light']) if not record.empty else 'No data'}"
            st.button(label, key=f"sector_{sector}", use_container_width=True, on_click=open_sector, args=(sector,))
    st.markdown("#### Assessment detail")
    view = snapshot[["Sectors", "Score", "Status", "Red indicators", "Data coverage %"]].rename(
        columns={"Sectors": "Industry", "Red indicators": "Red indicators", "Data coverage %": "Coverage (%)"})
    st.dataframe(view, hide_index=True, use_container_width=True)
    with st.expander("Historical traffic-light heatmap", expanded=False):
        hist = overall.pivot(index="Sectors", columns="Quarter", values="Final light").reindex(index=sectors)
        numeric = hist.replace({"Red": 0, "Amber": 1, "Green": 2})
        ordered = sorted(hist.columns, key=sort_period)
        chart = go.Figure(go.Heatmap(z=numeric[ordered].to_numpy(dtype=float), x=[pretty_period(x) for x in ordered],
                                    y=hist.index.tolist(), text=hist[ordered].fillna("No data").values,
                                    texttemplate="%{text}", zmin=0, zmax=2,
                                    colorscale=[[0, COLORS["Red"]], [0.49, COLORS["Red"]], [0.5, COLORS["Amber"]],
                                                [0.74, COLORS["Amber"]], [0.75, COLORS["Green"]], [1, COLORS["Green"]]],
                                    showscale=False, hovertemplate="%{y} · %{x}<br>%{text}<extra></extra>"))
        st.plotly_chart(clean_plot(chart, 310), use_container_width=True)
        st.caption("Ratings shown are the final traffic lights, including any override rules.")

# ------------------------- Page 2: single-industry detail -------------------------
elif st.session_state.page == "Industry Deep Dive":
    sector = st.session_state.sector
    st.subheader(f"{sector} · {pretty_period(selected_quarter)}")
    one = snapshot[snapshot["Sectors"] == sector]
    if one.empty:
        st.warning("No assessment for the selected industry and quarter.")
        st.stop()
    record = one.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Final status", status(record["Final light"]))
    c2.metric("Industry score", f"{fmt_num(record['Score'])} / 100")
    c3.metric("Red indicators", int(record["Red indicators"]))
    c4.metric("Data coverage", f"{record['Data coverage %']:.0f}%")
    if isinstance(record["Warning"], str) and record["Warning"].strip():
        st.warning(record["Warning"])
    if record["Data coverage %"] < 100:
        st.info("Some inputs were unavailable. The underlying scoring engine rescales available indicator weights; interpret the score alongside coverage.")
    st.markdown("#### What drives the rating?")
    detail = indicators[(indicators["Quarter"] == selected_quarter) & (indicators["Sectors"] == sector)].copy()
    detail["Status"] = detail["Light"].map(status)
    detail["Indicator value"] = detail["Value"].map(lambda x: fmt_num(x, 2))
    detail = detail[["Label", "Indicator value", "Value period", "Status", "Weight", "Points", "Pillar"]]
    detail.columns = ["Indicator", "Value", "Source period", "Status", "Weight (%)", "Earned points", "Pillar"]
    st.dataframe(detail, hide_index=True, use_container_width=True)
    p = pillars[(pillars["Quarter"] == selected_quarter) & (pillars["Sectors"] == sector)].copy()
    st.markdown("#### Three risk pillars")
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        p_plot = p.dropna(subset=["Score"])
        if not p_plot.empty:
            chart = px.bar(p_plot, x="Pillar name", y="Score", color="Light", text="Score", range_y=[0, 110],
                           color_discrete_map=COLORS, labels={"Pillar name": "Pillar", "Score": "Pillar score"})
            chart.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            st.plotly_chart(clean_plot(chart), use_container_width=True)
    with right:
        p["Status"] = p["Light"].map(status)
        st.dataframe(p[["Pillar name", "Score", "Status", "Data coverage %"]].rename(
            columns={"Pillar name": "Pillar", "Data coverage %": "Coverage (%)"}), hide_index=True,
            use_container_width=True)
        st.caption("Economic performance: GDP and GOS. Financial health: equity ratio. Workforce/operational: productivity and ESG.")
    st.markdown("#### Has the industry improved?")
    hist = overall[overall["Sectors"] == sector].copy().sort_values("Quarter", key=lambda x: x.map(sort_period))
    fig = go.Figure(go.Scatter(x=[pretty_period(x) for x in hist["Quarter"]], y=hist["Score"],
                               mode="lines+markers", line={"width": 3}, marker={"size": 7},
                               customdata=hist[["Final light", "Data coverage %"]].fillna("No data").to_numpy(),
                               hovertemplate="Quarter %{x}<br>Score %{y:.1f}<br>Status %{customdata[0]}<br>Coverage %{customdata[1]}<extra></extra>"))
    fig.add_hline(y=75, line_dash="dash", line_color=COLORS["Green"], annotation_text="Green threshold")
    fig.add_hline(y=40, line_dash="dash", line_color=COLORS["Amber"], annotation_text="Amber threshold")
    fig.update_yaxes(range=[0, 105], title="Score (0–100)")
    st.plotly_chart(clean_plot(fig, 340), use_container_width=True)
    st.caption("The score alone does not determine final status when a two-Red-indicator override applies.")
    if st.button("Explore the underlying economic indicators →", use_container_width=True):
        st.session_state.page = "Indicator Explorer"
        st.session_state.explorer_sectors = [sector]
        st.rerun()

# ------------------------- Page 3: raw-data indicator explorer -------------------------
elif st.session_state.page == "Indicator Explorer":
    metric = st.session_state.get("raw_metric", "Real GDP")
    chosen = st.session_state.get("explorer_sectors", sectors)
    years = st.session_state.get("trend_years", 5)
    st.subheader("Indicator Explorer")
    st.write("Select an indicator and industries in the left sidebar to compare their historical movements.")
    st.caption("Business Expectations is a contextual indicator and does not contribute to the team's final industry score.")
    source_name, unit = RAW_METRICS[metric]
    wide = getattr(eng, source_name).copy()
    long = wide.melt(id_vars="Sectors", var_name="Period", value_name="Value")
    long["Period"] = long["Period"].astype(str)
    long["Year"] = long["Period"].map(lambda v: sort_period(v)[0])
    long["Period order"] = long["Period"].map(sort_period)
    if years != "All" and not long.empty:
        latest_year = int(long["Year"].max())
        long = long[long["Year"] >= latest_year - int(years) + 1]
    long = long[long["Sectors"].isin(chosen)].dropna(subset=["Value"]).sort_values("Period order")
    if not chosen:
        st.info("Select at least one industry in the sidebar.")
    elif long.empty:
        st.warning("No data available for the selected indicator and industries.")
    else:
        ordering = sorted(long["Period"].unique().tolist(), key=sort_period)
        long["Period label"] = pd.Categorical(long["Period"].map(pretty_period),
                                               categories=[pretty_period(x) for x in ordering], ordered=True)
        left, right = st.columns([1, 3])
        with left:
            chart_kind = st.radio("Chart style", ["Line", "Grouped bars"], horizontal=False)
        with right:
            st.caption(f"{metric} · {unit}")
        common = dict(data_frame=long, x="Period label", y="Value", color="Sectors",
                      color_discrete_map=eng.SECTOR_COLORS,
                      labels={"Value": unit, "Period label": "Period", "Sectors": "Industry"})
        fig = px.line(**common, markers=True) if chart_kind == "Line" else px.bar(**common, barmode="group")
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(clean_plot(fig, 480), use_container_width=True)
        latest = long.sort_values("Period order").groupby("Sectors", as_index=False).tail(1)
        st.markdown("#### Latest available observations by industry")
        st.dataframe(latest[["Sectors", "Period", "Value"]].rename(columns={"Sectors": "Industry"}),
                     use_container_width=True, hide_index=True)
        with st.expander("View / download selected indicator data"):
            raw = long[["Sectors", "Period", "Value"]].rename(columns={"Sectors": "Industry"})
            st.dataframe(raw, use_container_width=True, hide_index=True)
            st.download_button("Download CSV", raw.to_csv(index=False).encode("utf-8"),
                               file_name="industry_indicator_data.csv", mime="text/csv")

# ------------------------- Page 4: transparent methodology -------------------------
else:
    st.subheader("Scoring Methodology & Data")
    st.write("These are the thresholds and weights defined by your teammate in AllCode.py; this dashboard does not change them.")
    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 Green", "Score ≥ 75")
    c2.metric("🟠 Amber", "40 ≤ Score < 75")
    c3.metric("🔴 Red", "Score < 40")
    st.markdown("#### Indicator thresholds and weights")
    rows = []
    for code, setting in eng.SCORE_INDICATORS.items():
        if setting["calculation"] == "esg":
            green, amber, red = "Low ESG risk", "Medium ESG risk", "High ESG risk"
        else:
            boundary = "≥" if setting["green_includes_limit"] else ">"
            green = f"{boundary} {setting['green_from']}"
            amber = f"≥ {setting['amber_from']} and below Green"
            red = f"< {setting['amber_from']}"
        rows.append({"Indicator": setting["label"], "Pillar": eng.PILLARS[setting["pillar"]],
                     "Weight (%)": setting["weight"], "Green": green, "Amber": amber, "Red": red})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    with st.expander("How does the score work?", expanded=True):
        st.markdown("""- Green earns 100% of an indicator's weight; Amber earns 50%; Red earns 0%.
- Available indicator points are divided by available weight and scaled to 100.
- **Data coverage** indicates how much of the configured weight was actually available.
- If a Green industry has **2 or more Red indicators**, the final status becomes Amber.
- If a Green industry has **1 Red indicator**, it stays Green but receives a warning.
- The ESG assessment is treated as a static report across quarters in the current model.
- Missing or invalid ESG reporting answers are treated as **No**; sectors without ESG reporting are classified High ESG risk.
- Business Expectations is shown only for context, not counted in the final score.""")
    with st.expander("Data pipeline and source tables"):
        st.write("CSV / XLSX input → SQLite → clean/standardize → calculate growth/ESG → weighted score → dashboard")
        st.write("The dashboard's source is AllCode.py; the underlying raw files are stored in the data folder.")
    with st.expander("Technical tables and downloads"):
        table_name = st.selectbox("Table", ["Overall results", "Indicator results", "Pillar results"])
        table_data = {"Overall results": overall, "Indicator results": indicators, "Pillar results": pillars}[table_name]
        st.dataframe(table_data, use_container_width=True, hide_index=True)
        st.download_button("Download selected table", table_data.to_csv(index=False).encode("utf-8"),
                           file_name=table_name.lower().replace(" ", "_") + ".csv", mime="text/csv")
