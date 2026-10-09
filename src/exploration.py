
######################################################################
# Purpose:
## Cleaning and exploration of the datafiles
# ereasing extra rows and columns, as we want to keep only the relevant data for the analysis and dashboard.
# Filtering the data just for the las 10 years, as we want to focus on the most recent data for the analysis and dashboard.
# Filtering to the sectors we are interested in, as we want to focus on the sectors that are relevant for the analysis and dashboard.
# Sectors: Manufacturing , Real Estate , Transportation and Storage ,Information and Communication
# Checking tendency of data and so on
# Creation day: 2026-09-28
# Moficiation day: 2026-10-01
# Created by: @ansanc
# Note that this code uses the help of Copilot or Claude IA, own knowledge and what was learnt in class.


######################################################################
# Same idea for all sources, only the steps change depending on the file.
# Everything we modify to the data before the charts and the score.
#
#   1. Cleaning the indicator files (SingStat)
#   2. Merging files that measure the same thing
#   3. Extra calculations (share of total)
#   4. Time helpers (sort periods, long format, last N years)
#   5. ESG file: compliance and risk
#   6. Data checks (table summary, summary per sector, unusual jumps)
#   7. Charts for exploring the data (Plotly), saved as HTML in Project_Dashboard/output


######################################################################
#%%
# Import libraries
import numpy as np
import pandas as pd
import plotly.express as px
from loguru import logger

from config import (TARGET_SECTORS, MISSING_VALUE_TEXTS, PLOTS_FOLDER, SECTOR_COLORS, SHOW_CHARTS_IN_BROWSER,
                    ESG_SECTOR_COLUMN, ESG_REPORTING_COLUMN, ESG_VALID_ANSWERS,
                    ESG_LOW_RISK_IF_YES_AT_LEAST, ESG_HIGH_RISK_IF_NO_AT_LEAST)

# display() shows tables nicely in the interactive window (if not available, print)
try:
    from IPython.display import display
except ImportError:
    display = print


######################################################################
# 1. CLEANING THE INDICATOR FILES (always BEFORE filtering by sector)
#%%
# This function is used to find the row that has the real column names: 
# the one whose first cell says 'Data Series' (SingStat files). 
# Each file can have it in a different row. 
def find_header_row(df_indicator: pd.DataFrame) -> int | None:
    """Find the row that has the real column names: the one whose first cell
    says 'Data Series' (SingStat files). Each file can have it in a different row.
    Returns None if the column names are already right (header in row 0)."""
    first_column_name = str(df_indicator.columns[0]).replace(" ", "").lower()
    if first_column_name == "dataseries":
        return None

    first_column_text = df_indicator.iloc[:, 0].astype(str).str.replace(" ", "").str.lower()
    header_rows = df_indicator.index[first_column_text == "dataseries"]
    if len(header_rows) > 0:
        return int(header_rows[0])

    return None
#%%
# This function is used to set the column names from a specific row, and then remove that row and any rows above it.
def set_column_names_from_row(df_indicator: pd.DataFrame, header_row: int) -> pd.DataFrame:
    """SingStat files: the row number `header_row` has the column names,
    and the data starts in the next row."""
    df_indicator = df_indicator.copy()
    df_indicator.columns = df_indicator.iloc[header_row]
    df_indicator = df_indicator.iloc[header_row + 1:].reset_index(drop=True)
    return df_indicator
#%%
# This function is used to rename the first column to 'Sectors', remove extra spaces in the column names,
#  and format the quarters consistently.
def rename_sector_column(df_indicator: pd.DataFrame) -> pd.DataFrame:
    """First column -> 'Sectors'. Also removes extra spaces in the column names
    and writes all the quarters the same way: '19801Q' -> '1980 1Q'."""
    column_names = []
    for column in df_indicator.columns:
        column_name = str(column).strip()
        # Quarter without space, e.g. "20252Q" -> "2025 2Q"
        if len(column_name) == 6 and column_name[:5].isdigit() and column_name[5].upper() == "Q":
            column_name = column_name[:4] + " " + column_name[4] + "Q"
        column_names.append(column_name)
    column_names[0] = "Sectors"

    df_indicator = df_indicator.copy()
    df_indicator.columns = column_names
    return df_indicator
