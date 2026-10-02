# 
# ## RISK SCORE and TRAFFIC LIGHTS by sector and quarter.
# ###
#  Purpose of this file:
# This file looks to generate plot to explore the data 
# ###
# Creation day: 2026-09-28
# Moficiation day: 2026-10-01
# Created by: @ansanc
# Note that this code uses the help of Copilot, own knowledge and what was learnt in class.
 
# PART 2: RISK SCORE and TRAFFIC LIGHTS by sector and quarter.
#
#   1. Preparing the values -> yearly growth, list of quarters, value of each quarter
#   2. Traffic lights       -> Green / Amber / Red
#   3. Indicator results    -> one row per sector + quarter + indicator
#   4. Scores               -> pillars (W1, W2, W3) and overall score + override rules
#   5. Tables and report    -> sectors as rows, quarters as columns + report per sector
#
# All the settings (weights, limits, points) are in config.py


import numpy as np
import pandas as pd

from config import (TARGET_SECTORS, SCORE_NUMBER_OF_YEARS, SCORE_QUARTERS_TAKEN_FROM,
                    MAX_YEARS_BACK_FOR_ANNUAL_DATA, PILLARS, SCORE_INDICATORS,
                    ESG_RISK_TO_LIGHT, POINTS_PER_LIGHT, GREEN_IF_SCORE_AT_LEAST,
                    AMBER_IF_SCORE_AT_LEAST, NUMBER_OF_REDS_THAT_BLOCK_GREEN)
from exploration import keep_last_years, convert_period_to_date


# %%%
# ###
# 1. PREPARING THE VALUES

def same_period_one_year_before(period):
    """'2025 2Q' -> '2024 2Q'  |  '2025' -> '2024'"""
    period_parts = period.split()
    year_before = int(period_parts[0]) - 1
    period_parts[0] = str(year_before)
    return " ".join(period_parts)


def calculate_yearly_growth(df_indicator):
    """% change vs the same period one year before:
    (value / value one year before - 1) * 100
    Works for quarterly ('2025 2Q' vs '2024 2Q') and annual data ('2025' vs '2024')."""
    df_growth = df_indicator[["Sectors"]].copy()
    for period in df_indicator.columns[1:]:
        period_before = same_period_one_year_before(period)
        if period_before in df_indicator.columns:
            df_growth[period] = (df_indicator[period] / df_indicator[period_before] - 1) * 100
    return df_growth


def get_score_quarters(df_quarters_source, n_years=SCORE_NUMBER_OF_YEARS):
    """List of quarters of the last `n_years` years that have data,
    from the oldest to the newest. These are the columns of the score tables."""
    df_last_years = keep_last_years(df_quarters_source, n_years)

    quarters = []
    for column in df_last_years.columns[1:]:
        if df_last_years[column].notna().any():
            quarters.append(column)

    quarters = sorted(quarters, key=convert_period_to_date)
    return quarters


def get_value_for_quarter(df_indicator_values, sector, quarter):
    """Value of one sector in one quarter, and the period it comes from.
    - Quarterly data: the value of that quarter.
    - Annual data   : the value of that year. If it's not published yet,
                      the year before (up to MAX_YEARS_BACK_FOR_ANNUAL_DATA years)."""
    sector_rows = df_indicator_values[df_indicator_values["Sectors"] == sector]
    if sector_rows.empty:
        return np.nan, None
    sector_row = sector_rows.iloc[0]

    # Quarterly data
    if quarter in df_indicator_values.columns:
        value = sector_row[quarter]
        if pd.isna(value):
            return np.nan, None
        return value, quarter

    # Annual data
    quarter_year = int(quarter.split()[0])
    for years_back in range(MAX_YEARS_BACK_FOR_ANNUAL_DATA + 1):
        year = str(quarter_year - years_back)
        if year in df_indicator_values.columns and pd.notna(sector_row[year]):
            return sector_row[year], year

    return np.nan, None


# %%%
# ###
# 2. TRAFFIC LIGHTS
# 
def get_indicator_light(value, indicator_settings):
    """Green / Amber / Red for one value, using the limits of the indicator."""
    if pd.isna(value):
        return np.nan

    green_from = indicator_settings["green_from"]
    if indicator_settings["green_includes_limit"]:
        is_green = value >= green_from
    else:
        is_green = value > green_from

    if is_green:
        return "Green"
    elif value >= indicator_settings["amber_from"]:
        return "Amber"
    else:
        return "Red"


def get_score_light(score):
    """Score 0-100 -> traffic light. 70 - 74.99 falls into Amber."""
    if pd.isna(score):
        return np.nan
    if score >= GREEN_IF_SCORE_AT_LEAST:
        return "Green"
    elif score >= AMBER_IF_SCORE_AT_LEAST:
        return "Amber"
    else:
        return "Red"


