import json
import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from matching import EUROPEAN_COUNTRIES
from scrapers.base import BaseScraper, Job
from scrapers.common import (
    build_url,
    cap_jobs,
    fetch_html,
    fetch_json,
    fetch_json_post,
    is_valid_job_title,
    MAX_JOBS_PER_SCRAPER,
    parse_erecruiter_jobs,
)

AUSTRIAN_CITIES = (
    r"\b(?:austria|österreich|wien|vienna|linz|graz|villach|salzburg|klagenfurt|innsbruck"
    r"|steyr|hagenberg|marchtrenk|wels|leonding|traun|pasching|ansfelden)\b"
)

# EUROPEAN_COUNTRIES is shared with location matching in matching.py.

def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _has_word_prefix(text: str, terms: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(term)}", text, re.I) for term in terms)


def _guess_category(title: str) -> str:
    if _has_word_prefix(title, ["software", "developer", "entwickl", "programm", "ai", "data", "it/"]):
        return "Development / Software / IT"
    if _has_word_prefix(title, ["masterarbeit", "bach", "thesis", "intern", "stud", "research", "forschung"]):
        return "Research"
    if _has_word_prefix(title, ["consultant", "product manager", "project", "management"]):
        return "Project Management"
    if _has_word_prefix(title, ["lehrling", "apprentice", "ausbildung", "lehre"]):
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
    """Silicon Austria Labs - moved from Personio to a rexx-systems career site.

    Listing is server-rendered and paginated via ?start=N.
    """

    LIST_URL = "https://career.silicon-austria-labs.com/stellenangebote.html"

    @property
    def name(self) -> str:
        return "sal"

    def fetch_jobs(self) -> list[Job]:
        try:
            return self._fetch_pages()
        except Exception:
            return []

    def _fetch_pages(self) -> list[Job]:
        jobs = []
        seen = set()
        for start in range(0, 100, 10):
            url = f"{self.LIST_URL}?start={start}" if start else self.LIST_URL
            try:
                html = fetch_html(url, retries=2)
            except Exception:
                break
            batch = self._parse_listing(html)
            new_jobs = []
            for job in batch:
                if job.url in seen:
                    continue
                seen.add(job.url)
                new_jobs.append(job)
            if not new_jobs:
                break
            jobs.extend(new_jobs)
        return cap_jobs(jobs)

    def _parse_listing(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for article in soup.find_all("article", class_=re.compile(r"joboffer", re.I)):
            link = article.find("a", href=re.compile(r"-j\d+\.html", re.I))
            if not link:
                continue
            title = link.get_text(" ", strip=True)
            if not is_valid_job_title(title):
                continue
            level_el = article.find(class_=re.compile(r"job_details_second", re.I))
            loc_el = article.find(class_=re.compile(r"job_standort", re.I))
            mode_el = article.find(class_=re.compile(r"job_location", re.I))
            location = ", ".join(
                x for x in (loc_el.get_text(" ", strip=True) if loc_el else "", mode_el.get_text(" ", strip=True) if mode_el else "") if x
            )
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country="Austria",
                    category="",
                    experience_level=level_el.get_text(" ", strip=True) if level_el else "",
                    source=self.name,
                    url=build_url(self.LIST_URL, link.get("href", "")),
                )
            )
        return jobs


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
    """Infineon - Workday career site. cxs API returns HTTP 422/500 and the SPA
    renders jobs client-side; kept as a no-op until a working feed is confirmed."""

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
    """LAM Research - Phenom career site renders jobs client-side; no public feed
    found. Kept as a no-op until a feed is confirmed."""

    @property
    def name(self) -> str:
        return "lam"

    def fetch_jobs(self) -> list[Job]:
        return []


class SiemensScraper(BaseScraper):
    """Siemens - AvaPortal careers site renders jobs client-side; no public feed
    found. Kept as a no-op until a feed is confirmed."""

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


class FabasoftScraper(BaseScraper):
    """Fabasoft - server-rendered career page with `list-group-item` job cards."""

    BASE_URL = "https://www.fabasoft.com"
    JOBS_URL = "https://www.fabasoft.com/en/career/jobs"

    @property
    def name(self) -> str:
        return "fabasoft"

    def fetch_jobs(self) -> list[Job]:
        try:
            html = fetch_html(self.JOBS_URL)
            return self._parse_jobs(html)
        except Exception:
            return []

    def _parse_jobs(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        seen = set()
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if not re.search(r"/(career|karriere)/jobs/", href) or href in seen:
                continue
            heading = anchor.find("h3")
            if not heading:
                continue
            title = _normalize_ws(heading.get_text(" ", strip=True))
            if not is_valid_job_title(title):
                continue
            seen.add(href)
            span = anchor.find("span")
            location = _normalize_ws(span.get_text(" ", strip=True)) if span else ""
            country = "Austria" if re.search(AUSTRIAN_CITIES, location, re.I) else ""
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category=_guess_category(title),
                    experience_level="",
                    source=self.name,
                    url=build_url(self.BASE_URL, href),
                )
            )
        return cap_jobs(jobs)


