import json
from pathlib import Path

import pytest

from app.main import app


@pytest.mark.contract
def test_openapi_required_paths_present() -> None:
    spec = app.openapi()
    paths = set(spec.get("paths", {}).keys())

    expected_path_file = Path(__file__).with_name("expected_openapi_paths.json")
    expected_paths = set(json.loads(expected_path_file.read_text(encoding="utf-8")))

    missing = sorted(expected_paths - paths)
    assert missing == []