#%%
# This function is used to remove bad columns from the DataFrame, 
# such as columns without a name and without data, or repeated column names.
# This tends to happen from cvs/excel files to df
def remove_bad_columns(df_indicator: pd.DataFrame) -> pd.DataFrame:
    """Fix the columns that would break the cleaning:
    - Columns WITHOUT a name (empty cell in the header row) and without data -> removed
    - Columns without a name but WITH data -> kept as 'Unnamed column N' (with a warning)
    - Repeated column names -> only the first one is kept (with a warning)"""
    df_indicator = df_indicator.copy()

    # 1. Columns without a name
    empty_names = ["", "nan", "None", "NaN"]
    columns_to_keep = []
    new_column_names = []
    for position in range(df_indicator.shape[1]):
        column_name = df_indicator.columns[position]
        column_values = df_indicator.iloc[:, position]
        if position > 0 and column_name in empty_names:
            if column_values.isna().all():
                continue                                    # empty column -> removed
            column_name = f"Unnamed column {position}"
            logger.warning("Column {} has no name but has data -> kept as '{}'", position, column_name)
        columns_to_keep.append(position)
        new_column_names.append(column_name)
    df_indicator = df_indicator.iloc[:, columns_to_keep]
    df_indicator.columns = new_column_names

    # 2. Repeated column names -> keep the first one
    is_repeated = df_indicator.columns.duplicated()
    if is_repeated.any():
        logger.warning("Repeated column names, only the first one is kept: {}",
                       list(df_indicator.columns[is_repeated]))
        df_indicator = df_indicator.loc[:, ~is_repeated]

    return df_indicator
#%%
# This function is used to remove footnotes from the DataFrame by cutting it at the 'Definitions and Footnotes' row and dropping empty rows.
def remove_footnotes(df_indicator: pd.DataFrame) -> pd.DataFrame:
    """Cut the df at the 'Definitions and Footnotes' row and drop empty rows."""
    first_column = df_indicator.columns[0]
    first_column_text = df_indicator[first_column].astype(str).str.strip()
    footnote_rows = df_indicator.index[first_column_text.str.startswith('Definitions and Footnotes')]

    if len(footnote_rows) > 0:
        first_footnote_row = footnote_rows[0]
        df_indicator = df_indicator.iloc[:first_footnote_row]

    df_indicator = df_indicator.dropna(how='all').reset_index(drop=True)
    return df_indicator

#%%
# This function is used to convert all the columns except the first one to numbers,
#  treating texts like 'na' or '-' as np NaN .
def convert_values_to_numbers(df_indicator: pd.DataFrame) -> pd.DataFrame:
    """All the columns except the first one -> numbers.
    Texts like 'na' or '-' become NaN (empty)."""
    df_indicator = df_indicator.copy()
    for column in df_indicator.columns[1:]:
        column_values = df_indicator[column].replace(MISSING_VALUE_TEXTS, np.nan)
        df_indicator[column] = pd.to_numeric(column_values, errors='coerce').astype(float)
    return df_indicator

#%%
# This function is used to remove spaces before/after the sector names to avoid mismatches.
def clean_sector_names(df_indicator: pd.DataFrame) -> pd.DataFrame:
    """Remove spaces before/after the sector names to avoid mismatches."""
    df_indicator = df_indicator.copy()
    df_indicator["Sectors"] = df_indicator["Sectors"].astype(str).str.strip()
    return df_indicator

