
# Purpose of the code/project:
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
# Moficiation day: 2026-09-30
# Created by: @ansanc
# Note that this code uses the help of Copilot, own knowledge and what was learnt in class.

#%%
## Purpose of this file: 
# The project in one file to run cell by cell for trying the code and experiment with it
#
#   PART 0  - Libraries and settings
#   PART 1  - Create the database from the files
#   PART 2  - Load the tables from the database
#   PART 3  - Review and clean each df
#             (head, tail, info and describe BEFORE any change)
#   PART 4  - Merge the two business expectations files
#   PART 5  - GDP share of total
#   PART 6  - ESG risk
#   PART 7  - Data checks (summary per sector + unusual jumps)
#   PART 8  - Charts
#   PART 9  - Last 5 years
#   PART 10 - Risk score (traffic lights, pillars, overall score)


# =====================================================================

# %%
# =====================================================================
# PART 0 - LIBRARIES AND SETTINGS
# =====================================================================
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px

# %%
# Folders: this file is in src/, so the project folder is one level up
PROJECT_FOLDER = Path(__file__).resolve().parent.parent
DATA_FOLDER = PROJECT_FOLDER / "data"
PLOTS_FOLDER = PROJECT_FOLDER / "output"
DATABASE_PATH = DATA_FOLDER / "Database_RiskDashboard.db"

# %%
# Create the output folder if it doesn't exist
PLOTS_FOLDER.mkdir(exist_ok=True)

# %%
# Sectors we focus on
TARGET_SECTORS = [
    'Manufacturing',
    'Real Estate',
    'Transportation & Storage',
    'Information & Communications',
    'Utilities',
]

# %%
# One fixed color per sector, so each sector has the same color in every chart
SECTOR_COLORS = {
    'Manufacturing':                '#2a78d6',   # blue
    'Real Estate':                  '#eb6834',   # orange
    'Transportation & Storage':     '#1baf7a',   # aqua
    'Information & Communications': '#eda100',   # yellow
    'Utilities':                    '#e87ba4',   # pink
    'Other Sectors':                '#b5b4ad',   # gray
}

# %%
# Text values that mean "no data" in the files
MISSING_VALUE_TEXTS = ['NaN', 'nan', 'na', '-', ' ', '']

# %%
# Exact name of the TOTAL row in each file  -> CHECK with your data
GDP_TOTAL_ROW = "GDP In Chained (2015) Dollars"
GOS_TOTAL_ROW = "Gross Operating Surplus"
LABOUR_PRODUCTIVITY_TOTAL_ROW = "Overall Economy"
EQUITY_RATIO_TOTAL_ROW = "All Industries"

# %%
# ESG file settings
ESG_SECTOR_COLUMN = "Sector"            # CHECK: real name of the sector column
ESG_REPORTING_COLUMN = "ESG reporting"
ESG_VALID_ANSWERS = ["Yes", "Partially", "No"]
ESG_LOW_RISK_IF_YES_AT_LEAST = 75       # >= 75% Yes -> Low risk
ESG_HIGH_RISK_IF_NO_AT_LEAST = 60       # >= 60% No  -> High risk

# %%
# Open the charts in the browser? False = only save the HTML files in output/
SHOW_CHARTS_IN_BROWSER = True

# %%
# =====================================================================
# PART 1 - CREATE THE DATABASE FROM THE FILES
# (only needed the first time or when the files change)
# Each file is saved as one table, exactly as it comes (no cleaning)
# =====================================================================
connection = sqlite3.connect(DATABASE_PATH)

# %%
df_file = pd.read_csv(DATA_FOLDER / "RealGDPGrowthByIndustry.csv")
df_file.to_sql("raw_gdp_growth", connection, if_exists="replace", index=False)

# %%
df_file = pd.read_csv(DATA_FOLDER / "GrossOperatingSurplusGrowthByIndustry.csv")
df_file.to_sql("raw_gross_operating_surplus", connection, if_exists="replace", index=False)

# %%
df_file = pd.read_csv(DATA_FOLDER / "LabourProductivityValueAddedPerWorker.csv")
df_file.to_sql("raw_labour_productivity", connection, if_exists="replace", index=False)

# %%
df_file = pd.read_csv(DATA_FOLDER / "EquityRatioOfCompaniesByIndustry.csv")
df_file.to_sql("raw_equity_ratio", connection, if_exists="replace", index=False)

# %%
df_file = pd.read_csv(DATA_FOLDER / "BusinessExpectationsOfTheManufacturingSector.csv")
df_file.to_sql("raw_business_exp_manufacturing", connection, if_exists="replace", index=False)

# %%
df_file = pd.read_csv(DATA_FOLDER / "BusinessExpectationsOfTheServiceSector.csv")
df_file.to_sql("raw_business_exp_services", connection, if_exists="replace", index=False)

# %%
df_file = pd.read_excel(DATA_FOLDER / "ESGReports.xlsx")
df_file.to_sql("raw_esg", connection, if_exists="replace", index=False)

# %%
# Save the changes
connection.commit()

# %%
# Check which tables are in the database
pd.read_sql("SELECT name FROM sqlite_master WHERE type = 'table'", connection)

# %%
# =====================================================================
# PART 2 - LOAD THE TABLES FROM THE DATABASE
# =====================================================================
# Real GDP by Industry - Million dollars (chained 2015)
df_GDP_Growth = pd.read_sql("SELECT * FROM raw_gdp_growth", connection)

# %%
# Gross Operating Surplus by Industry - Million dollars
df_GrossOperatingSurplusGrowth = pd.read_sql("SELECT * FROM raw_gross_operating_surplus", connection)

# %%
# Labour Productivity - value added per worker
df_LabourProductivity = pd.read_sql("SELECT * FROM raw_labour_productivity", connection)

# %%
# Equity Ratio of Companies by Industry
df_EquityRatio = pd.read_sql("SELECT * FROM raw_equity_ratio", connection)

# %%
# Business expectations - Manufacturing sector
df_Manufacturing_Business_Expectations = pd.read_sql("SELECT * FROM raw_business_exp_manufacturing", connection)

# %%
# Business expectations - Services sector
df_Service_Business_Expectations = pd.read_sql("SELECT * FROM raw_business_exp_services", connection)

# %%
# ESG reports (built by the team)
df_ESG = pd.read_sql("SELECT * FROM raw_esg", connection)

# %%
# We don't need the database anymore
connection.close()

# %%
# =====================================================================
# PART 3 - REVIEW AND CLEAN EACH DF
# Same steps for every SingStat file:
#   header -> rename -> footnotes -> numbers -> sector names -> filter
# =====================================================================

# %%
# =====================================================================
# 3.1 REAL GDP
# =====================================================================
# REVIEW BEFORE ANY CHANGE: first rows
df_GDP_Growth.head(10)

# %%
# Last rows
df_GDP_Growth.tail(10)

# %%
# Columns, types and empty values
df_GDP_Growth.info()

# %%
# Basic statistics
df_GDP_Growth.describe()

# %%
# Row 8 has the real column names -> use it as the header
df_GDP_Growth.columns = df_GDP_Growth.iloc[8]

