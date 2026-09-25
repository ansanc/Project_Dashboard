#
## Purpose of this file:
# The system will consolidate multiple indicators into a centralized database
# These indicators will then be processed into an overall industry assessment using a simple traffic-light rating system: Green, Amber, and Red.
# This will allow users to quickly identify industries showing signs of strength, deterioration, or elevated risk.  
# As an initial scope, we will focus on four key sectors to keep the initial phase manageable and allow the system to be developed and tested effectively. The framework is designed to be scalable, so additional sectors can be incorporated in future phases as the system is further developed.
# The initial sectors are: Manufacturing , Real Estate , Transportation and Storage ,Information and Communication 
# For a further analysis we be able to create the dashboard and the traffic-light system, this code we will also create a score that will fed the final traffic-light system. The score will be calculated based on the indicators and the weights assigned to each indicator. The final score will be used to determine the traffic-light rating for each industry.
# After this, we will create a dashboard that will allow users to visualize the data and the traffic-light ratings for each industry. 
# The dashboard will be interactive and will allow users to filter the data by sector, indicator, and time period. The dashboard will also provide a summary of the overall industry assessment and the traffic-light ratings for each industry.

## %% 
#Import libraries
import pandas as pd
import requests
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
df_asg = pd.read_excel(DATA_DIR / "ESGReports.xlsx")
# Real GDP Growth by Industry
df1
# Gross Operating Surplus Growth by Industry
df2
# Labour Productivity Value added per Worker
df3
# Equity Ratio of Companies by Industry
df4
# Wage Growth by Industry
df5
# Workplace Injury Incident by Industry

# After importing the data files, some cleaning and reviews of the data to make sure we keep what we want for the score and dashboard