#%%
# This function is used to find the row that has the real column names:
def clean_indicator_file(df_indicator: pd.DataFrame, file_name: str = "") -> pd.DataFrame:
    """All the cleaning steps in order:
    header -> rename -> bad columns -> footnotes -> numbers -> sector names"""
    header_row = find_header_row(df_indicator)
    if header_row is None:
        logger.info("{}: the column names are already in the header", file_name)
    else:
        logger.info("{}: column names found in row {}", file_name, header_row)
        df_indicator = set_column_names_from_row(df_indicator, header_row)
    df_indicator = rename_sector_column(df_indicator)
    df_indicator = remove_bad_columns(df_indicator)
    df_indicator = remove_footnotes(df_indicator)
    df_indicator = convert_values_to_numbers(df_indicator)
    df_indicator = clean_sector_names(df_indicator)
    return df_indicator

#%%
# This function is used to keep only the sectors we are interested in.
def keep_target_sectors(df_indicator: pd.DataFrame, sectors: list[str] = TARGET_SECTORS) -> pd.DataFrame:
    """Keep only the sectors we are interested in."""
    df_filtered = df_indicator[df_indicator["Sectors"].isin(sectors)]
    return df_filtered.reset_index(drop=True)


######################################################################
# 2. MERGING FILES THAT MEASURE THE SAME THING

# This function is used to put several cleaned dfs one below the other (same measure, different sectors).
def merge_indicator_files(list_of_dfs: list[pd.DataFrame]) -> pd.DataFrame:
    """Put several cleaned dfs one below the other (same measure, different sectors).
    Periods that exist in only one of them stay empty (NaN) in the others.
    Columns are ordered from the newest period to the oldest, like SingStat."""
    df_merged = pd.concat(list_of_dfs, ignore_index=True)

    period_columns = []
    for column in df_merged.columns:
        if column != "Sectors":
            period_columns.append(column)
    period_columns = sorted(period_columns, key=convert_period_to_date, reverse=True)

    df_merged = df_merged[["Sectors"] + period_columns]

    # Warn if a sector name appears more than once
    repeated_names = df_merged[df_merged["Sectors"].duplicated()]["Sectors"].unique()
    if len(repeated_names) > 0:
        logger.warning("Rows with the same name after merging: {}", list(repeated_names))

    return df_merged


######################################################################
# 3. EXTRA CALCULATIONS

#%% 
# This function is used to calculate each value as a percentage of the total row in the same period.
def calculate_share_of_total(df_indicator: pd.DataFrame, total_row_name: str) -> pd.DataFrame:
    """Each value as % of the total row in the same period:
    (sector value / total value) * 100. Used for the GDP concentration."""
    total_row = df_indicator[df_indicator["Sectors"] == total_row_name]
    if total_row.empty:
        raise ValueError(f"Total row '{total_row_name}' not found. Rows: {df_indicator['Sectors'].tolist()}")

    df_share = df_indicator.copy()
    for period in df_indicator.columns[1:]:
        total_value = total_row[period].values[0]
        df_share[period] = df_indicator[period] / total_value * 100
    return df_share


######################################################################
# 4. TIME HELPERS (used by the charts, the checks and the score)

#%% 
# This function is used to turn a period label into a real date, so periods can be sorted in time.
def convert_period_to_date(period_label: str) -> pd.Timestamp:
    """Turn a period label into a real date, so periods can be sorted in time.
    '2025 2Q' -> 2025-04-01 | '2024' -> 2024-01-01 | '2025 Jan' -> 2025-01-01"""
    period_label = str(period_label).strip()
    label_parts = period_label.split()
    try:
        # Quarterly, e.g. "2025 2Q"
        if len(label_parts) == 2 and label_parts[1].upper().endswith("Q"):
            year = int(label_parts[0])
            quarter = int(label_parts[1][0])
            return pd.Period(year=year, quarter=quarter, freq="Q").start_time
        # Annual, e.g. "2024"
        if len(label_parts) == 1 and label_parts[0].isdigit():
            return pd.Timestamp(year=int(label_parts[0]), month=1, day=1)
        # Monthly, e.g. "2025 Jan"
        return pd.to_datetime(period_label, format="%Y %b")
    except Exception:
        return pd.NaT