# %%
# Remove the rows above the data (rows 0 to 8)
df_GDP_Growth = df_GDP_Growth.iloc[9:].reset_index(drop=True)

# %%
# Column names as text, without spaces before/after
gdp_column_names = []
for column in df_GDP_Growth.columns:
    gdp_column_names.append(str(column).strip())

# %%
# First column -> "Sectors"
gdp_column_names[0] = "Sectors"

# %%
df_GDP_Growth.columns = gdp_column_names

# %%
df_GDP_Growth.head(5)

# %%
# Find the footnotes at the bottom of the file
gdp_first_column_text = df_GDP_Growth["Sectors"].astype(str).str.strip()
gdp_footnote_rows = df_GDP_Growth.index[gdp_first_column_text.str.startswith("Definitions and Footnotes")]
gdp_footnote_rows

# %%
# Cut the df where the footnotes start
if len(gdp_footnote_rows) > 0:
    df_GDP_Growth = df_GDP_Growth.iloc[:gdp_footnote_rows[0]]

# %%
# Drop the completely empty rows
df_GDP_Growth = df_GDP_Growth.dropna(how="all").reset_index(drop=True)

# %%
# Check that the df now ends at a real row
df_GDP_Growth.tail(5)

# %%
# Values as numbers (all the columns except "Sectors"). Texts like 'na' or '-' -> NaN
for column in df_GDP_Growth.columns[1:]:
    column_values = df_GDP_Growth[column].replace(MISSING_VALUE_TEXTS, np.nan)
    df_GDP_Growth[column] = pd.to_numeric(column_values, errors="coerce").astype(float)

# %%
# Remove spaces before/after the sector names to avoid mismatches
df_GDP_Growth["Sectors"] = df_GDP_Growth["Sectors"].astype(str).str.strip()

# %%
# Review AFTER cleaning
df_GDP_Growth.info()

# %%
df_GDP_Growth.describe()

# %%
df_GDP_Growth.head(5)

# %%
# Keep only the sectors we are interested in
df_GDP_Growth_filtered = df_GDP_Growth[df_GDP_Growth["Sectors"].isin(TARGET_SECTORS)].reset_index(drop=True)

# %%
df_GDP_Growth_filtered

# %%
# =====================================================================
# 3.2 GROSS OPERATING SURPLUS
# =====================================================================
# REVIEW BEFORE ANY CHANGE: first rows
df_GrossOperatingSurplusGrowth.head(10)

# %%
# Last rows
df_GrossOperatingSurplusGrowth.tail(10)

# %%
# Columns, types and empty values
df_GrossOperatingSurplusGrowth.info()

# %%
# Basic statistics
df_GrossOperatingSurplusGrowth.describe()

# %%
# Row 8 has the real column names -> use it as the header
df_GrossOperatingSurplusGrowth.columns = df_GrossOperatingSurplusGrowth.iloc[8]

# %%
# Remove the rows above the data (rows 0 to 8)
df_GrossOperatingSurplusGrowth = df_GrossOperatingSurplusGrowth.iloc[9:].reset_index(drop=True)

# %%
# Column names as text, without spaces before/after
gos_column_names = []
for column in df_GrossOperatingSurplusGrowth.columns:
    gos_column_names.append(str(column).strip())

# %%
# First column -> "Sectors"
gos_column_names[0] = "Sectors"

# %%
df_GrossOperatingSurplusGrowth.columns = gos_column_names

# %%
df_GrossOperatingSurplusGrowth.head(5)

# %%
# Find the footnotes at the bottom of the file
gos_first_column_text = df_GrossOperatingSurplusGrowth["Sectors"].astype(str).str.strip()
gos_footnote_rows = df_GrossOperatingSurplusGrowth.index[gos_first_column_text.str.startswith("Definitions and Footnotes")]
gos_footnote_rows

# %%
# Cut the df where the footnotes start
if len(gos_footnote_rows) > 0:
    df_GrossOperatingSurplusGrowth = df_GrossOperatingSurplusGrowth.iloc[:gos_footnote_rows[0]]

# %%
# Drop the completely empty rows
df_GrossOperatingSurplusGrowth = df_GrossOperatingSurplusGrowth.dropna(how="all").reset_index(drop=True)

# %%
# Check that the df now ends at a real row
df_GrossOperatingSurplusGrowth.tail(5)

# %%
# Values as numbers (all the columns except "Sectors"). Texts like 'na' or '-' -> NaN
for column in df_GrossOperatingSurplusGrowth.columns[1:]:
    column_values = df_GrossOperatingSurplusGrowth[column].replace(MISSING_VALUE_TEXTS, np.nan)
    df_GrossOperatingSurplusGrowth[column] = pd.to_numeric(column_values, errors="coerce").astype(float)

# %%
# Remove spaces before/after the sector names to avoid mismatches
df_GrossOperatingSurplusGrowth["Sectors"] = df_GrossOperatingSurplusGrowth["Sectors"].astype(str).str.strip()

# %%
# Review AFTER cleaning
df_GrossOperatingSurplusGrowth.info()

# %%
df_GrossOperatingSurplusGrowth.describe()

# %%
df_GrossOperatingSurplusGrowth.head(5)

# %%
# Keep only the sectors we are interested in
df_GrossOperatingSurplusGrowth_filtered = df_GrossOperatingSurplusGrowth[df_GrossOperatingSurplusGrowth["Sectors"].isin(TARGET_SECTORS)].reset_index(drop=True)

# %%
df_GrossOperatingSurplusGrowth_filtered

# %%
# =====================================================================
# 3.3 LABOUR PRODUCTIVITY
# =====================================================================
# REVIEW BEFORE ANY CHANGE: first rows
df_LabourProductivity.head(10)

# %%
# Last rows
df_LabourProductivity.tail(10)

# %%
# Columns, types and empty values
df_LabourProductivity.info()

# %%
# Basic statistics
df_LabourProductivity.describe()

# %%
# Row 8 has the real column names -> use it as the header
df_LabourProductivity.columns = df_LabourProductivity.iloc[8]

# %%
# Remove the rows above the data (rows 0 to 8)
df_LabourProductivity = df_LabourProductivity.iloc[9:].reset_index(drop=True)

# %%
# Column names as text, without spaces before/after
labour_productivity_column_names = []
for column in df_LabourProductivity.columns:
    labour_productivity_column_names.append(str(column).strip())

# %%
# First column -> "Sectors"
labour_productivity_column_names[0] = "Sectors"

# %%
df_LabourProductivity.columns = labour_productivity_column_names

# %%
df_LabourProductivity.head(5)

# %%
# Find the footnotes at the bottom of the file
labour_productivity_first_column_text = df_LabourProductivity["Sectors"].astype(str).str.strip()
labour_productivity_footnote_rows = df_LabourProductivity.index[labour_productivity_first_column_text.str.startswith("Definitions and Footnotes")]
labour_productivity_footnote_rows

# %%
# Cut the df where the footnotes start
if len(labour_productivity_footnote_rows) > 0:
    df_LabourProductivity = df_LabourProductivity.iloc[:labour_productivity_footnote_rows[0]]

