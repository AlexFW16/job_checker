import json

import main
from scrapers.base import BaseScraper, Job

CONFIG = {
    "keywords": {
        "junior_level": ["junior", "graduate", "intern"],
        "software_dev": ["software", "developer"],
        "mathematics": ["data", "optimization"],
    },
    "graduate_filter": {
        "exclude_min_years": 2,
        "seniority_exclude": ["senior", "lead"],
        "seniority_downgrade": ["manager", "architect"],
    },
    "filters": {
        "countries": ["Austria"],
        "remote_worldwide": True,
        "remote_eu": True,
        "allow_eu_nearby": True,
        "fetch_details": False,
        "rank_weights": {
            "linz_area": 5,
            "vienna_area": 4,
            "remote_eu": 3,
            "austria": 2,
            "remote": 2,
            "remote_worldwide": 1,
            "eu_nearby": 1,
        },
    },
    "scrapers": ["fake"],
}


def make_job(title, location="Linz", country="Austria", category="", experience_level="", url="https://x.example/j/1", description=""):
    job = Job(
        title=title,
        location=location,
        country=country,
        category=category,
        experience_level=experience_level,
        source="test",
        url=url,
    )
    job.description = description
    return job


class TestNormalizeTitle:
    def test_strips_gender_markers(self):
        assert main.normalize_title("Software Developer (m/w/d)") == "software developer"

    def test_strips_parenthetical(self):
        assert main.normalize_title("Entwickler (w/m)") == "entwickler"

    def test_collapses_whitespace(self):
        assert main.normalize_title("  Data   &   AI  ") == "data ai"

    def test_removes_single_letters(self):
        assert main.normalize_title("C Developer") == "developer"

    def test_preserves_unicode_letters(self):
        assert main.normalize_title("後端 工程師") == "後端 工程師"
        assert main.normalize_title("Software Müller (m/w/d)") == "software müller"


class TestDedupeResults:
    def test_removes_same_title_and_host(self):
        results = [
            {"title": "Software Developer (m/w/d)", "url": "https://a.example/1", "source": "x"},
            {"title": "Software Developer", "url": "https://a.example/2", "source": "x"},
        ]
        assert len(main.dedupe_results(results)) == 1

    def test_keeps_different_hosts(self):
        results = [
            {"title": "Software Developer", "url": "https://a.example/1", "source": "x"},
            {"title": "Software Developer", "url": "https://b.example/1", "source": "y"},
        ]
        assert len(main.dedupe_results(results)) == 2

    def test_relative_url_uses_source(self):
        results = [
            {"title": "Software Developer", "url": "/job/1", "source": "x"},
            {"title": "Software Developer", "url": "/job/2", "source": "x"},
            {"title": "Software Developer", "url": "/job/3", "source": "y"},
        ]
        assert len(main.dedupe_results(results)) == 2

    def test_preserves_order(self):
        results = [
            {"title": "Alpha", "url": "https://a.example/1", "source": "x"},
            {"title": "Beta", "url": "https://a.example/2", "source": "x"},
        ]
        assert [r["title"] for r in main.dedupe_results(results)] == ["Alpha", "Beta"]

    def test_keeps_distinct_chinese_titles_on_same_host(self):
        results = [
            {"title": "量化系統工程師", "url": "https://cake.example/1", "source": "talent_taiwan"},
            {"title": "網路維運工程師", "url": "https://cake.example/2", "source": "talent_taiwan"},
        ]
        assert len(main.dedupe_results(results)) == 2

    def test_still_dedupes_same_chinese_title(self):
        results = [
            {"title": "後端工程師", "url": "https://cake.example/1", "source": "talent_taiwan"},
            {"title": "後端工程師", "url": "https://cake.example/2", "source": "talent_taiwan"},
        ]
        assert len(main.dedupe_results(results)) == 1

    def test_empty_normalized_titles_never_collapse(self):
        results = [
            {"title": "!!!", "url": "https://x.example/1", "source": "x"},
            {"title": "???", "url": "https://x.example/2", "source": "x"},
        ]
        assert len(main.dedupe_results(results)) == 2


class TestBuildResult:
    def test_fields(self):
        job = make_job("Software Developer")
        result = main.build_result(job, {"score": 3}, "linz_area")
        assert result["title"] == "Software Developer"
        assert result["source"] == "test"
        assert result["location_match"] == "linz_area"
        assert result["match_details"] == {"score": 3}


