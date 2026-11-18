from datetime import datetime, timedelta, timezone

from history import _fingerprint, _is_stale, apply_history, load_history, save_history


def item(title="Software Developer", url="https://x.example/j/1", source="x", **kw):
    data = {"title": title, "url": url, "source": source}
    data.update(kw)
    return data


class TestFingerprint:
    def test_uses_url_host_and_path(self):
        assert _fingerprint(item(url="https://x.example/j/1")) == "x.example/j/1"

    def test_preserves_distinct_query_identifiers(self):
        first = "https://jobs.voestalpine.com/index.php?ac=jobad&id=21454"
        second = "https://jobs.voestalpine.com/index.php?ac=jobad&id=21132"
        assert _fingerprint(item(url=first)) != _fingerprint(item(url=second))

    def test_preserves_case_sensitive_path(self):
        assert _fingerprint(item(url="https://x.example/Jobs/A")) != _fingerprint(
            item(url="https://x.example/jobs/a")
        )

    def test_normalizes_url_host_case(self):
        assert _fingerprint(item(url="https://X.EXAMPLE/j/1")) == "x.example/j/1"

    def test_relative_url_uses_source_and_title(self):
        key = _fingerprint(item(url="/job/1", source="scch", title="Software Engineer"))
        assert key == "scch:software engineer"

    def test_missing_url(self):
        assert _fingerprint({"title": "Dev", "source": "x", "url": ""}) == "x:dev"


class TestApplyHistory:
    def test_first_run_marks_new(self):
        results, history = apply_history([item()], {})
        assert results[0]["is_new"] is True
        assert results[0]["first_seen"] == results[0]["last_seen"]
        assert len(history) == 1

    def test_second_run_not_new(self):
        now = datetime(2026, 1, 1, 12, 0, 0)
        _, history = apply_history([item()], {}, now=now)
        later = now + timedelta(days=1)
        results, _ = apply_history([item()], history, now=later)
        assert results[0]["is_new"] is False
        assert results[0]["first_seen"] == now.isoformat()

    def test_new_query_identifier_is_detected_as_new(self):
        now = datetime(2026, 1, 1)
        base_url = "https://jobs.voestalpine.com/index.php?ac=jobad&id="
        _, history = apply_history([item(url=f"{base_url}1"), item(url=f"{base_url}2")], {}, now=now)
        assert len(history) == 2

        later = now + timedelta(days=7)
        results, _ = apply_history(
            [item(url=f"{base_url}1"), item(url=f"{base_url}2"), item(url=f"{base_url}3")],
            history,
            now=later,
        )
        assert [result["is_new"] for result in results] == [False, False, True]

    def test_stale_entries_purged(self):
        now = datetime(2026, 1, 1)
        _, history = apply_history([item(url="https://x.example/j/old")], {}, now=now)
        later = now + timedelta(days=90)
        _, history2 = apply_history(
            [item(url="https://x.example/j/new")], history, now=later, max_age_days=60
        )
        assert not any("old" in key for key in history2)
        assert any("new" in key for key in history2)

    def test_timezone_aware_timestamp(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        results, _ = apply_history([item()], {}, now=now)
        assert results[0]["first_seen"].endswith("+00:00")

    def test_mixed_naive_and_aware_timestamps_do_not_crash(self):
        now = datetime(2026, 1, 15, tzinfo=timezone.utc)
        assert _is_stale({"last_seen": "2026-01-01T00:00:00"}, now, 10) is True
        assert _is_stale(
            {"last_seen": "2026-01-01T00:00:00+00:00"}, datetime(2026, 1, 15), 10
        ) is True

    def test_recent_unseen_entry_kept(self):
        now = datetime(2026, 1, 1)
        _, history = apply_history([item(url="https://x.example/j/1")], {}, now=now)
        later = now + timedelta(days=10)
        _, history2 = apply_history([], history, now=later, max_age_days=60)
        assert len(history2) == 1


class TestLoadSave:
    def test_load_missing_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert load_history() == {}

    def test_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        save_history({"a": {"title": "Dev", "last_seen": "2026-01-01T00:00:00"}})
        assert "a" in load_history()

    def test_corrupt_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "history.json").write_text("not json", encoding="utf-8")
        assert load_history() == {}