# %%%
# ###
# 3. INDICATOR RESULTS: one row per sector + quarter + indicator
# 
def build_indicator_results(filtered_data, df_esg_risk, sectors=TARGET_SECTORS):
    """Value, traffic light, weight and points of every indicator,
    for every sector and every quarter of the score.
    filtered_data : dictionary with the filtered dfs (from main.py)
    df_esg_risk   : df with Sector | ESG reporting compliance | risk_score"""

    # Check that the weights add up to 100
    total_weight = 0
    for indicator_settings in SCORE_INDICATORS.values():
        total_weight = total_weight + indicator_settings["weight"]
    if total_weight != 100:
        print(f"WARNING: the weights add up to {total_weight}, not 100 (check config.py)")

    score_quarters = get_score_quarters(filtered_data[SCORE_QUARTERS_TAKEN_FROM])

    indicator_result_rows = []
    for indicator_name, indicator_settings in SCORE_INDICATORS.items():

        # Values of this indicator (not needed for ESG)
        if indicator_settings["calculation"] == "yearly_growth":
            df_indicator_values = calculate_yearly_growth(filtered_data[indicator_settings["data_name"]])
        elif indicator_settings["calculation"] == "value":
            df_indicator_values = filtered_data[indicator_settings["data_name"]]

        for sector in sectors:
            for quarter in score_quarters:

                if indicator_settings["calculation"] == "esg":
                    # ESG has no quarters: the same result is used in every quarter
                    esg_row = df_esg_risk[df_esg_risk["Sector"] == sector]
                    value = esg_row["ESG reporting compliance"].values[0]   # % of companies with Yes
                    value_period = "ESG report"
                    light = ESG_RISK_TO_LIGHT[esg_row["risk_score"].values[0]]
                else:
                    value, value_period = get_value_for_quarter(df_indicator_values, sector, quarter)
                    light = get_indicator_light(value, indicator_settings)

                if pd.isna(light):
                    points = np.nan
                else:
                    points = POINTS_PER_LIGHT[light] * indicator_settings["weight"]

                indicator_result_rows.append({
                    "Sectors": sector,
                    "Quarter": quarter,
                    "Pillar": indicator_settings["pillar"],
                    "Indicator": indicator_name,
                    "Label": indicator_settings["label"],
                    "Value": round(value, 2) if pd.notna(value) else np.nan,
                    "Value period": value_period,
                    "Light": light,
                    "Weight": indicator_settings["weight"],
                    "Points": points,
                })

    df_indicator_results = pd.DataFrame(indicator_result_rows)
    return df_indicator_results

# %%%
# ###
# 4. SCORES
# 
def calculate_score(indicator_rows):
    """Score 0-100 of a group of indicators (one sector, one quarter).
    If an indicator has no data, the score is calculated only with the indicators
    that have data, and 'coverage' says how much of the weight had data."""
    rows_with_data = indicator_rows[indicator_rows["Light"].notna()]

    points_earned = rows_with_data["Points"].sum()
    max_points_with_data = rows_with_data["Weight"].sum()
    max_points_total = indicator_rows["Weight"].sum()

    if max_points_with_data == 0:
        return np.nan, 0.0

    score = points_earned / max_points_with_data * 100
    coverage = max_points_with_data / max_points_total * 100
    return round(score, 2), round(coverage, 1)


def build_pillar_results(df_indicator_results):
    """One row per sector + quarter + pillar (W1, W2, W3): score 0-100 and traffic light."""
    pillar_rows = []
    for sector in df_indicator_results["Sectors"].unique():
        for quarter in df_indicator_results["Quarter"].unique():
            for pillar in PILLARS:
                is_this_sector = df_indicator_results["Sectors"] == sector
                is_this_quarter = df_indicator_results["Quarter"] == quarter
                is_this_pillar = df_indicator_results["Pillar"] == pillar
                indicator_rows = df_indicator_results[is_this_sector & is_this_quarter & is_this_pillar]
                score, coverage = calculate_score(indicator_rows)
                pillar_rows.append({
                    "Sectors": sector,
                    "Quarter": quarter,
                    "Pillar": pillar,
                    "Pillar name": PILLARS[pillar],
                    "Score": score,
                    "Light": get_score_light(score),
                    "Data coverage %": coverage,
                })
    return pd.DataFrame(pillar_rows)


def build_overall_results(df_indicator_results):
    """One row per sector + quarter: overall score, traffic light and override rules.
    - Score >= 75 Green | 40 - 74.99 Amber | < 40 Red
    - 2 or more Red indicators -> it can't be Green (maximum Amber)
    - 1 Red indicator and Green score -> stays Green with a risk warning"""
    overall_rows = []
    for sector in df_indicator_results["Sectors"].unique():
        for quarter in df_indicator_results["Quarter"].unique():
            is_this_sector = df_indicator_results["Sectors"] == sector
            is_this_quarter = df_indicator_results["Quarter"] == quarter
            indicator_rows = df_indicator_results[is_this_sector & is_this_quarter]
            score, coverage = calculate_score(indicator_rows)
            light_by_score = get_score_light(score)

            red_indicators = indicator_rows[indicator_rows["Light"] == "Red"]["Label"].tolist()
            number_of_reds = len(red_indicators)

            # Override rules
            final_light = light_by_score
            override_applied = False
            warning = ""
            if light_by_score == "Green" and number_of_reds >= NUMBER_OF_REDS_THAT_BLOCK_GREEN:
                final_light = "Amber"
                override_applied = True
                warning = f"Green blocked: {number_of_reds} Red indicators ({', '.join(red_indicators)})"
            elif light_by_score == "Green" and number_of_reds == 1:
                warning = f"Risk warning: {red_indicators[0]} is Red"

            overall_rows.append({
                "Sectors": sector,
                "Quarter": quarter,
                "Score": score,
                "Light by score": light_by_score,
                "Red indicators": number_of_reds,
                "Override applied": override_applied,
                "Final light": final_light,
                "Warning": warning,
                "Data coverage %": coverage,
            })
    return pd.DataFrame(overall_rows)