# %%
# Drop the completely empty rows
df_LabourProductivity = df_LabourProductivity.dropna(how="all").reset_index(drop=True)

# %%
# Check that the df now ends at a real row
df_LabourProductivity.tail(5)

# %%
# Values as numbers (all the columns except "Sectors"). Texts like 'na' or '-' -> NaN
for column in df_LabourProductivity.columns[1:]:
    column_values = df_LabourProductivity[column].replace(MISSING_VALUE_TEXTS, np.nan)
    df_LabourProductivity[column] = pd.to_numeric(column_values, errors="coerce").astype(float)

# %%
# Remove spaces before/after the sector names to avoid mismatches
df_LabourProductivity["Sectors"] = df_LabourProductivity["Sectors"].astype(str).str.strip()

# %%
# Review AFTER cleaning
df_LabourProductivity.info()

# %%
df_LabourProductivity.describe()

# %%
df_LabourProductivity.head(5)

# %%
# Keep only the sectors we are interested in
df_LabourProductivity_filtered = df_LabourProductivity[df_LabourProductivity["Sectors"].isin(TARGET_SECTORS)].reset_index(drop=True)

# %%
df_LabourProductivity_filtered

# %%
# =====================================================================
# 3.4 EQUITY RATIO (THIS FILE ALREADY HAS THE RIGHT HEADER)
# =====================================================================
# REVIEW BEFORE ANY CHANGE: first rows
df_EquityRatio.head(10)

# %%
# Last rows
df_EquityRatio.tail(10)

# %%
# Columns, types and empty values
df_EquityRatio.info()

# %%
# Basic statistics
df_EquityRatio.describe()

# %%
# Column names as text, without spaces before/after
equity_ratio_column_names = []
for column in df_EquityRatio.columns:
    equity_ratio_column_names.append(str(column).strip())

# %%
# First column -> "Sectors"
equity_ratio_column_names[0] = "Sectors"

# %%
df_EquityRatio.columns = equity_ratio_column_names

# %%
df_EquityRatio.head(5)

# %%
# Find the footnotes at the bottom of the file
equity_ratio_first_column_text = df_EquityRatio["Sectors"].astype(str).str.strip()
equity_ratio_footnote_rows = df_EquityRatio.index[equity_ratio_first_column_text.str.startswith("Definitions and Footnotes")]
equity_ratio_footnote_rows

# %%
# Cut the df where the footnotes start
if len(equity_ratio_footnote_rows) > 0:
    df_EquityRatio = df_EquityRatio.iloc[:equity_ratio_footnote_rows[0]]

# %%
# Drop the completely empty rows
df_EquityRatio = df_EquityRatio.dropna(how="all").reset_index(drop=True)

# %%
# Check that the df now ends at a real row
df_EquityRatio.tail(5)

# %%
# Values as numbers (all the columns except "Sectors"). Texts like 'na' or '-' -> NaN
for column in df_EquityRatio.columns[1:]:
    column_values = df_EquityRatio[column].replace(MISSING_VALUE_TEXTS, np.nan)
    df_EquityRatio[column] = pd.to_numeric(column_values, errors="coerce").astype(float)

# %%
# Remove spaces before/after the sector names to avoid mismatches
df_EquityRatio["Sectors"] = df_EquityRatio["Sectors"].astype(str).str.strip()

# %%
# Review AFTER cleaning
df_EquityRatio.info()

# %%
df_EquityRatio.describe()

# %%
df_EquityRatio.head(5)

# %%
# Keep only the sectors we are interested in
df_EquityRatio_filtered = df_EquityRatio[df_EquityRatio["Sectors"].isin(TARGET_SECTORS)].reset_index(drop=True)

# %%
df_EquityRatio_filtered

# %%
# =====================================================================
# 3.5 BUSINESS EXPECTATIONS - MANUFACTURING
# =====================================================================
# REVIEW BEFORE ANY CHANGE: first rows
df_Manufacturing_Business_Expectations.head(10)

# %%
# Last rows
df_Manufacturing_Business_Expectations.tail(10)

# %%
# Columns, types and empty values
df_Manufacturing_Business_Expectations.info()

# %%
# Basic statistics
df_Manufacturing_Business_Expectations.describe()

# %%
# Row 8 has the real column names -> use it as the header
df_Manufacturing_Business_Expectations.columns = df_Manufacturing_Business_Expectations.iloc[8]

# %%
# Remove the rows above the data (rows 0 to 8)
df_Manufacturing_Business_Expectations = df_Manufacturing_Business_Expectations.iloc[9:].reset_index(drop=True)

# %%
# Column names as text, without spaces before/after
manufacturing_expectations_column_names = []
for column in df_Manufacturing_Business_Expectations.columns:
    manufacturing_expectations_column_names.append(str(column).strip())

# %%
# First column -> "Sectors"
manufacturing_expectations_column_names[0] = "Sectors"

# %%
df_Manufacturing_Business_Expectations.columns = manufacturing_expectations_column_names

# %%
df_Manufacturing_Business_Expectations.head(5)

# %%
# Find the footnotes at the bottom of the file
manufacturing_expectations_first_column_text = df_Manufacturing_Business_Expectations["Sectors"].astype(str).str.strip()
manufacturing_expectations_footnote_rows = df_Manufacturing_Business_Expectations.index[manufacturing_expectations_first_column_text.str.startswith("Definitions and Footnotes")]
manufacturing_expectations_footnote_rows

# %%
# Cut the df where the footnotes start
if len(manufacturing_expectations_footnote_rows) > 0:
    df_Manufacturing_Business_Expectations = df_Manufacturing_Business_Expectations.iloc[:manufacturing_expectations_footnote_rows[0]]

# %%
# Drop the completely empty rows
df_Manufacturing_Business_Expectations = df_Manufacturing_Business_Expectations.dropna(how="all").reset_index(drop=True)

# %%
# Check that the df now ends at a real row
df_Manufacturing_Business_Expectations.tail(5)

# %%
# Values as numbers (all the columns except "Sectors"). Texts like 'na' or '-' -> NaN
for column in df_Manufacturing_Business_Expectations.columns[1:]:
    column_values = df_Manufacturing_Business_Expectations[column].replace(MISSING_VALUE_TEXTS, np.nan)
    df_Manufacturing_Business_Expectations[column] = pd.to_numeric(column_values, errors="coerce").astype(float)

# %%
# Remove spaces before/after the sector names to avoid mismatches
df_Manufacturing_Business_Expectations["Sectors"] = df_Manufacturing_Business_Expectations["Sectors"].astype(str).str.strip()

# %%
# Review AFTER cleaning
df_Manufacturing_Business_Expectations.info()

# %%
df_Manufacturing_Business_Expectations.describe()

# %%
df_Manufacturing_Business_Expectations.head(5)

# %%
# =====================================================================
# 3.6 BUSINESS EXPECTATIONS - SERVICES
# =====================================================================
# REVIEW BEFORE ANY CHANGE: first rows
df_Service_Business_Expectations.head(10)

# %%
# Last rows
df_Service_Business_Expectations.tail(10)

# %%
# Columns, types and empty values
df_Service_Business_Expectations.info()

# %%
# Basic statistics
df_Service_Business_Expectations.describe()

