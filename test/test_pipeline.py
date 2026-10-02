# =====================================================================
# test_pipeline.py
#
# How to run this file:
#   1. uv run python src/pipeline.py      
#   2. uv run pytest -v                   
# =====================================================================

import sys
from pathlib import Path

import pandas as pd

# Tell Python to look for our code in src/, so we can do "from config import ..."
SRC_FOLDER = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_FOLDER))

from config import OVERALL_RESULTS_FILE, BASELINE_OVERALL_RESULTS_FILE, SCORE_INDICATORS


# ---------------------------------------------------------------------
# 1. The result is the same as the baseline we trust
# ---------------------------------------------------------------------
def test_output_matches_baseline():
    result = pd.read_csv(OVERALL_RESULTS_FILE)
    baseline = pd.read_csv(BASELINE_OVERALL_RESULTS_FILE)

    # Check same columns
    assert set(result.columns) == set(baseline.columns)

    # Reorder result to match baseline
    result = result[baseline.columns]

    # Check same data
    assert result.equals(baseline)


# ---------------------------------------------------------------------
# 2. The weights of the score add up to 100
# ---------------------------------------------------------------------
def test_weights_add_up_to_100():
    total_weight = 0
    for indicator_settings in SCORE_INDICATORS.values():
        total_weight = total_weight + indicator_settings["weight"]
    assert total_weight == 100


# ---------------------------------------------------------------------
# 3. All the scores are between 0 and 100
# ---------------------------------------------------------------------
def test_scores_between_0_and_100():
    result = pd.read_csv(OVERALL_RESULTS_FILE)
    assert result["Score"].dropna().between(0, 100).all()


# ---------------------------------------------------------------------
# 4. The final light is only Green, Amber or Red
# ---------------------------------------------------------------------
def test_lights_are_only_green_amber_red():
    result = pd.read_csv(OVERALL_RESULTS_FILE)
    assert result["Final light"].dropna().isin(["Green", "Amber", "Red"]).all()