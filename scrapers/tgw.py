import re

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job
from scrapers.common import build_url, cap_jobs, fetch_html, is_valid_job_title

TGW_URL = "https://www.tgw-group.com/en/career/jobs"


class TGWScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "tgw"

    def fetch_jobs(self) -> list[Job]:
        try:
            html = fetch_html(TGW_URL, retries=2)
            return self._parse_jobs(html)
        except Exception:
            return []

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
                        title = parts[0].get_text(strip=True)
                        if not is_valid_job_title(title):
                            continue
                        location = re.sub(r"\s+", " ", parts[1].get_text(strip=True))
                        jobs.append(
                            Job(
                                title=title,
                                location=location,
                                country=current_country,
                                category=parts[2].get_text(strip=True),
                                experience_level=parts[3].get_text(strip=True),
                                source=self.name,
                                url=build_url(TGW_URL, job_link.get("href", "")),
                            )
                        )

        return cap_jobs(jobs)