# scrapers/workable.py
import requests
from typing import List, Dict
from datetime import datetime
from .base_scraper import BaseScraper
from models import Job

class WorkableScraper(BaseScraper):
    def scrape(self, existing_jobs: Dict[str, str]) -> List[Job]:
        subdomain = self.config.get("subdomain")
        if not subdomain:
            print(f"No subdomain configured for {self.company_name}")
            return []

        url = f"https://apply.workable.com/api/v1/widget/accounts/{subdomain}"
        print(f"Fetching jobs for {self.company_name} from {url}...")
        
        try:
            response = requests.get(url, headers=self.base_headers, timeout=20)
            response.raise_for_status()
            api_jobs = response.json().get("jobs", [])
            
            scraped_jobs = [self._normalize_job(job, existing_jobs, subdomain) for job in api_jobs]
            print(f"Found {len(scraped_jobs)} jobs for {self.company_name}")
            return scraped_jobs
            
        except requests.RequestException as e:
            print(f"HTTP Error scraping {self.company_name}: {e}")
            return []

    def _normalize_job(self, job: Dict, existing_jobs: Dict[str, str], subdomain: str) -> Job:
        external_id = job['shortcode']
        location_dict = job.get('location', {})
        city = location_dict.get('city', '')
        country = location_dict.get('country', '')
        location = ', '.join(filter(None, [city, country])) or 'Remote' if job.get('remote') else None

        return Job(
            external_id=external_id,
            company_id=self.company_id,
            company_name=self.company_name,
            title=job['title'],
            url=f"https://apply.workable.com/{subdomain}/j/{external_id}/",
            location=location,
            category=job.get('department'),
            seniority=job.get('type'),
            first_posted=existing_jobs.get(external_id, job.get('published_on', datetime.now().isoformat())),
            last_updated=job.get('updated_on', datetime.now().isoformat()),
            last_scraped_at=datetime.now().isoformat()
        )