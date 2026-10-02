## Functions and so on for plots
# ###
#  Purpose of this file:
# This file looks to generate plot to explore the data 
# ###
# Creation day: 2026-09-15
# Moficiation day: 2026-09-28
# Created by: @ansanc
# Note that this code uses the help of Copilot, own knowledge and what was learnt in class.

# All the CHARTS (Plotly). Each one is saved as HTML in main_folder/plots

#   1. plot_trend_charts             -> line trend + grouped bars by sector
#   2. plot_share_of_total_donuts    -> donuts (only for amounts that add up: GDP, GOS)
#   3. plot_sectors_vs_total         -> bars vs the total (ratios, per worker, expectations)
#   4. plot_all_charts_for_indicator -> picks the right charts for one indicator


# import libraries
import pandas as pd
import plotly.express as px
from loguru import logger

from config import PLOTS_FOLDER, SECTOR_COLORS, SHOW_CHARTS_IN_BROWSER
from exploration import make_one_row_per_sector_and_period, find_latest_period_with_data


def save_and_show_chart(figure, file_name: str) -> None:
    """Save the chart as HTML in the plots folder and (optionally) open it in the browser."""
    PLOTS_FOLDER.mkdir(exist_ok=True)
    figure.write_html(PLOTS_FOLDER / file_name, include_plotlyjs="cdn")
    if SHOW_CHARTS_IN_BROWSER:
        figure.show(renderer="browser")


def make_chart_file_name(title: str) -> str:
    """'Gross Operating Surplus' -> 'gross_operating_surplus' (for the file names)"""
    return title.lower().replace("&", "and").replace(" ", "_")


# =====================================================================
# 1. LINE TREND AND GROUPED BARS
# =====================================================================
def plot_trend_charts(df_filtered: pd.DataFrame, title: str, unit: str,
                      number_of_bar_periods: int = 20) -> None:
    """Line chart with the full history of each sector, and grouped bars
    comparing the sectors in the last `number_of_bar_periods` periods."""
    if df_filtered.empty:
        logger.warning("{}: the filtered DataFrame is EMPTY -> check the sector names in this file", title)
        return

    df_one_row_per_period = make_one_row_per_sector_and_period(df_filtered)

    # Line chart
    line_chart = px.line(
        df_one_row_per_period, x="Date", y="Value", color="Sectors",
        markers=True,
        color_discrete_map=SECTOR_COLORS,
        hover_data={"Period": True, "Date": False},
        title=f"{title}: trend by industry sector",
        labels={"Date": "Period", "Value": unit, "Sectors": "Industry Sector"},
    )
    line_chart.update_layout(template="plotly_white", hovermode="x unified",
                             legend_title="Industry Sectors")
    save_and_show_chart(line_chart, f"{make_chart_file_name(title)}_trend_line.html")

    # Grouped bars: only the last periods, in time order
    periods_in_time_order = df_one_row_per_period.drop_duplicates("Period").sort_values("Date")["Period"].tolist()
    last_periods = periods_in_time_order[-number_of_bar_periods:]
    df_bar = df_one_row_per_period[df_one_row_per_period["Period"].isin(last_periods)]

    bar_chart = px.bar(
        df_bar, x="Period", y="Value", color="Sectors",
        barmode="group",
        color_discrete_map=SECTOR_COLORS,
        category_orders={"Period": last_periods},
        title=f"{title}: sector comparison (last {len(last_periods)} periods)",
        labels={"Period": "Period", "Value": unit, "Sectors": "Industry Sector"},
    )
    bar_chart.update_layout(template="plotly_white", legend_title="Industry Sectors")
    save_and_show_chart(bar_chart, f"{make_chart_file_name(title)}_sector_bar.html")


