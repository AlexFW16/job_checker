import json

import pytest
import requests

from scrapers import common
from scrapers.base import Job
from scrapers.common import (
    build_url,
    cap_jobs,
    clean_html_text,
    enrich_descriptions,
    extract_erecruiter_model,
    is_valid_job_title,
    parse_erecruiter_jobs,
    parse_rss_items,
)

ERECRUITER_HTML = """
<html><body>
<script>
new JobList($("#job-list"), "a, template, with commas", {"Jobs": [
  {"Title": "Software Developer (m/w/d)", "Location": "Linz, Österreich", "Id": 123, "ExternalUrl": "", "JobProfile": "R&D"},
  {"Title": "Senior Architect", "Location": "Vienna", "Id": 124},
  {"Title": "Reset filters", "Location": "Linz", "Id": 125}
], "TotalItems": 3});
</script>
</body></html>
"""


class FakeResponse:
    def __init__(self, status_code, text="", payload=None):
        self.status_code = status_code
        self.text = text if payload is None else json.dumps(payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class TestBuildUrl:
    def test_relative(self):
        assert build_url("https://example.com/a/b", "/c") == "https://example.com/c"

    def test_protocol_relative(self):
        assert build_url("https://example.com", "//cdn.example.com/x") == "https://cdn.example.com/x"

    def test_absolute(self):
        assert build_url("https://example.com", "https://other.com/x") == "https://other.com/x"

    def test_empty_href(self):
        assert build_url("https://example.com", "") == ""


class TestIsValidJobTitle:
    @pytest.mark.parametrize(
        "title",
        [
            "Reset filters",
            "Did you mean",
            "Zur Bewerbung",
            "zur Position",
            "Job Search",
            "Show more",
            "Show more jobs",
            "Find vacancies in Linz",
            "Aug 9, 2026",
            "2026-08-09",
            "123",
            "{{ title }}",
            "Job {id}",
            "",
            "git",
        ],
    )
    def test_rejects_junk(self, title):
        assert is_valid_job_title(title) is False

    @pytest.mark.parametrize(
        "title",
        [
            "Software Engineer (m/w/d)",
            "Data & AI Engineer",
            "Junior Fullstack Developer",
            "Werkstudent IT (w/m)",
            "Navigation Engineer",
            "數據分析",
            "資安工程",
            "後端工程師",
        ],
    )
    def test_accepts_real_titles(self, title):
        assert is_valid_job_title(title) is True

    def test_rejects_overlong(self):
        assert is_valid_job_title("x" * 201) is False

    def test_strips_whitespace(self):
        assert is_valid_job_title("  Software Engineer  ") is True


class TestCapJobs:
    def test_caps(self):
        assert cap_jobs(list(range(300)), limit=10) == list(range(10))

    def test_shorter_than_limit(self):
        assert cap_jobs([1, 2, 3], limit=10) == [1, 2, 3]


class TestErecruiter:
    def test_extract_model_with_commas_in_template(self):
        model = extract_erecruiter_model(ERECRUITER_HTML)
        assert model is not None
        assert len(model["Jobs"]) == 3

    def test_extract_returns_none_without_model(self):
        assert extract_erecruiter_model("<html>nothing here</html>") is None

    def test_parse_filters_junk_and_builds_jobs(self):
        jobs = parse_erecruiter_jobs(ERECRUITER_HTML, "https://jobs.keba.com")
        titles = [j.title for j in jobs]
        assert "Reset filters" not in titles
        assert len(jobs) == 2

        first = jobs[0]
        assert first.country == "Austria"
        assert first.url == "https://jobs.keba.com/Job/123"
        assert first.category == "R&D"

    def test_parse_uses_external_url_when_present(self):
        html = (
            '<script>new JobList(a, b, {"Jobs": [{"Title": "Dev Job", '
            '"Location": "Linz", "Id": 7, "ExternalUrl": "https://x.example/j/7"}]});</script>'
        )
        jobs = parse_erecruiter_jobs(html, "https://base.example")
        assert jobs[0].url == "https://x.example/j/7"

    def test_parse_non_austrian_location_has_no_country(self):
        html = (
            '<script>new JobList(a, b, {"Jobs": [{"Title": "Dev Job", '
            '"Location": "Munich", "Id": 7}]});</script>'
        )
        jobs = parse_erecruiter_jobs(html, "https://base.example")
        assert jobs[0].country == ""


class TestParseRssItems:
    def test_finds_items(self):
        xml = "<rss><channel><item><title>A</title></item><item><title>B</title></item></channel></rss>"
        items = parse_rss_items(xml)
        assert [i.findtext("title") for i in items] == ["A", "B"]


class TestCleanHtmlText:
    def test_strips_scripts_and_urls(self):
        html = "<html><body><main>Hello <script>bad()</script>world https://foo.com/x a.php</main></body></html>"
        text = clean_html_text(html)
        assert "Hello" in text
        assert "world" in text
        assert "bad()" not in text
        assert "https://foo.com" not in text
        assert "a.php" not in text

    def test_truncates(self):
        html = "<main>" + ("word " * 1000) + "</main>"
        assert len(clean_html_text(html, max_chars=50)) <= 50


class TestRequestText:
    def test_returns_text_on_success(self, monkeypatch):
        monkeypatch.setattr(common.requests, "get", lambda *a, **k: FakeResponse(200, "hello"))
        assert common._request_text("https://x") == "hello"

    def test_retries_then_succeeds(self, monkeypatch):
        calls = {"n": 0}

        def fake_get(*args, **kwargs):
            calls["n"] += 1
            return FakeResponse(500) if calls["n"] == 1 else FakeResponse(200, "ok")

        monkeypatch.setattr(common.requests, "get", fake_get)
        monkeypatch.setattr(common.time, "sleep", lambda *_: None)
        assert common._request_text("https://x", retries=2) == "ok"
        assert calls["n"] == 2

    def test_raises_after_retries(self, monkeypatch):
        monkeypatch.setattr(common.requests, "get", lambda *a, **k: FakeResponse(503))
        monkeypatch.setattr(common.time, "sleep", lambda *_: None)
        with pytest.raises(RuntimeError):
            common._request_text("https://x", retries=1)

    def test_does_not_retry_permanent_client_error(self, monkeypatch):
        calls = {"n": 0}

        def fake_get(*args, **kwargs):
            calls["n"] += 1
            return FakeResponse(400)

        monkeypatch.setattr(common.requests, "get", fake_get)
        with pytest.raises(RuntimeError):
            common._request_text("https://x", retries=2)
        assert calls["n"] == 1

    def test_fetch_json_parses(self, monkeypatch):
        monkeypatch.setattr(common.requests, "get", lambda *a, **k: FakeResponse(200, payload={"a": 1}))
        assert common.fetch_json("https://x") == {"a": 1}


class TestEnrichDescriptions:
    def test_fetches_only_missing_http(self, monkeypatch):
        jobs = [
            Job("A", "Linz", "Austria", "", "", "t", url="https://x/1"),
            Job("B", "Linz", "Austria", "", "", "t", url="https://x/2", description="already"),
            Job("C", "Linz", "Austria", "", "", "t", url="/relative"),
        ]
        monkeypatch.setattr(common, "fetch_text", lambda url, **k: f"desc for {url}")
        fetched = enrich_descriptions(jobs)
        assert fetched == 1
        assert jobs[0].description == "desc for https://x/1"
        assert jobs[1].description == "already"
        assert jobs[2].description == ""

    def test_respects_max_fetches(self, monkeypatch):
        jobs = [Job(f"J{i}", "Linz", "Austria", "", "", "t", url=f"https://x/{i}") for i in range(5)]
        monkeypatch.setattr(common, "fetch_text", lambda url, **k: "d")
        fetched = enrich_descriptions(jobs, max_fetches=2)
        assert fetched == 2
        assert jobs[0].description == "d"
        assert jobs[1].description == "d"
        assert jobs[2].description == ""

    def test_distributes_limited_fetches_across_sources(self, monkeypatch):
        jobs = [
            Job("A1", "Linz", "Austria", "", "", "a", url="https://x/1"),
            Job("A2", "Linz", "Austria", "", "", "a", url="https://x/2"),
            Job("B1", "Wien", "Austria", "", "", "b", url="https://x/3"),
        ]
        monkeypatch.setattr(common, "fetch_text", lambda url, **k: "d")
        assert enrich_descriptions(jobs, max_fetches=2) == 2
        assert jobs[0].description == "d"
        assert jobs[1].description == ""
        assert jobs[2].description == "d"

    def test_fetch_failure_leaves_empty(self, monkeypatch):
        jobs = [Job("A", "Linz", "Austria", "", "", "t", url="https://x/1")]

        def boom(url, **k):
            raise RuntimeError("network down")

        monkeypatch.setattr(common, "fetch_text", boom)
        assert enrich_descriptions(jobs) == 1
        assert jobs[0].description == ""