# %%
# Row 8 has the real column names -> use it as the header
df_Service_Business_Expectations.columns = df_Service_Business_Expectations.iloc[8]

# %%
# Remove the rows above the data (rows 0 to 8)
df_Service_Business_Expectations = df_Service_Business_Expectations.iloc[9:].reset_index(drop=True)

# %%
# Column names as text, without spaces before/after
services_expectations_column_names = []
for column in df_Service_Business_Expectations.columns:
    services_expectations_column_names.append(str(column).strip())

# %%
# First column -> "Sectors"
services_expectations_column_names[0] = "Sectors"

# %%
df_Service_Business_Expectations.columns = services_expectations_column_names

# %%
df_Service_Business_Expectations.head(5)

# %%
# Find the footnotes at the bottom of the file
services_expectations_first_column_text = df_Service_Business_Expectations["Sectors"].astype(str).str.strip()
services_expectations_footnote_rows = df_Service_Business_Expectations.index[services_expectations_first_column_text.str.startswith("Definitions and Footnotes")]
services_expectations_footnote_rows

# %%
# Cut the df where the footnotes start
if len(services_expectations_footnote_rows) > 0:
    df_Service_Business_Expectations = df_Service_Business_Expectations.iloc[:services_expectations_footnote_rows[0]]

# %%
# Drop the completely empty rows
df_Service_Business_Expectations = df_Service_Business_Expectations.dropna(how="all").reset_index(drop=True)

# %%
# Check that the df now ends at a real row
df_Service_Business_Expectations.tail(5)

# %%
# Values as numbers (all the columns except "Sectors"). Texts like 'na' or '-' -> NaN
for column in df_Service_Business_Expectations.columns[1:]:
    column_values = df_Service_Business_Expectations[column].replace(MISSING_VALUE_TEXTS, np.nan)
    df_Service_Business_Expectations[column] = pd.to_numeric(column_values, errors="coerce").astype(float)

# %%
# Remove spaces before/after the sector names to avoid mismatches
df_Service_Business_Expectations["Sectors"] = df_Service_Business_Expectations["Sectors"].astype(str).str.strip()

# %%
# Review AFTER cleaning
df_Service_Business_Expectations.info()

# %%
df_Service_Business_Expectations.describe()

# %%
df_Service_Business_Expectations.head(5)

# %%
# =====================================================================
# PART 4 - MERGE THE TWO BUSINESS EXPECTATIONS FILES
# They measure the same thing for different sectors -> one df
# =====================================================================
df_Business_Expectations = pd.concat(
    [df_Manufacturing_Business_Expectations, df_Service_Business_Expectations],
    ignore_index=True,
)

# %%
# Period columns from the newest to the oldest, like SingStat
# (with labels like "2025 2Q", sorting the text also sorts them in time)
business_expectations_period_columns = []
for column in df_Business_Expectations.columns:
    if column != "Sectors":
        business_expectations_period_columns.append(column)
business_expectations_period_columns = sorted(business_expectations_period_columns, reverse=True)

# %%
df_Business_Expectations = df_Business_Expectations[["Sectors"] + business_expectations_period_columns]

# %%
# Sector names that appear more than once after merging (should be empty)
df_Business_Expectations[df_Business_Expectations["Sectors"].duplicated()]["Sectors"].unique()

# %%
df_Business_Expectations.info()

# %%
# Keep only the sectors we are interested in
df_Business_Expectations_filtered = df_Business_Expectations[
    df_Business_Expectations["Sectors"].isin(TARGET_SECTORS)
].reset_index(drop=True)

# %%
df_Business_Expectations_filtered

# %%
# =====================================================================
# PART 5 - GDP: SHARE OF EACH SECTOR IN THE TOTAL GDP (%)
# (sector value / total GDP value) * 100
# =====================================================================
gdp_total_row = df_GDP_Growth[df_GDP_Growth["Sectors"] == GDP_TOTAL_ROW]
gdp_total_row

# %%
df_GDP_Share = df_GDP_Growth.copy()

# %%
for period in df_GDP_Growth.columns[1:]:
    total_value = gdp_total_row[period].values[0]
    df_GDP_Share[period] = df_GDP_Growth[period] / total_value * 100

# %%
df_GDP_Share_filtered = df_GDP_Share[df_GDP_Share["Sectors"].isin(TARGET_SECTORS)].reset_index(drop=True)

# %%
df_GDP_Share_filtered = df_GDP_Share_filtered.round(2)

# %%
df_GDP_Share_filtered.head()

# %%
# =====================================================================
# PART 6 - ESG RISK
# This file was created by the team, so its cleaning is minimum.
# Rule:
#   - If 75% or more of the companies answer Yes  -> Low risk
#   - If 60% or more of the companies answer No   -> High risk
#   - All the rest                                -> Medium risk
#   - Missing answers count as "No", missing sectors get High risk
# =====================================================================
# REVIEW BEFORE ANY CHANGE: first rows
df_ESG.head(10)

# %%
df_ESG.tail(10)

# %%
df_ESG.info()

# %%
df_ESG.describe()

# %%
# Different values in both columns
df_ESG[ESG_SECTOR_COLUMN].unique()

# %%
df_ESG[ESG_REPORTING_COLUMN].value_counts(dropna=False)

# %%
# Work on a copy, so df_ESG stays as it comes from the database
df_ESG_clean = df_ESG.copy()

# %%
# Remove spaces in the sector names
df_ESG_clean[ESG_SECTOR_COLUMN] = df_ESG_clean[ESG_SECTOR_COLUMN].astype(str).str.strip()

# %%
# Answers in phrase format: "yes", "YES " -> "Yes"
df_ESG_clean[ESG_REPORTING_COLUMN] = df_ESG_clean[ESG_REPORTING_COLUMN].astype(str).str.strip().str.capitalize()

# %%
# Answers that are empty or not Yes / Partially / No
esg_invalid_answers = ~df_ESG_clean[ESG_REPORTING_COLUMN].isin(ESG_VALID_ANSWERS)
esg_invalid_answers.sum()

# %%
df_ESG_clean.loc[esg_invalid_answers, ESG_REPORTING_COLUMN].value_counts(dropna=False)

# %%
# Missing / invalid answers -> "No" (worst case)
df_ESG_clean.loc[esg_invalid_answers, ESG_REPORTING_COLUMN] = "No"

# %%
# % of Yes / Partially / No per sector
df_ESG_percentages = (
    df_ESG_clean.groupby(ESG_SECTOR_COLUMN)[ESG_REPORTING_COLUMN]
    .value_counts(normalize=True)
    .unstack(fill_value=0) * 100
)

# %%
# Make sure the 3 columns always exist.
# A 0 here is NOT missing data: it means 0% of the companies gave that answer.
df_ESG_percentages = df_ESG_percentages.reindex(columns=ESG_VALID_ANSWERS, fill_value=0)

# %%
df_ESG_percentages

