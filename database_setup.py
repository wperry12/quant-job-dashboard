# database_setup.py
import sqlite3
import pandas as pd
from pathlib import Path

# --- Constants Definition ---
DB_FILE = Path(__file__).parent / "jobs.db"
CONFIG_PATH = Path(__file__).parent / "config"

def create_tables(cursor):
    """Creates all necessary tables in the database."""
    print("Creating database tables...")

    # --- Schema Definition for Config Tables ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "companies" (
        "id" TEXT PRIMARY KEY, "name" TEXT, "logo_filename" TEXT,
        "scraper_type" TEXT, "scraper_config" TEXT
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "job_roles" ("id" TEXT PRIMARY KEY, "title" TEXT);
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "experience_levels" ("id" TEXT PRIMARY KEY, "title" TEXT);
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "job_locations" ("normalized_name" TEXT PRIMARY KEY, "aliases" TEXT);
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "role_keywords" (
        "job_role_id" TEXT, "keyword" TEXT, "priority" INTEGER
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "seniority_keywords" (
        "experience_level_id" TEXT, "keyword" TEXT, "priority" INTEGER
    );
    """)

    # --- Schema Definition for Jobs Data Table ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "jobs" (
        "id" TEXT PRIMARY KEY, "company_id" TEXT, "external_id" TEXT, "requisition" TEXT,
        "title" TEXT, "location" TEXT, "seniority" TEXT, "category" TEXT,
        "first_posted" TEXT, "updated_at" TEXT, "url" TEXT, "is_active" INTEGER,
        "created_at" TEXT, "last_scraped_at" TEXT, "classified_role_id" TEXT,
        "classified_seniority_id" TEXT, "last_classified_at" TEXT, "raw_location" TEXT,
        UNIQUE("company_id", "external_id")
    );
    """)
    print("✅ Tables created successfully.")

def import_csv_data(conn):
    """Imports initial data from all CSV files into the newly created database tables."""
    print("\nImporting initial data from CSV files...")
    
    # A single map defining the source CSV file for each table.
    # We now include 'jobs' in this map.
    seed_data_map = {
        "companies": "companies.csv",
        "job_roles": "job_roles.csv",
        "experience_levels": "experience_levels.csv",
        "job_locations": "job_locations.csv",
        "role_keywords": "role_keywords.csv",
        "seniority_keywords": "seniority_keywords.csv",
        "jobs": "existing_jobs.csv" # Added jobs table here
    }
    
    # Loop through the map and import data for each table.
    try:
        for table_name, file_name in seed_data_map.items():
            path = CONFIG_PATH / file_name
            if path.exists():
                df = pd.read_csv(path)
                # Handle potential duplicate columns from CSV export issues (like in existing_jobs.csv)
                df = df.loc[:, ~df.columns.duplicated(keep='first')]
                
                df.to_sql(table_name, conn, if_exists="replace", index=False)
                print(f"    - Successfully imported {file_name} into '{table_name}' table.")
            else:
                print(f"    - ⚠️ Warning: Seed file not found, skipping: {file_name}")
        print("✅ Seed data imported successfully.")
    except Exception as e:
        print(f"❌ An error occurred during CSV import: {e}")

def main():
    """Main function to set up and initialize the database."""
    DB_FILE.parent.mkdir(exist_ok=True, parents=True)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    create_tables(cursor)
    import_csv_data(conn)
    
    conn.commit()
    conn.close()
    
    print(f"\nDatabase setup complete. Database file created at: {DB_FILE}")

if __name__ == "__main__":
    main()