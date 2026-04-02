from __future__ import annotations

from collections.abc import Callable, Sequence
import time
from pathlib import Path
from typing import TypeVar

from tests.support.database import DispatchDatabase


T = TypeVar("T")


def _as_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise AssertionError(f"Expected an int-compatible value, got {type(value).__name__}.")


def wait_until(
    *,
    description: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
    predicate: Callable[[], T | None],
) -> T:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(poll_interval_seconds)
    raise AssertionError(f"Timed out while waiting for {description}.")


def wait_for_file_to_leave_inbox(
    inbox_file: Path,
    *,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> None:
    wait_until(
        description=f"{inbox_file.name} to leave inbox",
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        predicate=lambda: not inbox_file.exists(),
    )


def wait_for_registry_completion(
    database: DispatchDatabase,
    *,
    filename: str,
    expected_row_count: int,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> dict[str, object]:
    def _predicate() -> dict[str, object] | None:
        entry = database.fetch_registry_entry(filename)
        if not entry:
            return None
        if entry.get("status") == "failed":
            raise AssertionError(f"Registry entry failed for {filename}: {entry}")
        # The current file watcher persists total CSV lines processed, which includes the header row.
        expected_registry_row_count = expected_row_count + 1
        if (
            entry.get("status") == "completed"
            and _as_int(entry.get("row_count", 0) or 0) == expected_registry_row_count
        ):
            return entry
        return None

    return wait_until(
        description=f"registry completion for {filename}",
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        predicate=_predicate,
    )


def wait_for_dispatch_rows(
    database: DispatchDatabase,
    *,
    transfer_ids: Sequence[str],
    expected_count: int,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[dict[str, object]]:
    def _predicate() -> list[dict[str, object]] | None:
        rows = database.fetch_dispatch_rows(transfer_ids)
        if any(row.get("status") == "failed" for row in rows):
            raise AssertionError(f"Dispatch rows contain failures: {rows}")
        if len(rows) == expected_count:
            return rows
        return None

    return wait_until(
        description=f"{expected_count} dispatch rows",
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        predicate=_predicate,
    )


def wait_for_processed_dispatch_rows(
    database: DispatchDatabase,
    *,
    transfer_ids: Sequence[str],
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> list[dict[str, object]]:
    expected_count = len(transfer_ids)

    def _predicate() -> list[dict[str, object]] | None:
        rows = database.fetch_dispatch_rows(transfer_ids)
        if any(row.get("status") == "failed" for row in rows):
            raise AssertionError(f"Dispatch rows contain failures: {rows}")
        if len(rows) != expected_count:
            return None
        if all(row.get("status") == "processed" for row in rows):
            return rows
        return None

    return wait_until(
        description=f"{expected_count} processed dispatch rows",
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        predicate=_predicate,
    )
