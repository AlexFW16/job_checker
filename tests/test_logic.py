import json
from pathlib import Path

import pytest

from main import matches_keywords, matches_location
from scrapers.base import Job
from scrapers.common import is_valid_job_title
from scrapers.companies import VoestalpineScraper

CONFIG = json.loads(Path("config.json").read_text(encoding="utf-8"))


def test_is_valid_job_title_filters_junk():
    for junk in [
        "Reset filters",
        "Did you mean",
        "Zur Bewerbung",
        "Job Search",
        "Show more",
        "Aug 9, 2026",
        "2026-08-09",
        "123",
        "git",
    ]:
        assert not is_valid_job_title(junk), junk
    for good in [
        "Software Engineer (m/w/d)",
        "Data & AI Engineer",
        "Junior Fullstack Developer",
        "Werkstudent IT (w/m)",
    ]:
        assert is_valid_job_title(good), good


def test_matches_keywords_is_score_based():
    job = Job(
        title="Junior Software Developer",
        location="Linz",
        country="Austria",
        category="",
        experience_level="",
        source="t",
    )
    info = matches_keywords(job, CONFIG)
    assert info["score"] >= 1
    assert info["is_software_dev"] is True
    assert info["is_relevant"] is True
    expected_junior = any(k in job.title.lower() for k in CONFIG["keywords"]["junior_level"])
    assert info["is_junior_level"] is expected_junior


def test_matches_keywords_rejects_unrelated():
    job = Job(
        title="Lagerlogistiker (m/w/d)",
        location="Linz",
        country="Austria",
        category="Logistik",
        experience_level="",
        source="t",
    )
    info = matches_keywords(job, CONFIG)
    assert info["is_relevant"] is False


def test_matches_location_linz_area():
    job = Job(
        title="Software Engineer",
        location="Hagenberg",
        country="Austria",
        category="",
        experience_level="",
        source="t",
    )
    ok, reason = matches_location(job, CONFIG["filters"])
    assert ok and reason in ("linz_area", "austria")


def test_matches_location_non_austria_excluded():
    job = Job(
        title="Software Engineer",
        location="Berlin",
        country="Germany",
        category="",
        experience_level="",
        source="t",
    )
    ok, _ = matches_location(job, CONFIG["filters"])
    assert ok is False


def test_voestalpine_parse_filters_austria():
    sample = {
        "SearchResult": {
            "SearchResultItems": [
                {
                    "MatchedObjectDescriptor": {
                        "PositionTitle": "Data & AI Engineer",
                        "PositionURI": "https://jobs.voestalpine.com/index.php?ac=jobad&id=1",
                        "PositionLocation": [{"CountryName": "Österreich", "CityName": "Linz"}],
                        "JobCategory": [{"Name": "IT"}],
                        "CareerLevel": [{"Name": "Mitarbeiter:in"}],
                    }
                },
                {
                    "MatchedObjectDescriptor": {
                        "PositionTitle": "Sales Manager",
                        "PositionURI": "https://jobs.voestalpine.com/index.php?ac=jobad&id=2",
                        "PositionLocation": [{"CountryName": "Belgien", "CityName": "Hooglede-Gits"}],
                        "JobCategory": [{"Name": "Sales"}],
                        "CareerLevel": [{"Name": "Mitarbeiter:in"}],
                    }
                },
            ]
        }
    }
    jobs = VoestalpineScraper()._parse_results(sample)
    assert len(jobs) == 1
    assert jobs[0].title == "Data & AI Engineer"
    assert jobs[0].country == "Austria"
    assert "Linz" in jobs[0].location