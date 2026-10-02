# ###
# Purpose:
# All the configurations of the project in one place: 
#   paths, files, sectors, indicators, colors. 
# Creation day: 2026-09-28
# Moficiation day: 2026-10-01
# Created by: @ansanc
# ##
# Import libraries
from pathlib import Path

# 1. FOLDERS
# Project_Dashboard/
# ├── data/          <- CSVs, Excel and the database (.db)
# ├── output/        <- HTML charts (created by plots.py)
# └── src/           <- all the .py files (this file is here)
# =====================================================================
PROJECT_FOLDER = Path(__file__).resolve().parent.parent
DATA_FOLDER = PROJECT_FOLDER / "data"
PLOTS_FOLDER = PROJECT_FOLDER / "output"
DATABASE_PATH = DATA_FOLDER / "Database_RiskDashboard.db"


# =====================================================================
# 2. DATA FILES
# For each file:
#   file_name  : name of the file inside the data folder
#   table_name : name of the table inside the database
#   header_row : row that has the column names (SingStat files = row 8)
#                None = the file already has the right column names
# =====================================================================
DATA_FILES = {
    "gdp": {
        "file_name": "RealGDPGrowthByIndustry.csv",
        "table_name": "raw_gdp_growth",
        "header_row": 8,
    },
    "gos": {
        "file_name": "GrossOperatingSurplusGrowthByIndustry.csv",
        "table_name": "raw_gross_operating_surplus",
        "header_row": 8,
    },
    "labour_productivity": {
        "file_name": "LabourProductivityValueAddedPerWorker.csv",
        "table_name": "raw_labour_productivity",
        "header_row": 8,
    },
    "equity_ratio": {
        "file_name": "EquityRatioOfCompaniesByIndustry.csv",
        "table_name": "raw_equity_ratio",
        "header_row": None,
    },
    "business_expectations_manufacturing": {
        "file_name": "BusinessExpectationsOfTheManufacturingSector.csv",
        "table_name": "raw_business_exp_manufacturing",
        "header_row": 8,
    },
    "business_expectations_services": {
        "file_name": "BusinessExpectationsOfTheServiceSector.csv",
        "table_name": "raw_business_exp_services",
        "header_row": 8,
    },
    "esg": {
        "file_name": "ESGReports.xlsx",
        "table_name": "raw_esg",
        "header_row": None,
    },
}

# ###
# COMBINED DF
# One variable is divided in two csv and therefore they are merged later on for the score
# The parts are replaced by the merged df.
FILES_TO_MERGE = {
    "business_expectations": ["business_expectations_manufacturing",
                              "business_expectations_services"],
}


# =====================================================================
# 3. SECTORS
# =====================================================================
TARGET_SECTORS = [
    'Manufacturing',
    'Real Estate',
    'Transportation & Storage',
    'Information & Communications',
    'Utilities',
]

# One fixed color per sector, so each sector has the same color in every chart
SECTOR_COLORS = {
    'Manufacturing':                '#2a78d6',   # blue
    'Real Estate':                  '#eb6834',   # orange
    'Transportation & Storage':     '#1baf7a',   # aqua
    'Information & Communications': '#eda100',   # yellow
    'Utilities':                    '#e87ba4',   # pink
    'Other Sectors':                '#b5b4ad',   # gray
}


# =====================================================================
# 4. INDICATORS TO ANALYSE: data checks and charts (after merging the files)
#   title            : name shown in charts and tables
#   unit             : unit shown in the axis
#   total_row        : exact name of the TOTAL row in the file   -> CHECK
#                      None = there is no total row
#   adds_up_to_total : True  -> amounts that add up (donut charts)
#                      False -> ratios / per worker / expectations (bars vs total)
# =====================================================================
INDICATORS_TO_ANALYSE = {
    "gdp": {
        "title": "Real GDP",
        "unit": "Million dollars (chained 2015)",
        "total_row": "GDP In Chained (2015) Dollars",
        "adds_up_to_total": True,
    },
    "gos": {
        "title": "Gross Operating Surplus",
        "unit": "Million dollars",
        "total_row": "Gross Operating Surplus",          # CHECK
        "adds_up_to_total": True,
    },
    "labour_productivity": {
        "title": "Labour Productivity",
        "unit": "Value added per worker",
        "total_row": "Overall Economy",                  # CHECK
        "adds_up_to_total": False,
    },
    "equity_ratio": {
        "title": "Equity Ratio",
        "unit": "Equity ratio (%)",
        "total_row": "All Industries",                   # CHECK
        "adds_up_to_total": False,
    },
    "business_expectations": {
        "title": "Business Expectations",
        "unit": "Net weighted balance (%)",
        "total_row": None,
        "adds_up_to_total": False,
    },
}


