import re

from matching import EUROPEAN_COUNTRIES
from scrapers.base import BaseScraper, Job
from scrapers.common import cap_jobs, fetch_json, is_valid_job_title


class GreenhouseScraper(BaseScraper):
    """Greenhouse public job-board API, limited to Austria or European remote roles."""

    def __init__(self, board_token: str, source_name: str, company: str):
        self.board_token = board_token
        self.source_name = source_name
        self.company = company
        self.api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
        self.job_base = f"https://job-boards.greenhouse.io/{board_token}/jobs"

    @property
    def name(self) -> str:
        return self.source_name

    def fetch_jobs(self) -> list[Job]:
        try:
            data = fetch_json(self.api_url)
            return cap_jobs(self._parse_results(data))
        except Exception:
            return []

    def _parse_results(self, data: dict) -> list[Job]:
        if not isinstance(data, dict):
            return []
        jobs = []
        seen = set()
        for entry in data.get("jobs", []) or []:
            title = (entry.get("title") or "").strip()
            if not is_valid_job_title(title):
                continue
            location = ((entry.get("location") or {}).get("name") or "").strip()
            remote = bool(re.search(r"\bremote\b", location, re.I))
            countries = sorted(
                (
                    country
                    for country in EUROPEAN_COUNTRIES
                    if re.search(rf"\b{re.escape(country)}\b", location, re.I)
                ),
                key=lambda country: location.lower().find(country.lower()),
            )
            european_region = bool(re.search(r"\b(europe|emea|eu)\b", location, re.I))
            if remote and not countries and not european_region:
                continue
            if not remote and not re.search(r"\baustria\b", location, re.I):
                continue

            country = "Austria" if "Austria" in countries else (countries[0] if countries else "")
            job_id = entry.get("id")
            url = entry.get("absolute_url") or (f"{self.job_base}/{job_id}" if job_id else "")
            key = job_id or url
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            jobs.append(
                Job(
                    title=title,
                    location=location or (countries[0] if countries else ""),
                    country=country,
                    category="",
                    experience_level="",
                    source=self.name,
                    url=url,
                    company=self.company,
                    raw={"id": job_id or ""},
                )
            )
        return jobs


class GitLabScraper(GreenhouseScraper):
    """GitLab's all-remote Greenhouse board; keeps European postings only."""

    def __init__(self):
        super().__init__("gitlab", "gitlab", "GitLab")