class TestFilterJobs:
    def test_keeps_relevant_location_and_domain(self):
        jobs = [make_job("Junior Software Developer")]
        results, tiers = main.filter_jobs(jobs, CONFIG)
        assert len(results) == 1
        assert tiers["graduate"] == 1
        assert tiers["excluded"] == 0

    def test_drops_non_location(self):
        jobs = [make_job("Software Developer", location="Berlin", country="Germany")]
        results, _ = main.filter_jobs(jobs, CONFIG)
        assert results == []

    def test_drops_unrelated_domain(self):
        jobs = [make_job("Lagerlogistiker")]
        results, _ = main.filter_jobs(jobs, CONFIG)
        assert results == []

    def test_excludes_senior_but_counts_tier(self):
        jobs = [make_job("Senior Software Developer")]
        results, tiers = main.filter_jobs(jobs, CONFIG)
        assert results == []
        assert tiers["excluded"] == 1

    def test_sorts_graduate_before_possible(self):
        jobs = [
            make_job("Software Developer", url="https://x.example/1"),
            make_job("Junior Software Developer", url="https://x.example/2"),
        ]
        results, _ = main.filter_jobs(jobs, CONFIG)
        assert results[0]["match_details"]["graduate_tier"] == "graduate"
        assert results[1]["match_details"]["graduate_tier"] == "possible"

    def test_dedupes(self):
        jobs = [
            make_job("Software Developer (m/w/d)", url="https://x.example/1"),
            make_job("Software Developer", url="https://x.example/2"),
        ]
        results, _ = main.filter_jobs(jobs, CONFIG)
        assert len(results) == 1

    def test_ranks_linz_above_remote(self):
        jobs = [
            make_job("Software Developer", location="Remote", country="", url="https://x.example/1"),
            make_job("Software Developer", location="Linz", country="Austria", url="https://x.example/2"),
        ]
        results, _ = main.filter_jobs(jobs, CONFIG)
        assert results[0]["location_match"] == "linz_area"
        assert results[0]["location_weight"] == 5

    def test_ranks_vienna_above_remote(self):
        jobs = [
            make_job("Software Developer", location="Remote", country="", url="https://x.example/1"),
            make_job("Software Developer", location="Vienna", country="Austria", url="https://x.example/2"),
        ]
        results, _ = main.filter_jobs(jobs, CONFIG)
        assert results[0]["location_match"] == "vienna_area"


class TestDomainCandidates:
    def test_keeps_domain_roles_only(self):
        jobs = [
            make_job("Python Engineer", description="You need 4 years of experience"),
            make_job("Retail Manager", description="Work closely with our software team"),
            make_job("Data Scientist"),
        ]
        candidates = main.domain_candidates(jobs, main.load_config())
        assert [job.title for job in candidates] == ["Python Engineer", "Data Scientist"]


class TestSaveResults:
    def test_writes_both_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        results = [main.build_result(make_job("Software Developer"), {"graduate_tier": "graduate"}, "linz_area")]
        output = main.save_results(results, total=5, output_path="results.json")

        assert output["total_jobs_found"] == 5
        assert output["matching_jobs"] == 1
        assert "check_date" in output
        assert json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))["check_date"].endswith("+00:00")

        assert (tmp_path / "results.json").exists()
        assert (tmp_path / "docs" / "results.json").exists()

        saved = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
        assert saved["results"][0]["title"] == "Software Developer"
        assert saved == json.loads((tmp_path / "docs" / "results.json").read_text(encoding="utf-8"))


class TestGetScraperInstances:
    def test_known(self):
        assert isinstance(main.get_scraper_instances([]), list)

    def test_unknown_warns(self, capsys):
        main.get_scraper_instances(["does-not-exist"])
        assert "Unknown scraper" in capsys.readouterr().out

    def test_configured_scrapers_are_registered(self):
        assert set(main.load_config()["scrapers"]) == set(main.SCRAPERS)


class TestPrintSummary:
    def test_prints_counts(self, capsys):
        output = {
            "check_date": "2026-01-01T00:00:00",
            "total_jobs_found": 10,
            "matching_jobs": 1,
            "results": [
                {
                    "title": "Software Developer",
                    "location": "Linz, Austria",
                    "country": "Austria",
                    "category": "Dev",
                    "experience_level": "Entry",
                    "source": "test",
                    "url": "https://x.example/1",
                    "location_match": "linz_area",
                    "match_details": {
                        "is_junior_level": True,
                        "is_software_dev": True,
                        "is_math_related": False,
                        "graduate_tier": "graduate",
                        "required_years": None,
                    },
                }
            ],
        }
        main.print_summary(output, {"graduate": 1, "possible": 0, "excluded": 0})
        out = capsys.readouterr().out
        assert "Matching jobs: 1" in out
        assert "Software Developer" in out


class FakeScraper(BaseScraper):
    jobs = []

    @property
    def name(self) -> str:
        return "fake"

    def fetch_jobs(self) -> list[Job]:
        return list(self.jobs)


class TestMainEndToEnd:
    def test_returns_zero_with_matches(self, tmp_path, monkeypatch, capsys):
        FakeScraper.jobs = [make_job("Junior Software Developer")]
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main, "load_config", lambda: CONFIG)
        monkeypatch.setattr(main, "SCRAPERS", {"fake": FakeScraper})
        assert main.main() == 0
        assert (tmp_path / "results.json").exists()
        output = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
        assert output["matching_jobs"] == 1

    def test_returns_one_without_matches(self, tmp_path, monkeypatch):
        FakeScraper.jobs = [make_job("Lagerlogistiker")]
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main, "load_config", lambda: CONFIG)
        monkeypatch.setattr(main, "SCRAPERS", {"fake": FakeScraper})
        assert main.main() == 1
