from __future__ import annotations

import pytest

from tests.support.config import E2ESettings
from tests.support.database import DispatchDatabase


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--progressive-record-counts",
        action="store",
        default=None,
        help=(
            "Comma-separated record counts for progressive CSV processing "
            "tests, for example: 5,10,15."
        ),
    )


@pytest.fixture(scope="session")
def settings() -> E2ESettings:
    loaded = E2ESettings.load()
    loaded.inbox_dir.mkdir(parents=True, exist_ok=True)
    loaded.response_dir.mkdir(parents=True, exist_ok=True)
    loaded.generated_dir.mkdir(parents=True, exist_ok=True)
    return loaded


@pytest.fixture(scope="session")
def dispatch_database(settings: E2ESettings) -> DispatchDatabase:
    return DispatchDatabase(settings)
