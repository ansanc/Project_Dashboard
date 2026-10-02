# Industry Risk Dashboard — Data & Scoring Engine

Early-warning system that consolidates several economic and ESG indicators into a central database and turns them into a **traffic-light rating (Green / Amber / Red)** per industry. It lets users quickly see which industries show signs of strength, deterioration or elevated risk.

This repository covers:

- **Part 1 – Data:** loading, cleaning, exploration and charts.
- **Part 2 – Risk score:** indicator traffic lights, pillar scores and the overall score.

The interactive dashboard (Plotly Dash) is the next phase and is not included yet.

---

## Scope

Initial phase, kept small so the system can be built and tested properly. The framework is scalable: new sectors and indicators are added from `config.py` only.

| Sectors covered |
|---|
| Manufacturing |
| Real Estate |
| Transportation & Storage |
| Information & Communications |
| Utilities |

---

## Project structure

```
main_folder/
├── data/                         <- source files + the SQLite database
│   ├── RealGDPGrowthByIndustry.csv
│   ├── GrossOperatingSurplusGrowthByIndustry.csv
│   ├── LabourProductivityValueAddedPerWorker.csv
│   ├── EquityRatioOfCompaniesByIndustry.csv
│   ├── BusinessExpectationsOfTheManufacturingSector.csv
│   ├── BusinessExpectationsOfTheServiceSector.csv
│   ├── ESGReports.xlsx
│   └── Database_RiskDashboard.db  <- created by database.py
├── plots/                        <- HTML charts (created automatically)
└── code_folder/
    ├── config.py                 <- all the settings
    ├── database.py               <- creates and reads the database
    ├── exploration.py            <- cleaning, merging, ESG, data checks
    ├── plots.py                  <- charts
    ├── scoring.py                <- risk score and traffic lights
    └── main.py                   <- runs everything, cell by cell
```

| File | What it does |
|---|---|
| `config.py` | Folders, data files, sectors, colors, indicators, ESG rules, score weights and limits. **Everything you may want to change is here.** |
| `database.py` | Reads every source file and saves it as a table in `Database_RiskDashboard.db`. Also loads the tables back into pandas. |
| `exploration.py` | Cleans the SingStat files, merges files that measure the same thing, calculates the share of total GDP, builds the ESG risk and runs the data checks. |
| `plots.py` | Line trends, grouped bars, donuts (share of total) and bars vs. total. Saves everything as HTML in `plots/`. |
| `scoring.py` | Yearly growth, traffic lights, pillar scores (W1, W2, W3), overall score, override rules and the report per sector. |
| `main.py` | Runs the whole process in order. Use it cell by cell (`# %%`) in VS Code. |

---

## How to run

**Requirements:** Python 3.10+, `pandas`, `numpy`, `plotly`, `openpyxl` (to read the Excel file).

```bash
pip install pandas numpy plotly openpyxl
```

1. **Create the database.** Run this only the first time, or when you get new or updated files.
   ```bash
   cd code_folder
   python database.py
   ```
2. **Run the analysis.** Open `main.py` in VS Code and run it cell by cell, or run the whole file:
   ```bash
   python main.py
   ```

> Tip: if you edit another `.py` file while working in the VS Code interactive window, run `%load_ext autoreload` and `%autoreload 2` once. Your changes will then be picked up without restarting.

> Set `SHOW_CHARTS_IN_BROWSER = False` in `config.py` if you don't want the charts to open in the browser. They are always saved in `plots/`.

---

## Data sources

| Name in code | File | Frequency | Used for |
|---|---|---|---|
| `gdp` | Real GDP by Industry (chained 2015 dollars) | Quarterly | Charts, GDP share, **score (W1)** |
| `gos` | Gross Operating Surplus by Industry | Quarterly | Charts, **score (W1)** |
| `labour_productivity` | Labour Productivity – value added per worker | Quarterly | Charts, **score (W3)** |
| `equity_ratio` | Equity Ratio of Companies by Industry | Annual | Charts, **score (W2)** |
| `business_expectations` | Business Expectations – Manufacturing + Services (merged) | Quarterly | Charts and checks (not in the score yet) |
| `esg` | ESG Reports (built by the team) | One snapshot | **score (W3)** |

### Cleaning of the SingStat files

All the SingStat files go through the same steps, **before** filtering by sector (`clean_indicator_file()` in `exploration.py`):

1. **Header:** row 8 has the column names, and the data starts in row 9.
2. **Rename:** the first column becomes `Sectors`.
3. **Footnotes:** everything from the `Definitions and Footnotes` row down is removed, together with empty rows.
4. **Numbers:** values become numbers, and texts like `na` or `-` become empty (NaN).
5. **Sector names:** extra spaces are removed so they match the target sectors.
6. **Filter:** only the target sectors are kept.

The Equity Ratio file already has the right header, so step 1 is skipped. The two Business Expectations files measure the same thing for different sectors, so after cleaning they are **merged into one df** (`business_expectations`).

### ESG file

This file was created by the team, so it needs much less cleaning than the other sources.

It was collected from the top companies in Singapore in the sectors we are interested in, and it records whether each company reports ESG criteria or not. We use it for two things:

1. **The level of reporting of each company:** a complete ESG report (`Yes`), partial reporting (`Partially`), or no reporting (`No`).
2. **The tendency of each sector:** a ratio calculated from those companies.

**Rule for the sector tendency:**

| Condition | ESG risk |
|---|---|
| 75% or more of the companies answer **Yes** | Low |
| 60% or more of the companies answer **No** | High |
| Any other case | Medium |

- Missing or invalid answers count as **No** (worst case).
- A target sector with no companies in the file gets **High** risk.
- `ESG reporting compliance` = % of companies in the sector that answer **Yes**.