#%%
# This function is used to change the shape of the table from wide format to long format.
def make_one_row_per_sector_and_period(df_indicator: pd.DataFrame) -> pd.DataFrame:
    """Change the shape of the table (same as the melt we did for GDP):
    FROM one row per sector and one column per period  (wide format)
    TO   one row per sector + period, with 4 columns:  (long format)
         Sectors | Period | Value | Date   (sorted in time)
    Plotly and the data checks need the table in this shape."""
    first_column = df_indicator.columns[0]
    df_one_row_per_period = df_indicator.melt(id_vars=[first_column], var_name="Period", value_name="Value")
    df_one_row_per_period = df_one_row_per_period.rename(columns={first_column: "Sectors"})
    df_one_row_per_period["Period"] = df_one_row_per_period["Period"].astype(str).str.strip()
    df_one_row_per_period["Value"] = pd.to_numeric(df_one_row_per_period["Value"], errors="coerce")
    df_one_row_per_period["Date"] = df_one_row_per_period["Period"].apply(convert_period_to_date)
    df_one_row_per_period = df_one_row_per_period.sort_values(["Date", "Sectors"]).reset_index(drop=True)
    return df_one_row_per_period

#%%
# This function is used to find the most recent period that has at least one value.
def find_latest_period_with_data(df_one_row_per_period: pd.DataFrame) -> str:
    """Most recent period that has at least one value."""
    rows_with_value = df_one_row_per_period.dropna(subset=["Value"])
    newest_row = rows_with_value["Date"].idxmax()
    return rows_with_value.loc[newest_row, "Period"]

#%% 
This function is used to keep only the sector column + the periods of the last `n_years` years.
def keep_last_years(df_indicator: pd.DataFrame, n_years: int = 5) -> pd.DataFrame:
    """Keep the sector column + the periods of the last `n_years` years
    (the most recent year in the df counts as year 1)."""
    period_columns = list(df_indicator.columns[1:])

    # Year of each period column
    year_of_column = {}
    for column in period_columns:
        date = convert_period_to_date(column)
        if pd.notna(date):
            year_of_column[column] = date.year

    if len(year_of_column) == 0:
        return df_indicator.copy()

    first_year_to_keep = max(year_of_column.values()) - (n_years - 1)

    columns_to_keep = [df_indicator.columns[0]]
    for column, year in year_of_column.items():
        if year >= first_year_to_keep:
            columns_to_keep.append(column)
    return df_indicator[columns_to_keep].copy()


######################################################################
# 5. ESG FILE: COMPLIANCE AND RISK
# Rule:
#   - If 75% or more of the companies answer Yes  -> Low risk
#   - If 60% or more of the companies answer No   -> High risk
#   - All the rest                                -> Medium risk
#   - Missing answers count as "No", missing sectors get High risk
#%%
# This function is used to clean the text and treat missing/invalid answers as 'No' (worst case).
def clean_esg(df_esg: pd.DataFrame) -> pd.DataFrame:
    """Clean the text and treat missing/invalid answers as 'No' (worst case)."""
    df_esg_clean = df_esg.copy()
    df_esg_clean[ESG_SECTOR_COLUMN] = df_esg_clean[ESG_SECTOR_COLUMN].astype(str).str.strip()
    df_esg_clean[ESG_REPORTING_COLUMN] = df_esg_clean[ESG_REPORTING_COLUMN].astype(str).str.strip().str.capitalize()

    is_invalid_answer = ~df_esg_clean[ESG_REPORTING_COLUMN].isin(ESG_VALID_ANSWERS)
    if is_invalid_answer.sum() > 0:
        invalid_answers = df_esg_clean.loc[is_invalid_answer, ESG_REPORTING_COLUMN].value_counts(dropna=False)
        logger.warning("ESG: {} companies with missing/invalid answer set to 'No': {}",
                       is_invalid_answer.sum(), invalid_answers.to_dict())
    df_esg_clean.loc[is_invalid_answer, ESG_REPORTING_COLUMN] = "No"
    return df_esg_clean

