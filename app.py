# app.py
import streamlit as st
import pandas as pd
from pathlib import Path
import base64
import main as scraper_main
import data_manager 
from location_normalizer import normalize_location_string 

# --- Page Configuration ---
# Set the title, icon, and layout for the Streamlit page. This should be the first Streamlit command.
st.set_page_config(
    page_title="Job Scraper Dashboard",
    page_icon="🔎",
    layout="wide"
)

# --- Handle notifications across reruns ---
# Check if a scraping session has just completed.
# This uses session_state to persist the status across Streamlit's script reruns.
if "scraping_complete" in st.session_state:
    if st.session_state.scraping_complete:
        st.success("Scraping complete!")
    # Reset the flag to prevent the message from showing again on subsequent interactions.
    del st.session_state.scraping_complete

# --- Custom CSS ---
# Inject custom CSS for styling the job cards, filters, and overall layout.
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #1f77b4;
        --secondary-color: #ff7f0e;
        --background-color: #f8f9fa;
        --card-background: #ffffff;
        --text-color: #2c3e50;
        --border-color: #e1e8ed;
        --shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .job-card { background: var(--card-background); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: var(--shadow); transition: all 0.3s ease; position: relative; overflow: hidden; }
    .job-card:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,0,0,0.15); border-color: var(--primary-color); }
    .job-card:hover .job-title { color: var(--secondary-color); }
    .job-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)); }
    .job-header { display: flex; align-items: flex-start; gap: 1rem; }
    .company-logo { width: 60px; height: 60px; border-radius: 8px; object-fit: contain; flex-shrink: 0; border: 2px solid var(--border-color); }
    .logo-placeholder { width: 60px; height: 60px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #666; font-size: 1.2rem; font-weight: bold; flex-shrink: 0; border: 2px solid var(--border-color); }
    .job-info { flex: 1; min-width: 0; }
    .job-title { font-size: 1.3rem; font-weight: 600; color: var(--primary-color); margin-bottom: 0.5rem; line-height: 1.3; transition: color 0.3s ease; }
    .company-name { font-size: 1.1rem; font-weight: 500; color: #666; margin-bottom: 0.5rem; }
    .job-location { color: #888; font-size: 0.95rem; display: flex; align-items: center; gap: 0.3rem; }
    .job-tags { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1rem; }
    .job-tag { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.85rem; font-weight: 500; border: none; }
    .job-tag.role { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .job-tag.seniority { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    div[data-testid="stHorizontalBlock"] > div:last-child { display: flex; align-items: flex-end; }
    .empty-state { text-align: center; padding: 3rem; color: #666; }
    .empty-state-icon { font-size: 4rem; margin-bottom: 1rem; opacity: 0.5; }
</style>
""", unsafe_allow_html=True)

# --- Helper Function ---
@st.cache_data
def get_image_b64_with_mime(path):
    """Encodes a local image to base64 and determines its MIME type."""
    if not path or not Path(path).exists():
        return None, None
    try:
        ext = Path(path).suffix.lower().replace('.', '')
        mime_type = f"image/{ext}" if ext else "image/png"
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return mime_type, encoded
    except Exception as e:
        # Silently fail on image encoding errors to prevent app crashes.
        return None, None

# --- Data Loading and Transformation ---
# This function is cached to prevent reloading and reprocessing data on every interaction.
# The cache is set to expire after 1 hour (3600 seconds).
@st.cache_data(ttl=3600)
def load_and_prep_data():
    """Loads all necessary data from the database and prepares it for display."""
    # Load all data tables from the database using the data_manager.
    jobs_df = data_manager.load_table("jobs")
    companies_df = data_manager.load_table("companies")
    roles_df = data_manager.load_table("job_roles")
    experience_df = data_manager.load_table("experience_levels")
    locations_df = data_manager.load_table("job_locations")

    # Build the location map from the locations DataFrame for normalization.
    location_map = {}
    for _, row in locations_df.iterrows():
        proper_name = row['normalized_name']
        if pd.notna(proper_name):
            location_map[str(proper_name).lower()] = proper_name
        if 'aliases' in locations_df.columns and pd.notna(row['aliases']):
            aliases = str(row['aliases']).split('|')
            for alias in aliases:
                if alias.strip():
                    location_map[alias.strip().lower()] = proper_name

    # If there are no jobs, return empty DataFrames to avoid errors downstream.
    if jobs_df.empty:
        return pd.DataFrame(), pd.DataFrame(), companies_df, roles_df, experience_df

    # Filter for active jobs only (SQLite uses 1 for True).
    active_jobs = jobs_df[jobs_df['is_active'] == 1].copy()
    if active_jobs.empty:
        return pd.DataFrame(), pd.DataFrame(), companies_df, roles_df, experience_df

    # Process job locations for consistent display and filtering.
    active_jobs['clean_locations'] = active_jobs['location'].apply(lambda loc: normalize_location_string(loc, location_map))
    
    # Merge job data with company, role, and experience level data to get descriptive names.
    # After each merge, drop the redundant 'id' column from the right table ('id_y')
    # and rename the main job 'id' column back from 'id_x' to 'id'.
    merged_df = active_jobs.merge(
        companies_df[['id', 'name', 'logo_filename']].rename(columns={'name': 'company_name'}), 
        left_on='company_id', right_on='id', how='left'
    ).drop('id_y', axis=1).rename(columns={'id_x': 'id'})
    
    merged_df = merged_df.merge(
        roles_df[['id', 'title']].rename(columns={'title': 'role_name'}), 
        left_on='classified_role_id', right_on='id', how='left'
    ).drop('id_y', axis=1).rename(columns={'id_x': 'id'})

    # The final merge renames the original 'title' column to 'job_title' to avoid conflicts.
    merged_df = merged_df.merge(
        experience_df[['id', 'title']].rename(columns={'title': 'seniority_name'}), 
        left_on='classified_seniority_id', right_on='id', how='left'
    ).drop('id_y', axis=1).rename(columns={'id_x': 'id', 'title': 'job_title'})

    # Fill any missing (NaN) values with default text to avoid display issues.
    for col, default in {'company_name': 'Unknown Company', 'role_name': 'Unclassified', 'seniority_name': 'Unclassified'}.items():
        merged_df[col] = merged_df[col].fillna(default)
        
    # Create a comma-separated string of locations for display in the job card.
    merged_df['display_locations'] = merged_df['clean_locations'].apply(lambda locs: ', '.join(locs))
    
    # Create an "exploded" DataFrame where each job has a separate row for each location.
    # This makes filtering by location straightforward.
    exploded_df = merged_df.explode('clean_locations').rename(columns={'clean_locations': 'filter_location'})
    
    return merged_df, exploded_df, companies_df, roles_df, experience_df

# --- Main Application ---
# Load and prepare all the data required for the dashboard.
display_df, filter_df, companies_df, roles_df, experience_df = load_and_prep_data()

# --- Filters and Controls ---
# Main title for the application.
st.title("Job Listings")

# Create a layout with 5 columns for the filter widgets.
filter_cols = st.columns([2, 2, 2, 2, 1])

# Company filter dropdown.
with filter_cols[0]:
    # Populate options only with companies that have active jobs.
    if not display_df.empty:
        active_company_ids = display_df['company_id'].unique()
        company_options_df = companies_df[companies_df['id'].isin(active_company_ids)].sort_values('name')
        company_options = company_options_df.set_index('id')['name'].to_dict()
    else:
        company_options = {}
    selected_companies = st.multiselect("Company", options=list(company_options.keys()), format_func=lambda x: company_options.get(x), placeholder="Filter by company...", label_visibility="collapsed")

# Location filter dropdown.
with filter_cols[1]:
    # Populate options from the 'filter_location' column of the exploded DataFrame.
    if not filter_df.empty:
        location_options = sorted(filter_df['filter_location'].dropna().unique())
    else:
        location_options = []
    selected_locations = st.multiselect("Location", options=location_options, placeholder="Filter by location...", label_visibility="collapsed")

# Role filter dropdown.
with filter_cols[2]:
    role_options = roles_df.set_index('id')['title'].to_dict()
    selected_roles = st.multiselect("Role", options=list(role_options.keys()), format_func=lambda x: role_options.get(x), placeholder="Filter by role...", label_visibility="collapsed")

# Seniority filter dropdown.
with filter_cols[3]:
    seniority_options = experience_df.set_index('id')['title'].to_dict()
    selected_seniority = st.multiselect("Seniority", options=list(seniority_options.keys()), format_func=lambda x: seniority_options.get(x), placeholder="Filter by seniority...", label_visibility="collapsed")

# Scrape Jobs button.
with filter_cols[4]:
    if st.button("Scrape Jobs", type="primary", use_container_width=True):
        with st.spinner("Scraping for new jobs..."):
            # Execute the main scraping and classification script.
            scraper_main.main()
            # Clear the Streamlit cache to force a reload of the new data.
            st.cache_data.clear()
        # Set a flag to show a success message on the next rerun.
        st.session_state.scraping_complete = True
        # Force an immediate rerun of the app to display the new data.
        st.rerun()

# --- Filtering Logic ---
# Apply the selected filters to the main display DataFrame.
if not display_df.empty:
    filtered_display_df = display_df.copy()
    if selected_locations:
        # Use the exploded DataFrame to find jobs matching any of the selected locations.
        matching_ids = filter_df[filter_df['filter_location'].isin(selected_locations)]['id'].unique()
        filtered_display_df = filtered_display_df[filtered_display_df['id'].isin(matching_ids)]
    if selected_companies: 
        filtered_display_df = filtered_display_df[filtered_display_df['company_id'].isin(selected_companies)]
    if selected_roles: 
        filtered_display_df = filtered_display_df[filtered_display_df['classified_role_id'].isin(selected_roles)]
    if selected_seniority: 
        filtered_display_df = filtered_display_df[filtered_display_df['classified_seniority_id'].isin(selected_seniority)]
else:
    # If there's no data, create an empty DataFrame.
    filtered_display_df = pd.DataFrame()


# --- Display Jobs ---
st.markdown(f"--- \n ### Showing {len(filtered_display_df)} Jobs")

# Display a message if no jobs match the current filters.
if filtered_display_df.empty:
    st.markdown("<div class='empty-state'><div class='empty-state-icon'>🤷</div><h3>No jobs match filters</h3><p>Try adjusting your search or scraping for new jobs.</p></div>", unsafe_allow_html=True)
else:
    # Sort the jobs for a consistent display order.
    filtered_display_df = filtered_display_df.sort_values(by=['company_name', 'job_title'])
    assets_path = Path(__file__).parent / "assets"
    
    # Iterate through the filtered DataFrame and display each job as a styled card.
    for _, job in filtered_display_df.iterrows():
        logo_filename = job.get('logo_filename')
        # Encode the company logo to base64 to embed it directly in the HTML.
        mime_type, b64_data = get_image_b64_with_mime(assets_path / logo_filename if pd.notna(logo_filename) else None)
        
        # If a logo exists, create an <img> tag.
        if b64_data:
            logo_html = f'<img src="data:{mime_type};base64,{b64_data}" class="company-logo" alt="{job["company_name"]} logo">'
        # Otherwise, create a placeholder with the company's initials.
        else:
            initials = ''.join([word[0].upper() for word in job["company_name"].split()[:2]])
            logo_html = f'<div class="logo-placeholder">{initials}</div>'
        
        # Use st.markdown to render the HTML for the job card.
        st.markdown(f"""
        <a href="{job['url']}" target="_blank" style="text-decoration: none;">
            <div class="job-card">
                <div class="job-header">
                    {logo_html}
                    <div class="job-info">
                        <div class="job-title">{job['job_title']}</div>
                        <div class="company-name">{job['company_name']}</div>
                        <div class="job-location">📍 {job.get('display_locations', 'Not specified')}</div>
                        <div class="job-tags">
                            <span class="job-tag seniority">{job['seniority_name']}</span>
                            <span class="job-tag role">{job['role_name']}</span>
                        </div>
                    </div>
                </div>
            </div>
        </a>
        """, unsafe_allow_html=True)