# scrapers/greenhouse.py
import requests
from typing import List, Dict
from datetime import datetime
from .base_scraper import BaseScraper
from models import Job

class GreenhouseScraper(BaseScraper):
    def scrape(self, existing_jobs: Dict[str, str]) -> List[Job]:
        board_token = self.config.get("board_token")
        if not board_token:
            print(f"No board_token for {self.company_name}")
            return []

        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        print(f"Fetching jobs for {self.company_name} from {url}...")
        
        try:
            response = requests.get(url, headers=self.base_headers, timeout=20)
            response.raise_for_status()
            api_jobs = response.json().get("jobs", [])
            
            scraped_jobs = [self._normalize_job(job, existing_jobs) for job in api_jobs]
            print(f"Found {len(scraped_jobs)} jobs for {self.company_name}")
            return scraped_jobs
            
        except requests.RequestException as e:
            print(f"HTTP Error scraping {self.company_name}: {e}")
            return []

    def _normalize_job(self, job: Dict, existing_jobs: Dict[str, str]) -> Job:
        external_id = str(job['id'])
        meta = {m['name']: m['value'] for m in job.get('metadata', []) or []}
        
        return Job(
            external_id=external_id,
            company_id=self.company_id,
            company_name=self.company_name,
            title=job['title'],
            url=job['absolute_url'],
            location=job.get('location', {}).get('name'),
            category=meta.get('Job Category'),
            seniority=meta.get('Worker Sub Type'),
            first_posted=existing_jobs.get(external_id, job.get('first_published_at', job.get('updated_at'))),
            last_updated=job.get('updated_at'),
            last_scraped_at=datetime.now().isoformat()
        )