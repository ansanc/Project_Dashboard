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
# Note that this code uses the help of Copilot, own knowledge and what was learnt in class.

# %%
# Import the libraries we will use
import numpy as np # Managing of numbers
import pandas as pd # Dataframes 
import plotly.express as px #Plots

# Our own database file, this file will help us to read the db file.
from database import load_table, list_tables

# %%
# Check which tables are in the database
list_tables()

# %%
# Importing the data from the database
#ESG base
df_ESG = load_table("raw_esg")
# Real GDP Growth by Industry - Million dolars
df_GDP_Growth = load_table("raw_gdp_growth")
# Gross Operating Surplus Growth by Industry - Million dolars
df_GrossOperatingSurplusGrowth = load_table("raw_gross_operating_surplus")
# Labour Productivity Value added per Worker
df_LabourProductivity = load_table("raw_labour_productivity")
# Equity Ratio of Companies by Industry
df_EquityRatio = load_table("raw_equity_ratio")
# Bussiness expectations by Manufacturing Sector - Changes In Value Added Per Worker In Chained
df_Manufacturing_Business_Expectations = load_table("raw_business_exp_manufacturing")
# Bussiness expectations by Service Sector - Changes In Value Added Per Worker In Chained
df_Service_Business_Expectations = load_table("raw_business_exp_services")

# The sectors we will focus on are the following:
target_sectors = [
    'Manufacturing',
    'Real Estate',
    'Transportation & Storage',
    'Information & Communications',
    'Utilities'
]

### CLEANING THE DATA
# After importing the data files, some cleaning and reviews of the data to make sure we keep what we want for the score and dashboard

# %%
# Checkig the first rows of the different dataframes to see the structure and the columns of each dataframe
# We start with the ESG report file. This file was created by the team, therefore the cleaning of it is minimum in comparison to the others sources.
# This is a file that recolected from the top companies in Singapure from the sectors we are interested si they report ESG criteria or not
# In this file we are interested in two things:
# First, if a companies has a very complete ESG report, partially reporting, or does not report
# Second, a calculated ratio of the tendancy of the sector based in this companies
# There is one relevant decision done by the team that creates a big limitation: just 10 of the biggest companies of each sector were selected,
#  and therefore the tendancy is created in this case with the probable most mature companies of the sector that in some cases could be the "exceptions"
# But the idea would be that in a bank we would have the list of all clients and then the pool of information would be larger
df_ESG.head(10)
# df_ESG.info()

# %%
# ESG REPORTING COMPLIANCE BY SECTOR
# New df based on df_ESG showing the ratio of compliance of each sector in terms of ESG reporting.
# Each company has an "ESG reporting" answer: Yes, Partially or No.
# Rule:
#   - If 75% or more of the companies answer Yes  -> Low risk
#   - If 60% or more of the companies answer No   -> High risk
#   - All the rest                                -> Medium risk

# Names of the columns in df_ESG -> CHANGE the sector one to the real name you see in df_ESG.info()
esg_sector_col = "Sector"
esg_reporting_col = "ESG reporting"

# %%
# Check the different values in both columns before calculating
df_ESG[esg_sector_col].unique()
df_ESG[esg_reporting_col].value_counts(dropna=False)

# %%
# Clean the text: remove spaces and put it in phrase format,
# so "yes", "YES " and "Yes" all become "Yes"
df_ESG[esg_sector_col] = df_ESG[esg_sector_col].astype(str).str.strip().str.capitalize()
df_ESG[esg_reporting_col] = df_ESG[esg_reporting_col].astype(str).str.strip().str.capitalize()

