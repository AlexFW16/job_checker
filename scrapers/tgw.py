import re

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job

TGW_URL = "https://www.tgw-group.com/en/career/jobs"


class TGWScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "tgw"

    def fetch_jobs(self) -> list[Job]:
        html = self._fetch_page()
        return self._parse_jobs(html)

    def _fetch_page(self) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; JobChecker/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        resp = requests.get(TGW_URL, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _parse_jobs(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        current_country = ""

        fade_container = soup.find("div", class_="fadeContainer")
        if not fade_container:
            return jobs

        for child in fade_container.children:
            if not hasattr(child, "name") or not child.name:
                continue

            classes = child.get("class", [])

            if "countryHeader" in classes:
                current_country = child.get_text(strip=True)
                continue

            if "jobWrapper" in classes:
                for job_link in child.find_all("a", class_="jobItem"):
                    parts = job_link.find_all("div", class_="jobListPart")
                    if len(parts) >= 4:
                        location = re.sub(
                            r"\s+", " ", parts[1].get_text(strip=True)
                        )
                        jobs.append(
                            Job(
                                title=parts[0].get_text(strip=True),
                                location=location,
                                country=current_country,
                                category=parts[2].get_text(strip=True),
                                experience_level=parts[3].get_text(strip=True),
                                source=self.name,
                                url=job_link.get("href", ""),
                            )
                        )

        return jobs
