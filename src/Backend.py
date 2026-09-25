#%%
## Purpose of this file:
# The system will consolidate multiple indicators into a centralized database
# These indicators will then be processed into an overall industry assessment using a simple traffic-light rating system: Green, Amber, and Red.
# This will allow users to quickly identify industries showing signs of strength, deterioration, or elevated risk.  
# As an initial scope, we will focus on four key sectors to keep the initial phase manageable and allow the system to be developed and tested effectively. The framework is designed to be scalable, so additional sectors can be incorporated in future phases as the system is further developed.
# The initial sectors are: Manufacturing , Real Estate , Transportation and Storage ,Information and Communication 
# For a further analysis we be able to create the dashboard and the traffic-light system, this code we will also create a score that will fed the final traffic-light system. The score will be calculated based on the indicators and the weights assigned to each indicator. The final score will be used to determine the traffic-light rating for each industry.
# After this, we will create a dashboard that will allow users to visualize the data and the traffic-light ratings for each industry. 
# The dashboard will be interactive and will allow users to filter the data by sector, indicator, and time period. The dashboard will also provide a summary of the overall industry assessment and the traffic-light ratings for each industry.
# ###
# Creation day: 2024-06-10
# Moficiation day: 2024-06-10
# Created by: @ansanc
## %% 
#Import libraries
import pandas as pd
# import requests # for working with APIs
import plotly.express as px
import plotly.graph_objects as go
# %%
# This block of code intends to import all the necessary data files for the dashboard.
# In this case, we are importing the data files from the "data" folder located in the root directory of the project.
# Later on, this data will be used to create a database for the dashboard.

# Import base related to esg reports

#PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
#ESG base
df_ESG = pd.read_excel(DATA_DIR / "ESGReports.xlsx")
# Real GDP Growth by Industry - Million dolars
df1 = pd.read_csv(DATA_DIR / "RealGDPGrowthByIndustry.csv")
# Gross Operating Surplus Growth by Industry - Million dolars
df2 = pd.read_csv(DATA_DIR / "GrossOperatingSurplusGrowthByIndustry.csv")
# Labour Productivity Value added per Worker
df3 = pd.read_csv(DATA_DIR / "LabourProductivityValueAddedPerWorker.csv")
# Equity Ratio of Companies by Industry
df4 = pd.read_csv(DATA_DIR / "EquityRatioOfCompaniesByIndustry.csv")
# Wage Growth by Industry - Changes In Value Added Per Worker In Chained
df5 = pd.read_csv(DATA_DIR / "WageGrowthByIndustry.csv")
# Bussiness expectations by Manufacturing Sector - Changes In Value Added Per Worker In Chained
df6 = pd.read_csv(DATA_DIR / "BusinessExpectationsOfTheManufacturingSector.csv")
# Bussiness expectations by Service Sector - Changes In Value Added Per Worker In Chained
df7 = pd.read_csv(DATA_DIR / "BusinessExpectationsOfTheServiceSector.csv")

# After importing the data files, some cleaning and reviews of the data to make sure we keep what we want for the score and dashboard
# %%
## Cleaning of the datafiles
# ereasing extra rows and columns, as we want to keep only the relevant data for the analysis and dashboard.

# Filtering the data just for the las 10 years, as we want to focus on the most recent data for the analysis and dashboard.

# Filtering to the sectors we are interested in, as we want to focus on the sectors that are relevant for the analysis and dashboard.
# Sectors: Manufacturing , Real Estate , Transportation and Storage ,Information and Communication

# %%
# creating ranges for each dataframe, to be able to create the score and the traffic-light system based on the ranges of each indicator.
# Red 3 Yellow 2 Green 1
# 