# %%
# Risk of each sector
esg_rows = []
for sector in df_ESG_percentages.index:
    yes_percentage = df_ESG_percentages.loc[sector, "Yes"]
    no_percentage = df_ESG_percentages.loc[sector, "No"]

    if yes_percentage >= ESG_LOW_RISK_IF_YES_AT_LEAST:
        risk = "Low"
    elif no_percentage >= ESG_HIGH_RISK_IF_NO_AT_LEAST:
        risk = "High"
    else:
        risk = "Medium"

    esg_rows.append({
        "Sector": sector,
        "ESG reporting compliance": round(yes_percentage, 2),   # % of companies with Yes
        "risk_score": risk,
    })

# %%
# Target sectors with no ESG data -> High risk (worst case)
esg_missing_sectors = []
for sector in TARGET_SECTORS:
    if sector not in df_ESG_percentages.index:
        esg_missing_sectors.append(sector)
        esg_rows.append({
            "Sector": sector,
            "ESG reporting compliance": np.nan,   # no data -> empty, not 0
            "risk_score": "High",
        })
esg_missing_sectors

# %%
# Final ESG df: Sector | ESG reporting compliance | risk_score
df_ESG_risk = pd.DataFrame(esg_rows)

# %%
df_ESG_risk

# %%
# =====================================================================
# PART 7 - DATA CHECKS: tables to zoom in on data that may not make sense
#   - summary per sector: periods, missing values, first/last period, min, max, mean
#   - unusual jumps: change vs the previous period bigger than 3 standard deviations
# =====================================================================
dfs_to_check = {
    "Real GDP": df_GDP_Growth_filtered,
    "Gross Operating Surplus": df_GrossOperatingSurplusGrowth_filtered,
    "Labour Productivity": df_LabourProductivity_filtered,
    "Equity Ratio": df_EquityRatio_filtered,
    "Business Expectations": df_Business_Expectations_filtered,
}

# %%
UNUSUAL_JUMP_LIMIT = 3

# %%
data_check_summaries = {}
data_check_jumps = {}

for title, df_filtered in dfs_to_check.items():

    # One row per sector + period (same as the melt for the charts)
    df_one_row_per_period = df_filtered.melt(id_vars=["Sectors"], var_name="Period", value_name="Value")
    df_one_row_per_period = df_one_row_per_period.sort_values(["Period", "Sectors"]).reset_index(drop=True)

    summary_rows = []
    jump_tables = []
    for sector in df_one_row_per_period["Sectors"].unique():
        sector_rows = df_one_row_per_period[df_one_row_per_period["Sectors"] == sector].copy()
        sector_rows_with_value = sector_rows.dropna(subset=["Value"])
        has_values = len(sector_rows_with_value) > 0

        # Summary of this sector
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

        # Unusual jumps of this sector
        sector_rows["Change"] = sector_rows["Value"].diff()
        average_change = sector_rows["Change"].mean()
        usual_variation = sector_rows["Change"].std()
        sector_rows["Jump size (std)"] = (sector_rows["Change"] - average_change) / usual_variation
        unusual_rows = sector_rows[sector_rows["Jump size (std)"].abs() > UNUSUAL_JUMP_LIMIT]
        jump_tables.append(unusual_rows[["Sectors", "Period", "Value", "Change", "Jump size (std)"]])

    data_check_summaries[title] = pd.DataFrame(summary_rows).sort_values("Sector").reset_index(drop=True)
    data_check_jumps[title] = pd.concat(jump_tables).round(2).reset_index(drop=True)

# %%
# Look at each check (change the name to see another one)
data_check_summaries["Real GDP"]

# %%
data_check_jumps["Real GDP"]

# %%
data_check_summaries["Gross Operating Surplus"]

# %%
data_check_jumps["Gross Operating Surplus"]

# %%
data_check_summaries["Labour Productivity"]

# %%
data_check_jumps["Labour Productivity"]

# %%
data_check_summaries["Equity Ratio"]

# %%
data_check_jumps["Equity Ratio"]

# %%
data_check_summaries["Business Expectations"]

# %%
data_check_jumps["Business Expectations"]

# %%
# =====================================================================
# PART 8 - CHARTS (saved as HTML in output/)
#   1. Line trend by sector (full history)
#   2. Grouped bars by sector (last 20 periods)
#   3. Donuts (only for amounts that add up to a total: GDP, GOS)
#   4. Bars vs. total (ratios, per worker, expectations: a donut makes no sense)
# =====================================================================
chart_settings = {
    "Real GDP": {
        "df_clean": df_GDP_Growth, "df_filtered": df_GDP_Growth_filtered,
        "unit": "Million dollars (chained 2015)", "total_row": GDP_TOTAL_ROW, "adds_up_to_total": True,
    },
    "Gross Operating Surplus": {
        "df_clean": df_GrossOperatingSurplusGrowth, "df_filtered": df_GrossOperatingSurplusGrowth_filtered,
        "unit": "Million dollars", "total_row": GOS_TOTAL_ROW, "adds_up_to_total": True,
    },
    "Labour Productivity": {
        "df_clean": df_LabourProductivity, "df_filtered": df_LabourProductivity_filtered,
        "unit": "Value added per worker", "total_row": LABOUR_PRODUCTIVITY_TOTAL_ROW, "adds_up_to_total": False,
    },
    "Equity Ratio": {
        "df_clean": df_EquityRatio, "df_filtered": df_EquityRatio_filtered,
        "unit": "Equity ratio (%)", "total_row": EQUITY_RATIO_TOTAL_ROW, "adds_up_to_total": False,
    },
    "Business Expectations": {
        "df_clean": df_Business_Expectations, "df_filtered": df_Business_Expectations_filtered,
        "unit": "Net weighted balance (%)", "total_row": None, "adds_up_to_total": False,
    },
}

# %%
NUMBER_OF_BAR_PERIODS = 20

