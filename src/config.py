# ###
# Purpose:
# All the configurations of the project in one place: 
#   paths, files, sectors, indicators, colors. 
# Creation day: 2026-09-28
# Moficiation day: 2026-10-01
# Created by: @ansanc
# ##

from pathlib import Path

# ###
# PATHS
# ##
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "Database_RiskDashboard.db"
PLOTS_DIR = PROJECT_ROOT / "plots"

# ###
# RAW FILES 
# 
SOURCE_FILES = {
    "raw_esg":                        "ESGReports.xlsx",
    "raw_gdp_growth":                 "RealGDPGrowthByIndustry.csv",
    "raw_gross_operating_surplus":    "GrossOperatingSurplusGrowthByIndustry.csv",
    "raw_labour_productivity":        "LabourProductivityValueAddedPerWorker.csv",
    "raw_equity_ratio":               "EquityRatioOfCompaniesByIndustry.csv",
    "raw_business_exp_manufacturing": "BusinessExpectationsOfTheManufacturingSector.csv",
    "raw_business_exp_services":      "BusinessExpectationsOfTheServiceSector.csv",
}

# ###
# SECTORS WE FOCUS ON
# ##
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

# ###
# INDICATORS (one entry per data file, except ESG)
#   table      : table name in the database
#   name       : readable name for titles
#   unit       : unit for the axis labels
#   header_row : row that has the column names (SingStat files = 8).
#                None = the file already has the right header
#   total_row  : exact name of the TOTAL row in the file  -> CHECK with your data
#   adds_up    : True  -> it's an amount that adds up to a total (donut charts)
#                False -> ratio / per worker / expectations (bars vs total)
# ###
INDICATORS = {
    "gdp": {
        "table": "raw_gdp_growth",
        "name": "Real GDP",
        "unit": "Million dollars (chained 2015)",
        "header_row": 8,
        "total_row": "GDP In Chained (2015) Dollars",
        "adds_up": True,
    },
    "gos": {
        "table": "raw_gross_operating_surplus",
        "name": "Gross Operating Surplus",
        "unit": "Million dollars",
        "header_row": 8,
        "total_row": "Gross Operating Surplus",          # CHECK
        "adds_up": True,
    },
    "labour_productivity": {
        "table": "raw_labour_productivity",
        "name": "Labour Productivity",
        "unit": "Value added per worker",
        "header_row": 8,
        "total_row": "Overall Economy",                  # CHECK
        "adds_up": False,
    },
    "equity_ratio": {
        "table": "raw_equity_ratio",
        "name": "Equity Ratio",
        "unit": "Equity ratio (%)",
        "header_row": None,
        "total_row": "All Industries",                   # CHECK
        "adds_up": False,
    },
    "biz_exp_manufacturing": {
        "table": "raw_business_exp_manufacturing",
        "name": "Manufacturing Business Expectations",
        "unit": "Net weighted balance (%)",
        "header_row": 8,
        "total_row": "Total Manufacturing",              # CHECK
        "adds_up": False,
    },
    "biz_exp_services": {
        "table": "raw_business_exp_services",
        "name": "Service Business Expectations",
        "unit": "Net weighted balance (%)",
        "header_row": 8,
        "total_row": "Total Services Sector",            # CHECK
        "adds_up": False,
    },
}

# ###
# COMBINED DF
# One variable is divided in two csv and therefore they are merged later on for the score
# The parts are replaced by the combined df.
# ---------------------------------------------------------------------
COMBINED_INDICATORS = {
    "business_expectations": {
        "parts": ["biz_exp_manufacturing", "biz_exp_services"],
        "name": "Business Expectations",
        "unit": "Net weighted balance (%)",
        "total_row": None,        # no common total for manufacturing + services
        "adds_up": False,
    },
}

# ###
# ESG FILE
# This file was created by the team, therefore the cleaning of it is minimum in comparison to the others sources.
# This is a file that recolected from the top companies in Singapure from the sectors we are interested si they report ESG criteria or not
# In this file we are interested in two things:
# First, if a companies has a very complete ESG report, partially reporting, or does not report
# Second, a calculated ratio of the tendancy of the sector based in this companies
# There is one relevant decision done by the team that creates a big limitation: just 10 of the biggest companies of each sector were selected,
# and therefore the tendancy is created in this case with the probable most mature companies of the sector that in some cases could be the "exceptions"
# But the idea would be that in a bank we would have the list of all clients and then the pool of information would be larger

