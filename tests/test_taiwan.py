import json

import main
import taiwan_main
from config_loader import load_taiwan_config
from matching import JobClassifier, matches_location, matches_location_taiwan
from scrapers.base import Job
from scrapers.taiwan import talent_taiwan
from scrapers.taiwan.talent_taiwan import TalentTaiwanScraper, format_salary


def make_job(
    title,
    location="Taipei City",
    country="Taiwan",
    category="",
    experience_level="",
    description="",
    url="",
    source="talent_taiwan",
):
    return Job(
        title=title,
        location=location,
        country=country,
        category=category,
        experience_level=experience_level,
        source=source,
        url=url,
        description=description,
    )


SAMPLE_RESULT = {
    "id": "cake:1",
    "source": "cake",
    "source_job_id": "1",
    "title": "後端工程師 Backend Engineer",
    "company": "Foo Inc.",
    "company_logo": "/api/logos/x.jpg",
    "description": "Build APIs with Python.",
    "url": "https://www.cake.me/jobs/1",
    "location": {
        "country_code": "TW",
        "region_code": "TPE",
        "name_zh": "臺北市",
        "name_en": "Taipei City",
    },
    "salary": {"min": 60000, "max": 80000, "currency": "TWD", "type": "per_month"},
    "employment_type": "full_time",
    "category": "it_software-engineer",
    "posted_at": "2026-10-08T13:51:49.237389Z",
    "updated_at": "2026-10-08T13:51:49.237389Z",
}

TAIWAN_FILTERS = {
    "region": "taiwan",
    "countries": ["Taiwan"],
    "remote_worldwide": False,
    "remote_eu": False,
    "allow_eu_nearby": False,
}


class TestTaiwanLocation:
    def test_taipei_city(self):
        matched, reason = matches_location_taiwan(make_job("Backend Engineer"), TAIWAN_FILTERS)
        assert matched and reason == "taipei_area"

    def test_new_taipei(self):
        job = make_job("Backend Engineer", location="New Taipei City")
        matched, reason = matches_location_taiwan(job, TAIWAN_FILTERS)
        assert matched and reason == "taipei_area"

    def test_chinese_taipei(self):
        job = make_job("後端工程師", location="臺北市")
        matched, reason = matches_location_taiwan(job, TAIWAN_FILTERS)
        assert matched and reason == "taipei_area"

    def test_taiwan_unknown_city(self):
        job = make_job("Backend Engineer", location="Somewhere", country="Taiwan")
        matched, reason = matches_location_taiwan(job, TAIWAN_FILTERS)
        assert matched and reason == "taiwan"

    def test_non_taiwan_rejected(self):
        job = make_job("Backend Engineer", location="Linz", country="Austria")
        assert matches_location_taiwan(job, TAIWAN_FILTERS) == (False, "")

    def test_remote_worldwide(self):
        filters = dict(TAIWAN_FILTERS, remote_worldwide=True)
        job = make_job("Backend Engineer", location="Remote - Worldwide", country="")
        matched, reason = matches_location_taiwan(job, filters)
        assert matched and reason == "remote_worldwide"

    def test_matches_location_dispatches_on_region(self):
        job = make_job("Backend Engineer")
        assert matches_location(job, TAIWAN_FILTERS) == (True, "taipei_area")

    def test_matches_location_defaults_to_austria(self):
        job = make_job("Backend Engineer", location="Linz", country="Austria")
        matched, reason = matches_location(job, {"countries": ["Austria"]})
        assert matched and reason == "linz_area"


class TestFormatSalary:
    def test_range(self):
        text, value = format_salary(
            {"min": 60000, "max": 80000, "currency": "TWD", "type": "per_month"}
        )
        assert text == "TWD 60,000–80,000 / month"
        assert value == 60000

    def test_single_value(self):
        text, value = format_salary(
            {"min": 50000, "max": 50000, "currency": "TWD", "type": "per_month"}
        )
        assert text == "TWD 50,000 / month"
        assert value == 50000

    def test_missing(self):
        assert format_salary(None) == ("", None)
        assert format_salary({}) == ("", None)


