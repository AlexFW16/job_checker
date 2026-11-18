from matching import matches_location
from scrapers import greenhouse
from scrapers.greenhouse import GitLabScraper

GITLAB_JSON = {
    "jobs": [
        {
            "id": 1001,
            "title": "Backend Engineer (Python), AI Engineering",
            "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/1001",
            "location": {"name": "Remote, Canada; Remote, Poland; Remote, United Kingdom"},
        },
        {
            "id": 1002,
            "title": "Backend Engineer, US Only",
            "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/1002",
            "location": {"name": "Remote, United States"},
        },
        {
            "id": 1003,
            "title": "Frontend Developer",
            "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/1003",
            "location": {"name": "Remote Ireland; Remote, Spain"},
        },
        {
            "id": 1004,
            "title": "Software Engineer, Linz",
            "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/1004",
            "location": {"name": "Linz, Austria"},
        },
        {
            "id": 1005,
            "title": "Reset filters",
            "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/1005",
            "location": {"name": "Remote, Poland"},
        },
    ]
}


class TestGitLabScraper:
    def test_parse_keeps_european_remote_and_austria(self):
        jobs = GitLabScraper()._parse_results(GITLAB_JSON)
        assert len(jobs) == 3
        assert jobs[0].title == "Backend Engineer (Python), AI Engineering"
        assert jobs[0].country == "Poland"
        assert jobs[0].company == "GitLab"
        assert jobs[0].url.endswith("/1001")
        assert jobs[0].raw["id"] == 1001

    def test_irish_remote_is_available_for_eu(self):
        jobs = GitLabScraper()._parse_results(GITLAB_JSON)
        frontend = next(job for job in jobs if job.title == "Frontend Developer")
        assert frontend.country == "Ireland"
        matched, reason = matches_location(
            frontend,
            {"countries": ["Austria"], "remote_worldwide": True, "remote_eu": True},
        )
        assert matched is True
        assert reason == "remote_eu"

    def test_linz_on_site_matches_locally(self):
        jobs = GitLabScraper()._parse_results(GITLAB_JSON)
        linz = next(job for job in jobs if job.title == "Software Engineer, Linz")
        assert linz.country == "Austria"
        assert matches_location(linz, {"countries": ["Austria"]}) == (True, "linz_area")

    def test_parse_dedupes_by_api_id(self):
        data = {"jobs": [GITLAB_JSON["jobs"][0], GITLAB_JSON["jobs"][0]]}
        assert len(GitLabScraper()._parse_results(data)) == 1

    def test_parse_rejects_non_dict(self):
        assert GitLabScraper()._parse_results([]) == []

    def test_fetch_jobs_offline(self, monkeypatch):
        monkeypatch.setattr(greenhouse, "fetch_json", lambda url: GITLAB_JSON)
        jobs = GitLabScraper().fetch_jobs()
        assert len(jobs) == 3

    def test_fetch_jobs_returns_empty_on_error(self, monkeypatch):
        def boom(url):
            raise RuntimeError("network down")

        monkeypatch.setattr(greenhouse, "fetch_json", boom)
        assert GitLabScraper().fetch_jobs() == []
