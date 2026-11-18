import shutil
import subprocess
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    ("filename", "data_url"),
    [("index.html", "results.json"), ("taiwan.html", "results.taiwan.json")],
)
def test_dashboard_uses_shared_assets_and_expected_data(filename, data_url):
    html = (ROOT / "docs" / filename).read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    assert soup.find("link", href="dashboard.css") is not None
    assert soup.find("script", src="dashboard.js") is not None
    assert data_url in html
    for element_id in ("filters", "reset-filters", "results-info", "job-list"):
        assert soup.find(id=element_id) is not None


def test_dashboard_javascript_smoke():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is unavailable")
    result = subprocess.run(
        [node, str(ROOT / "tests" / "dashboard_smoke.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Dashboard helper smoke tests passed" in result.stdout
