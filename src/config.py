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
LOGO_FILE = DATA_FOLDER / "IndustryPulse_logo.png"           # logo shown in the dashboard

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
        "unit": "Ratio (not %)",
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
#   unit          : "%" (growth rates) or "ratio" (equity ratio: 0.40 is a ratio, NOT 40%)
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
        "unit": "%",
        "calculation": "yearly_growth",
        "green_from": 3, "green_includes_limit": False, "amber_from": 0,    # >3 | 0-3 | <0
    },
    "gos_growth": {
        "label": "GOS growth (YoY %)",
        "data_name": "gos",
        "pillar": "W1",
        "weight": 20,
        "unit": "%",
        "calculation": "yearly_growth",
        "green_from": 5, "green_includes_limit": False, "amber_from": 0,    # >5 | 0-5 | <0
    },
    "equity_ratio": {
        "label": "Equity ratio",
        "data_name": "equity_ratio",
        "pillar": "W2",
        "weight": 40,
        "unit": "ratio",
        "calculation": "value",
        # The file gives a ratio (e.g. 0.51), so the limits are ratios too
        "green_from": 0.40, "green_includes_limit": True, "amber_from": 0.20,   # >=0.40 | 0.20-<0.40 | <0.20
    },
    "labour_productivity": {
        "label": "Labour productivity growth (YoY %)",
        "data_name": "labour_productivity",
        "pillar": "W3",
        "weight": 10,
        "unit": "%",
        "calculation": "yearly_growth",
        "green_from": 0, "green_includes_limit": True, "amber_from": -3,    # >=0 | -3-<0 | <-3
    },
    "esg": {
        "label": "ESG reporting",
        "data_name": "esg",
        "pillar": "W3",
        "weight": 10,
        "unit": "% of companies",
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


######################################################################
# 8. DASHBOARD (PART 3)
######################################################################
# What each final traffic light suggests for the credit committee
# (a starting point for the discussion, not an automatic decision)
CREDIT_SIGNAL = {
    "Green": "Grow",
    "Amber": "Grow selectively",
    "Red": "Slow growth",
}

# AI analysis (only in the sector zoom of the dashboard), using OpenRouter
#   The key is NOT written here: it goes in the .env file of the project folder
#   (never upload .env to git, it is in .gitignore):
#       OPENROUTER_API_KEY=your-key
#   If the app is published on Streamlit Community Cloud, the key goes in st.secrets instead.
#   Model: cost-effective one recommended by the professor (group key with a USD 2 limit).
#   Price checked on openrouter.ai (Oct 2026): USD 0.0173 input / 0.80 output per million tokens,
#   about USD 0.0007 per analysis (prompt ~700 tokens + answer up to 800 tokens).
#   Other option from the professor: "inclusionai/ling-3.0-flash"
AI_BASE_URL = "https://openrouter.ai/api/v1"
AI_MODEL = "deepseek/deepseek-v4.1-flash"
AI_API_KEY_NAME = "OPENROUTER_API_KEY"

# Every AI run is written here (timestamp, view, status, answer). Never the API key
AI_LOG_FILE = LOG_FOLDER / "ai_runs.log"

# ESG risk profile of each sector (shown in the ESG tab of the dashboard).
# General tendencies of the sector in Singapore, NOT an assessment of each company.
# Every text comes from the official sources listed in "Sources" (checked October 2026).
# If you add a sector in TARGET_SECTORS, add its profile here too.
ESG_SECTOR_RISKS = {
    "Manufacturing": {
        "Physical": "More very hot days and longer dry spells are projected for Singapore (V3 climate "
                    "study), affecting workers, cooling and water supply. Water management is a key "
                    "disclosure topic for semiconductors (IFRS S2 industry guidance).",
        "Transition": "Facilities emitting 25,000 tCO2e or more a year pay the carbon tax: S$45/t in "
                      "2026-2027 and S$50-80/t expected by 2030. About 50 facilities pay it, in "
                      "manufacturing, power, waste and water. GHG emissions and energy management in "
                      "manufacturing are key topics (IFRS S2: Semiconductors, Chemicals).",
        "Governance": "SASB topics: employee health & safety, waste management, materials sourcing, "
                      "intellectual property protection & competitive behaviour.",
        "Sources": [
            ["NCCS - Carbon tax", "https://www.nccs.gov.sg/singapores-climate-action/mitigation-efforts/carbontax/"],
            ["NEA - Singapore climate projections (V3)", "https://www.nea.gov.sg/media/news/news/index/latest-climate-projections-for-singapore-show-intensifying-urban-heat-and-more-wet-dry-extremes"],
            ["IFRS - Industry-based guidance (Semiconductors)", "https://www.ifrs.org/content/dam/ifrs/project/climate-related-disclosures/industry/technology-and-communications/issb-exposure-draft-2022-2-b57-semiconductors.pdf"],
            ["IFRS - SASB Standards", "https://www.ifrs.org/issued-standards/sasb-standards/"],
        ],
    },
    "Real Estate": {
        "Physical": "Mean sea level could rise 0.23-1.15 m by 2100 and about 30% of the island is less "
                    "than 5 m above sea level (NCCS). Properties in flood-prone areas are part of the "
                    "'Climate Change Adaptation' topic (IFRS S2 Real Estate).",
        "Transition": "Green Building Masterplan '80-80-80 in 2030' (BCA): 80% of buildings green by "
                      "floor area, 80% of new developments Super Low Energy from 2030, 80% energy "
                      "efficiency improvement for best-in-class buildings (about 66% greened by Dec 2025). "
                      "Energy and water management are key topics (IFRS S2 Real Estate).",
        "Governance": "SASB topic: management of tenant sustainability impacts (e.g. green leases), "
                      "and the quality of the energy and water data reported.",
        "Sources": [
            ["NCCS - Impact of climate change in Singapore", "https://www.nccs.gov.sg/singapores-climate-action/national-circumstances/impact-of-climate-change-in-singapore/"],
            ["BCA - Singapore Green Building Masterplan", "https://www1.bca.gov.sg/sustainability/sgbmp/"],
            ["IFRS - Industry-based guidance (Real Estate)", "https://cdn.ifrs.org/content/dam/ifrs/project/climate-related-disclosures/industry/infrastructure/issb-exposure-draft-2022-2-b36-real-estate.pdf"],
        ],
    },
    "Transportation & Storage": {
        "Physical": "Sea-level rise and more extreme rainfall (NCCS, V3 study) threaten low-lying "
                    "port, airport and logistics infrastructure.",
        "Transition": "IMO 2023 Strategy: net-zero shipping emissions by or around 2050, at least -20% "
                      "by 2030 and -70% by 2040 (vs 2008), and at least 5% zero/near-zero fuels by 2030. "
                      "Singapore's sustainable aviation fuel levy applies to tickets sold from "
                      "1 Oct 2026 for flights departing from 1 Jan 2027 (air cargo one year later).",
        "Governance": "SASB topics: business ethics, accident & safety management, ecological impacts "
                      "(marine transport); supply-chain management of contracted carriers (logistics).",
        "Sources": [
            ["IMO - 2023 GHG Strategy", "https://www.imo.org/en/mediacentre/pressbriefings/pages/revised-ghg-reduction-strategy-for-global-shipping-adopted-.aspx"],
            ["CAAS - Sustainable aviation fuel levy", "https://www.caas.gov.sg/resources/media-and-publication/newsroom/caas-to-start-sustainable-aviation-fuel-levy-for-origin-destination-passengers-from-1-october-2026-for-flights-departing-from-1-january-2027/"],
            ["NCCS - Impact of climate change in Singapore", "https://www.nccs.gov.sg/singapores-climate-action/national-circumstances/impact-of-climate-change-in-singapore/"],
            ["IFRS - Industry-based guidance (Marine Transportation)", "https://www.ifrs.org/content/dam/ifrs/project/climate-related-disclosures/industry/transportation/issb-exposure-draft-2022-2-b66-marine-transportation.pdf"],
        ],
    },
    "Information & Communications": {
        "Physical": "Higher temperatures increase cooling needs and energy demand (NCCS), a direct "
                    "cost for data centres.",
        "Transition": "IMDA Green Data Centre Roadmap: at least 300 MW of additional capacity, linked to "
                      "energy efficiency and green energy; all data centres expected to reach a PUE of "
                      "1.3 or lower. Key topic: environmental footprint of hardware infrastructure "
                      "(IFRS S2 Software & IT Services).",
        "Governance": "Managing systemic risks from technology disruptions (service outages), plus "
                      "data security and data privacy (SASB).",
        "Sources": [
            ["IMDA - Green Data Centre Roadmap", "https://imda.gov.sg/how-we-can-help/green-dc-roadmap"],
            ["IFRS - Industry-based guidance (Software & IT Services)", "https://cdn.ifrs.org/content/dam/ifrs/project/climate-related-disclosures/industry/technology-and-communications/issb-exposure-draft-2022-2-b58-software-and-it-services.pdf"],
            ["NCCS - Impact of climate change in Singapore", "https://www.nccs.gov.sg/singapores-climate-action/national-circumstances/impact-of-climate-change-in-singapore/"],
        ],
    },
    "Utilities": {
        "Physical": "Droughts can affect the reliability of water supply and intense rainfall can "
                    "overwhelm drainage (NCCS). Network resiliency & impacts of climate change is a "
                    "key topic (IFRS S2 Water Utilities).",
        "Transition": "About 94% of electricity came from natural gas in 2024; Singapore plans to "
                      "import around 6 GW of low-carbon electricity by 2035 (about one-third of demand) "
                      "and reach 3 GWp of solar by 2030 (NCCS). Power plants pay the carbon tax. "
                      "Key topic: GHG emissions & energy resource planning (IFRS S2 Electric Utilities).",
        "Governance": "SASB topics: grid resiliency (including cybersecurity), workforce health & "
                      "safety, energy affordability.",
        "Sources": [
            ["NCCS - Power sector", "https://www.nccs.gov.sg/singapores-climate-action/mitigation-efforts/power/"],
            ["NCCS - Carbon tax", "https://www.nccs.gov.sg/singapores-climate-action/mitigation-efforts/carbontax/"],
            ["IFRS - Industry-based guidance (Electric Utilities)", "https://www.ifrs.org/content/dam/ifrs/project/climate-related-disclosures/industry/infrastructure/issb-exposure-draft-2022-2-b32-electric-utilities-and-power-generators.pdf"],
            ["IFRS - Industry-based guidance (Water Utilities)", "https://www.ifrs.org/content/dam/ifrs/project/climate-related-disclosures/industry/infrastructure/issb-exposure-draft-2022-2-b39-water-utilities-and-services.pdf"],
        ],
    },
}
