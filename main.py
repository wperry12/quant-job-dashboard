# main.py
import time
import json
import pandas as pd
from typing import List, Dict
from dataclasses import asdict
from datetime import datetime
import uuid

# Local module imports for data handling, classification, and models.
import data_manager
import classifier
from models import Job

# Import specific scraper classes.
from scrapers.greenhouse import GreenhouseScraper
from scrapers.lever import LeverScraper
from scrapers.workable import WorkableScraper

# A mapping to dynamically select the correct scraper class based on a string identifier.
# This makes the main loop cleaner and easier to extend with new scrapers.
SCRAPER_MAPPING = {
    "greenhouse": GreenhouseScraper,
    "lever": LeverScraper,
    "workable": WorkableScraper,
}

def build_scraper_config(company: pd.Series) -> Dict:
    """
    Dynamically builds the configuration dictionary required by a scraper instance.
    It checks for specific config columns (like greenhouse_board_token) and falls
    back to a generic JSON config column.

    Args:
        company: A pandas Series representing a single row from the companies table.

    Returns:
        A dictionary with the necessary configuration for the scraper.
    """
    config_str = company.get("scraper_config", "{}")
    
    # Handle Greenhouse-specific configuration.
    if pd.notna(company["greenhouse_board_token"]):
        return {"board_token": company["greenhouse_board_token"]}
    
    # Fallback to parsing a JSON string from the 'scraper_config' column for other types.
    try:
        if pd.notna(config_str):
            return json.loads(config_str)
    except (json.JSONDecodeError, TypeError):
        # Return an empty dict if the config is not valid JSON.
        return {}
    return {}


def main():
    """Main orchestration function to run the entire scraping and classification process."""
    print("Starting the job scraping process...")

    # --- 1. Load Data ---
    # Load all configuration tables and existing job data from the database.
    companies_df = data_manager.load_table("companies")
    role_keywords_df = data_manager.load_table("role_keywords")
    seniority_keywords_df = data_manager.load_table("seniority_keywords")
    existing_jobs_df = data_manager.load_table("jobs")
    
    # Rename keyword DataFrame columns to match the generic names expected by the classifier.
    role_keywords_df = role_keywords_df.rename(columns={"job_role_id": "role_id"})
    seniority_keywords_df = seniority_keywords_df.rename(columns={"experience_level_id": "seniority_id"})
    
    # Create a lookup dictionary to preserve the original 'first_posted' date of jobs
    # that are scraped again. This prevents the date from being updated on every scrape.
    existing_jobs_lookup = {}
    if not existing_jobs_df.empty and 'external_id' in existing_jobs_df.columns:
        # Using a temporary string column for the index ensures consistent matching.
        existing_jobs_df['external_id_str'] = existing_jobs_df['external_id'].astype(str)
        existing_jobs_df.set_index('external_id_str', inplace=True)
        existing_jobs_lookup = existing_jobs_df['first_posted'].to_dict()
    
    all_scraped_jobs: List[Job] = []

    # --- 2. Scrape Jobs ---
    # Iterate over each company configured in the database.
    print("\nScraping jobs for each company...")
    for _, company in companies_df.iterrows():
        scraper_type = company["scraper_type"]
        ScraperClass = SCRAPER_MAPPING.get(scraper_type)

        if not ScraperClass:
            print(f"Warning: No scraper found for type: '{scraper_type}'. Skipping {company['name']}.")
            continue

        try:
            config = build_scraper_config(company)
            if not config:
                print(f"Warning: Config for {company['name']} is empty. Skipping.")
                continue

            # Dynamically instantiate the correct scraper class with its config.
            scraper = ScraperClass(
                company_id=str(company["id"]),
                company_name=company["name"],
                config=config
            )
            scraped_jobs = scraper.scrape(existing_jobs_lookup)
            all_scraped_jobs.extend(scraped_jobs)
            time.sleep(1) # Pause briefly to be respectful to the APIs being scraped.
        except Exception as e:
            print(f"An error occurred scraping {company['name']}: {e}")

    # Reset index of the existing jobs DataFrame if it was modified for the lookup.
    if 'external_id_str' in existing_jobs_df.columns:
        existing_jobs_df.reset_index(inplace=True)

    # Handle the case where no new jobs were found.
    if not all_scraped_jobs:
        if not existing_jobs_df.empty:
            print("No new jobs were scraped. Marking all existing jobs as inactive...")
            existing_jobs_df['is_active'] = 0 # Use 0 for False for database compatibility.
            data_manager.save_jobs_to_db(existing_jobs_df)
        else:
            print("No new jobs were scraped and no existing jobs found. Exiting.")
        return

    # --- 3. Process Scraped Data ---
    # Convert the list of Job dataclass objects into a pandas DataFrame.
    scraped_jobs_df = pd.DataFrame([asdict(job) for job in all_scraped_jobs])

    # Pass the new jobs to the classifier module.
    classified_jobs_df = classifier.classify_jobs(scraped_jobs_df, role_keywords_df, seniority_keywords_df)
    classified_jobs_df['last_classified_at'] = datetime.now().isoformat()

    # --- 4. Merge and Update Job Statuses ---
    print("\nMerging new and existing jobs...")
    
    # Create a set of unique keys (company_id, external_id) for all newly scraped jobs.
    scraped_job_keys = set(
        zip(
            classified_jobs_df['company_id'].astype(str), 
            classified_jobs_df['external_id'].astype(str)
        )
    )

    # If there are existing jobs, update their 'is_active' status.
    if not existing_jobs_df.empty:
        # Any existing job NOT found in the latest scrape is now considered inactive.
        existing_job_keys = zip(
            existing_jobs_df['company_id'].astype(str), 
            existing_jobs_df['external_id'].astype(str)
        )
        is_now_inactive = [key not in scraped_job_keys for key in existing_job_keys]
        existing_jobs_df.loc[is_now_inactive, 'is_active'] = 0 # 0 for False

    # All jobs found in the current scrape are considered active.
    classified_jobs_df['is_active'] = 1 # 1 for True
    
    # Combine the updated old jobs and the new jobs.
    if not existing_jobs_df.empty:
        # `drop_duplicates` with `keep='last'` ensures that if a job exists in both
        # old and new data, the new version (which was concatenated last) is kept.
        combined_df = pd.concat([existing_jobs_df, classified_jobs_df]).drop_duplicates(
            subset=['company_id', 'external_id'], keep='last'
        )
    else:
        combined_df = classified_jobs_df

    # --- 5. Finalize and Save ---
    # Ensure every job has a primary key 'id'. Generate one if it's missing.
    if 'id' not in combined_df.columns or combined_df['id'].isnull().any():
        mask = combined_df['id'].isnull()
        combined_df.loc[mask, 'id'] = [str(uuid.uuid4()) for _ in range(mask.sum())]

    # Save the final, unified DataFrame back to the database.
    data_manager.save_jobs_to_db(combined_df)

    print("\nScraping and classification process complete!")

# Standard Python entry point to run the main function when the script is executed.
if __name__ == "__main__":
    main()