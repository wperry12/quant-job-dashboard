# classifier.py
import pandas as pd

def classify_jobs(jobs_df: pd.DataFrame, role_keywords_df: pd.DataFrame, seniority_keywords_df: pd.DataFrame) -> pd.DataFrame:
    """
    Classifies jobs in the DataFrame based on keywords.

    This function takes a DataFrame of jobs and two DataFrames containing keywords
    for job roles and seniority levels. It attempts to match keywords against
    each job title to assign a role and seniority ID.

    Args:
        jobs_df: DataFrame containing the job listings to be classified.
        role_keywords_df: DataFrame with 'role_id', 'keyword', and 'priority' columns.
        seniority_keywords_df: DataFrame with 'seniority_id', 'keyword', and 'priority' columns.

    Returns:
        The input jobs_df with two new columns: 'classified_role_id' and
        'classified_seniority_id'.
    """
    # Return immediately if there are no jobs to process.
    if jobs_df.empty:
        return jobs_df

    print("\nStarting job classification...")

    # Create a temporary, lowercase version of the title for case-insensitive matching.
    jobs_df['title_lower'] = jobs_df['title'].str.lower().fillna('')

    # Sort keywords by priority to ensure that higher-priority keywords are checked first.
    # For example, "Senior Engineer" should match "Senior" before it matches "Engineer".
    role_keywords_df = role_keywords_df.sort_values('priority')
    seniority_keywords_df = seniority_keywords_df.sort_values('priority')

    def find_match(title: str, keywords_df: pd.DataFrame, id_column_name: str):
        """
        Iterates through keywords and returns the ID of the first match found in the title.
        
        Args:
            title: The lowercase job title string.
            keywords_df: The sorted DataFrame of keywords to search for.
            id_column_name: The name of the ID column ('role_id' or 'seniority_id') to return.
            
        Returns:
            The ID corresponding to the first keyword match, or None if no match is found.
        """
        for _, row in keywords_df.iterrows():
            keyword = str(row.get('keyword', '')).lower()
            if keyword in title:
                return row[id_column_name]
        return None

    # Apply the classification logic to each job title for both roles and seniority.
    # The .apply() method iterates over each row in the 'title_lower' Series.
    jobs_df['classified_role_id'] = jobs_df['title_lower'].apply(
        lambda title: find_match(title, role_keywords_df, 'role_id')
    )
    
    jobs_df['classified_seniority_id'] = jobs_df['title_lower'].apply(
        lambda title: find_match(title, seniority_keywords_df, 'seniority_id')
    )

    # For any job where a seniority level could not be determined, assign a default value.
    default_seniority_id = 'f4e0e33e-b8b2-4d9f-8216-29471f8e696f' # Corresponds to 'Experienced'
    jobs_df['classified_seniority_id'] = jobs_df['classified_seniority_id'].fillna(default_seniority_id)

    # Remove the temporary column as it's no longer needed.
    jobs_df = jobs_df.drop(columns=['title_lower'])

    # Calculate summary statistics for logging purposes.
    # Count how many jobs received either a role or a seniority classification.
    classified_count = jobs_df[['classified_role_id', 'classified_seniority_id']].notna().any(axis=1).sum()
    unclassified_role_count = jobs_df['classified_role_id'].isna().sum()

    # Print a summary of the classification results.
    print(f"Classification complete. {classified_count} of {len(jobs_df)} jobs were assigned a role or seniority.")
    print(f"There are {unclassified_role_count} jobs with an unclassified role.")

    return jobs_df