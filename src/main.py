
## MAIN 
# ###
#  Purpose of this file:
# The system will consolidate multiple indicators into a centralized database
# These indicators will then be processed into an overall industry assessment using a simple traffic-light rating system: Green, Amber, and Red.
# This will allow users to quickly identify industries showing signs of strength, deterioration, or elevated risk.  
# As an initial scope, we will focus on four key sectors to keep the initial phase manageable and allow the system to be developed and tested effectively. The framework is designed to be scalable, so additional sectors can be incorporated in future phases as the system is further developed.
# The initial sectors are: Manufacturing , Real Estate , Transportation and Storage ,Information and Communication 
# For a further analysis we be able to create the dashboard and the traffic-light system, this code we will also create a score that will fed the final traffic-light system. The score will be calculated based on the indicators and the weights assigned to each indicator. The final score will be used to determine the traffic-light rating for each industry.
# After this, we will create a dashboard that will allow users to visualize the data and the traffic-light ratings for each industry. 
# The dashboard will be interactive and will allow users to filter the data by sector, indicator, and time period. The dashboard will also provide a summary of the overall industry assessment and the traffic-light ratings for each industry.
# ###
# Creation day: 2026-09-15
# Moficiation day: 2026-09-28
# Created by: @ansanc
# Note that this code uses the help of Copilot, own knowledge and what was learnt in class.


#
# PART 1 - DATA
#   1. Load the tables from the database
#   2. Clean each df (BEFORE filtering)
#   3. Merge the files that measure the same thing
#   4. Filter the target sectors
#   5. GDP share of total
#   6. ESG risk
#   7. Data checks
#   8. Charts
#   9. Last 5 years
# PART 2 - RISK SCORE
#   10. Indicator results (value, light and points per sector / quarter / indicator)
#   11. Pillar scores (W1, W2, W3) and overall score
#   12. Tables (sectors x quarters) and report per sector
#
# The dfs are kept in dictionaries. Example with GDP:
#   raw_data["gdp"]       -> the table as it comes from the database
#   clean_data["gdp"]     -> after cleaning
#   filtered_data["gdp"]  -> only the target sectors
# Names: gdp, gos, labour_productivity, equity_ratio, business_expectations
#

# %%
from config import DATA_FILES, FILES_TO_MERGE, INDICATORS_TO_ANALYSE
from database import list_database_tables, load_all_tables
from exploration import (clean_indicator_file, merge_indicator_files, keep_target_sectors,
                         calculate_share_of_total, keep_last_years, build_esg_risk_table,
                         summarize_tables, check_data_quality)
from plots import plot_all_charts_for_indicator
from scoring import (build_indicator_results, build_pillar_results, build_overall_results,
                     make_sector_by_quarter_table, make_indicator_tables,
                     make_pillar_tables, print_score_report)


# =====================================================================
# PART 1 - DATA
# =====================================================================

# %%
# 1. LOAD THE TABLES FROM THE DATABASE
list_database_tables()

# %%
raw_data = load_all_tables()
summarize_tables(raw_data)

# %%
# Look at one table (change the name to see another one)
raw_data["gdp"].head(10)

# %%
# 2. CLEAN EACH DF (header -> rename -> footnotes -> numbers -> sector names)
#    The ESG file is different, it's cleaned in step 6
clean_data = {}
for data_name, file_settings in DATA_FILES.items():
    if data_name == "esg":
        continue
    clean_data[data_name] = clean_indicator_file(raw_data[data_name], file_settings["header_row"])

summarize_tables(clean_data)

# %%
# 3. MERGE THE FILES THAT MEASURE THE SAME THING
#    business_expectations = manufacturing + services
for merged_name, files_to_merge in FILES_TO_MERGE.items():
    dfs_to_merge = []
    for file_name in files_to_merge:
        dfs_to_merge.append(clean_data[file_name])
        del clean_data[file_name]          # the separate dfs are not needed anymore
    clean_data[merged_name] = merge_indicator_files(dfs_to_merge)

list(clean_data.keys())

# %%
# Check that each df ends at a real row (no footnotes)
for data_name, df_clean in clean_data.items():
    print(f"{data_name:25s} last row: {df_clean['Sectors'].iloc[-1]}")

