# data_manager.py
import pandas as pd
import sqlite3
from pathlib import Path

# Define a constant for the database file path.
# This makes it easy to change the database location in one place.
DB_FILE = Path(__file__).parent / "jobs.db"

def load_table(table_name: str) -> pd.DataFrame:
    """
    Loads a full table from the SQLite database into a pandas DataFrame.

    Args:
        table_name: The name of the database table to load.

    Returns:
        A pandas DataFrame containing the data from the specified table.
    """
    # Before attempting to connect, check if the database file has been created.
    if not DB_FILE.exists():
        raise FileNotFoundError(f"Database file not found at {DB_FILE}. Please run database_setup.py first.")
    
    try:
        # Use a 'with' statement to ensure the database connection is automatically closed.
        with sqlite3.connect(DB_FILE) as conn:
            # Use pandas' built-in SQL reader to directly load the query result into a DataFrame.
            df = pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)
            return df
    except pd.io.sql.DatabaseError:
        # If the table doesn't exist yet (e.g., on the first run), handle it gracefully.
        print(f"Warning: Table '{table_name}' not found. Returning empty DataFrame.")
        return pd.DataFrame()

def save_jobs_to_db(jobs_df: pd.DataFrame):
    """
    Saves the final DataFrame of jobs to the 'jobs' table in the SQLite database.
    This will completely replace the existing table with the new data.
    
    Args:
        jobs_df: The DataFrame containing the final, merged job data to be saved.
    """
    # Define the exact columns for the 'jobs' table to ensure the DataFrame schema
    # matches the database table schema before writing.
    db_columns = [
        'id', 'company_id', 'external_id', 'title', 'location', 'seniority', 
        'category', 'first_posted', 'last_updated', 'url', 'is_active', 
        'last_scraped_at', 'classified_role_id', 'classified_seniority_id', 
        'last_classified_at'
    ]
    
    # Ensure all required columns from the database schema exist in the DataFrame.
    # If a column is missing (e.g., 'category'), add it and fill with None.
    for col in db_columns:
        if col not in jobs_df.columns:
            jobs_df[col] = None
            
    # Filter the DataFrame to include only the columns that exist in the database table.
    # This prevents errors from extra columns that may have been created during processing.
    jobs_to_save = jobs_df[db_columns]

    with sqlite3.connect(DB_FILE) as conn:
        # Write the cleaned DataFrame to the 'jobs' table.
        # 'if_exists="replace"' will drop the table if it already exists and create a new one.
        # This is a simple way to ensure the table is always up-to-date with the latest scrape.
        jobs_to_save.to_sql('jobs', conn, if_exists='replace', index=False)
        print(f"Successfully saved {len(jobs_to_save)} jobs to the database.")