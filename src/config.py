# ###
# Purpose:
# All the configurations of the project in one place: 
#   paths, files, sectors, indicators, colors. 
# Creation day: 2026-09-28
# Moficiation day: 2026-10-01
# Created by: @ansanc
# Note that this code uses the help of Copilot or Claude IA, own knowledge and what was learnt in class.





######################################################################
# 1. FOLDERS
# Project_Dashboard/
# ├── data/          <- CSVs, Excel, the database (.db) and the baselines
# ├── output/        <- HTML charts and result CSVs
# ├── log/           <- pipeline.log (what happened in each run)
# ├── test/          <- pytest tests
# └── src/           <- all the .py files (this file is here)
######################################################################
# import libraries
from pathlib import Path
# routes/ path of files to read or deliver
PROJECT_FOLDER = Path(__file__).resolve().parent.parent
DATA_FOLDER = PROJECT_FOLDER / "data"
OUTPUT_FOLDER = PROJECT_FOLDER / "output"
PLOTS_FOLDER = OUTPUT_FOLDER
DATABASE_PATH = DATA_FOLDER / "Database_RiskDashboard.db"

# Logs: every run writes what happened in log/pipeline.log
LOG_FOLDER = PROJECT_FOLDER / "log"
LOG_FILE = LOG_FOLDER / "pipeline.log"

# Results saved by the pipeline (the "analysis-ready" outputs)
INDICATOR_RESULTS_FILE = OUTPUT_FOLDER / "indicator_results.csv"
PILLAR_RESULTS_FILE = OUTPUT_FOLDER / "pillar_results.csv"
OVERALL_RESULTS_FILE = OUTPUT_FOLDER / "overall_results.csv"

# Baseline: a copy of a result we trust. The tests compare every new run against it
# Put True ONLY for one run, when you are sure the results are correct,
# and then put it back to False (if not, every run overwrites the baseline)
SAVE_BASELINE = False
BASELINE_OVERALL_RESULTS_FILE = DATA_FOLDER / "reconciliation_baseline_overall_results.csv"
BASELINE_INDICATOR_RESULTS_FILE = DATA_FOLDER / "reconciliation_baseline_indicator_results.csv"


######################################################################
# 2. DATA FILES
# For each file:
#   file_name  : name of the file inside the data folder
#   table_name : name of the table inside the database
#   (the row with the column names is found automatically: the one that says "Data Series")
######################################################################

DATA_FILES = {
    "gdp": {
        "file_name": "RealGDPGrowthByIndustry.csv",
        "table_name": "raw_gdp_growth",
    },
    "gos": {
        "file_name": "GrossOperatingSurplusGrowthByIndustry.csv",
        "table_name": "raw_gross_operating_surplus",
    },
    "labour_productivity": {
        "file_name": "LabourProductivityValueAddedPerWorker.csv",
        "table_name": "raw_labour_productivity",
    },
    "equity_ratio": {
        "file_name": "EquityRatioOfCompaniesByIndustry.csv",
        "table_name": "raw_equity_ratio",
    },
    "business_expectations_manufacturing": {
        "file_name": "BusinessExpectationsOfTheManufacturingSector.csv",
        "table_name": "raw_business_exp_manufacturing",
    },
    "business_expectations_services": {
        "file_name": "BusinessExpectationsOfTheServiceSector.csv",
        "table_name": "raw_business_exp_services",
    },
    "esg": {
        "file_name": "ESGReports.xlsx",
        "table_name": "raw_esg",
    },
}

# Files that measure the SAME thing for different sectors -> merged into one df
FILES_TO_MERGE = {
    "business_expectations": ["business_expectations_manufacturing",
                              "business_expectations_services"],
}


######################################################################
# 3. SECTORS
######################################################################

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


######################################################################
# 4. INDICATORS TO ANALYSE: data checks and charts (after merging the files)
#   title            : name shown in charts and tables
#   unit             : unit shown in the axis
#   total_row        : exact name of the TOTAL row in the file   -> CHECK
#                      None = there is no total row
#   adds_up_to_total : True  -> amounts that add up (donut charts)
#                      False -> ratios / per worker / expectations (bars vs total)
######################################################################

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