# %%
for title, settings in chart_settings.items():
    df_clean = settings["df_clean"]
    df_filtered = settings["df_filtered"]
    unit = settings["unit"]
    total_row_name = settings["total_row"]
    file_name = title.lower().replace("&", "and").replace(" ", "_")

    if df_filtered.empty:
        print(f"{title}: the filtered df is EMPTY -> check the sector names in this file")
        continue

    # One row per sector + period, sorted in time
    df_one_row_per_period = df_filtered.melt(id_vars=["Sectors"], var_name="Period", value_name="Value")
    df_one_row_per_period = df_one_row_per_period.sort_values(["Period", "Sectors"]).reset_index(drop=True)
    periods_in_time_order = sorted(df_one_row_per_period["Period"].unique())

    # ---------- 1. Line trend ----------
    line_chart = px.line(
        df_one_row_per_period, x="Period", y="Value", color="Sectors",
        markers=True,
        color_discrete_map=SECTOR_COLORS,
        category_orders={"Period": periods_in_time_order},
        title=f"{title}: trend by industry sector",
        labels={"Period": "Period", "Value": unit, "Sectors": "Industry Sector"},
    )
    line_chart.update_layout(template="plotly_white", hovermode="x unified", legend_title="Industry Sectors")
    line_chart.write_html(PLOTS_FOLDER / f"{file_name}_trend_line.html", include_plotlyjs="cdn")
    if SHOW_CHARTS_IN_BROWSER:
        line_chart.show(renderer="browser")

    # ---------- 2. Grouped bars (last periods) ----------
    last_periods = periods_in_time_order[-NUMBER_OF_BAR_PERIODS:]
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
    bar_chart.write_html(PLOTS_FOLDER / f"{file_name}_sector_bar.html", include_plotlyjs="cdn")
    if SHOW_CHARTS_IN_BROWSER:
        bar_chart.show(renderer="browser")

    # Total row of this file (if there is one)
    if total_row_name is None:
        total_row = df_clean.iloc[0:0]
    else:
        total_row = df_clean[df_clean["Sectors"] == total_row_name]
        if total_row.empty:
            print(f"{title}: total row '{total_row_name}' not found. Row names:")
            print(df_clean["Sectors"].tolist())

    # ---------- 3. Donuts (amounts that add up) ----------
    if settings["adds_up_to_total"] and not total_row.empty:
        # Latest period where the total has a value
        total_periods_with_value = []
        for period in df_clean.columns[1:]:
            if pd.notna(total_row[period].values[0]):
                total_periods_with_value.append(period)
        newest_period = sorted(total_periods_with_value)[-1]
        total_value = total_row[newest_period].values[0]

        # % of the total for each selected sector
        df_pie = df_filtered[["Sectors", newest_period]].copy()
        df_pie.columns = ["Sector", "Percentage"]
        df_pie["Percentage"] = df_pie["Percentage"] / total_value * 100
        selected_sectors_percentage = df_pie["Percentage"].sum()

        # Donut 1: selected sectors + "Other Sectors"
        other_sectors_row = pd.DataFrame([{"Sector": "Other Sectors",
                                           "Percentage": max(0.0, 100.0 - selected_sectors_percentage)}])
        df_pie_with_others = pd.concat([df_pie, other_sectors_row], ignore_index=True)
        donut_total = px.pie(
            df_pie_with_others, names="Sector", values="Percentage", hole=0.4,
            color="Sector", color_discrete_map=SECTOR_COLORS,
            title=f"{title}: share of total ({newest_period}) — selected vs. other sectors",
        )
        donut_total.update_traces(textposition="inside", textinfo="percent+label",
                                  hovertemplate="<b>%{label}</b><br>Share of total: %{value:.2f}%<extra></extra>")
        donut_total.update_layout(template="plotly_white", legend_title="Sectors Breakdown")
        donut_total.write_html(PLOTS_FOLDER / f"{file_name}_total_concentration.html", include_plotlyjs="cdn")
        if SHOW_CHARTS_IN_BROWSER:
            donut_total.show(renderer="browser")

        # Donut 2: zoom in on the selected sectors
        donut_selected = px.pie(
            df_pie, names="Sector", values="Percentage", hole=0.4,
            color="Sector", color_discrete_map=SECTOR_COLORS,
            title=f"{title}: selected sectors ({newest_period}) — {selected_sectors_percentage:.2f}% of the total",
        )
        donut_selected.update_traces(textposition="inside", textinfo="percent+label",
                                     hovertemplate="<b>%{label}</b><br>Share of total: %{value:.2f}%<extra></extra>")
        donut_selected.update_layout(template="plotly_white", legend_title="Selected Sectors")
        donut_selected.write_html(PLOTS_FOLDER / f"{file_name}_selected_sectors.html", include_plotlyjs="cdn")
        if SHOW_CHARTS_IN_BROWSER:
            donut_selected.show(renderer="browser")

    # ---------- 4. Bars vs. total (ratios, per worker, expectations) ----------
    if not settings["adds_up_to_total"]:
        newest_period = sorted(df_one_row_per_period.dropna(subset=["Value"])["Period"].unique())[-1]
        df_bar = df_one_row_per_period[df_one_row_per_period["Period"] == newest_period].sort_values("Value")
        bar_chart = px.bar(
            df_bar, x="Value", y="Sectors", orientation="h",
            color="Sectors", color_discrete_map=SECTOR_COLORS,
            title=f"{title}: selected sectors vs. total ({newest_period})",
            labels={"Value": unit, "Sectors": "Industry Sector"},
        )
        if not total_row.empty:
            total_value = total_row[newest_period].values[0]
            bar_chart.add_vline(x=total_value, line_dash="dash", line_color="#555555",
                                annotation_text=f"{total_row_name}: {total_value:,.2f}",
                                annotation_position="top")
        bar_chart.update_layout(template="plotly_white", showlegend=False)
        bar_chart.write_html(PLOTS_FOLDER / f"{file_name}_vs_total.html", include_plotlyjs="cdn")
        if SHOW_CHARTS_IN_BROWSER:
            bar_chart.show(renderer="browser")

# %%
# =====================================================================
# PART 9 - LAST 5 YEARS
# The most recent year of each df counts as year 1
# =====================================================================
NUMBER_OF_YEARS = 5

# %%
filtered_data = {
    "gdp": df_GDP_Growth_filtered,
    "gos": df_GrossOperatingSurplusGrowth_filtered,
    "labour_productivity": df_LabourProductivity_filtered,
    "equity_ratio": df_EquityRatio_filtered,
    "business_expectations": df_Business_Expectations_filtered,
}

# %%
filtered_data_5_years = {}
for data_name, df_filtered in filtered_data.items():
    # The year is the first 4 characters of the period: "2025 2Q" -> 2025
    newest_year = 0
    for column in df_filtered.columns[1:]:
        newest_year = max(newest_year, int(str(column)[:4]))
    first_year_to_keep = newest_year - (NUMBER_OF_YEARS - 1)

    columns_to_keep = ["Sectors"]
    for column in df_filtered.columns[1:]:
        if int(str(column)[:4]) >= first_year_to_keep:
            columns_to_keep.append(column)

    filtered_data_5_years[data_name] = df_filtered[columns_to_keep].copy()

# %%
filtered_data_5_years["gdp"].head()

# %%
# =====================================================================
# PART 10 - RISK SCORE
#   W1 Economic performance (40): GDP growth 20 + GOS growth 20
#   W2 Financial health     (40): Equity ratio 40
#   W3 Workforce / operational (20): Labour productivity growth 10 + ESG 10
#   Points: Green = 100% of the weight, Amber = 50%, Red = 0%
#   Overall: >= 75 Green | 40 - 74.99 Amber | < 40 Red
#   Override: 2+ Red indicators -> max Amber | 1 Red + Green -> warning
# =====================================================================
PILLARS = {
    "W1": "Economic performance",
    "W2": "Financial health",
    "W3": "Workforce / operational risk",
}

