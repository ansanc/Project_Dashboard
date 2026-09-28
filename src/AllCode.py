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
# Creation day: 2026-09-15
# Moficiation day: 2026-09-28
# Created by: @ansanc
## %% 
#Import libraries
import numpy as np # Numeric
import pandas as pd # Dataframes
# import requests # for working with APIs
import plotly.express as px #Graphs
import plotly.graph_objects as go #Graphs
from pathlib import Path # Rute for our files
import openpyxl # Managing excel files

# %% 
# Ruta de los archivos de datos
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# %% 
# Importing the data files
#ESG base
df_ESG = pd.read_excel(DATA_DIR / "ESGReports.xlsx")
# Real GDP Growth by Industry - Million dolars
df_GDP_Growth = pd.read_csv(DATA_DIR / "RealGDPGrowthByIndustry.csv")
# Gross Operating Surplus Growth by Industry - Million dolars
df_GrossOperatingSurplusGrowth = pd.read_csv(DATA_DIR / "GrossOperatingSurplusGrowthByIndustry.csv")
# Labour Productivity Value added per Worker
df_LabourProductivity = pd.read_csv(DATA_DIR / "LabourProductivityValueAddedPerWorker.csv")
# Equity Ratio of Companies by Industry
df_EquityRatio = pd.read_csv(DATA_DIR / "EquityRatioOfCompaniesByIndustry.csv")
# Bussiness expectations by Manufacturing Sector - Changes In Value Added Per Worker In Chained
df_Manufacturing_Business_Expectations = pd.read_csv(DATA_DIR / "BusinessExpectationsOfTheManufacturingSector.csv")
# Bussiness expectations by Service Sector - Changes In Value Added Per Worker In Chained
df_Service_Business_Expectations = pd.read_csv(DATA_DIR / "BusinessExpectationsOfTheServiceSector.csv")

# The sectors we will focus on are the following:
target_sectors = [
    'Manufacturing',
    'Real Estate',
    'Transportation & Storage',
    'Information & Communications',
    'Utilities'
]
# After importing the data files, some cleaning and reviews of the data to make sure we keep what we want for the score and dashboard

# %%
# Checkig the first rows of the different dataframes to see the structure and the columns of each dataframe
df_ESG.head(10)

df_ESG.info()

# %%
#df_GDP_Growth.head(10)
# This DataFrame needs to be modified to remove the first 7 rows
# In turn, the 8th row should be used as the column headers
# In here we name the coulmns with the values of the index 8 row
df_GDP_Growth.columns = df_GDP_Growth.iloc[8]
# %%
# Then lets erease the rows above the 9 
df_GDP_Growth = df_GDP_Growth.iloc[9:].reset_index(drop=True)
# %%
# The first column has a name of Data Series, I would prefer it to be called Sectors
# Therefore we rename the first column to Sectors
df_GDP_Growth.columns.values[0] = "Sectors"


# %% 
# Lets check the general behavour of the df
df_GDP_Growth.info()
# As we saw in our last function all values seems to be register as a str
# Therefore we need to modify all the values different from the first column
df_GDP_Growth = df_GDP_Growth.replace(['NaN', 'nan', '-', ' '], np.nan)

for col in df_GDP_Growth.columns[1:]:
    df_GDP_Growth[col] = pd.to_numeric(df_GDP_Growth[col], errors='coerce').astype(float)

df_GDP_Growth.describe()
# %%
# We also need to erease spaces on our str sectors to avoid any mismatch due to spaces from our list
df_GDP_Growth['Sectors'] = df_GDP_Growth['Sectors'].astype(str).str.strip()
df_GDP_Growth.head(5)
# %%
# Lets filter the df to the sectors we are interested in
# Filter original DataFrame
df_GDP_Growth_filtered = df_GDP_Growth[df_GDP_Growth['Sectors'].isin(target_sectors)].reset_index(drop=True)

df_GDP_Growth_filtered.head(10)
# %% 
# I consider something also would be to see the concentration of each sector
# Extract the baseline row containing Total GDP to serve as the 100% denominator
total_gdp_row = df_GDP_Growth[
    df_GDP_Growth['Sectors'].str.strip() == 'GDP In Chained (2015) Dollars'
]

# Identify all quarterly data columns excluding the sector label column
quarter_cols = [col for col in df_GDP_Growth.columns if col != 'Sectors']