class DynatraceScraper(BaseScraper):
    """Dynatrace - careers site backed by a Coveo search API (JSON POST).

    The listing is a client-side Astro/React app; the job data comes from
    `/api/coveo/search/`. Keeps Austrian postings plus remote European ones.
    """

    COVEO_URL = "https://www.dynatrace.com/api/coveo/search/"
    FIELDS = [
        "team",
        "office_locations",
        "country",
        "seniority",
        "technologies",
        "flex_option",
        "capability",
        "employment_type",
        "is_karriere_at",
        "job_id",
        "region",
    ]

    @property
    def name(self) -> str:
        return "dynatrace"

    def fetch_jobs(self) -> list[Job]:
        payload = {
            "q": "",
            "numberOfResults": 1000,
            "wildcards": True,
            "fieldsToInclude": self.FIELDS,
            "facets": [],
        }
        try:
            data = fetch_json_post(self.COVEO_URL, payload)
            return self._parse_results(data)
        except Exception:
            return []

    def _parse_results(self, data: dict) -> list[Job]:
        jobs = []
        for entry in data.get("results", []) or []:
            title = entry.get("title", "")
            if not is_valid_job_title(title):
                continue
            raw = entry.get("raw") or {}
            countries = [str(c) for c in raw.get("country") or []]
            flex = [str(f) for f in raw.get("flex_option") or []]
            remote = any("remote" in f.lower() for f in flex)
            austria = any("austria" in c.lower() for c in countries)
            europe = any(c in EUROPEAN_COUNTRIES for c in countries)
            if not austria and not (remote and europe):
                continue
            locations = [str(x) for x in raw.get("office_locations") or []]
            if remote:
                locations.append("Remote")
            jobs.append(
                Job(
                    title=title,
                    location=", ".join(dict.fromkeys(locations)),
                    country="Austria" if austria else (countries[0] if countries else ""),
                    category=", ".join(str(t) for t in raw.get("team") or []),
                    experience_level=", ".join(str(s) for s in raw.get("seniority") or []),
                    source=self.name,
                    url=entry.get("uri") or entry.get("clickUri") or "",
                    raw=raw,
                )
            )
        return cap_jobs(jobs)


class BRScraper(BaseScraper):
    """B&R (ABB) - Workday cxs JSON API; searches the Eggelsberg HQ postings.

    Workday rate-limits aggressive callers (HTTP 400 on rapid repeats), so pages
    are bounded and fetched without retries; earlier pages survive later failures.
    """

    WORKDAY_URL = "https://abb.wd3.myworkdayjobs.com/wday/cxs/abb/External_Career_Page/jobs"
    JOB_BASE = "https://abb.wd3.myworkdayjobs.com/en-US/External_Career_Page"

    @property
    def name(self) -> str:
        return "br"

    def fetch_jobs(self) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        for offset in range(0, MAX_JOBS_PER_SCRAPER, 50):
            payload = {
                "appliedFacets": {},
                "limit": 50,
                "offset": offset,
                "searchText": "Eggelsberg",
            }
            try:
                data = fetch_json_post(self.WORKDAY_URL, payload, retries=0)
            except Exception:
                break
            postings = data.get("jobPostings", []) if isinstance(data, dict) else []
            if not postings:
                break
            batch = self._parse_results(data)
            new_jobs = [job for job in batch if job.url not in seen]
            jobs.extend(new_jobs)
            seen.update(job.url for job in new_jobs)
            total = data.get("total", 0)
            if not new_jobs or len(postings) < 50 or offset + len(postings) >= total:
                break
        return cap_jobs(jobs)

    def _parse_results(self, data: dict) -> list[Job]:
        jobs = []
        for post in data.get("jobPostings", []) or []:
            path = post.get("externalPath", "")
            locations = post.get("locationsText", "")
            # Multi-location postings report "2 Locations"; the country is only
            # visible in the externalPath slug (e.g. Eggelsberg-Oberosterreich-Austria).
            if not path or not re.search(r"austria", f"{path} {locations}", re.I):
                continue
            title = post.get("title", "")
            if not is_valid_job_title(title):
                continue
            location = _normalize_ws(locations)
            if re.fullmatch(r"\d+\s+locations?", location, re.I):
                location = "Eggelsberg, Austria" if re.search(r"eggelsberg", path, re.I) else ""
            jobs.append(
                Job(
                    title=title,
                    location=location or "Eggelsberg, Austria",
                    country="Austria",
                    category=_guess_category(title),
                    experience_level="",
                    source=self.name,
                    url=f"{self.JOB_BASE}{path}",
                )
            )
        return cap_jobs(jobs)


class JKUScraper(BaseScraper):
    """JKU Jobbörse - server-rendered Drupal board for JKU students & alumni."""

    BASE_URL = "https://jobboerse.jku.at"
    JOBS_URL = "https://jobboerse.jku.at/jobs"
    MAX_PAGES = 20

    @property
    def name(self) -> str:
        return "jku"

    def fetch_jobs(self) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        for page in range(1, self.MAX_PAGES + 1):
            url = self.JOBS_URL if page == 1 else f"{self.JOBS_URL}?page={page}"
            try:
                html = fetch_html(url)
            except Exception:
                break
            batch = self._parse_jobs(html, seen)
            if not batch:
                break
            jobs.extend(batch)
        return cap_jobs(jobs)

    def _parse_jobs(self, html: str, seen: set[str]) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        for card in soup.select(".jcl-job-teaser-content"):
            link = card.select_one(".jcl-job-teaser-title a")
            if not link:
                continue
            href = link.get("href", "")
            if not href or href in seen:
                continue
            title = _normalize_ws(link.get_text(" ", strip=True))
            if not is_valid_job_title(title):
                continue
            seen.add(href)
            company_el = card.select_one(".jcl-job-teaser-company a")
            company = _normalize_ws(company_el.get_text(" ", strip=True)) if company_el else ""
            location = ""
            loc_el = card.select_one(".jcl-job-teaser-location")
            if loc_el:
                for svg in loc_el.find_all("svg"):
                    svg.decompose()
                location = _normalize_ws(loc_el.get_text(" ", strip=True))
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country="Austria" if re.search(r"österreich|austria", location, re.I) else "",
                    category=_guess_category(title),
                    experience_level="",
                    source=self.name,
                    company=company,
                    url=build_url(self.BASE_URL, href),
                )
            )
        return jobs