# %%
# Indicators of the score
#   calculation: "yearly_growth" -> % change vs the same quarter one year before
#                "value"         -> the value as it is
#                "esg"           -> uses the ESG risk (Low / Medium / High)
#   Green  if value >  green_from  (>= if green_includes_limit is True)
#   Amber  if value >= amber_from
#   Red    in any other case
SCORE_INDICATORS = {
    "gdp_growth": {
        "label": "Real GDP growth (YoY %)", "data_name": "gdp", "pillar": "W1", "weight": 20,
        "calculation": "yearly_growth",
        "green_from": 3, "green_includes_limit": False, "amber_from": 0,     # >3 | 0-3 | <0
    },
    "gos_growth": {
        "label": "GOS growth (YoY %)", "data_name": "gos", "pillar": "W1", "weight": 20,
        "calculation": "yearly_growth",
        "green_from": 5, "green_includes_limit": False, "amber_from": 0,     # >5 | 0-5 | <0
    },
    "equity_ratio": {
        "label": "Equity ratio (%)", "data_name": "equity_ratio", "pillar": "W2", "weight": 40,
        "calculation": "value",
        "green_from": 40, "green_includes_limit": True, "amber_from": 20,    # >=40 | 20-<40 | <20
    },
    "labour_productivity": {
        "label": "Labour productivity growth (YoY %)", "data_name": "labour_productivity", "pillar": "W3", "weight": 10,
        "calculation": "yearly_growth",
        "green_from": 0, "green_includes_limit": True, "amber_from": -3,     # >=0 | -3-<0 | <-3
    },
    "esg": {
        "label": "ESG reporting", "data_name": "esg", "pillar": "W3", "weight": 10,
        "calculation": "esg",
    },
}

# %%
ESG_RISK_TO_LIGHT = {"Low": "Green", "Medium": "Amber", "High": "Red"}

# %%
POINTS_PER_LIGHT = {"Green": 1.0, "Amber": 0.5, "Red": 0.0}

# %%
GREEN_IF_SCORE_AT_LEAST = 75
AMBER_IF_SCORE_AT_LEAST = 40
NUMBER_OF_REDS_THAT_BLOCK_GREEN = 2

# %%
# Annual data (equity ratio): if a year is not published yet,
# use the value of the year before (up to this many years back)
MAX_YEARS_BACK_FOR_ANNUAL_DATA = 1

# %%
# Check that the weights add up to 100
total_weight = 0
for indicator_settings in SCORE_INDICATORS.values():
    total_weight = total_weight + indicator_settings["weight"]
total_weight

# %%
# ---------------------------------------------------------------------
# 10.1 QUARTERS OF THE SCORE
# Quarters of the last 5 years that have data in the GDP df (oldest -> newest)
# ---------------------------------------------------------------------
score_quarters = []
for column in filtered_data_5_years["gdp"].columns[1:]:
    if filtered_data_5_years["gdp"][column].notna().any():
        score_quarters.append(column)
score_quarters = sorted(score_quarters)
score_quarters

# %%
# ---------------------------------------------------------------------
# 10.2 VALUES OF EACH INDICATOR
# Growth = (value / value of the same period one year before - 1) * 100
# "2025 2Q" is compared with "2024 2Q"
# ---------------------------------------------------------------------
score_values = {}
for indicator_name, indicator_settings in SCORE_INDICATORS.items():

    if indicator_settings["calculation"] == "esg":
        continue

    df_indicator = filtered_data[indicator_settings["data_name"]]

    if indicator_settings["calculation"] == "value":
        score_values[indicator_name] = df_indicator
        continue

    # Yearly growth
    df_growth = df_indicator[["Sectors"]].copy()
    for period in df_indicator.columns[1:]:
        period_parts = period.split()
        period_parts[0] = str(int(period_parts[0]) - 1)
        period_one_year_before = " ".join(period_parts)
        if period_one_year_before in df_indicator.columns:
            df_growth[period] = (df_indicator[period] / df_indicator[period_one_year_before] - 1) * 100
    score_values[indicator_name] = df_growth

# %%
score_values["gdp_growth"].head()

# %%
# ---------------------------------------------------------------------
# 10.3 INDICATOR RESULTS: one row per sector + quarter + indicator
# (value, period used, traffic light, weight and points)
# ---------------------------------------------------------------------
indicator_result_rows = []

for indicator_name, indicator_settings in SCORE_INDICATORS.items():
    for sector in TARGET_SECTORS:
        for quarter in score_quarters:

            value = np.nan
            value_period = None

            if indicator_settings["calculation"] == "esg":
                # ESG has no quarters: the same result is used in every quarter
                esg_row = df_ESG_risk[df_ESG_risk["Sector"] == sector]
                value = esg_row["ESG reporting compliance"].values[0]   # % of companies with Yes
                value_period = "ESG report"
                light = ESG_RISK_TO_LIGHT[esg_row["risk_score"].values[0]]

            else:
                df_indicator_values = score_values[indicator_name]
                sector_rows = df_indicator_values[df_indicator_values["Sectors"] == sector]

                if not sector_rows.empty:
                    sector_row = sector_rows.iloc[0]

                    if quarter in df_indicator_values.columns:
                        # Quarterly data: the value of that quarter
                        if pd.notna(sector_row[quarter]):
                            value = sector_row[quarter]
                            value_period = quarter
                    else:
                        # Annual data: the value of that year, or the year before
                        quarter_year = int(quarter.split()[0])
                        for years_back in range(MAX_YEARS_BACK_FOR_ANNUAL_DATA + 1):
                            year = str(quarter_year - years_back)
                            if year in df_indicator_values.columns and pd.notna(sector_row[year]):
                                value = sector_row[year]
                                value_period = year
                                break

                # Traffic light of the value
                if pd.isna(value):
                    light = np.nan
                else:
                    if indicator_settings["green_includes_limit"]:
                        is_green = value >= indicator_settings["green_from"]
                    else:
                        is_green = value > indicator_settings["green_from"]

                    if is_green:
                        light = "Green"
                    elif value >= indicator_settings["amber_from"]:
                        light = "Amber"
                    else:
                        light = "Red"

            # Points earned
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

# %%
df_indicator_results = pd.DataFrame(indicator_result_rows)

# %%
df_indicator_results.head(10)

# %%
df_indicator_results.info()

# %%
# ---------------------------------------------------------------------
# 10.4 PILLAR RESULTS: one row per sector + quarter + pillar
# Score 0-100 = points earned / max points of the indicators WITH data * 100
# ---------------------------------------------------------------------
pillar_result_rows = []

for sector in TARGET_SECTORS:
    for quarter in score_quarters:
        for pillar in PILLARS:
            is_this_sector = df_indicator_results["Sectors"] == sector
            is_this_quarter = df_indicator_results["Quarter"] == quarter
            is_this_pillar = df_indicator_results["Pillar"] == pillar
            indicator_rows = df_indicator_results[is_this_sector & is_this_quarter & is_this_pillar]

            rows_with_data = indicator_rows[indicator_rows["Light"].notna()]
            points_earned = rows_with_data["Points"].sum()
            max_points_with_data = rows_with_data["Weight"].sum()
            max_points_total = indicator_rows["Weight"].sum()

            if max_points_with_data == 0:
                score = np.nan
                coverage = 0.0
            else:
                score = round(points_earned / max_points_with_data * 100, 2)
                coverage = round(max_points_with_data / max_points_total * 100, 1)

            if pd.isna(score):
                pillar_light = np.nan
            elif score >= GREEN_IF_SCORE_AT_LEAST:
                pillar_light = "Green"
            elif score >= AMBER_IF_SCORE_AT_LEAST:
                pillar_light = "Amber"
            else:
                pillar_light = "Red"

            pillar_result_rows.append({
                "Sectors": sector,
                "Quarter": quarter,
                "Pillar": pillar,
                "Pillar name": PILLARS[pillar],
                "Score": score,
                "Light": pillar_light,
                "Data coverage %": coverage,
            })

