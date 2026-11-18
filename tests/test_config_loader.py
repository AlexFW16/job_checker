import json
from pathlib import Path

import config_loader


REPO_ROOT = Path(__file__).resolve().parent.parent


class TestLoadConfig:
    def test_missing_file_returns_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = config_loader.load_config()
        assert config == config_loader.DEFAULT_CONFIG

    def test_reads_existing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.json").write_text(json.dumps({"scrapers": ["tgw"]}), encoding="utf-8")
        assert config_loader.load_config() == {"scrapers": ["tgw"]}

    def test_default_is_deep_copied(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = config_loader.load_config()
        config["scrapers"].append("mutated")
        assert "mutated" not in config_loader.DEFAULT_CONFIG["scrapers"]


class TestSaveConfig:
    def test_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        payload = {"scrapers": ["a", "b"], "filters": {"countries": ["Austria"]}}
        config_loader.save_config(payload)
        assert json.loads((tmp_path / "config.json").read_text(encoding="utf-8")) == payload


class TestGetDefaultConfig:
    def test_returns_copy(self):
        first = config_loader.get_default_config()
        first["scrapers"].append("mutated")
        second = config_loader.get_default_config()
        assert "mutated" not in second["scrapers"]

    def test_has_expected_sections(self):
        config = config_loader.get_default_config()
        for key in ("keywords", "graduate_filter", "filters", "scrapers"):
            assert key in config

    def test_matches_committed_config_json(self):
        # Guards against the embedded fallback drifting from the repo config.
        committed = json.loads((REPO_ROOT / "config.json").read_text(encoding="utf-8"))
        assert config_loader.DEFAULT_CONFIG == committed


class TestTaiwanConfig:
    def test_default_matches_committed_config_taiwan_json(self):
        committed = json.loads((REPO_ROOT / "config_taiwan.json").read_text(encoding="utf-8"))
        assert config_loader.DEFAULT_TAIWAN_CONFIG == committed

    def test_load_taiwan_config_applies_overrides(self):
        config = config_loader.load_taiwan_config()
        assert config["region"] == "taiwan"
        assert config["filters"]["region"] == "taiwan"
        assert config["filters"]["countries"] == ["Taiwan"]
        assert config["filters"]["fetch_details"] is False
        assert config["scrapers"] == ["talent_taiwan"]

    def test_load_taiwan_config_extends_defaults(self):
        config = config_loader.load_taiwan_config()
        # English defaults survive...
        assert "backend" in config["keywords"]["software_dev"]
        assert config["graduate_filter"]["exclude_min_years"] == 4
        # ...and the Taiwan extras are appended without duplication.
        assert "系統工程師" in config["keywords"]["software_dev"]
        assert "工程師" not in config["keywords"]["software_dev"]
        assert "資深" in config["graduate_filter"]["seniority_exclude"]
        assert "經理" in config["graduate_filter"]["seniority_downgrade"]

    def test_get_default_taiwan_config_returns_copy(self):
        first = config_loader.get_default_taiwan_config()
        first["scrapers"].append("mutated")
        assert "mutated" not in config_loader.get_default_taiwan_config()["scrapers"]
