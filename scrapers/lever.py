# scrapers/lever.py
import requests
from typing import List, Dict
from datetime import datetime
from .base_scraper import BaseScraper
from models import Job

class LeverScraper(BaseScraper):
    def scrape(self, existing_jobs: Dict[str, str]) -> List[Job]:
        site = self.config.get("site")
        if not site:
            print(f"🚨 No site configured for {self.company_name}")
            return []
            
        url = f"https://api.lever.co/v0/postings/{site}?mode=json"
        print(f"Fetching jobs for {self.company_name} from {url}...")
        
        try:
            response = requests.get(url, headers=self.base_headers, timeout=20)
            response.raise_for_status()
            api_jobs = response.json()
            
            scraped_jobs = [self._normalize_job(job, existing_jobs) for job in api_jobs]
            print(f"Found {len(scraped_jobs)} jobs for {self.company_name}")
            return scraped_jobs
            
        except requests.RequestException as e:
            print(f"HTTP Error scraping {self.company_name}: {e}")
            return []

    def _normalize_job(self, job: Dict, existing_jobs: Dict[str, str]) -> Job:
        external_id = job['id']
        categories = job.get('categories', {})
        
        return Job(
            external_id=external_id,
            company_id=self.company_id,
            company_name=self.company_name,
            title=job['text'],
            url=job['hostedUrl'],
            location=categories.get('location'),
            category=categories.get('team'),
            seniority=categories.get('commitment'),
            first_posted=existing_jobs.get(external_id, datetime.fromtimestamp(job['createdAt'] / 1000).isoformat()),
            last_updated=datetime.fromtimestamp(job.get('updatedAt', job['createdAt']) / 1000).isoformat(),
            last_scraped_at=datetime.now().isoformat()
        )