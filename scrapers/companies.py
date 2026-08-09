import json
import re
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job
from scrapers.common import (
    build_url,
    cap_jobs,
    fetch_html,
    fetch_json,
    is_valid_job_title,
    parse_erecruiter_jobs,
)

AUSTRIAN_CITIES = (
    "austria|österreich|wien|vienna|linz|graz|villach|salzburg|klagenfurt|innsbruck"
    "|steyr|hagenberg|marchtrenk|wels|leonding|traun|pasching|ansfelden"
)


def _guess_category(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["software", "developer", "entwickl", "programm", "ai", "data", "it/", "engineer"]):
        return "Development / Software / IT"
    if any(k in t for k in ["masterarbeit", "bach", "thesis", "intern", "stud", "research", "forschung"]):
        return "Research"
    if any(k in t for k in ["consultant", "product manager", "project", "management"]):
        return "Project Management"
    if any(k in t for k in ["lehrling", "apprentice", "ausbildung", "lehre"]):
        return "Apprenticeship"
    return "Other"


class SCCHScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "scch"

    def fetch_jobs(self) -> list[Job]:
        try:
            html = fetch_html("https://www.scch.at/karriere/offene-positionen/")
            return self._parse_jobs(html)
        except Exception:
            return []

    def _parse_jobs(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        container = soup.find(class_=re.compile(r"job-list", re.I))
        if container:
            for a in container.find_all("a", href=True):
                href = a.get("href", "")
                if not re.search(r"detail|position|job", href, re.I):
                    continue
                title = a.get_text(strip=True)
                if not is_valid_job_title(title):
                    continue
                jobs.append(
                    Job(
                        title=title,
                        location="Hagenberg, Austria",
                        country="Austria",
                        category=_guess_category(title),
                        experience_level="",
                        source=self.name,
                        url=build_url("https://www.scch.at", href),
                    )
                )
        return cap_jobs(jobs)


class RISCRScraper(BaseScraper):
    WP_API = "https://career.risc-software.at/wp-json/wp/v2/job"

    @property
    def name(self) -> str:
        return "risc"

    def fetch_jobs(self) -> list[Job]:
        try:
            data = fetch_json(f"{self.WP_API}?per_page=100&status=publish")
            jobs = self._parse_api_jobs(data)
            if jobs:
                return cap_jobs(jobs)
        except Exception:
            pass
        try:
            html = fetch_html("https://career.risc-software.at/en/")
            return self._parse_featured_jobs(html)
        except Exception:
            return []

    def _parse_api_jobs(self, data: list | dict) -> list[Job]:
        if not isinstance(data, list):
            return []
        jobs = []
        for item in data:
            title = item.get("title", {})
            title = title.get("rendered", "") if isinstance(title, dict) else title
            if not is_valid_job_title(title):
                continue
            jobs.append(
                Job(
                    title=title,
                    location="",
                    country="Austria",
                    category=_guess_category(title),
                    experience_level="",
                    source=self.name,
                    url=item.get("link", ""),
                    raw=item,
                )
            )
        return jobs

    def _parse_featured_jobs(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for card in soup.find_all(class_=re.compile(r"\bposition\b", re.I)):
            title = card.get_text(strip=True)
            if not is_valid_job_title(title):
                continue
            link = card.find("a", href=True)
            jobs.append(
                Job(
                    title=title,
                    location="Hagenberg, Austria",
                    country="Austria",
                    category=_guess_category(title),
                    experience_level="",
                    source=self.name,
                    url=build_url("https://career.risc-software.at", link.get("href", "")) if link else "",
                )
            )
        return cap_jobs(jobs)


class SALScraper(BaseScraper):
    """Silicon Austria Labs - uses Personio ATS."""

    @property
    def name(self) -> str:
        return "sal"

    def fetch_jobs(self) -> list[Job]:
        try:
            html = fetch_html(
                "https://silicon-austria-labs.jobs.personio.de/?language=en",
                retries=3,
            )
            return self._parse_html_jobs(html)
        except Exception:
            return []

    def _parse_html_jobs(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "job" not in href.lower():
                continue
            title = a.get_text(strip=True)
            if not is_valid_job_title(title) or title in seen:
                continue
            seen.add(title)
            container = a.find_parent("li") or a.find_parent("div")
            location = ""
            if container:
                for el in container.find_all(class_=re.compile(r"location|data-location", re.I)):
                    location = el.get_text(strip=True)
                    if location:
                        break
            country = "Austria" if re.search(AUSTRIAN_CITIES, f"{location} {a.get_text(strip=True)}", re.I) else ""
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category=_guess_category(title),
                    experience_level="",
                    source=self.name,
                    url=build_url("https://silicon-austria-labs.jobs.personio.de", href),
                )
            )
        return cap_jobs(jobs)


class AITScraper(BaseScraper):
    """AIT - uses eRecruiter ATS; reads the embedded job model from the page."""

    BASE_URL = "https://jobs.ait.ac.at"

    @property
    def name(self) -> str:
        return "ait"

    def fetch_jobs(self) -> list[Job]:
        try:
            html = fetch_html(f"{self.BASE_URL}/Jobs")
            jobs = parse_erecruiter_jobs(html, self.BASE_URL)
            for job in jobs:
                job.source = self.name
            return cap_jobs(jobs)
        except Exception:
            return []


class AVLLScraper(BaseScraper):
    """AVL - SAP SuccessFactors; scrapes the server-rendered search result table."""

    SEARCH_URL = "https://jobs.avl.com/careers/search"

    @property
    def name(self) -> str:
        return "avl"

    def fetch_jobs(self) -> list[Job]:
        jobs = []
        seen = set()
        for page in range(1, 6):
            url = f"{self.SEARCH_URL}?page={page}&location=austria"
            try:
                html = fetch_html(url)
            except Exception:
                break
            batch = self._parse_page(html)
            if not batch:
                break
            new_jobs = []
            for job in batch:
                key = (job.title.lower(), job.url)
                if key in seen:
                    continue
                seen.add(key)
                new_jobs.append(job)
            if not new_jobs:
                break
            jobs.extend(new_jobs)
        return cap_jobs(jobs)

    def _parse_page(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            title_cell = cells[1]
            link = title_cell.find("a", href=True)
            title = re.sub(r"\s+", " ", link.get_text(" ", strip=True)) if link else re.sub(r"\s+", " ", title_cell.get_text(" ", strip=True))
            if not is_valid_job_title(title):
                continue
            location = re.sub(r"\s+", " ", cells[2].get_text(" ", strip=True))
            if not re.search(r"\bat\b|austria|graz|steyr|österreich|wien|vienna", location, re.I):
                continue
            url = build_url("https://jobs.avl.com", link.get("href", "")) if link else ""
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country="Austria",
                    category=cells[3].get_text(" ", strip=True) if len(cells) > 3 else "",
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )
        return jobs


class KEBAScraper(BaseScraper):
    """KEBA - uses eRecruiter ATS; reads the embedded job model from the page."""

    BASE_URL = "https://jobs.keba.com"

    @property
    def name(self) -> str:
        return "keba"

    def fetch_jobs(self) -> list[Job]:
        try:
            html = fetch_html(f"{self.BASE_URL}/")
            jobs = parse_erecruiter_jobs(html, self.BASE_URL)
            for job in jobs:
                job.source = self.name
            return cap_jobs(jobs)
        except Exception:
            return []


class InfineonScraper(BaseScraper):
    """Infineon - Workday career site renders jobs client-side; no public feed found.
    Kept as a no-op that returns no jobs rather than garbage."""

    @property
    def name(self) -> str:
        return "infineon"

    def fetch_jobs(self) -> list[Job]:
        return []


class PrimetalsScraper(BaseScraper):
    """Primetals - uses eRecruiter ATS; reads the embedded job model from the page."""

    BASE_URL = "https://jobs.primetals.com"

    @property
    def name(self) -> str:
        return "primetals"

    def fetch_jobs(self) -> list[Job]:
        try:
            html = fetch_html(f"{self.BASE_URL}/")
            jobs = parse_erecruiter_jobs(html, self.BASE_URL)
            for job in jobs:
                job.source = self.name
            return cap_jobs(jobs)
        except Exception:
            return []


class LAMResearchScraper(BaseScraper):
    """LAM Research - Phenom career site renders jobs client-side; no public feed found.
    Kept as a no-op that returns no jobs rather than garbage."""

    @property
    def name(self) -> str:
        return "lam"

    def fetch_jobs(self) -> list[Job]:
        return []


class SiemensScraper(BaseScraper):
    """Siemens - AvaPortal careers site renders jobs client-side; no public feed found.
    Kept as a no-op that returns no jobs rather than garbage."""

    @property
    def name(self) -> str:
        return "siemens"

    def fetch_jobs(self) -> list[Job]:
        return []


class SynopsysScraper(BaseScraper):
    """Synopsys - TalentBrew RSS feed; keeps jobs mentioning Austrian cities."""

    RSS_URL = "https://careers.synopsys.com/rss"

    @property
    def name(self) -> str:
        return "synopsys"

    def fetch_jobs(self) -> list[Job]:
        try:
            xml_text = fetch_html(self.RSS_URL, retries=1)
            return self._parse_rss(xml_text)
        except Exception:
            return []

    def _parse_rss(self, xml_text: str) -> list[Job]:
        from scrapers.common import parse_rss_items

        jobs = []
        for item in parse_rss_items(xml_text):
            title = item.findtext("title") or ""
            if not is_valid_job_title(title):
                continue
            if not re.search(AUSTRIAN_CITIES, title, re.I):
                continue
            link = item.findtext("link") or ""
            jobs.append(
                Job(
                    title=title,
                    location="",
                    country="Austria",
                    category=_guess_category(title),
                    experience_level="",
                    source=self.name,
                    url=link,
                )
            )
        return cap_jobs(jobs)


class VoestalpineScraper(BaseScraper):
    """voestalpine - beeSITE Global JobBoard (GJB) JSON API.

    The search endpoint ignores common pagination params; it honours the
    frontend search payload (GET ?data=<json>) with SearchParameters.CountItem.
    Request CountItem=10000 to pull the full result set, then filter for Austria.
    """

    BASE_URL = "https://voestalpine-beesite-production-gjb.app.beesite.de"
    SEARCH_URL = f"{BASE_URL}/search/"

    MATCHED_OBJECT_DESCRIPTOR = [
        "ID",
        "PositionTitle",
        "PositionURI",
        "PositionLocation.CountryName",
        "PositionLocation.CityName",
        "JobCategory.Name",
        "CareerLevel.Name",
        "ParentOrganizationName",
    ]

    @property
    def name(self) -> str:
        return "voestalpine"

    def fetch_jobs(self) -> list[Job]:
        try:
            data = fetch_json(self._search_url())
            return self._parse_results(data)
        except Exception:
            return []

    def _search_url(self) -> str:
        payload = {
            "LanguageCode": "DE",
            "SearchParameters": {
                "FirstItem": 1,
                "CountItem": 10000,
                "Sort": [{"Criterion": "PublicationStartDate", "Direction": "DESC"}],
                "MatchedObjectDescriptor": self.MATCHED_OBJECT_DESCRIPTOR,
            },
            "SearchCriteria": [],
        }
        return f"{self.SEARCH_URL}?{urlencode({'data': json.dumps(payload)})}"

    def _parse_results(self, data: dict) -> list[Job]:
        result = data.get("SearchResult", {})
        jobs = []
        for item in result.get("SearchResultItems", []):
            desc = item.get("MatchedObjectDescriptor", {})
            title = desc.get("PositionTitle", "")
            if not is_valid_job_title(title):
                continue
            locations = desc.get("PositionLocation", [])
            if not isinstance(locations, list):
                locations = [locations]
            country_names = [loc.get("CountryName", "") for loc in locations]
            if not any(re.search(r"österreich|austria", c, re.I) for c in country_names):
                continue
            city_names = [loc.get("CityName", "") for loc in locations]
            location = ", ".join(dict.fromkeys([x for x in city_names + country_names if x]))
            category = self._first_name(desc.get("JobCategory"))
            experience_level = self._first_name(desc.get("CareerLevel"))
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country="Austria",
                    category=category,
                    experience_level=experience_level,
                    source=self.name,
                    url=desc.get("PositionURI", ""),
                    raw=desc,
                )
            )
        return cap_jobs(jobs)

    @staticmethod
    def _first_name(value) -> str:
        if not value:
            return ""
        if isinstance(value, list):
            return value[0].get("Name", "") if value and isinstance(value[0], dict) else ""
        if isinstance(value, dict):
            return value.get("Name", "")
        return str(value)