# MISSING ANSWERS -> worst case
# Any company whose answer is empty or not Yes/Partially/No (blank, NaN, typo...)
# is treated as "No", so missing information pushes the sector towards High risk.
valid_answers = ["Yes", "Partially", "No"]
not_valid = ~df_ESG[esg_reporting_col].isin(valid_answers)
print(f"Companies with missing/invalid answer set to 'No': {not_valid.sum()}")
# %%
df_ESG.loc[not_valid, esg_reporting_col].value_counts(dropna=False)
# %%
df_ESG.loc[not_valid, esg_reporting_col] = "No"
# %%
# Percentage of Yes, Partially and No per sector
# (value_counts with normalize=True gives the proportion of each answer inside each sector)
esg_pct = (
    df_ESG.groupby(esg_sector_col)[esg_reporting_col]
    .value_counts(normalize=True)
    .unstack(fill_value=0) * 100
)
# Make sure the 3 columns always exist.
# The 0 here is NOT missing data: if no company in a sector answers "Yes", then 0% of them are Yes.
esg_pct = esg_pct.reindex(columns=valid_answers, fill_value=0)
esg_pct.head(10)

# %%
# Risk rule
def esg_risk(row):
    if row["Yes"] >= 75:
        return "Low"
    elif row["No"] >= 60:
        return "High"
    else:
        return "Medium"

# Final df with the 3 columns
df_ESG_risk = pd.DataFrame({
    "Sector": esg_pct.index,
    "ESG reporting compliance": esg_pct["Yes"].round(2).values,   # % of companies that answer Yes
    "risk_score": esg_pct.apply(esg_risk, axis=1).values,
})

# MISSING SECTORS 
# If one of our target sectors has no companies in the ESG file,
# we have no information about it, so we give it High risk.
missing_sectors = [s for s in target_sectors if s not in df_ESG_risk["Sector"].values]
print("Target sectors with no ESG data (set to High risk):", missing_sectors)

df_missing = pd.DataFrame({
    "Sector": missing_sectors,
    "ESG reporting compliance": np.nan,   # no data -> empty, not 0
    "risk_score": "High",
})
df_ESG_risk = pd.concat([df_ESG_risk, df_missing], ignore_index=True)



# %% 
# we check again the last df created
df_ESG_risk.head()


# %%
# GDP GROWTH BY SECTOR

#df_GDP_Growth.head(10)
#df_GDP_Growth.sample()
df_GDP_Growth.tail(40)

# %%
# This DataFrame needs to be modified to remove the first 7 rows and the rows after de 38 line
# In turn, the 8th row should be used as the column headers
# In here we name the coulmns with the values of the index 8 row
df_GDP_Growth.columns = df_GDP_Growth.iloc[8]
# %%
# Then lets erease the rows above the 9
df_GDP_Growth = df_GDP_Growth.iloc[9:].reset_index(drop=True)
# %%
# The first column has a name of Data Series, so we changed to Sectors to be align with all
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
# GROSS OPERATING SURPLUS
df_GrossOperatingSurplusGrowth.head(10)
# df_GrossOperatingSurplusGrowth.describe()
# df_GrossOperatingSurplusGrowth.info()
#df_GrossOperatingSurplusGrowth.tail(30)

# %%
# FIXED: before it was ".values[0] = 'Sectors'", which overwrote the first data row.
# Same structure as GDP: row 8 has the headers, data starts at row 9
# (check in the head(10) above that row 8 is the "Data Series" row)
df_GrossOperatingSurplusGrowth.columns = df_GrossOperatingSurplusGrowth.iloc[8]
df_GrossOperatingSurplusGrowth = df_GrossOperatingSurplusGrowth.iloc[9:].reset_index(drop=True)
# Lets rename the sectors column
df_GrossOperatingSurplusGrowth.columns.values[0] = "Sectors"


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
df_GrossOperatingSurplusGrowth_filtered = df_GrossOperatingSurplusGrowth[df_GrossOperatingSurplusGrowth['Sectors'].isin(target_sectors)].reset_index(drop=True)

# %%
# LABOUR PRODUCTIVITY
# Lets drop the first rows and set the correct name of columns
df_LabourProductivity.columns = df_LabourProductivity.iloc[8]
df_LabourProductivity = df_LabourProductivity.iloc[9:].reset_index(drop=True)
# Lets rename the sectors column
df_LabourProductivity.columns.values[0] = "Sectors"