# %%
df_pillar_results = pd.DataFrame(pillar_result_rows)

# %%
df_pillar_results.head(10)

# %%
# ---------------------------------------------------------------------
# 10.5 OVERALL RESULTS: one row per sector + quarter, with the override rules
# ---------------------------------------------------------------------
overall_result_rows = []

for sector in TARGET_SECTORS:
    for quarter in score_quarters:
        is_this_sector = df_indicator_results["Sectors"] == sector
        is_this_quarter = df_indicator_results["Quarter"] == quarter
        indicator_rows = df_indicator_results[is_this_sector & is_this_quarter]

        # Score
        rows_with_data = indicator_rows[indicator_rows["Light"].notna()]
        points_earned = rows_with_data["Points"].sum()
        max_points_with_data = rows_with_data["Weight"].sum()
        max_points_total = indicator_rows["Weight"].sum()

        if max_points_with_data == 0:
            score = np.nan
            coverage = 0.0
        else:
            score = round(points_earned / max_points_with_data * 100, 2)
            coverage = round(max_points_with_data / max_points_total * 100, 1)

        # Light by score
        if pd.isna(score):
            light_by_score = np.nan
        elif score >= GREEN_IF_SCORE_AT_LEAST:
            light_by_score = "Green"
        elif score >= AMBER_IF_SCORE_AT_LEAST:
            light_by_score = "Amber"
        else:
            light_by_score = "Red"

        # Override rules
        red_indicators = indicator_rows[indicator_rows["Light"] == "Red"]["Label"].tolist()
        number_of_reds = len(red_indicators)

        final_light = light_by_score
        override_applied = False
        warning = ""
        if light_by_score == "Green" and number_of_reds >= NUMBER_OF_REDS_THAT_BLOCK_GREEN:
            final_light = "Amber"
            override_applied = True
            warning = f"Green blocked: {number_of_reds} Red indicators ({', '.join(red_indicators)})"
        elif light_by_score == "Green" and number_of_reds == 1:
            warning = f"Risk warning: {red_indicators[0]} is Red"

        overall_result_rows.append({
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

# %%
df_overall_results = pd.DataFrame(overall_result_rows)

# %%
df_overall_results.head(10)

# %%
# ---------------------------------------------------------------------
# 10.6 FINAL TABLES: sectors as rows, quarters of the last 5 years as columns
# ---------------------------------------------------------------------
df_overall_score_table = df_overall_results.pivot(index="Sectors", columns="Quarter", values="Score")
df_overall_score_table = df_overall_score_table.reindex(index=TARGET_SECTORS, columns=score_quarters)
df_overall_score_table.columns.name = None

# %%
df_overall_score_table

# %%
df_overall_light_table = df_overall_results.pivot(index="Sectors", columns="Quarter", values="Final light")
df_overall_light_table = df_overall_light_table.reindex(index=TARGET_SECTORS, columns=score_quarters)
df_overall_light_table.columns.name = None

# %%
df_overall_light_table

# %%
# One table per indicator (values, lights and points)
indicator_value_tables = {}
indicator_light_tables = {}
indicator_points_tables = {}
for indicator_name in SCORE_INDICATORS:
    indicator_rows = df_indicator_results[df_indicator_results["Indicator"] == indicator_name]
    for column_to_show, tables in [("Value", indicator_value_tables),
                                   ("Light", indicator_light_tables),
                                   ("Points", indicator_points_tables)]:
        df_table = indicator_rows.pivot(index="Sectors", columns="Quarter", values=column_to_show)
        df_table = df_table.reindex(index=TARGET_SECTORS, columns=score_quarters)
        df_table.columns.name = None
        tables[indicator_name] = df_table

# %%
indicator_value_tables["gdp_growth"]

# %%
indicator_light_tables["gdp_growth"]

# %%
# One table per pillar (score and light)
pillar_score_tables = {}
pillar_light_tables = {}
for pillar in PILLARS:
    pillar_rows = df_pillar_results[df_pillar_results["Pillar"] == pillar]
    for column_to_show, tables in [("Score", pillar_score_tables), ("Light", pillar_light_tables)]:
        df_table = pillar_rows.pivot(index="Sectors", columns="Quarter", values=column_to_show)
        df_table = df_table.reindex(index=TARGET_SECTORS, columns=score_quarters)
        df_table.columns.name = None
        tables[pillar] = df_table

# %%
pillar_score_tables["W1"]

# %%
pillar_light_tables["W1"]

# %%
# Sectors and quarters with a warning (override or a single Red)
df_warnings = df_overall_results[df_overall_results["Warning"] != ""]
df_warnings[["Sectors", "Quarter", "Score", "Final light", "Warning"]]

# %%
# ---------------------------------------------------------------------
# 10.7 REPORT FOR ONE SECTOR AND ONE QUARTER (change them here)
# ---------------------------------------------------------------------
report_sector = "Manufacturing"
report_quarter = score_quarters[-1]     # latest quarter

# %%
is_this_sector = df_indicator_results["Sectors"] == report_sector
is_this_quarter = df_indicator_results["Quarter"] == report_quarter
report_indicator_rows = df_indicator_results[is_this_sector & is_this_quarter]

# %%
is_this_sector = df_overall_results["Sectors"] == report_sector
is_this_quarter = df_overall_results["Quarter"] == report_quarter
report_overall_row = df_overall_results[is_this_sector & is_this_quarter].iloc[0]

# %%
# 1. INDICATOR BREAKDOWN
report_breakdown = report_indicator_rows[["Pillar", "Label", "Value", "Value period", "Light", "Weight", "Points"]].copy()
report_breakdown["Light"] = report_breakdown["Light"].fillna("No data")
report_breakdown

# %%
# 2. CALCULATION
report_rows_with_data = report_indicator_rows[report_indicator_rows["Light"].notna()]
report_points_earned = report_rows_with_data["Points"].sum()
report_max_points = report_rows_with_data["Weight"].sum()
print(f"Points: {report_points_earned:.2f} out of {report_max_points:.0f}")
if report_overall_row["Data coverage %"] < 100:
    print(f"Some indicators have no data -> rescaled to 100: "
          f"{report_points_earned:.2f} / {report_max_points:.0f} x 100 = {report_overall_row['Score']:.2f}")
print(f"Overall score: {report_overall_row['Score']:.2f} / 100  ->  {report_overall_row['Light by score']} by score")

# %%
# 3. OVERRIDE RULE CHECK
print(f"Red indicators: {report_overall_row['Red indicators']}")
if report_overall_row["Override applied"]:
    print(f"APPLIES: {report_overall_row['Warning']} -> maximum allowed is Amber")
elif report_overall_row["Warning"] != "":
    print(f"Does not apply (only 1 Red). {report_overall_row['Warning']}")
else:
    print("Does not apply")

# %%
# 4. FINAL RESULT
print(f"Numerical score : {report_overall_row['Score']:.2f}")
print(f"Final status    : {report_overall_row['Final light']}")