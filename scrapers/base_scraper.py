# scrapers/base_scraper.py
from abc import ABC, abstractmethod
from typing import List, Dict
from models import Job

class BaseScraper(ABC):
    """Abstract base class for all job board scrapers."""
    
    def __init__(self, company_id: str, company_name: str, config: Dict):
        self.company_id = company_id
        self.company_name = company_name
        self.config = config
        self.base_headers = {'User-Agent': 'Python Job Scraper/1.0'}

    @abstractmethod
    def scrape(self, existing_jobs: Dict[str, str]) -> List[Job]:
        """
        The main method to scrape jobs.
        It should return a list of Job objects.
        `existing_jobs` is a dict mapping (external_id) -> first_posted_date
        to preserve historical posting dates.
        """
        pass