# ###
# 5. ESG FILE
# This file was created by the team, therefore the cleaning of it is minimum in comparison to the others sources.
# This is a file that recolected from the top companies in Singapure from the sectors we are interested si they report ESG criteria or not
# In this file we are interested in two things:
# First, if a companies has a very complete ESG report, partially reporting, or does not report
# Second, a calculated ratio of the tendancy of the sector based in this companies
# There is one relevant decision done by the team that creates a big limitation: just 10 of the biggest companies of each sector were selected,
# and therefore the tendancy is created in this case with the probable most mature companies of the sector that in some cases could be the "exceptions"
# But the idea would be that in a bank we would have the list of all clients and then the pool of information would be larger

ESG_SECTOR_COLUMN = "Sector"            # CHECK: real name of the sector column
ESG_REPORTING_COLUMN = "ESG reporting"
ESG_VALID_ANSWERS = ["Yes", "Partially", "No"]

# Each company has an "ESG reporting" answer: Yes, Partially or No.
# Rule:
#   - If 75% or more of the companies answer Yes  -> Low risk
#   - If 60% or more of the companies answer No   -> High risk
#   - All the rest     
ESG_LOW_RISK_IF_YES_AT_LEAST = 75       # >= 75% Yes -> Low risk
ESG_HIGH_RISK_IF_NO_AT_LEAST = 60       # >= 60% No  -> High risk


# =====================================================================
# 6. OTHER SETTINGS
# =====================================================================
# Text values that mean "no data" in the files
MISSING_VALUE_TEXTS = ['NaN', 'nan', 'na', '-', ' ', '']

# Open the charts in the browser? False = only save the HTML files
SHOW_CHARTS_IN_BROWSER = True


# =====================================================================
# 7. RISK SCORE (PART 2)
# =====================================================================
# How many years of quarters the score tables show
SCORE_NUMBER_OF_YEARS = 5

# The quarters of the score tables are taken from this indicator
SCORE_QUARTERS_TAKEN_FROM = "gdp"

# Annual data (equity ratio): if a year is not published yet, use the
# value of the year before (up to this many years back)
MAX_YEARS_BACK_FOR_ANNUAL_DATA = 1

# The 3 pillars (each one is also a traffic light)
PILLARS = {
    "W1": "Economic performance",
    "W2": "Financial health",
    "W3": "Workforce / operational risk",
}

# Indicators of the score
#   label         : name shown in the tables
#   data_name     : which df the values come from (or "esg")
#   pillar        : W1 / W2 / W3
#   weight        : points out of 100  (W1 = 40, W2 = 40, W3 = 20)
#   calculation   : "yearly_growth" -> % change vs the same quarter one year before
#                   "value"         -> the value as it is
#                   "esg"           -> uses the ESG risk (Low / Medium / High)
#   green_from, green_includes_limit, amber_from : traffic light limits
#       Green  if value >  green_from   (>= if green_includes_limit is True)
#       Amber  if value >= amber_from
#       Red    in any other case
SCORE_INDICATORS = {
    "gdp_growth": {
        "label": "Real GDP growth (YoY %)",
        "data_name": "gdp",
        "pillar": "W1",
        "weight": 20,
        "calculation": "yearly_growth",
        "green_from": 3, "green_includes_limit": False, "amber_from": 0,    # >3 | 0-3 | <0
    },
    "gos_growth": {
        "label": "GOS growth (YoY %)",
        "data_name": "gos",
        "pillar": "W1",
        "weight": 20,
        "calculation": "yearly_growth",
        "green_from": 5, "green_includes_limit": False, "amber_from": 0,    # >5 | 0-5 | <0
    },
    "equity_ratio": {
        "label": "Equity ratio (%)",
        "data_name": "equity_ratio",
        "pillar": "W2",
        "weight": 40,
        "calculation": "value",
        "green_from": 40, "green_includes_limit": True, "amber_from": 20,   # >=40 | 20-<40 | <20
    },
    "labour_productivity": {
        "label": "Labour productivity growth (YoY %)",
        "data_name": "labour_productivity",
        "pillar": "W3",
        "weight": 10,
        "calculation": "yearly_growth",
        "green_from": 0, "green_includes_limit": True, "amber_from": -3,    # >=0 | -3-<0 | <-3
    },
    "esg": {
        "label": "ESG reporting",
        "data_name": "esg",
        "pillar": "W3",
        "weight": 10,
        "calculation": "esg",
    },
}

# ESG risk -> traffic light
ESG_RISK_TO_LIGHT = {"Low": "Green", "Medium": "Amber", "High": "Red"}

# Part of the indicator's weight earned by each light (1 = all the points)
POINTS_PER_LIGHT = {"Green": 1.0, "Amber": 0.5, "Red": 0.0}

# Overall score -> traffic light (70 - 74.99 falls into Amber)
GREEN_IF_SCORE_AT_LEAST = 75
AMBER_IF_SCORE_AT_LEAST = 40

# Override rule: with this many Red indicators (or more) a sector can't be Green
NUMBER_OF_REDS_THAT_BLOCK_GREEN = 2