# =====================================================================
# 5. TABLES (sectors as rows, quarters as columns) AND REPORT
# =====================================================================
def make_sector_by_quarter_table(df_one_row_per_quarter, column_to_show):
    """Long table -> sectors as rows, quarters as columns (oldest to newest).
    column_to_show: the column whose values fill the table (e.g. 'Score')"""
    quarters_in_order = df_one_row_per_quarter["Quarter"].unique()
    sectors_in_order = df_one_row_per_quarter["Sectors"].unique()

    df_table = df_one_row_per_quarter.pivot(index="Sectors", columns="Quarter", values=column_to_show)
    df_table = df_table.reindex(index=sectors_in_order, columns=quarters_in_order)
    df_table.columns.name = None
    return df_table


def make_indicator_tables(df_indicator_results, column_to_show):
    """Dictionary with one table (sectors x quarters) per indicator.
    column_to_show: 'Value', 'Light' or 'Points'"""
    indicator_tables = {}
    for indicator_name in SCORE_INDICATORS:
        indicator_rows = df_indicator_results[df_indicator_results["Indicator"] == indicator_name]
        indicator_tables[indicator_name] = make_sector_by_quarter_table(indicator_rows, column_to_show)
    return indicator_tables


def make_pillar_tables(df_pillar_results, column_to_show):
    """Dictionary with one table (sectors x quarters) per pillar.
    column_to_show: 'Score' or 'Light'"""
    pillar_tables = {}
    for pillar in PILLARS:
        pillar_rows = df_pillar_results[df_pillar_results["Pillar"] == pillar]
        pillar_tables[pillar] = make_sector_by_quarter_table(pillar_rows, column_to_show)
    return pillar_tables


def print_score_report(df_indicator_results, df_overall_results, sector, quarter=None):
    """Report for one sector and one quarter (the latest one if quarter is None):
    1. Indicator breakdown  2. Calculation  3. Override check  4. Final result"""
    if quarter is None:
        quarter = df_overall_results["Quarter"].unique()[-1]

    indicator_rows = df_indicator_results[(df_indicator_results["Sectors"] == sector) &
                                          (df_indicator_results["Quarter"] == quarter)]
    overall_rows = df_overall_results[(df_overall_results["Sectors"] == sector) &
                                      (df_overall_results["Quarter"] == quarter)]
    if indicator_rows.empty:
        print(f"No data for {sector} in {quarter}")
        return None
    overall_row = overall_rows.iloc[0]

    print(f"\n========== {sector} — {quarter} ==========")

    # 1. Indicator breakdown
    print("\n1. INDICATOR BREAKDOWN")
    breakdown = indicator_rows[["Pillar", "Label", "Value", "Value period", "Light", "Weight", "Points"]].copy()
    breakdown["Light"] = breakdown["Light"].fillna("No data")
    print(breakdown.to_string(index=False))

    # 2. Calculation
    print("\n2. CALCULATION")
    rows_with_data = indicator_rows[indicator_rows["Light"].notna()]
    points_earned = rows_with_data["Points"].sum()
    max_points_with_data = rows_with_data["Weight"].sum()
    points_text = " + ".join(f"{points:.1f}" for points in rows_with_data["Points"])
    print(f"Points: {points_text} = {points_earned:.2f} out of {max_points_with_data:.0f}")
    if overall_row["Data coverage %"] < 100:
        print(f"Some indicators have no data -> rescaled to 100: "
              f"{points_earned:.2f} / {max_points_with_data:.0f} x 100 = {overall_row['Score']:.2f}")
    print(f"Overall score: {overall_row['Score']:.2f} / 100  ->  {overall_row['Light by score']} by score")

    # 3. Override rule check
    print("\n3. OVERRIDE RULE CHECK")
    print(f"Red indicators: {overall_row['Red indicators']}")
    if overall_row["Override applied"]:
        print(f"APPLIES: {overall_row['Warning']} -> maximum allowed is Amber")
    elif overall_row["Warning"] != "":
        print(f"Does not apply (only 1 Red). {overall_row['Warning']}")
    else:
        print("Does not apply")

    # 4. Final result
    print("\n4. FINAL RESULT")
    final_light = overall_row["Final light"]
    print(f"Numerical score : {overall_row['Score']:.2f}")
    print(f"Final status    : {final_light}")
    return breakdown