# Create a copy of the original dataset to calculate percentage shares
df_GDP_Percentage = df_GDP_Growth.copy()

# Compute percentage share per quarter: (Sector Value / Total GDP Value) * 100
# We use GDP In Chained (2015) Dollars as mantion on the original database that this is the official value
for col in quarter_cols:
    total_val = pd.to_numeric(total_gdp_row[col].values[0], errors='coerce')
    df_GDP_Percentage[col] = pd.to_numeric(df_GDP_Percentage[col], errors='coerce')
    df_GDP_Percentage[col] = (df_GDP_Percentage[col] / total_val) * 100

# Filter the percentage DataFrame to keep only target sectors
df_GDP_Pct_filtered = df_GDP_Percentage[
    df_GDP_Percentage['Sectors'].isin(df_GDP_Growth_filtered['Sectors'])
].reset_index(drop=True)

# Format numerical results rounded to two decimal places
df_GDP_Pct_filtered[quarter_cols] = df_GDP_Pct_filtered[quarter_cols].round(2)

# Display calculated percentage shares DataFrame
df_GDP_Pct_filtered.head(5)


# %%
df_GrossOperatingSurplusGrowth.head(10)

df_GrossOperatingSurplusGrowth.values[0] = "Sectors"


# %% 
# Lets check the general behavour of the df
df_GrossOperatingSurplusGrowth.info()
# As we saw in our last function all values seems to be register as a str
# Therefore we need to modify all the values different from the first column

df_GrossOperatingSurplusGrowth = df_GrossOperatingSurplusGrowth.replace(['NaN', 'nan', '-', ' '], np.nan)
for col in df_GrossOperatingSurplusGrowth.columns[1:]:
    df_GrossOperatingSurplusGrowth[col] = pd.to_numeric(df_GrossOperatingSurplusGrowth[col], errors='coerce').astype(float)

df_GrossOperatingSurplusGrowth.describe()
# %%
# We also need to erease spaces on our str sectors to avoid any mismatch due to spaces from our list
df_GrossOperatingSurplusGrowth['Sectors'] = df_GrossOperatingSurplusGrowth['Sectors'].astype(str).str.strip()
df_GrossOperatingSurplusGrowth.head(5)
# %%
# Lets filter the df to the sectors we are interested in
# Filter original DataFrame
df_GDP_Growth_filtered = df_GDP_Growth[df_GDP_Growth['Sectors'].isin(target_sectors)].reset_index(drop=True)

# %%
df_LabourProductivity.head(5)
# %%
df_EquityRatio.head(5)
# %%
df_Manufacturing_Business_Expectations.head(5)
# %%
df_Service_Business_Expectations.head(5)

# %%
####### PLOTS 
# Now lets make some plots to

# Lets Transform quarterly columns into a single categorical column ('Quarter')
# and values into 'GDP_Value' for Plotly compatibility.
df_melted_GDP_Growth = df_GDP_Growth_filtered.melt(
    id_vars=['Sectors'], 
    var_name='Quarter', 
    value_name='GDP_Value'
)
# Convert values to float and replace invalid string entries with NaN
df_melted_GDP_Growth['GDP_Value'] = pd.to_numeric(
    df_melted_GDP_Growth['GDP_Value'].replace(['NaN', 'nan', 'null', '-', ''], np.nan),
    errors='coerce'
)

# Sort chronologically by Quarter and Sector
df_melted_GDP_Growth = df_melted_GDP_Growth.sort_values(by=['Quarter', 'Sectors']).reset_index(drop=True)

# Line Chart: Time Series Trends
fig_line = px.line(
    df_melted_GDP_Growth, 
    x='Quarter', 
    y='GDP_Value', 
    color='Sectors',
    markers=True,
    title="Quarterly GDP Growth Trend by Industry Sector (Chained 2015 Dollars)",
    labels={
        'Quarter': 'Quarter Period',
        'GDP_Value': 'GDP (In Chained 2015 Dollars)',
        'Sectors': 'Industry Sector'
    }
)

fig_line.update_layout(
    template="plotly_white",
    hovermode="x unified",
    xaxis_title="Quarter Period",
    yaxis_title="GDP Value (Chained 2015 USD)",
    legend_title="Industry Sectors"
)

