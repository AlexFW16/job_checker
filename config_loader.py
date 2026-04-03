import json
from pathlib import Path

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "keywords": {
        "junior_level": [
            "junior",
            "graduate",
            "entry level",
            "recent graduate",
            "trainee",
            "apprentice",
            "intern",
            "co-op",
            "co op",
            "student",
            "werkstudent",
            "praktikum",
        ],
        "software_dev": [
            "software",
            "developer",
            "programmer",
            "engineer",
            "coding",
            "programming",
            " it",
            "it ",
            "computer",
            "full stack",
            "fullstack",
            "backend",
            "frontend",
            "web developer",
            "application",
            "controls",
            "devops",
            "dev ops",
            "simulation",
            "embedded",
            "sap",
            "abap",
            "c#",
            "java",
            "python",
            "javascript",
        ],
        "mathematics": [
            "math",
            "mathematician",
            "mathematics",
            "statistic",
            "algorithm",
            "data ",
            " data",
            "analytics",
            "analysis",
            "quantitative",
            "numerical",
            "simulation",
            "optimization",
            "modelling",
            "modeling",
        ],
    },
    "filters": {
        "countries": ["Austria"],
        "remote": True,
        "experience_levels": [
            "Recent Graduates",
            "Students",
            "Apprentices",
            "Experienced Professionals",
        ],
    },
    "scrapers": ["tgw"],
}


def load_config() -> dict:
    path = Path(CONFIG_FILE)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return DEFAULT_CONFIG


def save_config(config: dict) -> None:
    Path(CONFIG_FILE).write_text(json.dumps(config, indent=2), encoding="utf-8")


def get_default_config() -> dict:
    return DEFAULT_CONFIG.copy()