# %%
# 4. FILTER THE SECTORS WE ARE INTERESTED IN
filtered_data = {}
for data_name, df_clean in clean_data.items():
    filtered_data[data_name] = keep_target_sectors(df_clean)
    print(f"{data_name:25s} {len(filtered_data[data_name])} sectors: "
          f"{filtered_data[data_name]['Sectors'].tolist()}")

# %%
# 5. GDP: SHARE OF EACH SECTOR IN THE TOTAL GDP (%)
df_gdp_share = calculate_share_of_total(clean_data["gdp"], INDICATORS_TO_ANALYSE["gdp"]["total_row"])
df_gdp_share_filtered = keep_target_sectors(df_gdp_share).round(2)
df_gdp_share_filtered.head()

# %%
# 6. ESG RISK
df_esg_risk = build_esg_risk_table(raw_data["esg"])
df_esg_risk

# %%
# 7. DATA CHECKS (summary per sector + unusual jumps)
data_quality_checks = {}
for indicator_name, indicator_settings in INDICATORS_TO_ANALYSE.items():
    data_quality_checks[indicator_name] = check_data_quality(filtered_data[indicator_name], indicator_settings["title"])

# %%
# 8. CHARTS
# All the indicators at once (set SHOW_CHARTS_IN_BROWSER = False in config.py
# if you don't want ~20 browser tabs)
for indicator_name, indicator_settings in INDICATORS_TO_ANALYSE.items():
    plot_all_charts_for_indicator(clean_data[indicator_name], filtered_data[indicator_name], indicator_settings)

# %%
# ... or just one indicator
plot_all_charts_for_indicator(clean_data["gdp"], filtered_data["gdp"], INDICATORS_TO_ANALYSE["gdp"])

# %%
# 9. LAST 5 YEARS
filtered_data_5_years = {}
for data_name, df_filtered in filtered_data.items():
    filtered_data_5_years[data_name] = keep_last_years(df_filtered, n_years=5)

filtered_data_5_years["gdp"].head()


# =====================================================================
# PART 2 - RISK SCORE
# =====================================================================

# %%
# 10. INDICATOR RESULTS: one row per sector + quarter + indicator
#     (value, traffic light, weight and points earned)
df_indicator_results = build_indicator_results(filtered_data, df_esg_risk)
df_indicator_results.head(10)

# %%
# 11a. PILLAR RESULTS: W1 economic, W2 financial, W3 workforce (traffic lights 1, 2, 3)
df_pillar_results = build_pillar_results(df_indicator_results)
df_pillar_results.head(10)

# %%
# 11b. OVERALL RESULTS: score with the override rules
df_overall_results = build_overall_results(df_indicator_results)
df_overall_results.head(10)

# %%
# 12a. FINAL TABLES: sectors as rows, quarters of the last 5 years as columns
df_overall_score_table = make_sector_by_quarter_table(df_overall_results, "Score")        # 0 - 100
df_overall_light_table = make_sector_by_quarter_table(df_overall_results, "Final light")  # Green / Amber / Red
df_overall_score_table

# %%
df_overall_light_table

# %%
# One table per indicator (value, light or points)
indicator_value_tables = make_indicator_tables(df_indicator_results, "Value")
indicator_light_tables = make_indicator_tables(df_indicator_results, "Light")
indicator_points_tables = make_indicator_tables(df_indicator_results, "Points")
indicator_value_tables["gdp_growth"]

# %%
# One table per pillar (score or light)
pillar_score_tables = make_pillar_tables(df_pillar_results, "Score")
pillar_light_tables = make_pillar_tables(df_pillar_results, "Light")
pillar_score_tables["W1"]

# %%
# Sectors and quarters with a warning (override or a single Red)
df_warnings = df_overall_results[df_overall_results["Warning"] != ""]
df_warnings[["Sectors", "Quarter", "Score", "Final light", "Warning"]]

# %%
# 12b. REPORT FOR ONE SECTOR (latest quarter; add quarter="2025 2Q" for another one)
print_score_report(df_indicator_results, df_overall_results, "Manufacturing")