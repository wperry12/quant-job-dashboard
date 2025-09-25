# location_normalizer.py
import pandas as pd
import re

def normalize_location_string(raw_location, location_map):
    """
    Cleans a raw location string and maps it to a list of standardized locations.

    This function takes a free-text location string (e.g., "New York / London (Remote)")
    and a pre-built mapping dictionary to produce a clean, sorted list of
    standardized locations (e.g., ['London', 'New York']).

    Args:
        raw_location: The raw location string from the job posting.
        location_map: A dictionary mapping lowercase location aliases to their
                      proper, standardized names (e.g., {'nyc': 'New York'}).

    Returns:
        A sorted list of standardized location names found in the raw string.
    """
    # Handle cases where the input is not a valid string or is empty.
    if not isinstance(raw_location, str) or pd.isna(raw_location) or not raw_location.strip():
        return ["Not specified"]

    # Use a set to automatically handle and store unique locations.
    found_locations = set()
    
    # Split the raw string into fragments using common delimiters like slashes,
    # commas, semicolons, or the words 'and'/'or'.
    fragments = re.split(r'\s*[/|,;]\s*|\s+(?:and|or)\s+', raw_location.lower())

    # Process each fragment to find a matching standardized location.
    for fragment in fragments:
        # First, clean the fragment by removing parenthetical text and common,
        # non-specific keywords like 'hybrid' or 'remote'.
        clean_fragment = re.sub(r'\(.*?\)|hybrid|remote|office', '', fragment).strip()

        # Skip empty fragments that result from the cleaning process.
        if not clean_fragment:
            continue

        matched = False
        # --- Multi-stage Matching Logic ---
        
        # 1. Attempt an exact match first for highest accuracy.
        if clean_fragment in location_map:
            found_locations.add(location_map[clean_fragment])
            matched = True
        else:
            # 2. If no exact match, fall back to a substring search.
            # This handles cases like "London, UK" where a known key ("london") is part of the fragment.
            for map_key, proper_name in location_map.items():
                if map_key in clean_fragment:
                    found_locations.add(proper_name)
                    matched = True
        
        # 3. If no standardized location was found, use the cleaned fragment as a fallback.
        # This captures locations that may not be in our predefined map.
        if not matched:
            found_locations.add(clean_fragment.title())

    # If after all processing no locations were found, return a default value.
    if not found_locations:
        return ["Not specified"]
        
    # Convert the set of found locations to a list and sort it alphabetically for consistent output.
    return sorted(list(found_locations))