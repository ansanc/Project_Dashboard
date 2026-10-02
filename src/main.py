
## MAIN 
# ###
#  Purpose of this project:
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
####
# Porpuse of the file:
# load -> clean -> merge -> filter -> ESG -> data checks -> score -> save -> charts
#   How to use on terminal?
#   uv run python src/main.py              -> Run to get the plots
#   uv run python src/main.py --baseline   -> also save the results as the new baseline
#   For running the tests: uv run pytest -v
#
# What happened in each run is written in log/pipeline.log
# To explore the data step by step, use AllCode.py
# =====================================================================


from loguru import logger

from config import (DATA_FILES, FILES_TO_MERGE, INDICATORS_TO_ANALYSE, LOG_FOLDER, LOG_FILE,
                    OUTPUT_FOLDER, INDICATOR_RESULTS_FILE, PILLAR_RESULTS_FILE, OVERALL_RESULTS_FILE,
                    BASELINE_OVERALL_RESULTS_FILE, BASELINE_INDICATOR_RESULTS_FILE)
from database import load_all_tables
from exploration import (clean_indicator_file, merge_indicator_files, keep_target_sectors,
                         build_esg_risk_table, check_data_quality)
from plots import plot_all_charts_for_indicator
from scoring import (build_indicator_results, build_pillar_results, build_overall_results,
                     make_sector_by_quarter_table)


def setup_logging() -> None:
    """Write the logs in log/pipeline.log (and keep showing them on screen)."""
    LOG_FOLDER.mkdir(exist_ok=True)
    logger.add(LOG_FILE, level="DEBUG", rotation="1 MB", encoding="utf-8")


def run_pipeline() -> dict:
    """Run all the steps and return the results in a dictionary."""
    logger.info("Pipeline started")

    try:
        # 1. LOAD the tables from the database
        logger.info("Loading the tables from the database")
        raw_data = load_all_tables()
        for data_name, df_raw in raw_data.items():
            logger.debug("{} raw shape: {}", data_name, df_raw.shape)

        # 2. CLEAN each file (BEFORE filtering)
        logger.info("Cleaning the indicator files")
        clean_data = {}
        for data_name, file_settings in DATA_FILES.items():
            if data_name == "esg":
                continue
            clean_data[data_name] = clean_indicator_file(raw_data[data_name], file_settings["header_row"])

        # 3. MERGE the files that measure the same thing
        logger.info("Merging the files that measure the same thing")
        for merged_name, files_to_merge in FILES_TO_MERGE.items():
            dfs_to_merge = []
            for file_name in files_to_merge:
                dfs_to_merge.append(clean_data[file_name])
                del clean_data[file_name]
            clean_data[merged_name] = merge_indicator_files(dfs_to_merge)

        # 4. FILTER the target sectors
        logger.info("Keeping the target sectors")
        filtered_data = {}
        for data_name, df_clean in clean_data.items():
            filtered_data[data_name] = keep_target_sectors(df_clean)
            if filtered_data[data_name].empty:
                logger.warning("{}: no target sectors found -> check the sector names", data_name)
            else:
                logger.debug("{} filtered shape: {}", data_name, filtered_data[data_name].shape)

        # 5. ESG RISK
        logger.info("Building the ESG risk table")
        df_esg_risk = build_esg_risk_table(raw_data["esg"])

        # 6. DATA CHECKS (only the warnings go to the log)
        logger.info("Checking the data quality")
        for indicator_name, indicator_settings in INDICATORS_TO_ANALYSE.items():
            check_data_quality(filtered_data[indicator_name], indicator_settings["title"], show_tables=False)

        # 7. RISK SCORE
        logger.info("Calculating the risk score")
        df_indicator_results = build_indicator_results(filtered_data, df_esg_risk)
        df_pillar_results = build_pillar_results(df_indicator_results)
        df_overall_results = build_overall_results(df_indicator_results)

        # Alerts: indicators without data and override rules
        missing_values = df_indicator_results["Light"].isna().sum()
        if missing_values > 0:
            logger.warning("{} indicator values without data (the score was rescaled)", missing_values)
        overrides = df_overall_results["Override applied"].sum()
        if overrides > 0:
            logger.warning("Green blocked by the override rule in {} sector-quarters", overrides)

    except Exception as error:
        logger.error("Pipeline failed: {}", error)
        raise

    logger.success("Pipeline completed successfully")
    return {
        "clean_data": clean_data,
        "filtered_data": filtered_data,
        "df_esg_risk": df_esg_risk,
        "df_indicator_results": df_indicator_results,
        "df_pillar_results": df_pillar_results,
        "df_overall_results": df_overall_results,
    }


def save_results(results: dict) -> None:
    """8. SAVE the score results as CSV in the output folder."""
    try:
        OUTPUT_FOLDER.mkdir(exist_ok=True)
        results["df_indicator_results"].to_csv(INDICATOR_RESULTS_FILE, index=False)
        results["df_pillar_results"].to_csv(PILLAR_RESULTS_FILE, index=False)
        results["df_overall_results"].to_csv(OVERALL_RESULTS_FILE, index=False)
        logger.success("Results saved in {}", OUTPUT_FOLDER)
    except Exception as error:
        logger.error("Failed to save the results: {}", error)
        raise


def log_final_lights(results: dict) -> None:
    """Write in the log the final traffic light of each sector in the latest quarter."""
    df_light_table = make_sector_by_quarter_table(results["df_overall_results"], "Final light")
    latest_quarter = df_light_table.columns[-1]
    for sector in df_light_table.index:
        logger.info("{} | {}: {}", latest_quarter, sector, df_light_table.loc[sector, latest_quarter])


def make_charts(results: dict) -> None:
    """9. CHARTS: saved as HTML in the output folder.
    If a chart fails, the error is logged (the results are already saved)."""
    logger.info("Making the charts")
    try:
        for indicator_name, indicator_settings in INDICATORS_TO_ANALYSE.items():
            plot_all_charts_for_indicator(results["clean_data"][indicator_name],
                                          results["filtered_data"][indicator_name],
                                          indicator_settings)
        logger.success("Charts saved in {}", OUTPUT_FOLDER)
    except Exception as error:
        logger.error("Failed to make the charts: {}", error)


def save_baseline() -> None:
    """Copy the saved results as the baseline the tests compare against.
    Do it ONLY when you are sure the results are correct."""
    shutil.copy(OVERALL_RESULTS_FILE, BASELINE_OVERALL_RESULTS_FILE)
    shutil.copy(INDICATOR_RESULTS_FILE, BASELINE_INDICATOR_RESULTS_FILE)
    logger.success("Baseline saved in {}", BASELINE_OVERALL_RESULTS_FILE.parent)


if __name__ == "__main__":
    setup_logging()
    pipeline_results = run_pipeline()
    save_results(pipeline_results)
    log_final_lights(pipeline_results)
    make_charts(pipeline_results)
    if "--baseline" in sys.argv:
        save_baseline()