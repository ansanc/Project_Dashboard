# %%
## Cleaning and exploration of the datafiles
# ereasing extra rows and columns, as we want to keep only the relevant data for the analysis and dashboard.

# Filtering the data just for the las 10 years, as we want to focus on the most recent data for the analysis and dashboard.

# Filtering to the sectors we are interested in, as we want to focus on the sectors that are relevant for the analysis and dashboard.
# Sectors: Manufacturing , Real Estate , Transportation and Storage ,Information and Communication


# Same idea for all sources, only the steps change depending on the file.
# Everything we modify to the data before the charts and the score.
#
#   1. Cleaning the indicator files (SingStat)
#   2. Merging files that measure the same thing
#   3. Extra calculations (share of total)
#   4. Time helpers (sort periods, long format, last N years)
#   5. ESG file: compliance and risk
#   6. Data checks (table summary, summary per sector, unusual jumps)
# =====================================================================
# =====================================================================
# exploration.py
# Everything we DO to the data before the charts and the score.
#
#   1. Cleaning the indicator files (SingStat)
#   2. Merging files that measure the same thing
#   3. Extra calculations (share of total)
#   4. Time helpers (sort periods, long format, last N years)
#   5. ESG file: compliance and risk
#   6. Data checks (table summary, summary per sector, unusual jumps)
# =====================================================================

# Import libraries

import numpy as np # Managing number
import pandas as pd # managing of df
from loguru import logger # to manage log alerts

from config import (TARGET_SECTORS, MISSING_VALUE_TEXTS,
                    ESG_SECTOR_COLUMN, ESG_REPORTING_COLUMN, ESG_VALID_ANSWERS,
                    ESG_LOW_RISK_IF_YES_AT_LEAST, ESG_HIGH_RISK_IF_NO_AT_LEAST)

# =====================================================================
# 1. CLEANING THE INDICATOR FILES (always BEFORE filtering by sector)
# =====================================================================
def set_column_names_from_row(df_indicator: pd.DataFrame, header_row: int) -> pd.DataFrame:
    """SingStat files: the row number `header_row` has the column names,
    and the data starts in the next row."""
    df_indicator = df_indicator.copy()
    df_indicator.columns = df_indicator.iloc[header_row]
    df_indicator = df_indicator.iloc[header_row + 1:].reset_index(drop=True)
    return df_indicator


def rename_sector_column(df_indicator: pd.DataFrame) -> pd.DataFrame:
    """First column -> 'Sectors'. Also removes extra spaces in the column names."""
    column_names = []
    for column in df_indicator.columns:
        column_names.append(str(column).strip())
    column_names[0] = "Sectors"

    df_indicator = df_indicator.copy()
    df_indicator.columns = column_names
    return df_indicator


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


def convert_values_to_numbers(df_indicator: pd.DataFrame) -> pd.DataFrame:
    """All the columns except the first one -> numbers.
    Texts like 'na' or '-' become NaN (empty)."""
    df_indicator = df_indicator.copy()
    for column in df_indicator.columns[1:]:
        column_values = df_indicator[column].replace(MISSING_VALUE_TEXTS, np.nan)
        df_indicator[column] = pd.to_numeric(column_values, errors='coerce').astype(float)
    return df_indicator


def clean_sector_names(df_indicator: pd.DataFrame) -> pd.DataFrame:
    """Remove spaces before/after the sector names to avoid mismatches."""
    df_indicator = df_indicator.copy()
    df_indicator["Sectors"] = df_indicator["Sectors"].astype(str).str.strip()
    return df_indicator


def clean_indicator_file(df_indicator: pd.DataFrame, header_row: int | None) -> pd.DataFrame:
    """All the cleaning steps in order:
    header -> rename -> bad columns -> footnotes -> numbers -> sector names"""
    if header_row is not None:
        df_indicator = set_column_names_from_row(df_indicator, header_row)
    df_indicator = rename_sector_column(df_indicator)
    df_indicator = remove_bad_columns(df_indicator)
    df_indicator = remove_footnotes(df_indicator)
    df_indicator = convert_values_to_numbers(df_indicator)
    df_indicator = clean_sector_names(df_indicator)
    return df_indicator


def keep_target_sectors(df_indicator: pd.DataFrame, sectors: list[str] = TARGET_SECTORS) -> pd.DataFrame:
    """Keep only the sectors we are interested in."""
    df_filtered = df_indicator[df_indicator["Sectors"].isin(sectors)]
    return df_filtered.reset_index(drop=True)


# =====================================================================
# 2. MERGING FILES THAT MEASURE THE SAME THING
# =====================================================================
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


# =====================================================================
# 3. EXTRA CALCULATIONS
# =====================================================================
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


# =====================================================================
# 4. TIME HELPERS (used by the charts, the checks and the score)
# =====================================================================
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


def find_latest_period_with_data(df_one_row_per_period: pd.DataFrame) -> str:
    """Most recent period that has at least one value."""
    rows_with_value = df_one_row_per_period.dropna(subset=["Value"])
    newest_row = rows_with_value["Date"].idxmax()
    return rows_with_value.loc[newest_row, "Period"]


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


# =====================================================================
# 5. ESG FILE: COMPLIANCE AND RISK
# Rule:
#   - If 75% or more of the companies answer Yes  -> Low risk
#   - If 60% or more of the companies answer No   -> High risk
#   - All the rest                                -> Medium risk
#   - Missing answers count as "No", missing sectors get High risk
# =====================================================================
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


def calculate_esg_answer_percentages(df_esg_clean: pd.DataFrame) -> pd.DataFrame:
    """% of Yes / Partially / No per sector.
    A 0 here is NOT missing data: it means 0% of the companies gave that answer."""
    answers_by_sector = df_esg_clean.groupby(ESG_SECTOR_COLUMN)[ESG_REPORTING_COLUMN]
    df_percentages = answers_by_sector.value_counts(normalize=True).unstack(fill_value=0) * 100
    # Make sure the 3 columns always exist
    df_percentages = df_percentages.reindex(columns=ESG_VALID_ANSWERS, fill_value=0)
    return df_percentages


def get_esg_risk_level(yes_percentage: float, no_percentage: float) -> str:
    """Risk rule for one sector."""
    if yes_percentage >= ESG_LOW_RISK_IF_YES_AT_LEAST:
        return "Low"
    elif no_percentage >= ESG_HIGH_RISK_IF_NO_AT_LEAST:
        return "High"
    else:
        return "Medium"


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


# =====================================================================
# 6. DATA CHECKS: tables to zoom in on data that may not make sense
# =====================================================================
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


def check_data_quality(df_filtered: pd.DataFrame, title: str,
                       unusual_jump_limit: float = 3) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Prints and returns 2 tables:
    - summary : per sector -> periods, missing values, first/last period with data,
                min, max, mean and latest value
    - jumps   : periods where the change vs the previous period is unusually big
                for that sector (more than `unusual_jump_limit` standard deviations)
    Also warns about sectors that appear twice."""
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

    display(summary)
    if len(jumps) > 0:
        logger.warning("{}: {} unusual jumps (more than {} standard deviations)",
                       title, len(jumps), unusual_jump_limit)
        display(jumps)
    return summary, jumps