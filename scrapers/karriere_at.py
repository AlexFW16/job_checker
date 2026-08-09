import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job
from scrapers.common import cap_jobs, is_valid_job_title

SEARCH_URL = "https://www.karriere.at/jobs/softwareentwicklung/ober%C3%B6sterreich"


class KarriereAtScraper(BaseScraper):
    """Austrian job board - covers many companies including Linz area."""

    SEARCH_URL = SEARCH_URL
    MAX_PAGES = 3

    @property
    def name(self) -> str:
        return "karriere.at"

    def fetch_jobs(self) -> list[Job]:
        jobs = []
        for page in range(1, self.MAX_PAGES + 1):
            url = f"{self.SEARCH_URL}?page={page}"
            try:
                resp = requests.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=30,
                )
                resp.raise_for_status()
            except Exception:
                break
            batch = self._parse_listing(resp.text)
            if not batch:
                break
            jobs.extend(batch)
        return cap_jobs(jobs)

    def _parse_listing(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for item in soup.find_all(class_=re.compile(r"m-jobsListItem", re.I)):
            title_el = item.find(class_=re.compile(r"m-jobsListItem__title", re.I))
            if not title_el:
                title_el = item.find(["h2", "h3"])
            title = title_el.get_text(" ", strip=True) if title_el else ""
            if not is_valid_job_title(title):
                continue

            link_el = item.find("a", href=True)
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://www.karriere.at", url)

            company_el = item.find(class_=re.compile(r"employer|company|firma", re.I))
            company = company_el.get_text(" ", strip=True) if company_el else ""

            location_el = item.find(class_=re.compile(r"m-jobsListItem__location", re.I))
            if not location_el:
                location_el = item.find(class_=re.compile(r"location|standort", re.I))
            location = location_el.get_text(" ", strip=True) if location_el else ""
            location = re.sub(r"[\s,;]+$", "", location)

            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country="Austria",
                    category=company,
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )
        return jobs