#%%
# This function is used to calculate the percentage of Yes / Partially / No per sector.
def calculate_esg_answer_percentages(df_esg_clean: pd.DataFrame) -> pd.DataFrame:
    """% of Yes / Partially / No per sector.
    A 0 here is NOT missing data: it means 0% of the companies gave that answer."""
    answers_by_sector = df_esg_clean.groupby(ESG_SECTOR_COLUMN)[ESG_REPORTING_COLUMN]
    df_percentages = answers_by_sector.value_counts(normalize=True).unstack(fill_value=0) * 100
    # Make sure the 3 columns always exist
    df_percentages = df_percentages.reindex(columns=ESG_VALID_ANSWERS, fill_value=0)
    return df_percentages

#%%
# This function is used to determine the ESG risk level for one sector based on the percentages of Yes and No answers.
def get_esg_risk_level(yes_percentage: float, no_percentage: float) -> str:
    """Risk rule for one sector."""
    if yes_percentage >= ESG_LOW_RISK_IF_YES_AT_LEAST:
        return "Low"
    elif no_percentage >= ESG_HIGH_RISK_IF_NO_AT_LEAST:
        return "High"
    else:
        return "Medium"

#%%
# This function is used to build the final ESG DataFrame with 3 columns: Sector | ESG reporting compliance | risk_score.
def build_esg_risk_table(df_esg: pd.DataFrame, sectors: list[str] = TARGET_SECTORS) -> pd.DataFrame:
    """Final ESG df with 3 columns: Sector | ESG reporting compliance | risk_score"""
    df_esg_clean = clean_esg(df_esg)
    df_percentages = calculate_esg_answer_percentages(df_esg_clean)

    rows = []
    for sector in df_percentages.index:
        yes_percentage = df_percentages.loc[sector, "Yes"]
        no_percentage = df_percentages.loc[sector, "No"]
        rows.append({
            "Sector": sector,
            "ESG reporting compliance": round(yes_percentage, 2),   # % of companies with Yes
            "risk_score": get_esg_risk_level(yes_percentage, no_percentage),
        })

    # Target sectors with no ESG data -> High risk (worst case)
    missing_sectors = []
    for sector in sectors:
        if sector not in df_percentages.index:
            missing_sectors.append(sector)
            rows.append({
                "Sector": sector,
                "ESG reporting compliance": np.nan,   # no data -> empty, not 0
                "risk_score": "High",
            })
    if len(missing_sectors) > 0:
        logger.warning("ESG: target sectors with no data, set to High risk: {}", missing_sectors)

    return pd.DataFrame(rows)


######################################################################
# 6. DATA CHECKS: tables to zoom in on data that may not make sense