# =====================================================================
# 2. DONUTS (only for amounts that add up to a total)
# =====================================================================
def plot_share_of_total_donuts(df_clean: pd.DataFrame, df_filtered: pd.DataFrame,
                               total_row_name: str | None, title: str) -> None:
    """Donut 1: selected sectors vs 'Other Sectors' (share of the total).
    Donut 2: zoom in on the selected sectors only.
    df_clean = cleaned df with ALL the rows (it needs the total row)"""
    if total_row_name is None:
        logger.info("{}: no total row defined, donuts skipped", title)
        return

    total_row = df_clean[df_clean["Sectors"] == total_row_name]
    if total_row.empty:
        logger.warning("{}: total row '{}' not found. Row names in this df are: {}",
                       title, total_row_name, df_clean["Sectors"].tolist())
        return

    # Latest period where the total has a value
    newest_period = find_latest_period_with_data(make_one_row_per_sector_and_period(total_row))
    total_value = total_row[newest_period].values[0]

    # % of the total for each selected sector
    df_pie = df_filtered[["Sectors", newest_period]].copy()
    df_pie.columns = ["Sector", "Percentage"]
    df_pie["Percentage"] = df_pie["Percentage"] / total_value * 100
    selected_sectors_percentage = df_pie["Percentage"].sum()

    # Donut 1: selected sectors + "Other Sectors"
    other_sectors_percentage = max(0.0, 100.0 - selected_sectors_percentage)
    other_sectors_row = pd.DataFrame([{"Sector": "Other Sectors", "Percentage": other_sectors_percentage}])
    df_pie_with_others = pd.concat([df_pie, other_sectors_row], ignore_index=True)

    donut_total = px.pie(
        df_pie_with_others, names="Sector", values="Percentage", hole=0.4,
        color="Sector", color_discrete_map=SECTOR_COLORS,
        title=f"{title}: share of total ({newest_period}) — selected vs. other sectors",
    )
    donut_total.update_traces(textposition="inside", textinfo="percent+label",
                              hovertemplate="<b>%{label}</b><br>Share of total: %{value:.2f}%<extra></extra>")
    donut_total.update_layout(template="plotly_white", legend_title="Sectors Breakdown")
    save_and_show_chart(donut_total, f"{make_chart_file_name(title)}_total_concentration.html")

    # Donut 2: zoom in on the selected sectors
    donut_selected = px.pie(
        df_pie, names="Sector", values="Percentage", hole=0.4,
        color="Sector", color_discrete_map=SECTOR_COLORS,
        title=f"{title}: selected sectors ({newest_period}) — {selected_sectors_percentage:.2f}% of the total",
    )
    donut_selected.update_traces(textposition="inside", textinfo="percent+label",
                                 hovertemplate="<b>%{label}</b><br>Share of total: %{value:.2f}%<extra></extra>")
    donut_selected.update_layout(template="plotly_white", legend_title="Selected Sectors")
    save_and_show_chart(donut_selected, f"{make_chart_file_name(title)}_selected_sectors.html")


# =====================================================================
# 3. BARS VS TOTAL (ratios, per worker, expectations)
# A donut makes no sense here: a ratio doesn't add up to a total.
# =====================================================================
def plot_sectors_vs_total(df_clean: pd.DataFrame, df_filtered: pd.DataFrame,
                          total_row_name: str | None, title: str, unit: str) -> None:
    """Horizontal bars with the latest value of each selected sector,
    plus a dashed line with the value of the whole economy (if there is a total row)."""
    if df_filtered.empty:
        logger.warning("{}: the filtered DataFrame is EMPTY -> check the sector names in this file", title)
        return

    df_one_row_per_period = make_one_row_per_sector_and_period(df_filtered)
    newest_period = find_latest_period_with_data(df_one_row_per_period)
    df_bar = df_one_row_per_period[df_one_row_per_period["Period"] == newest_period].sort_values("Value")

    bar_chart = px.bar(
        df_bar, x="Value", y="Sectors", orientation="h",
        color="Sectors", color_discrete_map=SECTOR_COLORS,
        title=f"{title}: selected sectors vs. total ({newest_period})",
        labels={"Value": unit, "Sectors": "Industry Sector"},
    )

    # Dashed line with the total (only if the file has a total row)
    if total_row_name is not None:
        total_row = df_clean[df_clean["Sectors"] == total_row_name]
        if total_row.empty:
            logger.warning("{}: total row '{}' not found, plotting without the total line. Row names: {}",
                           title, total_row_name, df_clean["Sectors"].tolist())
        else:
            total_value = total_row[newest_period].values[0]
            bar_chart.add_vline(x=total_value, line_dash="dash", line_color="#555555",
                                annotation_text=f"{total_row_name}: {total_value:,.2f}",
                                annotation_position="top")

    bar_chart.update_layout(template="plotly_white", showlegend=False)
    save_and_show_chart(bar_chart, f"{make_chart_file_name(title)}_vs_total.html")


# =====================================================================
# 4. ALL THE CHARTS OF ONE INDICATOR
# =====================================================================
def plot_all_charts_for_indicator(df_clean: pd.DataFrame, df_filtered: pd.DataFrame,
                                  indicator_settings: dict) -> None:
    """indicator_settings = one entry of INDICATORS_TO_ANALYSE in config.py"""
    title = indicator_settings["title"]
    unit = indicator_settings["unit"]
    total_row_name = indicator_settings["total_row"]

    plot_trend_charts(df_filtered, title, unit)

    if indicator_settings["adds_up_to_total"]:
        plot_share_of_total_donuts(df_clean, df_filtered, total_row_name, title)
    else:
        plot_sectors_vs_total(df_clean, df_filtered, total_row_name, title, unit)