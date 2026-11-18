import re
from itertools import zip_longest

from matching import EU_NEARBY_CITIES
from scrapers.base import BaseScraper, Job
from scrapers.common import (
    cap_jobs,
    clean_html_text,
    fetch_json_post,
    is_valid_job_title,
)

SEARCH_URL = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"
DETAIL_URL = "https://europa.eu/eures/portal/jv-se/jv-details/{id}"
RESULTS_PER_PAGE = 50
MAX_PAGES = 2

# Targeted queries keep the result set bounded and relevant (the classifier still
# filters everything afterwards). EURES is the official EU public employment
# portal; keep volume polite.
SEARCH_TERMS = [
    "software developer",
    "software engineer",
    "softwareentwickler",
    "data engineer",
    "data scientist",
    "embedded",
    "firmware",
    "python",
    "backend",
    "machine learning",
    "artificial intelligence",
    "data analyst",
    "mathematik",
    "informatik",
]

# Junior + mid only: exclude more_than_5_years so senior roles never enter.
EXPERIENCE_CODES = [
    "NS",
    "none_required",
    "up_to_1_year",
    "between_1_and_2_years",
    "between_2_and_5_years",
]

AUSTRIA_NUTS = {
    "AT11": "Burgenland",
    "AT12": "Niederösterreich",
    "AT13": "Wien",
    "AT21": "Kärnten",
    "AT22": "Steiermark",
    "AT31": "Oberösterreich",
    "AT32": "Salzburg",
    "AT33": "Tirol",
    "AT34": "Vorarlberg",
}

COUNTRY_NAMES = {
    "AT": "Austria",
    "DE": "Germany",
    "CH": "Switzerland",
    "CZ": "Czechia",
    "SK": "Slovakia",
    "HU": "Hungary",
    "SI": "Slovenia",
    "IT": "Italy",
}

_REMOTE = re.compile(
    r"\b(?:fully\s+remote|100\s*%\s*remote|100\s*%\s*home[\s-]?office|"
    r"remote\s+(?:possible|work|working)|work(?:ing)?\s+remotely|"
    r"(?:position|role|job)\s+(?:is\s+)?remote|"
    r"vollst(?:ä|ae)ndig\s+remote)\b",
    re.I,
)


class EuresScraper(BaseScraper):
    """EU EURES public employment portal (unofficial but documented search API)."""

    @property
    def name(self) -> str:
        return "eures"

    def __init__(self, location_codes: list[str] | None = None):
        self.location_codes = location_codes or ["at", "de"]

    def fetch_jobs(self) -> list[Job]:
        batches_by_term: list[list[list[Job]]] = []
        for term in SEARCH_TERMS:
            term_batches: list[list[Job]] = []
            for page in range(1, MAX_PAGES + 1):
                payload = self._build_payload(term, page)
                try:
                    data = fetch_json_post(SEARCH_URL, payload)
                except Exception:
                    break
                raw_results = data.get("jvs", []) if isinstance(data, dict) else []
                batch = self._parse_response(data)
                if not batch:
                    break
                term_batches.append(batch)
                if len(raw_results) < RESULTS_PER_PAGE:
                    break
                records = data.get("numberRecords")
                if isinstance(records, int) and page * RESULTS_PER_PAGE >= records:
                    break
            batches_by_term.append(term_batches)

        jobs: list[Job] = []
        seen: set[str] = set()
        jobs_by_term = [
            [job for batch in term_batches for job in batch]
            for term_batches in batches_by_term
        ]
        # Round-robin jobs, not whole pages, so broad early terms share the cap.
        for candidates in zip_longest(*jobs_by_term):
            for job in candidates:
                if job is None or job.url in seen:
                    continue
                seen.add(job.url)
                jobs.append(job)
        return cap_jobs(jobs)

    def _build_payload(self, term: str, page: int = 1) -> dict:
        return {
            "resultsPerPage": RESULTS_PER_PAGE,
            "page": page,
            "sortSearch": "MOST_RECENT",
            "keywords": [{"keyword": term, "specificSearchCode": "EVERYWHERE"}],
            "publicationPeriod": "LAST_MONTH",
            "occupationUris": [],
            "skillUris": [],
            "requiredExperienceCodes": EXPERIENCE_CODES,
            "positionScheduleCodes": [],
            "sectorCodes": [],
            "educationAndQualificationLevelCodes": [],
            "positionOfferingCodes": [],
            "locationCodes": self.location_codes,
            "euresFlagCodes": [],
            "otherBenefitsCodes": [],
            "requiredLanguages": [],
            "minNumberPost": None,
            "sessionId": "job-checker",
            "requestLanguage": "en",
        }

    def _parse_response(self, data: dict) -> list[Job]:
        if not isinstance(data, dict):
            return []
        jobs = []
        for entry in data.get("jvs", []) or []:
            title = (entry.get("title") or "").strip()
            if not is_valid_job_title(title):
                continue
            description = clean_html_text(entry.get("description", "") or "")
            location, country = self._resolve_location(entry.get("locationMap"), title, description)
            employer = entry.get("employer") or {}
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category="",
                    experience_level="",
                    source=self.name,
                    url=DETAIL_URL.format(id=entry.get("id", "")),
                    company=employer.get("name", "") or "",
                    description=description,
                    raw={"id": entry.get("id", "")},
                )
            )
        return jobs

    def _resolve_location(
        self, location_map: dict | None, title: str, description: str
    ) -> tuple[str, str]:
        parts: list[str] = []
        country = ""
        for code, regions in (location_map or {}).items():
            country = country or COUNTRY_NAMES.get(code.upper(), code)
            for region in regions or []:
                name = AUSTRIA_NUTS.get(region.upper())
                if name:
                    parts.append(name)
        text = f"{title} {description}"
        for city in sorted(EU_NEARBY_CITIES, key=len, reverse=True):
            if re.search(rf"\b{re.escape(city)}\b", text, re.I):
                parts.append(city.title())
        if _REMOTE.search(text):
            parts.append("Remote")
        location = ", ".join(dict.fromkeys(parts))
        return location, country
