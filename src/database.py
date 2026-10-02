# =====================================================================
# Creates the SQLite database from the raw data files.
# Run this file ONLY when you create the database for the first time
# or when you receive new/updated data files.
# Put it in the SAME folder as your exploration file.
# Creation day: 2026-09-30
# Moficiation day: 2026-09-30
# Created by: @ansanc
# Note that this code was generated with Cloude IA.

import sqlite3
import pandas as pd

from config import DATA_FOLDER, DATABASE_PATH, DATA_FILES


def create_database():
    """Read every file in DATA_FILES and save it as a table in the database.
    Tables are replaced each time, so running it again never duplicates data."""
    connection = sqlite3.connect(DATABASE_PATH)

    for data_name, file_settings in DATA_FILES.items():
        file_path = DATA_FOLDER / file_settings["file_name"]

        # Read the file (Excel or CSV)
        if file_path.suffix == ".xlsx":
            df_file = pd.read_excel(file_path)
        else:
            df_file = pd.read_csv(file_path)

        # Save it as a table
        df_file.to_sql(file_settings["table_name"], connection, if_exists="replace", index=False)
        print(f"{file_settings['file_name']:50s} -> {file_settings['table_name']} ({len(df_file)} rows)")

    connection.commit()
    connection.close()
    print(f"\nDatabase ready: {DATABASE_PATH}")


def load_table(table_name):
    """Read one table from the database and return it as a DataFrame."""
    connection = sqlite3.connect(DATABASE_PATH)
    df_table = pd.read_sql(f"SELECT * FROM {table_name}", connection)
    connection.close()
    return df_table


def list_database_tables():
    """Show which tables exist in the database."""
    connection = sqlite3.connect(DATABASE_PATH)
    df_tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type = 'table'", connection)
    connection.close()
    return df_tables


def load_all_tables():
    """Load every table of DATA_FILES into a dictionary:
    {'gdp': df, 'gos': df, ..., 'esg': df}"""
    raw_data = {}
    for data_name, file_settings in DATA_FILES.items():
        raw_data[data_name] = load_table(file_settings["table_name"])
    return raw_data


# Runs ONLY with "python database.py", not when another file imports it
if __name__ == "__main__":
    create_database()
    print(list_database_tables())