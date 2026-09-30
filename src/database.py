# =====================================================================
# Creates the SQLite database from the raw data files.
# Run this file ONLY when you create the database for the first time
# or when you receive new/updated data files.
# Put it in the SAME folder as your exploration file.
# Creation day: 2026-09-30
# Moficiation day: 2026-09-30
# Created by: @ansanc
# Note that this code was generated with Cloude IA.
# =====================================================================

from pathlib import Path
import sqlite3
import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "Database_RiskDashboard.db"

# Table name in the database  ->  file in the data folder
SOURCE_FILES = {
    "raw_esg":                        "ESGReports.xlsx",
    "raw_gdp_growth":                 "RealGDPGrowthByIndustry.csv",
    "raw_gross_operating_surplus":    "GrossOperatingSurplusGrowthByIndustry.csv",
    "raw_labour_productivity":        "LabourProductivityValueAddedPerWorker.csv",
    "raw_equity_ratio":               "EquityRatioOfCompaniesByIndustry.csv",
    "raw_business_exp_manufacturing": "BusinessExpectationsOfTheManufacturingSector.csv",
    "raw_business_exp_services":      "BusinessExpectationsOfTheServiceSector.csv",
}


def create_database():
    """Read every file in SOURCE_FILES and save it as a table in the database.
    Tables are replaced each time, so running it again never duplicates data."""
    conn = sqlite3.connect(DB_PATH)
    for table_name, file_name in SOURCE_FILES.items():
        file_path = DATA_DIR / file_name
        if file_path.suffix == ".xlsx":
            df_raw = pd.read_excel(file_path)
        else:
            df_raw = pd.read_csv(file_path)
        df_raw.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"{file_name:50s} -> {table_name:32s} ({len(df_raw)} rows)")
    conn.commit()
    conn.close()
    print(f"\nDatabase ready: {DB_PATH}")


def load_table(table_name):
    """Read one table from the database and return it as a DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df


def list_tables():
    """Show which tables exist in the database."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT name FROM sqlite_master WHERE type = 'table'", conn)
    conn.close()
    return df


# This block runs ONLY when you execute this file directly
# (python database.py), NOT when another file imports it.
if __name__ == "__main__":
    create_database()
    print(list_tables())