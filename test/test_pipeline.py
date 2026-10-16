
######################################################################
# test_pipeline.py
# Simple tests on the results saved by the pipeline and on the dashboard.
#
#   1. uv run python main.py          -> creates output/overall_results.csv
#   2. uv run pytest -v                   -> runs these tests
######################################################################

import sys
import tomllib
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

# Tell Python to look for our code in src/, so we can do "from config import ..."
SRC_FOLDER = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_FOLDER))

from config import (OVERALL_RESULTS_FILE, BASELINE_OVERALL_RESULTS_FILE, SCORE_INDICATORS,
                    PROJECT_FOLDER, CREDIT_SIGNAL, POINTS_PER_LIGHT, AI_LOG_FILE)


###################################
# 1. The result is the same as the baseline we trust
###################################
def test_output_matches_baseline():
    result = pd.read_csv(OVERALL_RESULTS_FILE)
    baseline = pd.read_csv(BASELINE_OVERALL_RESULTS_FILE)

    # Check same columns
    assert set(result.columns) == set(baseline.columns)

    # Reorder result to match baseline
    result = result[baseline.columns]

    # Check same data
    assert result.equals(baseline)


###################################
# 2. The weights of the score add up to 100
###################################
def test_weights_add_up_to_100():
    total_weight = 0
    for indicator_settings in SCORE_INDICATORS.values():
        total_weight = total_weight + indicator_settings["weight"]
    assert total_weight == 100


###################################
# 3. All the scores are between 0 and 100
###################################
def test_scores_between_0_and_100():
    result = pd.read_csv(OVERALL_RESULTS_FILE)
    assert result["Score"].dropna().between(0, 100).all()


###################################
# 4. The final light is only Green, Amber or Red
###################################
def test_lights_are_only_green_amber_red():
    result = pd.read_csv(OVERALL_RESULTS_FILE)
    assert result["Final light"].dropna().isin(["Green", "Amber", "Red"]).all()


###################################
# 5. The dashboard opens without errors
#    (Streamlit's own test tool: it runs dashboard.py without a browser)
###################################
def test_dashboard_runs_without_errors():
    dashboard = AppTest.from_file(str(SRC_FOLDER / "dashboard.py"), default_timeout=120)
    dashboard.run()
    assert not dashboard.exception


###################################
# 6. Every light has a credit signal (Grow / Grow selectively / Slow growth)
###################################
def test_every_light_has_a_credit_signal():
    assert set(CREDIT_SIGNAL) == set(POINTS_PER_LIGHT)


###################################
# 7. Guardrail: the API key is never written in the AI log
###################################
def test_api_key_is_never_in_the_ai_log():
    secrets_file = PROJECT_FOLDER / ".streamlit" / "secrets.toml"
    if not secrets_file.exists() or not AI_LOG_FILE.exists():
        return      # nothing to check yet (no key or no AI run)

    with open(secrets_file, "rb") as file:
        api_key = tomllib.load(file)["OPENROUTER_API_KEY"]
    assert api_key not in AI_LOG_FILE.read_text(encoding="utf-8")