######################################################################
# 5. ESG FILE
######################################################################

ESG_SECTOR_COLUMN = "Sector"            # CHECK: real name of the sector column
ESG_REPORTING_COLUMN = "ESG reporting"
ESG_VALID_ANSWERS = ["Yes", "Partially", "No"]
ESG_LOW_RISK_IF_YES_AT_LEAST = 75       # >= 75% Yes -> Low risk
ESG_HIGH_RISK_IF_NO_AT_LEAST = 60       # >= 60% No  -> High risk


######################################################################
# 6. OTHER SETTINGS
######################################################################
# Text values that mean "no data" in the files
MISSING_VALUE_TEXTS = ['NaN', 'nan', 'na', '-', ' ', '']

# Open the charts in the browser? False = only save the HTML files in output/
SHOW_CHARTS_IN_BROWSER = False


######################################################################
# 7. RISK SCORE (PART 2)
# There are traffic lights (Green / Amber / Red) at 3 levels:
#   1. Each INDICATOR (5 lights)  -> its own limits in SCORE_INDICATORS
#                                    (ESG included, it is one more indicator of W3)
#   2. Each PILLAR    (3 lights)  -> W1, W2, W3, from the score of its indicators
#   3. The OVERALL score (1 light) -> from the weighted sum of all the indicators
######################################################################
# How many years of quarters the score tables show
SCORE_NUMBER_OF_YEARS = 5

# The quarters of the score tables are taken from this indicator
SCORE_QUARTERS_TAKEN_FROM = "gdp"

# Annual data (equity ratio): if a year is not published yet, use the
# value of the year before (up to this many years back)
MAX_YEARS_BACK_FOR_ANNUAL_DATA = 1

# The 3 pillars (each one has its own traffic light, level 2)
PILLARS = {
    "W1": "Economic performance",          # 40 points (GDP growth + GOS growth)
    "W2": "Financial health",              # 40 points (Equity ratio)
    "W3": "Workforce / operational risk",  # 20 points (Labour productivity growth + ESG reporting)
}
# What each pillar contains and how its score is calculated:
#   W1 (40) = GDP growth (20) + GOS growth (20)
#   W2 (40) = Equity ratio (40)
#   W3 (20) = Labour productivity growth (10) + ESG reporting (10)
#
#   Points of each indicator = weight x points of its light (Green 1 | Amber 0.5 | Red 0)
#   Pillar score  = points of its indicators / maximum points of the pillar x 100
#   Overall score = W1 points + W2 points + W3 points   (out of 100)
#   Example: GDP Green (20) + GOS Red (0) -> W1 = 20 / 40 x 100 = 50 -> Amber

# Indicators of the score (each one has its own traffic light, level 1)
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
#   ESG is the only one without these limits: its light comes from its risk
#   (Low / Medium / High, rule in section 5) -> see ESG_RISK_TO_LIGHT below
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
        # Light: >= 75% Yes -> Green | >= 60% No -> Red | rest -> Amber
        # (limits in section 5: ESG_LOW_RISK_IF_YES_AT_LEAST, ESG_HIGH_RISK_IF_NO_AT_LEAST)
    },
}

# ESG risk -> traffic light of the ESG indicator
# (ESG gives a risk word instead of a number, so it only needs to be translated)
ESG_RISK_TO_LIGHT = {"Low": "Green", "Medium": "Amber", "High": "Red"}

# Part of the indicator's weight earned by each light (1 = all the points)
POINTS_PER_LIGHT = {"Green": 1.0, "Amber": 0.5, "Red": 0.0}

# Pillar score and overall score -> traffic light (levels 2 and 3)
# >= 75 Green | 40 - 74.99 Amber (70 - 74.99 falls into Amber) | < 40 Red
GREEN_IF_SCORE_AT_LEAST = 75
AMBER_IF_SCORE_AT_LEAST = 40

# Override rule: with this many Red indicators (or more) a sector can't be Green
NUMBER_OF_REDS_THAT_BLOCK_GREEN = 2