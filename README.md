# Industry Risk Dashboard — Data & Scoring Engine

Early-warning system that consolidates several economic and ESG indicators into a central database and turns them into a **traffic-light rating (Green / Amber / Red)** per industry. It lets users quickly see which industries show signs of strength, deterioration or elevated risk.

This repository covers:

- **Part 1 – Data:** loading, cleaning, exploration and charts.
- **Part 2 – Risk score:** indicator traffic lights, pillar scores and the overall score.
- **Part 3 – Dashboard:** Streamlit dashboard for the credit committee, with an AI commentary per sector.

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
Project_Dashboard/
├── data/                         <- source files + the SQLite database
│   ├── RealGDPGrowthByIndustry.csv
│   ├── GrossOperatingSurplusGrowthByIndustry.csv
│   ├── LabourProductivityValueAddedPerWorker.csv
│   ├── EquityRatioOfCompaniesByIndustry.csv
│   ├── BusinessExpectationsOfTheManufacturingSector.csv
│   ├── BusinessExpectationsOfTheServiceSector.csv
│   ├── ESGReports.xlsx
│   ├── IndustryPulse_logo.png     <- logo shown at the top of the dashboard sidebar
│   ├── Database_RiskDashboard.db  <- created by database.py
│   └── reconciliation_baseline_*.csv  <- trusted results the tests compare against
├── output/                       <- HTML charts + result CSVs
├── log/
│   ├── pipeline.log              <- what happened in each run (main.py and dashboard)
│   └── ai_runs.log               <- each AI analysis requested in the dashboard
├── src/                          <- all the code
│   ├── config.py                 <- all the settings
│   ├── database.py               <- creates and reads the database
│   ├── exploration.py            <- cleaning, merging, ESG, data checks and charts
│   ├── scoring.py                <- risk score and traffic lights
│   ├── main.py                   <- RUNS the whole project with one command (logs, results, charts)
│   └── dashboard.py              <- Streamlit dashboard (Part 3)
├── test/
│   └── test_pipeline.py          <- 7 simple pytest tests
├── .streamlit/
│   └── config.toml               <- dashboard colours (dark blue accent, light and dark theme)
├── .env                          <- your OpenRouter API key (NOT on GitHub)
├── check_setup.py                <- checks that the environment is ready
├── pyproject.toml                <- project and dependencies (uv)
├── uv.lock                       <- exact versions of the dependencies (uv)
├── .python-version
├── .gitignore
└── README.md
```

| File | What it does |
|---|---|
| `config.py` | Folders, data files, sectors, colors, indicators, ESG rules, score weights and limits. **Everything you may want to change is here.** |
| `database.py` | Reads every source file and saves it as a table in `Database_RiskDashboard.db`. Also loads the tables back into pandas. |
| `exploration.py` | Cleans the SingStat files, merges files that measure the same thing, calculates the share of total GDP, builds the ESG risk, runs the data checks and makes the charts (line trends, grouped bars, donuts and bars vs. total, saved as HTML in `output/`). |
| `scoring.py` | Yearly growth, traffic lights, pillar scores (W1, W2, W3), overall score, override rules and the report per sector. |
| `main.py` | **Runs** the whole project with one command: load, clean, merge, filter, ESG, data checks, score, save the results in `output/` (which the tests read), charts and, when asked, the baseline. Everything is written in `log/pipeline.log`. |
| `dashboard.py` | **Shows** the results in a Streamlit dashboard for the credit committee: overview, sector zoom with AI commentary, indicator data, ESG and methodology (see Part 3). |

---

## How to run

The project uses [uv](https://docs.astral.sh/uv/) to manage Python and the dependencies (`pandas`, `numpy`, `plotly`, `openpyxl`, `loguru`, `streamlit`, `openai`, `dotenv`, and `pytest` for the tests). All the commands are run from the `Project_Dashboard/` folder.

0. **Install the environment** (first time only):
   ```bash
   uv sync
   uv add pandas numpy plotly openpyxl loguru streamlit openai dotenv   # if they are not in pyproject.toml yet
   uv add --dev pytest
   ```
1. **Create the database.** Run this only the first time, or when you get new or updated files.
   ```bash
   uv run python src/database.py
   ```
2. **Run the project.** Results, charts and log:
   ```bash
   uv run python src/main.py
   ```
3. **Create the baseline.** If there is no baseline yet (for example after cloning from GitHub), `main.py` asks at the end:
   `There is no baseline yet. Will you run the test files? (yes/no)`. Answer `yes` and the baseline is saved in `data/`.
   If the baseline already exists, it doesn't ask. Keep `SAVE_BASELINE = False` in `config.py`.
4. **Run the tests** (after running `main.py`, because they read `output/overall_results.csv`):
   ```bash
   uv run pytest -v
   ```
5. **Open the dashboard** (after creating the database in step 1):
   ```bash
   uv run streamlit run src/dashboard.py
   ```
   For the AI analysis, create a `.env` file in the `Project_Dashboard/` folder with `OPENROUTER_API_KEY=your-key` (see Part 3).

> The `.py` files import each other (`from config import ...`), so Python must look for them in `src/`. From the terminal the commands above already do it. In the VS Code interactive window, if you get `ModuleNotFoundError: No module named 'config'`, add `"jupyter.notebookFileRoot": "${fileDirname}"` to `.vscode/settings.json`.

> Tip: if you edit another `.py` file while working in the VS Code interactive window, run `%load_ext autoreload` and `%autoreload 2` once. Your changes will then be picked up without restarting.

> The charts are always saved in `output/`. Set `SHOW_CHARTS_IN_BROWSER = True` in `config.py` if you also want them to open in the browser.

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

1. **Header:** the row with the column names is found automatically (the one that says `Data Series`). Each file can have it in a different row; if it is already the header, nothing changes.
2. **Rename:** the first column becomes `Sectors`, and all the quarters are written the same way (`19801Q` -> `1980 1Q`).
3. **Bad columns:** columns without a name that are completely empty are removed, and repeated column names keep only the first one.
4. **Footnotes:** everything from the `Definitions and Footnotes` row down is removed, together with completely empty rows.
5. **Numbers:** values become numbers, and texts like `na` or `-` become empty (NaN).
6. **Sector names:** extra spaces are removed so they match the target sectors.
7. **Filter:** only the target sectors are kept.

The two Business Expectations files measure the same thing for different sectors, so after cleaning they are **merged into one df** (`business_expectations`).

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

**Results of `main.py`:** `run_pipeline()` returns a dictionary with:

| Key | Content |
|---|---|
| `clean_data[name]` | Cleaned dfs, with all the rows (including totals) |
| `filtered_data[name]` | Only the target sectors |
| `df_esg_risk` | Sector, ESG reporting compliance, risk_score |

The data checks (missing values, repeated sectors, unusual jumps) are written as warnings in `log/pipeline.log`.

**Charts** (saved as HTML in `output/`), made by `make_charts()` in `main.py` with the functions of section 7 of `exploration.py`:

| Function | Chart | For which indicators |
|---|---|---|
| `plot_trend_charts` | Line trend by sector (full history) + grouped bars (last 20 periods) | All |
| `plot_share_of_total_donuts` | 2 donuts: selected sectors vs. "Other Sectors", and a zoom on the selected sectors | Only amounts that add up to a total: GDP, GOS (`adds_up_to_total = True`) |
| `plot_sectors_vs_total` | Bars with the latest value of each sector and a dashed line with the total | Ratios, per worker and expectations (`adds_up_to_total = False`), where a donut would make no sense |

In total: 4 charts for GDP and GOS, 3 for each of the other indicators (17 charts).

---

## Part 2 – Risk score

### Pillars and indicators

The overall score is the weighted sum of three pillars. Each pillar is also a traffic light of its own.

| Pillar | Weight | Indicator | Weight | Green | Amber | Red |
|---|---|---|---|---|---|---|
| **W1** Economic performance | 40 | Real GDP growth (YoY) | 20 | > 3% | 0% to 3% | < 0% |
| | | GOS growth (YoY) | 20 | > 5% | 0% to 5% | < 0% |
| **W2** Financial health | 40 | Equity ratio (a ratio, not %) | 40 | ≥ 0.40 | 0.20 to < 0.40 | < 0.20 |
| **W3** Workforce / operational | 20 | Labour productivity growth (YoY) | 10 | ≥ 0% | −3% to < 0% | < −3% |
| | | ESG reporting | 10 | Low risk | Medium risk | High risk |

**Points per indicator:** Green = 100% of its weight, Amber = 50%, Red = 0%.

### Overall rating

| Score | Rating |
|---|---|
| 75.00 – 100 | Green |
| 40.00 – 74.99 | Amber (70.00 – 74.99 is provisionally Amber) |
| 0 – 39.99 | Red |

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

**Files saved by `main.py` in `output/`** (the tests and the dashboard read them):

| File | Content |
|---|---|
| `indicator_results.csv` | One row per sector + quarter + indicator: value, light, weight, points |
| `pillar_results.csv` | One row per sector + quarter + pillar: score and light |
| `overall_results.csv` | One row per sector + quarter: score, light by score, number of Reds, override, final light, warning |

The log also shows the final light of each sector in the latest quarter.

Tables with sectors as rows and quarters as columns can be made from the CSVs with `make_sector_by_quarter_table()` in `scoring.py`.

---

## Part 3 – Dashboard

`dashboard.py` is a Streamlit dashboard for the monthly / quarterly meeting between the credit area and the credit risk area. It goes from the **general picture to the details**, and it shows **colours, not scores**: the score stays in the Methodology tab.

```bash
uv run streamlit run src/dashboard.py
```

When it opens, it runs the same pipeline as `main.py` once (from the database) and keeps the results in memory, so it doesn't need the files in `output/`.

### Sidebar (filters for every tab)

| Element | What it does |
|---|---|
| Logo | `data/IndustryPulse_logo.png` (only if the file exists) |
| Assessment quarter | The quarter shown in every tab (latest quarter by default) |
| Traffic light | Shows only the sectors with the selected colours in that quarter |
| Reset | Back to the latest quarter and all the colours |
| Reload data | Runs the pipeline again (after changing the data files or `config.py`) |

### Tabs

| Tab | What it shows |
|---|---|
| **Overview** | Number of sectors per colour, the committee table (traffic light, change vs. previous quarter, W1–W3 and Red indicators, with CSV download), a light map of all the sectors over time and a pillar map. **Click a sector in the table to open it in Sector zoom.** |
| **Sector zoom** | Traffic light, quarters with the same colour, Red indicators and data coverage; a red box with the risk warning when there is one; each pillar explained with its indicators and units; the history of the colours; one chart per indicator (points coloured with their traffic light, y axis up to 1.5 × the historical maximum, a dotted line on the selected quarter); and the **AI analysis**. |
| **Indicator data** | The underlying data of each indicator with its unit: line or bars, period slider, latest data and download. Business Expectations is shown for context only. |
| **ESG** | Latest ESG report only (no history): Yes / Partially / No per sector, the physical, transition and governance risks each sector tends to have, and why ESG / TCFD / TNFD reports matter for credit, with official sources. |
| **Methodology** | The rules of the score, the limits of each indicator and the technical tables, with downloads. |

### AI analysis (Sector zoom only)

The AI is **complementary**: it comments on what the dashboard already shows, it doesn't decide anything.

- **How:** the button *Generate AI analysis* sends the colours of the sector, its indicators, the change vs. the previous quarter and the ESG profile to a model through [OpenRouter](https://openrouter.ai/).
- **Answer:** executive, maximum 200 words: *Key strengths & vulnerabilities*, *Outlook & risk commentary* and *Sector trends* (bullets, each with an official source link), plus a limitation line.
- **Links:** the model has no internet access, so it can only cite the official sources given in `ESG_SECTOR_RISKS` (`config.py`). Any other link is flagged with a warning.
- **Model:** `AI_MODEL` in `config.py` (`deepseek/deepseek-v4.1-flash`, a low-cost model).
- **Cost:** answers are cached, so the same sector and quarter is not sent twice; short prompt and `max_tokens=500`.
- **Log:** each request is written in `log/ai_runs.log` (the API key never is; a test checks it).

**API key** (the key is private and is never written in the code):

| Where | How |
|---|---|
| Your computer | A `.env` file in `Project_Dashboard/` with `OPENROUTER_API_KEY=your-key`. `.env` is in `.gitignore`, so it is never committed. |
| Streamlit Community Cloud | Add `OPENROUTER_API_KEY` in the app's **Secrets** (`st.secrets`). |

Without a key, the dashboard works normally and only the AI section shows how to add it.

### Colours

The dashboard follows the user's light or dark system theme. The accent colour (dark blue) is set in `.streamlit/config.toml`, so it is not confused with the red of the traffic light.

---

## Tests

`test/test_pipeline.py` has 7 simple tests on the results saved in `output/overall_results.csv`, the dashboard and the AI log:

| Test | What it checks |
|---|---|
| `test_output_matches_baseline` | The result is exactly the same as the baseline in `data/` (same columns, same data). |
| `test_weights_add_up_to_100` | The weights of the score add up to 100. |
| `test_scores_between_0_and_100` | All the scores are between 0 and 100. |
| `test_lights_are_only_green_amber_red` | The final light is only Green, Amber or Red. |
| `test_dashboard_runs_without_errors` | The dashboard opens without errors (Streamlit `AppTest`, no browser needed). |
| `test_every_light_has_a_credit_signal` | Every traffic light has a credit signal in `config.py`. |
| `test_api_key_is_never_in_the_ai_log` | The API key of `.env` is never written in `log/ai_runs.log`. |

**How to run them:**

```bash
uv run python src/main.py          # 1. creates the results in output/
uv run pytest -v                   # 2. runs the tests
```

**The baseline** is a copy of results you have checked and trust. If it doesn't exist yet, `main.py` asks if you will run the tests and creates it when you answer `yes`. The baseline test doesn't prove the results are correct, only that they **haven't changed** since then.

**Break it on purpose:** a test that has never failed hasn't proven anything. For example, change the equity ratio weight from 40 to 30 in `config.py`, run the pipeline and the tests: they must **FAIL**. Then undo the change.

> When you change the logic **on purpose** (new weights, a new indicator…), check the new results and then create the baseline again with `SAVE_BASELINE = True`.

---

## Logs

Every run of `main.py` (and of the dashboard) writes what happened in `log/pipeline.log` (with [loguru](https://github.com/Delgan/loguru)). The AI requests of the dashboard go to `log/ai_runs.log`.

| Level | Used for |
|---|---|
| `info` | Each step that starts (loading, cleaning, merging, scoring…). |
| `debug` | Shapes of the tables. |
| `warning` | **Alerts:** a filtered df is empty, a total row is not found, a sector appears twice, unusual jumps in the data, invalid ESG answers, sectors without ESG data, indicators without data (score rescaled), Green blocked by the override rule, weights that don't add up to 100. |
| `success` | Pipeline completed, results saved, baseline saved. |
| `error` | A step failed (`try/except`): the error is written in the log before stopping. |

---

## Assumptions and limitations

- **Wage sustainability** (wage growth vs. productivity gap) and **workplace injury** are part of the original framework, but there is no data for them yet. For now, **labour productivity growth** and **ESG reporting** form pillar W3.
- **Weights** follow the pillar split (40 / 40 / 20). The equity ratio is the only indicator in W2, so it carries the full 40.
- **ESG sample:** only the 10 biggest companies per sector (see the limitation above).
- **Business expectations** are cleaned, merged and charted, but they are not part of the score yet.
- **Total row names** in `config.py` are marked `# CHECK` and must match the source files exactly.
- **Equity ratio** is a ratio (e.g. 0.45, not 45%), so its limits are 0.40 and 0.20. If the source file ever changes to %, the limits must change too.
- **Utilities** is not in the Equity ratio and Labour productivity files, so those charts show "No data" and its score uses the other indicators.
- **AI analysis** is a commentary to support the discussion: it can be wrong and must be checked before using it.

---

## Adding a sector or an indicator

- **New sector:** add it to `TARGET_SECTORS` (and to `SECTOR_COLORS` for the charts).
- **New data file:** add it to `DATA_FILES`, run `python database.py`, and add it to `INDICATORS_TO_ANALYSE`.
- **New score indicator:** add it to `SCORE_INDICATORS` with its pillar, weight, calculation and limits. The weights must add up to 100 (the code warns if they don't).

