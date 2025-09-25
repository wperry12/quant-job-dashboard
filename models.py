# models.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Job:
    """A standardized dataclass for a job posting."""
    external_id: str
    company_id: str
    company_name: str
    title: str
    url: str
    location: Optional[str] = None
    category: Optional[str] = None
    seniority: Optional[str] = None
    first_posted: Optional[str] = None
    last_updated: Optional[str] = None
    last_scraped_at: Optional[str] = None
    classified_role_id: Optional[str] = field(default=None, repr=False)
    classified_seniority_id: Optional[str] = field(default=None, repr=False)