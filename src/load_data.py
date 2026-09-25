import pandas as pd
import sqlite3

# In this case, we are importing the data files from the "data" folder located in the root directory of the project.
# Later on, this data will be used to create a database for the dashboard.

def load_data(database_file_path, database_sql):
    
    with sqlite3.connect(database_file_path) as conn:
        df = pd.read_sql_query(
        database_sql,
        conn,
    )
    return df