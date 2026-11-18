import json
import re
from html import unescape

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job
from scrapers.common import build_url, cap_jobs, fetch_html, fetch_json, is_valid_job_title


class A1Scraper(BaseScraper):
    """A1 Group WordPress jobs API (official jobs.a1.com feed)."""

    SEARCH_URL = "https://jobs.a1.com/de/wp-json/a1-group/v1/filter-jobs?country=austria"
    MAX_PAGES = 50

    @property
    def name(self) -> str:
        return "a1"

    def fetch_jobs(self) -> list[Job]:
        jobs = []
        seen = set()
        requested_urls = set()
        url = self.SEARCH_URL
        for _ in range(self.MAX_PAGES):
            if not url or url in requested_urls:
                break
            requested_urls.add(url)
            try:
                data = fetch_json(url)
            except Exception:
                break
            for item in self._parse_response(data):
                key = item.url or item.raw.get("id")
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                jobs.append(item)
            next_url = data.get("nextPageUrl") if isinstance(data, dict) else None
            url = build_url(self.SEARCH_URL, next_url) if next_url else ""
        return cap_jobs(jobs)

    def _parse_response(self, data: dict) -> list[Job]:
        if not isinstance(data, dict):
            return []
        jobs = []
        for item in data.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            title = unescape(item.get("title") or "").strip()
            if not is_valid_job_title(title):
                continue
            job_type = item.get("type") or {}
            jobs.append(
                Job(
                    title=title,
                    location=unescape(item.get("location") or item.get("dataLocation") or ""),
                    country="Austria",
                    category=unescape(job_type.get("category") or ""),
                    experience_level=unescape(job_type.get("timeType") or ""),
                    source=self.name,
                    url=item.get("url") or "",
                    company=unescape(item.get("company") or item.get("dataCompany") or ""),
                    raw={"id": item.get("id") or ""},
                )
            )
        return jobs


class FrequentisScraper(BaseScraper):
    """Frequentis Avature server-rendered job cards, including Vienna postings."""

    BASE_URL = "https://jobs.frequentis.com"
    JOBS_URL = f"{BASE_URL}/careers/SearchJobs/"
    PAGE_SIZE = 20
    MAX_PAGES = 15

    @property
    def name(self) -> str:
        return "frequentis"

    def fetch_jobs(self) -> list[Job]:
        jobs = []
        seen = set()
        for page in range(self.MAX_PAGES):
            url = self.JOBS_URL if page == 0 else f"{self.JOBS_URL}?jobOffset={page * self.PAGE_SIZE}"
            try:
                html_text = fetch_html(url)
            except Exception:
                break
            batch, has_next = self._parse_page(html_text)
            new_jobs = [job for job in batch if job.url not in seen]
            jobs.extend(new_jobs)
            seen.update(job.url for job in new_jobs)
            if not has_next or not new_jobs:
                break
        return cap_jobs(jobs)

    def _parse_response(self, html_text: str) -> list[Job]:
        jobs, _ = self._parse_page(html_text)
        return jobs

    def _parse_page(self, html_text: str) -> tuple[list[Job], bool]:
        soup = BeautifulSoup(html_text, "html.parser")
        jobs = []
        for item in soup.select("ul.list--jobs > li.list__item"):
            link = item.select_one(".list__item__text__title a[href*='/JobDetail/']")
            subtitle = item.select_one(".list__item__text__subtitle")
            if not link or not subtitle:
                continue
            title = link.get_text(" ", strip=True)
            if not is_valid_job_title(title):
                continue
            parts = [
                part.strip()
                for part in subtitle.get_text(" ", strip=True).split("|")
                if part.strip()
            ]
            if len(parts) < 4:
                continue
            category = " | ".join(parts[:-3])
            country, location, company = parts[-3:]
            url = build_url(self.BASE_URL, link.get("href", ""))
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category=category,
                    experience_level="",
                    source=self.name,
                    url=url,
                    company=company,
                    raw={"id": url.rstrip("/").rsplit("/", 1)[-1]},
                )
                # The teaser is not a full posting; leave description empty so
                # domain-focused enrichment can fetch the detail page.
            )
        has_next = any(
            "joboffset=" in link.get("href", "").lower()
            and "next" in link.get_text(" ", strip=True).lower()
            for link in soup.find_all("a")
        )
        return jobs, has_next


class WienEnergieScraper(BaseScraper):
    """Wien Energie d.vinci job list with an embedded DvinciData JSON model."""

    JOBS_URL = "https://jobs.wienerstadtwerke.at/de/p/WienEnergie/jobs"

    @property
    def name(self) -> str:
        return "wien_energie"

    def fetch_jobs(self) -> list[Job]:
        try:
            return cap_jobs(self._parse_response(fetch_html(self.JOBS_URL)))
        except Exception:
            return []

    def _parse_response(self, html_text: str) -> list[Job]:
        data = None
        soup = BeautifulSoup(html_text, "html.parser")
        for script in soup.find_all("script"):
            text = script.get_text().strip()
            if "var DvinciData" not in text:
                continue
            match = re.search(r"var\s+DvinciData\s*=\s*(\{.*\})\s*;?\s*$", text, re.S)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    return []
                break
        if not isinstance(data, dict):
            return []

        jobs = []
        for publication in data.get("jobPublications", []) or []:
            if not isinstance(publication, dict):
                continue
            opening = publication.get("jobOpening") or {}
            title = (publication.get("position") or publication.get("pageTitle") or "").strip()
            if not is_valid_job_title(title):
                continue
            locations = opening.get("locations") or []
            location = self._location_text(opening, locations)
            country = "Austria" if self._is_austria(locations) else ""
            company = (opening.get("company") or {}).get("name") or (
                (opening.get("orgUnit") or {}).get("name") or "Wien Energie"
            )
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category=", ".join(
                        category.get("name", "")
                        for category in opening.get("categories", [])
                        if category.get("name")
                    ),
                    experience_level=", ".join(
                        group.get("name", "")
                        for group in opening.get("targetGroups", [])
                        if group.get("name")
                    ),
                    source=self.name,
                    url=publication.get("jobPublicationURL") or "",
                    company=company,
                    raw={
                        "id": publication.get("id") or "",
                        "reference": opening.get("reference") or "",
                    },
                )
            )
        return jobs

    @staticmethod
    def _location_text(opening: dict, locations: list[dict]) -> str:
        location = opening.get("location") or " / ".join(
            item.get("name", "") for item in locations if item.get("name")
        )
        for item in locations:
            city = ((item.get("address") or {}).get("city") or "").strip()
            if city and city.lower() not in location.lower():
                location = f"{location}, {city}" if location else city
        return location

    @staticmethod
    def _is_austria(locations: list[dict]) -> bool:
        for item in locations:
            country = item.get("country") or {}
            address_country = (item.get("address") or {}).get("country") or {}
            if "AT" in (country.get("isoA2"), address_country.get("isoA2")):
                return True
        return False
