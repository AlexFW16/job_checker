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
    raw: dict = field(default_factory=dict)


class BaseScraper(ABC):
    @abstractmethod
    def fetch_jobs(self) -> list[Job]:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
