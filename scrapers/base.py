from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Job:
    title: str
    location: str
    country: str
    category: str
    experience_level: str
    source: str
    url: str = ""
    company: str = ""
    raw: dict = field(default_factory=dict)
    description: str = ""
    # Structured salary from feeds that expose it directly (e.g. Talent Taiwan).
    # When set, build_result() prefers these over scraping the description.
    salary_text: str = ""
    salary_min: int | float | None = None


class BaseScraper(ABC):
    @abstractmethod
    def fetch_jobs(self) -> list[Job]:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