> **Important limitation:** the team decided to select only the **10 biggest companies of each sector**. The sector tendency is therefore based on what are probably the most mature companies of the sector, which in some cases could be the "exceptions" rather than the norm.
>
> The idea is that in a bank we would have the list of **all clients**, so the pool of information would be much larger and the tendency more representative.

---

## Part 1 – Outputs

| Variable in `main.py` | Content |
|---|---|
| `raw_data[name]` | Tables as they come from the database |
| `clean_data[name]` | Cleaned dfs, with all the rows (including totals) |
| `filtered_data[name]` | Only the target sectors |
| `df_gdp_share_filtered` | % of total GDP per sector and quarter |
| `df_esg_risk` | Sector, ESG reporting compliance, risk_score |
| `data_quality_checks[name]` | Summary per sector (missing values, min, max, latest…) and unusual jumps |
| `filtered_data_5_years[name]` | Last 5 years only |

**Charts** (saved in `plots/`):

1. Line trend by sector (full history).
2. Grouped bars by sector (last 20 periods).
3. Donut charts: selected sectors vs. "Other Sectors", and a zoom on the selected sectors. These are only for amounts that add up to a total (GDP, GOS).
4. Bars vs. total for ratios and per-worker values (a donut would make no sense for them).

---

## Part 2 – Risk score

### Pillars and indicators

The overall score is the weighted sum of three pillars. Each pillar is also a traffic light of its own.

| Pillar | Weight | Indicator | Weight | 🟢 Green | 🟠 Amber | 🔴 Red |
|---|---|---|---|---|---|---|
| **W1** Economic performance | 40 | Real GDP growth (YoY) | 20 | > 3% | 0% to 3% | < 0% |
| | | GOS growth (YoY) | 20 | > 5% | 0% to 5% | < 0% |
| **W2** Financial health | 40 | Equity ratio | 40 | ≥ 40% | 20% to < 40% | < 20% |
| **W3** Workforce / operational | 20 | Labour productivity growth (YoY) | 10 | ≥ 0% | −3% to < 0% | < −3% |
| | | ESG reporting | 10 | Low risk | Medium risk | High risk |

**Points per indicator:** Green = 100% of its weight, Amber = 50%, Red = 0%.

### Overall rating

| Score | Rating |
|---|---|
| 75.00 – 100 | 🟢 Green |
| 40.00 – 74.99 | 🟠 Amber (70.00 – 74.99 is provisionally Amber) |
| 0 – 39.99 | 🔴 Red |

### Override rules

1. **Green override:** a sector with **2 or more Red indicators** can't be Green, even if its score is ≥ 75. The maximum is Amber.
2. **Single Red:** if only **1 indicator is Red** and the score is ≥ 75, the sector stays Green but gets a **risk warning** that names that indicator.

### How the values are calculated

- **Yearly growth (YoY):** `(value / value of the same quarter one year before − 1) × 100`. This is used for GDP, GOS and labour productivity, which are levels in the files.
- **Quarters of the score:** taken from the GDP file (`SCORE_QUARTERS_TAKEN_FROM`), last 5 years (`SCORE_NUMBER_OF_YEARS`).
- **Annual data (equity ratio):** each quarter uses the value of its year. If that year is not published yet, it uses the previous year. The `Value period` column shows which one was used.
- **ESG:** a single snapshot, so the same result is used in every quarter.
- **Missing data:** if an indicator has no value in a quarter, the score is calculated only with the indicators that do have data and rescaled to 100. `Data coverage %` shows how much of the weight had data.

### Outputs

| Variable in `main.py` | Content |
|---|---|
| `df_overall_score_table` | **Final table:** sectors as rows, quarters (last 5 years) as columns, score 0–100 |
| `df_overall_light_table` | Same shape, final traffic light after the override rules |
| `df_indicator_results` | One row per sector + quarter + indicator: value, light, weight, points (long format, for the dashboard) |
| `df_pillar_results` | One row per sector + quarter + pillar: score and light |
| `df_overall_results` | One row per sector + quarter: score, light by score, number of Reds, override, final light, warning |
| `indicator_value_tables`, `indicator_light_tables`, `indicator_points_tables` | One table (sectors × quarters) per indicator, e.g. `indicator_value_tables["gdp_growth"]` |
| `pillar_score_tables`, `pillar_light_tables` | One table (sectors × quarters) per pillar, e.g. `pillar_score_tables["W1"]` |
| `print_score_report(...)` | Printed report for one sector and quarter: indicator breakdown, calculation, override check, final result |

---

## Assumptions and limitations

- **Wage sustainability** (wage growth vs. productivity gap) and **workplace injury** are part of the original framework, but there is no data for them yet. For now, **labour productivity growth** and **ESG reporting** form pillar W3.
- **Weights** follow the pillar split (40 / 40 / 20). The equity ratio is the only indicator in W2, so it carries the full 40.
- **ESG sample:** only the 10 biggest companies per sector (see the limitation above).
- **Business expectations** are cleaned, merged and charted, but they are not part of the score yet.
- **Total row names** in `config.py` are marked `# CHECK` and must match the source files exactly.
- **Equity ratio** must be in % (e.g. 45, not 0.45), otherwise every sector will be rated Red.

---

## Adding a sector or an indicator

- **New sector:** add it to `TARGET_SECTORS` (and to `SECTOR_COLORS` for the charts).
- **New data file:** add it to `DATA_FILES`, run `python database.py`, and add it to `INDICATORS_TO_ANALYSE`.
- **New score indicator:** add it to `SCORE_INDICATORS` with its pillar, weight, calculation and limits. The weights must add up to 100 (the code warns if they don't).

## Next steps

- Interactive dashboard in Plotly Dash, with filters by sector, indicator and time period.
- Add wage and workplace injury data to complete pillar W3.