# %%
# Check the general info of the df
df_LabourProductivity.info()
# Modifying the NaN or empty values to np format
df_LabourProductivity = df_LabourProductivity.replace(['NaN', 'nan', '-', ' '], np.nan)
# Modifying the values of the quarters to float format
for col in df_LabourProductivity.columns[1:]:
    df_LabourProductivity[col] = pd.to_numeric(df_LabourProductivity[col], errors='coerce').astype(float)

# %%
# Checking the min, max and other stats of the df
df_LabourProductivity.describe()

# %%
# Cleaning the possible spaces on the Sectors column
df_LabourProductivity['Sectors'] = df_LabourProductivity['Sectors'].astype(str).str.strip()
# Filtering the df to sectors we are interested
df_LabourProductivity_filtered = df_LabourProductivity[
    df_LabourProductivity['Sectors'].isin(target_sectors)
].reset_index(drop=True)


# %%
# EQUITY RATIO

# Check the general info of the df
#df_EquityRatio.info()
# df_EquityRatio.head(15)
df_EquityRatio.describe()
 # %%
# Modifying the NaN or empty values to np format
df_EquityRatio = df_EquityRatio.replace(['NaN', 'nan', '-', ' '], np.nan)
# Modifying the values of the quarters to float format
for col in df_EquityRatio.columns[1:]:
    df_EquityRatio[col] = pd.to_numeric(df_EquityRatio[col], errors='coerce').astype(float)


# %%
# Cleaning the possible spaces on the Sectors column
first_col_equity = df_EquityRatio.columns[0]
df_EquityRatio[first_col_equity] = df_EquityRatio[first_col_equity].astype(str).str.strip()
# Filtering the df to sectors we are interested
df_EquityRatio_filtered = df_EquityRatio[
    df_EquityRatio[first_col_equity].isin(target_sectors)
].reset_index(drop=True)


# %%
# MANUFACTURING BUSINESS EXPECTATIONS
#df_Manufacturing_Business_Expectations.head(5)

#df_Manufacturing_Business_Expectations.tail(35)
df_Manufacturing_Business_Expectations.info()

#df_Manufacturing_Business_Expectations.describe()   
# %%
# Lets drop the first rows and set the correct name of columns
df_Manufacturing_Business_Expectations.columns = df_Manufacturing_Business_Expectations.iloc[8]
df_Manufacturing_Business_Expectations = df_Manufacturing_Business_Expectations.iloc[9:].reset_index(drop=True)
# Lets rename the sectors column
df_Manufacturing_Business_Expectations.columns.values[0] = "Sectors"

# %%
# Modifying the NaN or empty values to np format
df_Manufacturing_Business_Expectations = df_Manufacturing_Business_Expectations.replace(['NaN', 'nan', '-', ' '], np.nan)
# Modifying the values of the quarters to float format
for col in df_Manufacturing_Business_Expectations.columns[1:]:
    df_Manufacturing_Business_Expectations[col] = pd.to_numeric(df_Manufacturing_Business_Expectations[col], errors='coerce').astype(float)

# %%
# Checking the min, max and other stats of the df
df_Manufacturing_Business_Expectations.describe()

# %%
# Cleaning the possible spaces on the Sectors column
df_Manufacturing_Business_Expectations['Sectors'] = df_Manufacturing_Business_Expectations['Sectors'].astype(str).str.strip()
# Filtering the df to sectors we are interested
df_Manufacturing_Business_Expectations_filtered = df_Manufacturing_Business_Expectations[
    df_Manufacturing_Business_Expectations['Sectors'].isin(target_sectors)
].reset_index(drop=True)