class TestTalentTaiwanScraper:
    def test_parse_job(self):
        job = TalentTaiwanScraper()._parse_job(SAMPLE_RESULT)
        assert job.title == "後端工程師 Backend Engineer"
        assert job.company == "Foo Inc."
        assert job.location == "Taipei City"
        assert job.country == "Taiwan"
        assert job.category == "it_software-engineer"
        assert job.source == "talent_taiwan"
        assert job.url == "https://www.cake.me/jobs/1"
        assert job.salary_min == 60000
        assert "TWD" in job.salary_text

    def test_parse_job_null_location(self):
        item = dict(SAMPLE_RESULT, location=None)
        job = TalentTaiwanScraper()._parse_job(item)
        assert job.location == "Taiwan"

    def test_parse_job_rejects_junk_title(self):
        item = dict(SAMPLE_RESULT, title="Reset filters")
        assert TalentTaiwanScraper()._parse_job(item) is None

    def test_parse_job_rejects_non_dict(self):
        assert TalentTaiwanScraper()._parse_job("nope") is None

    def test_fetch_jobs_paginates_and_queries_taipei(self, monkeypatch):
        calls = []

        def fake_fetch_json(url):
            calls.append(url)
            if "page=1" in url:
                return {"total": 101, "results": [SAMPLE_RESULT, dict(SAMPLE_RESULT, url="https://x/2")]}
            return {"total": 101, "results": [dict(SAMPLE_RESULT, url="https://x/3")]}

        monkeypatch.setattr(talent_taiwan, "fetch_json", fake_fetch_json)
        jobs = TalentTaiwanScraper().fetch_jobs()

        assert len(jobs) == 3
        assert len(calls) == 2
        assert all("location=TPE" in url and "location=NWT" in url for url in calls)
        assert "page_size=100" in calls[0]

    def test_fetch_jobs_dedupes_by_url(self, monkeypatch):
        monkeypatch.setattr(
            talent_taiwan,
            "fetch_json",
            lambda url: {"total": 1, "results": [SAMPLE_RESULT, dict(SAMPLE_RESULT)]},
        )
        assert len(TalentTaiwanScraper().fetch_jobs()) == 1

    def test_fetch_jobs_keeps_distinct_url_less_postings(self, monkeypatch):
        first = dict(SAMPLE_RESULT, id="cake:1", url="", title="後端工程師")
        second = dict(SAMPLE_RESULT, id="cake:2", url="", title="前端工程師")
        monkeypatch.setattr(
            talent_taiwan,
            "fetch_json",
            lambda url: {"total": 2, "results": [first, second]},
        )
        assert len(TalentTaiwanScraper().fetch_jobs()) == 2

    def test_fetch_jobs_preserves_pages_before_an_error(self, monkeypatch):
        def fake_fetch_json(url):
            if "page=1" in url:
                return {"total": 101, "results": [SAMPLE_RESULT]}
            raise RuntimeError("second page failed")

        monkeypatch.setattr(talent_taiwan, "fetch_json", fake_fetch_json)
        jobs = TalentTaiwanScraper().fetch_jobs()
        assert len(jobs) == 1
        assert jobs[0].url == SAMPLE_RESULT["url"]

    def test_fetch_jobs_returns_empty_on_error(self, monkeypatch):
        def boom(url):
            raise RuntimeError("network down")

        monkeypatch.setattr(talent_taiwan, "fetch_json", boom)
        assert TalentTaiwanScraper().fetch_jobs() == []


class TestTaiwanClassifier:
    def setup_method(self):
        self.classifier = JobClassifier(load_taiwan_config())

    def test_chinese_software_role_relevant(self):
        result = self.classifier.classify(make_job("後端工程師", category="it_software-engineer"))
        assert result["is_software_dev"] is True
        assert result["is_relevant"] is True

    def test_chinese_intern_is_excluded(self):
        result = self.classifier.classify(make_job("軟體實習生", category="it_software-engineer"))
        assert result["graduate_tier"] == "excluded"
        assert result["is_relevant"] is False

    def test_chinese_senior_excluded(self):
        result = self.classifier.classify(make_job("資深後端工程師", category="it_software-engineer"))
        assert result["graduate_tier"] == "excluded"
        assert result["is_relevant"] is False

    def test_generic_chinese_engineering_is_not_software(self):
        for title in ("機械工程師", "土木工程師"):
            result = self.classifier.classify(make_job(title))
            assert result["is_software_dev"] is False
            assert result["is_relevant"] is False

    def test_chinese_systems_engineer_remains_relevant(self):
        result = self.classifier.classify(make_job("量化系統工程師"))
        assert result["is_software_dev"] is True
        assert result["is_relevant"] is True


class TestBuildResultSalary:
    def test_prefers_structured_salary(self):
        job = make_job("Backend Engineer")
        job.salary_text = "TWD 60,000 / month"
        job.salary_min = 60000
        result = main.build_result(job, {"graduate_tier": "graduate"}, "taipei_area")
        assert result["salary_text"] == "TWD 60,000 / month"
        assert result["salary_min"] == 60000


class TestTaiwanMain:
    def test_get_scraper_instances_known(self):
        instances = taiwan_main.get_scraper_instances(["talent_taiwan"])
        assert len(instances) == 1
        assert instances[0].name == "talent_taiwan"

    def test_get_scraper_instances_unknown_warns(self, capsys):
        taiwan_main.get_scraper_instances(["nope"])
        assert "Unknown scraper" in capsys.readouterr().out

    def test_main_writes_taiwan_outputs(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        job = make_job(
            "Junior Backend Engineer",
            location="Taipei City",
            category="it_software-engineer",
        )
        monkeypatch.setattr(taiwan_main, "fetch_all_jobs", lambda scrapers: [job])

        assert taiwan_main.main() == 0

        assert (tmp_path / "results.taiwan.json").exists()
        assert (tmp_path / "docs" / "results.taiwan.json").exists()
        assert (tmp_path / "history.taiwan.json").exists()

        saved = json.loads((tmp_path / "results.taiwan.json").read_text(encoding="utf-8"))
        assert saved["matching_jobs"] == 1
        assert saved["results"][0]["location_match"] == "taipei_area"
        assert saved["results"][0]["country"] == "Taiwan"

    def test_main_returns_one_without_matches(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(taiwan_main, "fetch_all_jobs", lambda scrapers: [])
        assert taiwan_main.main() == 1