# Grouped Bar Chart: Sector Comparisons
fig_bar = px.bar(
    df_melted_GDP_Growth, 
    x='Quarter', 
    y='GDP_Value', 
    color='Sectors', 
    barmode='group',
    title="Quarterly GDP Sector Breakdown & Size Comparison",
    labels={
        'Quarter': 'Quarter Period',
        'GDP_Value': 'GDP (In Chained 2015 Dollars)',
        'Sectors': 'Industry Sector'
    }
)

fig_bar.update_layout(
    template="plotly_white",
    xaxis_title="Quarter Period",
    yaxis_title="GDP Value (Chained 2015 USD)",
    legend_title="Industry Sectors"
)

# Uses CDN for lightweight file sizes (~3MB instead of ~14MB each)
fig_line.write_html("gdp_trend_line_chart.html", include_plotlyjs='cdn')
fig_bar.write_html("gdp_sector_bar_chart.html", include_plotlyjs='cdn')

print("HTML files generated successfully: 'gdp_trend_line_chart.html' and 'gdp_sector_bar_chart.html'")

# Forces Plotly to launch your system's default browser window to view interactive outputs
fig_line.show(renderer="browser")
fig_bar.show(renderer="browser")

# %%
# Lets check in a graph the proportion of the sectors in compare to the total including the other sectors

# Identify the latest available quarter column in the percentage DataFrame
latest_quarter = df_GDP_Pct_filtered.columns[1]

# Extract percentage data for the latest quarter
pie_full_data = df_GDP_Pct_filtered[['Sectors', latest_quarter]].copy()
pie_full_data.columns = ['Sector', 'Percentage']

# Calculate total percentage contribution of selected sectors
sum_selected_pct = pie_full_data['Percentage'].sum()

# Compute remaining share for 'Other Sectors' to reach 100%
other_sectors_pct = max(0.0, 100.0 - sum_selected_pct)

# Append 'Other Sectors' row to complete the 100% total economy pie
other_row = pd.DataFrame([{'Sector': 'Other Sectors', 'Percentage': other_sectors_pct}])
pie_full_data = pd.concat([pie_full_data, other_row], ignore_index=True)

# Generate Chart 1: Donut chart showing overall economic concentration
fig_donut_full = px.pie(
    pie_full_data, 
    names='Sector', 
    values='Percentage',
    title=f"Total GDP Concentration Share ({latest_quarter}) — Selected vs. Other Sectors",
    hole=0.4,
    labels={'Percentage': 'GDP Share (%)', 'Sector': 'Industry Sector'}
)

fig_donut_full.update_traces(
    textposition='inside', 
    textinfo='percent+label',
    hovertemplate="<b>%{label}</b><br>Share of Total GDP: %{value:.2f}%<extra></extra>"
)

fig_donut_full.update_layout(
    template="plotly_white",
    legend_title="Sectors Breakdown"
)

# Export Chart 1 to HTML and open in browser
fig_donut_full.write_html("gdp_total_concentration_latest_q.html", include_plotlyjs='cdn')
fig_donut_full.show(renderer="browser")


# %%
# With this plot we will center just in the sectors we are interested in
# Extract the latest available quarter column

# Prepare dataset containing only the selected sectors for the latest quarter
pie_selected_data = df_GDP_Pct_filtered[['Sectors', latest_quarter]].copy()
pie_selected_data.columns = ['Sector', 'Percentage']

# Generate Chart 2: Focused donut chart with cumulative share in title
fig_donut_selected = px.pie(
    pie_selected_data, 
    names='Sector', 
    values='Percentage',
    title=f"Selected Sectors Breakdown ({latest_quarter}) — Representing {sum_selected_pct:.2f}% of Total GDP",
    hole=0.4,
    labels={'Percentage': 'GDP Share (%)', 'Sector': 'Industry Sector'}
)

fig_donut_selected.update_traces(
    textposition='inside', 
    textinfo='percent+label',
    hovertemplate="<b>%{label}</b><br>Share of Total GDP: %{value:.2f}%<extra></extra>"
)

fig_donut_selected.update_layout(
    template="plotly_white",
    legend_title="Selected Sectors"
)

# Export Chart 2 to HTML and open in browser
fig_donut_selected.write_html("gdp_selected_sectors_latest_q.html", include_plotlyjs='cdn')
fig_donut_selected.show(renderer="browser")


# %%
# creating ranges for each dataframe, to be able to create the score and the traffic-light system based on the ranges of each indicator.
# Red 3 Yellow 2 Green 1
# 





#if __name__ == "__main__":
#    main()

# %%
