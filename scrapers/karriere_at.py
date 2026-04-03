import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job


class KarriereAtScraper(BaseScraper):
    """Austrian job board - covers many companies including Linz area."""

    SEARCH_URL = "https://www.karriere.at/jobs/softwareentwicklung/ober%C3%B6sterreich"

    @property
    def name(self) -> str:
        return "karriere.at"

    def fetch_jobs(self) -> list[Job]:
        try:
            return self._fetch_page()
        except Exception:
            return []

    def _fetch_page(self) -> list[Job]:
        resp = requests.get(
            self.SEARCH_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []

        for item in soup.find_all(class_=re.compile(r"search-result|job-item|serp-item", re.I)):
            title_el = item.find(class_=re.compile(r"title|titel|job-title", re.I))
            if not title_el:
                title_el = item.find(["h2", "h3"])
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            link_el = item.find("a", href=re.compile(r"/job/", re.I))
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://www.karriere.at", url)

            company_el = item.find(class_=re.compile(r"company|firma|employer", re.I))
            company = company_el.get_text(strip=True) if company_el else ""

            location_el = item.find(class_=re.compile(r"location|standort|city|place", re.I))
            location = location_el.get_text(strip=True) if location_el else ""

            country = "Austria"

            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category=company,
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )

        return jobs
