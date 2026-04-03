import re
import json
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, Job


class SCCHScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "scch"

    def fetch_jobs(self) -> list[Job]:
        html = self._fetch_page()
        return self._parse_jobs(html)

    def _fetch_page(self) -> str:
        resp = requests.get(
            "https://www.scch.at/karriere/offene-positionen/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.text

    def _parse_jobs(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        for item in soup.find_all(class_=re.compile(r"position|job|stelle", re.I)):
            title_el = item.find(class_=re.compile(r"title|titel|name", re.I))
            if not title_el:
                title_el = item
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            link_el = item.find("a")
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://www.scch.at", url)

            jobs.append(
                Job(
                    title=title,
                    location="Hagenberg, Austria",
                    country="Austria",
                    category=self._guess_category(title),
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )

        return jobs

    def _guess_category(self, title: str) -> str:
        t = title.lower()
        if any(k in t for k in ["software", "entwickl", "ai solution"]):
            return "Development / Software / IT"
        if any(k in t for k in ["data", "masterarbeit", "forschung"]):
            return "Research"
        if any(k in t for k in ["consultant", "product manager"]):
            return "Project Management"
        if any(k in t for k in ["lehrling", "apprentice"]):
            return "Apprenticeship"
        return "Other"


class RISCRScraper(BaseScraper):
    @property
    def name(self) -> str:
        return "risc"

    def fetch_jobs(self) -> list[Job]:
        html = self._fetch_page()
        return self._parse_jobs(html)

    def _fetch_page(self) -> str:
        resp = requests.get(
            "https://career.risc-software.at/en/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.text

    def _parse_jobs(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        # Jobs are h3.title elements followed by sibling info
        for h3 in soup.find_all("h3", class_="title"):
            title = h3.get_text(strip=True)
            if not title or len(title) < 5 or len(title) > 120:
                continue
            # Skip non-job headings
            if any(skip in title.lower() for skip in ["open to", "with us", "which pioneer", "your career"]):
                continue

            # Find the "Mehr erfahren" link in the same card
            parent = h3.find_parent()
            if not parent:
                parent = h3
            link_el = parent.find_next_sibling("a") or parent.find("a", class_="link")
            url = ""
            if link_el:
                url = str(link_el.get("href", ""))
                if url and not url.startswith("http"):
                    url = urljoin("https://career.risc-software.at", url)

            # Extract badges for experience level
            badges = []
            badges_container = h3.find_next_sibling(class_="badges")
            if badges_container:
                for badge in badges_container.find_all(class_="badge"):
                    badges.append(badge.get_text(strip=True))

            jobs.append(
                Job(
                    title=title,
                    location="Hagenberg, Austria",
                    country="Austria",
                    category=self._guess_category(title),
                    experience_level=" ".join(badges),
                    source=self.name,
                    url=url,
                )
            )

        return jobs

    def _guess_category(self, title: str) -> str:
        t = title.lower()
        if any(k in t for k in ["software", "developer", "ai", "research"]):
            return "Development / Software / IT"
        if any(k in t for k in ["intern", "thesis", "student"]):
            return "Research"
        return "Other"


class SALScraper(BaseScraper):
    """Silicon Austria Labs - uses Personio ATS."""

    @property
    def name(self) -> str:
        return "sal"

    def fetch_jobs(self) -> list[Job]:
        jobs = []
        try:
            jobs = self._fetch_personio_api()
        except Exception:
            pass
        if not jobs:
            try:
                jobs = self._fetch_page_fallback()
            except Exception:
                pass
        return jobs

    def _fetch_personio_api(self) -> list[Job]:
        resp = requests.get(
            "https://api.personio.de/v1/company/jobs",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
            params={"company_id": "silicon-austria-labs"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for j in data.get("jobs", []):
            location = j.get("location", {}).get("name", "Austria")
            country = "Austria" if any(
                c in location.lower()
                for c in ["austria", "osterreich", "wien", "linz", "graz", "villach"]
            ) else ""
            jobs.append(
                Job(
                    title=j.get("name", ""),
                    location=location,
                    country=country,
                    category=j.get("department", {}).get("name", ""),
                    experience_level="",
                    source=self.name,
                    url=j.get("url", ""),
                )
            )
        return jobs

    def _fetch_page_fallback(self) -> list[Job]:
        resp = requests.get(
            "https://silicon-austria-labs.jobs.personio.de/?language=en",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        for item in soup.find_all(class_=re.compile(r"job", re.I)):
            title_el = item.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            location = ""
            loc_el = item.find(class_=re.compile(r"location|standort", re.I))
            if loc_el:
                location = loc_el.get_text(strip=True)
            link_el = item.find("a")
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://silicon-austria-labs.jobs.personio.de", url)
            country = "Austria" if any(
                c in location.lower() for c in ["austria", "linz", "graz", "villach", "wien"]
            ) else ""
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category="",
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )
        return jobs


class AITScraper(BaseScraper):
    """AIT - uses eRecruiter ATS."""

    @property
    def name(self) -> str:
        return "ait"

    def fetch_jobs(self) -> list[Job]:
        try:
            return self._fetch_api()
        except Exception:
            return self._fetch_page_fallback()

    def _fetch_api(self) -> list[Job]:
        resp = requests.get(
            "https://jobs.ait.ac.at/api/v1/vacancies",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return self._parse_api_jobs(data)

    def _parse_api_jobs(self, data: dict) -> list[Job]:
        jobs = []
        for j in data.get("vacancies", data.get("jobs", [])):
            title = j.get("title", j.get("name", ""))
            location = j.get("location", j.get("city", ""))
            country = "Austria"
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category=j.get("category", j.get("department", "")),
                    experience_level="",
                    source=self.name,
                    url=j.get("url", j.get("link", "")),
                )
            )
        return jobs

    def _fetch_page_fallback(self) -> list[Job]:
        resp = requests.get(
            "https://jobs.ait.ac.at/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        for item in soup.find_all(class_=re.compile(r"vacanc|job|stelle", re.I)):
            title_el = item.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            link_el = item.find("a")
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://jobs.ait.ac.at", url)
            jobs.append(
                Job(
                    title=title,
                    location="",
                    country="Austria",
                    category="",
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )
        return jobs


class AVLLScraper(BaseScraper):
    """AVL - uses SAP SuccessFactors."""

    @property
    def name(self) -> str:
        return "avl"

    def fetch_jobs(self) -> list[Job]:
        try:
            return self._fetch_page()
        except Exception:
            return []

    def _clean_title(self, raw: str) -> str:
        # Titles appear duplicated: "Software EngineerSoftware EngineerGraz, AT"
        # Split by looking for the first repeat
        for i in range(1, len(raw) // 2):
            if raw[:i] == raw[i:2*i]:
                return raw[:i]
        return raw

    def _fetch_page(self) -> list[Job]:
        resp = requests.get(
            "https://jobs.avl.com/go/Jobs-in-Austria/9215001/?q=&sortColumn=sort_date&sortDirection=desc",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []

        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            raw_title = cells[0].get_text(strip=True) if len(cells) > 0 else ""
            location = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            title = self._clean_title(raw_title)
            if not title or len(title) < 5:
                continue
            # Only keep Austria jobs
            if not any(c in location for c in ["AT", "Graz", "Steyr", "Austria", "österreich"]):
                continue
            link_el = row.find("a")
            url = str(link_el.get("href", "")) if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://jobs.avl.com", url)
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country="Austria",
                    category="",
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )

        return jobs


class KEBAScraper(BaseScraper):
    """KEBA - uses eRecruiter ATS."""

    @property
    def name(self) -> str:
        return "keba"

    def fetch_jobs(self) -> list[Job]:
        try:
            return self._fetch_api()
        except Exception:
            return self._fetch_page_fallback()

    def _fetch_api(self) -> list[Job]:
        resp = requests.get(
            "https://jobs.keba.com/api/v1/vacancies",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return self._parse_api_jobs(data)

    def _parse_api_jobs(self, data: dict) -> list[Job]:
        jobs = []
        for j in data.get("vacancies", data.get("jobs", [])):
            title = j.get("title", j.get("name", ""))
            location = j.get("location", j.get("city", ""))
            country = "Austria" if any(
                c in location.lower() for c in ["austria", "linz"]
            ) else ""
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category=j.get("category", j.get("department", "")),
                    experience_level="",
                    source=self.name,
                    url=j.get("url", j.get("link", "")),
                )
            )
        return jobs

    def _fetch_page_fallback(self) -> list[Job]:
        resp = requests.get(
            "https://jobs.keba.com/Jobs",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        for item in soup.find_all(class_=re.compile(r"vacanc|job|stelle", re.I)):
            title_el = item.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            link_el = item.find("a")
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://jobs.keba.com", url)
            jobs.append(
                Job(
                    title=title,
                    location="",
                    country="Austria",
                    category="",
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )
        return jobs


class InfineonScraper(BaseScraper):
    """Infineon - uses Workday ATS."""

    @property
    def name(self) -> str:
        return "infineon"

    def fetch_jobs(self) -> list[Job]:
        try:
            return self._fetch_workday_api()
        except Exception:
            return []

    def _fetch_workday_api(self) -> list[Job]:
        resp = requests.get(
            "https://wd1.myworkdaysite.com/en-US/recruiting/infineon/jobs",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
            allow_redirects=True,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        for item in soup.find_all(class_=re.compile(r"job|position|posting", re.I)):
            title_el = item.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            link_el = item.find("a")
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://wd1.myworkdaysite.com", url)
            location = ""
            loc_el = item.find(class_=re.compile(r"location|place", re.I))
            if loc_el:
                location = loc_el.get_text(strip=True)
            country = "Austria" if "austria" in location.lower() or "linz" in location.lower() else ""
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category="",
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )
        return jobs


class PrimetalsScraper(BaseScraper):
    """Primetals - uses eRecruiter ATS."""

    @property
    def name(self) -> str:
        return "primetals"

    def fetch_jobs(self) -> list[Job]:
        try:
            return self._fetch_api()
        except Exception:
            return self._fetch_page_fallback()

    def _fetch_api(self) -> list[Job]:
        resp = requests.get(
            "https://jobs.primetals.com/api/v1/vacancies",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return self._parse_api_jobs(data)

    def _parse_api_jobs(self, data: dict) -> list[Job]:
        jobs = []
        for j in data.get("vacancies", data.get("jobs", [])):
            title = j.get("title", j.get("name", ""))
            location = j.get("location", j.get("city", ""))
            country = "Austria" if any(
                c in location.lower() for c in ["austria", "linz"]
            ) else ""
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category=j.get("category", j.get("department", "")),
                    experience_level="",
                    source=self.name,
                    url=j.get("url", j.get("link", "")),
                )
            )
        return jobs

    def _fetch_page_fallback(self) -> list[Job]:
        resp = requests.get(
            "https://jobs.primetals.com/Jobs?culture=en",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        for item in soup.find_all(class_=re.compile(r"vacanc|job|stelle", re.I)):
            title_el = item.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            link_el = item.find("a")
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://jobs.primetals.com", url)
            jobs.append(
                Job(
                    title=title,
                    location="",
                    country="Austria",
                    category="",
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )
        return jobs


class LAMResearchScraper(BaseScraper):
    """LAM Research - uses Phenom/Brassring ATS."""

    @property
    def name(self) -> str:
        return "lam"

    def fetch_jobs(self) -> list[Job]:
        try:
            return self._fetch_page()
        except Exception:
            return []

    def _fetch_page(self) -> list[Job]:
        resp = requests.get(
            "https://careers.lamresearch.com/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        for item in soup.find_all(class_=re.compile(r"job|position|posting|card", re.I)):
            title_el = item.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            link_el = item.find("a")
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://careers.lamresearch.com", url)
            location = ""
            loc_el = item.find(class_=re.compile(r"location|place|city", re.I))
            if loc_el:
                location = loc_el.get_text(strip=True)
            country = "Austria" if "austria" in location.lower() or "salzburg" in location.lower() else ""
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category="",
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )
        return jobs


class SiemensScraper(BaseScraper):
    """Siemens - uses SAP SuccessFactors."""

    @property
    def name(self) -> str:
        return "siemens"

    def fetch_jobs(self) -> list[Job]:
        try:
            return self._fetch_page()
        except Exception:
            return []

    def _fetch_page(self) -> list[Job]:
        resp = requests.get(
            "https://jobs.siemens.com/careers?location=austria&sortby=job_post_date&pagesize=50",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        for item in soup.find_all(class_=re.compile(r"job|position|posting|card|result", re.I)):
            title_el = item.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            link_el = item.find("a")
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://jobs.siemens.com", url)
            location = ""
            loc_el = item.find(class_=re.compile(r"location|place|city", re.I))
            if loc_el:
                location = loc_el.get_text(strip=True)
            country = "Austria" if any(
                c in location.lower() for c in ["austria", "linz"]
            ) else ""
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category="",
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )
        return jobs


class SynopsysScraper(BaseScraper):
    """Synopsys - uses SAP SuccessFactors."""

    @property
    def name(self) -> str:
        return "synopsys"

    def fetch_jobs(self) -> list[Job]:
        try:
            return self._fetch_page()
        except Exception:
            return []

    def _fetch_page(self) -> list[Job]:
        resp = requests.get(
            "https://careers.synopsys.com/search-jobs/Austria/44408/1",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        for item in soup.find_all(class_=re.compile(r"job|position|posting|card|result", re.I)):
            title_el = item.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            link_el = item.find("a")
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://careers.synopsys.com", url)
            location = ""
            loc_el = item.find(class_=re.compile(r"location|place|city", re.I))
            if loc_el:
                location = loc_el.get_text(strip=True)
            country = "Austria" if "austria" in location.lower() else ""
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category="",
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )
        return jobs


class VoestalpineScraper(BaseScraper):
    """voestalpine - uses eRecruiter ATS."""

    @property
    def name(self) -> str:
        return "voestalpine"

    def fetch_jobs(self) -> list[Job]:
        try:
            return self._fetch_api()
        except Exception:
            return self._fetch_page_fallback()

    def _fetch_api(self) -> list[Job]:
        resp = requests.get(
            "https://jobs.voestalpine.com/api/v1/vacancies",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return self._parse_api_jobs(data)

    def _parse_api_jobs(self, data: dict) -> list[Job]:
        jobs = []
        for j in data.get("vacancies", data.get("jobs", [])):
            title = j.get("title", j.get("name", ""))
            location = j.get("location", j.get("city", ""))
            country = "Austria" if any(
                c in location.lower() for c in ["austria", "linz"]
            ) else ""
            jobs.append(
                Job(
                    title=title,
                    location=location,
                    country=country,
                    category=j.get("category", j.get("department", "")),
                    experience_level="",
                    source=self.name,
                    url=j.get("url", j.get("link", "")),
                )
            )
        return jobs

    def _fetch_page_fallback(self) -> list[Job]:
        resp = requests.get(
            "https://jobs.voestalpine.com/index.php?ac=search_result&language=1",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        for item in soup.find_all(class_=re.compile(r"vacanc|job|stelle|result", re.I)):
            title_el = item.find(["h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            link_el = item.find("a")
            url = link_el.get("href", "") if link_el else ""
            if url and not url.startswith("http"):
                url = urljoin("https://jobs.voestalpine.com", url)
            jobs.append(
                Job(
                    title=title,
                    location="",
                    country="Austria",
                    category="",
                    experience_level="",
                    source=self.name,
                    url=url,
                )
            )
        return jobs