#%%
# This function is used to summarize several DataFrames, showing the number of rows, columns, missing values, and the first column name for each.
def summarize_tables(dictionary_of_dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Quick look at several dfs: rows, columns and missing values of each one."""
    rows = []
    for df_name, df_table in dictionary_of_dfs.items():
        rows.append({
            "Table name": df_name,
            "rows": df_table.shape[0],
            "columns": df_table.shape[1],
            "missing values": int(df_table.isna().sum().sum()),
            "first column": df_table.columns[0],
        })
    return pd.DataFrame(rows)

#%%
# This function is used to check the data quality of a filtered DataFrame, printing and returning summary and jump tables.
def check_data_quality(df_filtered: pd.DataFrame, title: str, unusual_jump_limit: float = 3,
                       show_tables: bool = True) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Prints and returns 2 tables:
    - summary : per sector -> periods, missing values, first/last period with data,
                min, max, mean and latest value
    - jumps   : periods where the change vs the previous period is unusually big
                for that sector (more than `unusual_jump_limit` standard deviations)
    Also warns about sectors that appear twice.
    show_tables=False -> only the warnings in the log, without printing the tables."""
    logger.info("Data check: {}", title)
    if df_filtered.empty:
        logger.warning("{}: EMPTY DataFrame -> check the sector names in this file", title)
        return None, None

    # Sectors that appear more than once
    repeated_sectors = df_filtered[df_filtered["Sectors"].duplicated()]["Sectors"].unique()
    if len(repeated_sectors) > 0:
        logger.warning("{}: sectors that appear more than once: {}", title, list(repeated_sectors))

    df_one_row_per_period = make_one_row_per_sector_and_period(df_filtered)

    summary_rows = []
    jump_tables = []
    for sector in df_one_row_per_period["Sectors"].unique():
        sector_rows = df_one_row_per_period[df_one_row_per_period["Sectors"] == sector].copy()
        sector_rows_with_value = sector_rows.dropna(subset=["Value"])

        # Summary of this sector
        has_values = len(sector_rows_with_value) > 0
        summary_rows.append({
            "Sector": sector,
            "Periods": len(sector_rows),
            "Missing": sector_rows["Value"].isna().sum(),
            "% Missing": round(sector_rows["Value"].isna().mean() * 100, 1),
            "First period": sector_rows_with_value["Period"].iloc[0] if has_values else None,
            "Last period": sector_rows_with_value["Period"].iloc[-1] if has_values else None,
            "Min": sector_rows_with_value["Value"].min(),
            "Max": sector_rows_with_value["Value"].max(),
            "Mean": round(sector_rows_with_value["Value"].mean(), 2),
            "Latest value": sector_rows_with_value["Value"].iloc[-1] if has_values else None,
        })

        # Unusual jumps of this sector:
        # change vs the previous period, compared with the usual change of the sector
        sector_rows["Change"] = sector_rows["Value"].diff()
        average_change = sector_rows["Change"].mean()
        usual_variation = sector_rows["Change"].std()
        sector_rows["Jump size (std)"] = (sector_rows["Change"] - average_change) / usual_variation
        unusual_rows = sector_rows[sector_rows["Jump size (std)"].abs() > unusual_jump_limit]
        jump_tables.append(unusual_rows[["Sectors", "Period", "Value", "Change", "Jump size (std)"]])

    summary = pd.DataFrame(summary_rows).sort_values("Sector").reset_index(drop=True)
    jumps = pd.concat(jump_tables).round(2).reset_index(drop=True)

    if show_tables:
        display(summary)
    if len(jumps) > 0:
        logger.warning("{}: {} unusual jumps (more than {} standard deviations): {}",
                       title, len(jumps), unusual_jump_limit,
                       list(zip(jumps["Sectors"], jumps["Period"])))
        if show_tables:
            display(jumps)
    return summary, jumps


######################################################################
# 7. CHARTS (Plotly). Each one is saved as HTML in Project_Dashboard/output
#   plot_trend_charts             -> line trend + grouped bars by sector
#   plot_share_of_total_donuts    -> donuts (only for amounts that add up: GDP, GOS)
#   plot_sectors_vs_total         -> bars vs the total (ratios, per worker, expectations)
#   plot_all_charts_for_indicator -> picks the right charts for one indicator

#%%
# This function is used to save the chart as HTML in the plots folder and (optionally) open it in the browser.
def save_and_show_chart(figure, file_name: str) -> None:
    """Save the chart as HTML in the plots folder and (optionally) open it in the browser."""
    PLOTS_FOLDER.mkdir(exist_ok=True)
    figure.write_html(PLOTS_FOLDER / file_name, include_plotlyjs="cdn")
    if SHOW_CHARTS_IN_BROWSER:
        figure.show(renderer="browser")

# This function is used to make a file name from the chart title, 
# converting it to lowercase and replacing spaces with underscores.
def make_chart_file_name(title: str) -> str:
    """'Gross Operating Surplus' -> 'gross_operating_surplus' (for the file names)"""
    return title.lower().replace("&", "and").replace(" ", "_")


######################################################################
# 7.1 LINE TREND AND GROUPED BARS

# %%
# This function is used to create a line chart with the full history of each sector, 
# and grouped bars comparing the sectors in the last `number_of_bar_periods` periods.
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


######################################################################
# 7.2 DONUTS (only for amounts that add up to a total)

#%% 
# This function is used to create two donut charts: one showing the share of selected sectors vs 'Other Sectors' 
# and another zooming in on the selected sectors only.
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