# %%
# SERVICE BUSINESS EXPECTATIONS
# df_Service_Business_Expectations.head(10)
# df_Service_Business_Expectations.tail(10)
df_Service_Business_Expectations.info()
# %%
# Lets drop the first rows and set the correct name of columns
df_Service_Business_Expectations.columns = df_Service_Business_Expectations.iloc[8]
df_Service_Business_Expectations = df_Service_Business_Expectations.iloc[9:].reset_index(drop=True)
# Lets rename the sectors column
df_Service_Business_Expectations.columns.values[0] = "Sectors"

# %%
# Modifying the NaN or empty values to np format
df_Service_Business_Expectations = df_Service_Business_Expectations.replace(['NaN', 'nan', '-', ' '], np.nan)
# Modifying the values of the quarters to float format
for col in df_Service_Business_Expectations.columns[1:]:
    df_Service_Business_Expectations[col] = pd.to_numeric(df_Service_Business_Expectations[col], errors='coerce').astype(float)

# %%
# Checking the min, max and other stats of the df
df_Service_Business_Expectations.describe()

# %%
# Cleaning the possible spaces on the Sectors column
df_Service_Business_Expectations['Sectors'] = df_Service_Business_Expectations['Sectors'].astype(str).str.strip()
# Filtering the df to sectors we are interested
df_Service_Business_Expectations_filtered = df_Service_Business_Expectations[
    df_Service_Business_Expectations['Sectors'].isin(target_sectors)
].reset_index(drop=True)
# %%
df_Service_Business_Expectations_filtered.head(5)

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
# Fist we are going to filter the data to the last five years
# List of cleaned DataFrames to filter for the last 5 years
dataframes = {
    'df_GDP_Growth': df_GDP_Growth_filtered,
    'df_GrossOperatingSurplusGrowth': df_GrossOperatingSurplusGrowth_filtered,
    'df_LabourProductivity': df_LabourProductivity_filtered,
    'df_EquityRatio': df_EquityRatio_filtered,
    'df_Manufacturing_Business_Expectations': df_Manufacturing_Business_Expectations_filtered,
    'df_Service_Business_Expectations': df_Service_Business_Expectations_filtered
}

# Dictionary to store the 5-year filtered DataFrames
filtered_5yr_dfs = {}

# Iterate over each DataFrame to apply the 5-year window filter
for df_name, df in dataframes.items():
    # Identify sector column (handles both 'Sectors' and original first column name)
    sector_col = df.columns[0]

    # Extract quarterly data columns excluding the sector label column
    quarter_cols = [col for col in df.columns if col != sector_col]

    # Extract numeric year values from quarterly column names
    years = [int(col.split()[0]) for col in quarter_cols if col.split()[0].isdigit()]

    # Calculate the 5-year cutoff threshold based on the maximum year present
    max_year = max(years)
    cutoff_year_5yr = max_year - 4  # Includes max_year and the previous 4 years (5 total)

    # Select quarterly columns falling within the last 5 years
    selected_5yr_cols = [
        col for col in quarter_cols
        if int(col.split()[0]) >= cutoff_year_5yr
    ]

    # Filter DataFrame to keep sector column and the 5-year quarterly columns
    filtered_5yr_dfs[f"{df_name}_5yr"] = df[[sector_col] + selected_5yr_cols].copy()

# Assign filtered DataFrames to explicit variable names
df_GDP_Growth_5yr = filtered_5yr_dfs['df_GDP_Growth_5yr']
df_GrossOperatingSurplusGrowth_5yr = filtered_5yr_dfs['df_GrossOperatingSurplusGrowth_5yr']
df_LabourProductivity_5yr = filtered_5yr_dfs['df_LabourProductivity_5yr']
df_EquityRatio_5yr = filtered_5yr_dfs['df_EquityRatio_5yr']
df_Manufacturing_Expectations_5yr = filtered_5yr_dfs['df_Manufacturing_Business_Expectations_5yr']
df_Service_Expectations_5yr = filtered_5yr_dfs['df_Service_Business_Expectations_5yr']