# ###
ESG_TABLE = "raw_esg"
ESG_SECTOR_COL = "Sector"            
ESG_REPORTING_COL = "ESG reporting"

# Each company has an "ESG reporting" answer: Yes, Partially or No.
# Rule:
#   - If 75% or more of the companies answer Yes  -> Low risk
#   - If 60% or more of the companies answer No   -> High risk
#   - All the rest     
ESG_VALID_ANSWERS = ["Yes", "Partially", "No"]
ESG_LOW_RISK_YES_PCT = 75            # >= 75% Yes -> Low risk
ESG_HIGH_RISK_NO_PCT = 60            # >= 60% No  -> High risk

# ###
# OTHER SETTINGS
# @
# Text values that mean "no data" in the files
MISSING_MARKERS = ['NaN', 'nan', 'na', '-', ' ', '']

# Open the charts in the browser. This is mainly use for easier checkups
# False = only save the HTML files
SHOW_IN_BROWSER = False


# ###
#  RISK SCORE
# 
# Number of years shown in the score tables (quarters of the last N years)
SCORE_YEARS = 5


# The 3 pillars 
PILLARS = {
    "W1": "Economic performance",
    "W2": "Financial health",
    "W3": "Operational risk",
}

# Indicators of the score
#   source     : key of the cleaned/filtered df (INDICATORS) or "esg"
#   pillar     : W1 / W2 / W3
#   weight     : points out of 100  (W1 = 40, W2 = 40, W3 = 20 -> total 100)
#   transform  : "yoy_growth" -> % change vs the same quarter one year before
#                "level"      -> the value as it is
#                "esg"        -> uses the ESG risk (Low/Medium/High)
#   green_above / green_inclusive / amber_from : traffic light thresholds
#       Green  if value >  green_above   (or >= if green_inclusive is True)
#       Amber  if value >= amber_from
#       Red    otherwise
SCORE_INDICATORS = {
    "gdp_growth": {
        "label": "Real GDP growth (YoY %)",
        "source": "gdp", "pillar": "W1", "weight": 20,
        "transform": "yoy_growth",
        "green_above": 3, "green_inclusive": False, "amber_from": 0,     # >3 | 0-3 | <0
    },
    "gos_growth": {
        "label": "GOS growth (YoY %)",
        "source": "gos", "pillar": "W1", "weight": 20,
        "transform": "yoy_growth",
        "green_above": 5, "green_inclusive": False, "amber_from": 0,     # >5 | 0-5 | <0
    },
    "equity_ratio": {
        "label": "Equity ratio (%)",
        "source": "equity_ratio", "pillar": "W2", "weight": 40,
        "transform": "level",
        "green_above": 40, "green_inclusive": True, "amber_from": 20,    # >=40 | 20-<40 | <20
    },
    "labour_productivity": {
        "label": "Labour productivity growth (YoY %)",
        "source": "labour_productivity", "pillar": "W3", "weight": 10,
        "transform": "yoy_growth",
        "green_above": 0, "green_inclusive": True, "amber_from": -3,     # >=0 | -3-<0 | <-3
    },
    "esg": {
        "label": "ESG reporting",
        "source": "esg", "pillar": "W3", "weight": 10,
        "transform": "esg",
    },
}

# ESG risk -> traffic light
ESG_RISK_TO_LIGHT = {"Low": "Green", "Medium": "Amber", "High": "Red"}

# Share of the indicator's weight earned by each light
LIGHT_POINTS = {"Green": 1.0, "Amber": 0.5, "Red": 0.0}

# Overall score -> traffic light (70-74.99 falls into Amber)
SCORE_GREEN_MIN = 75
SCORE_AMBER_MIN = 40

# Override: with this many Red indicators (or more) a sector can't be Green
OVERRIDE_REDS_BLOCK_GREEN = 2

# Annual data (e.g. equity ratio) is repeated in the quarters after it
# for at most this many days (so a 2024 value can still be used in 2025)
MAX_CARRY_FORWARD_DAYS = 730