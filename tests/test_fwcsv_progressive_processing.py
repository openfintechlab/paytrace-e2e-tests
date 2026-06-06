from __future__ import annotations

import csv
import time

import pytest

from tests.support.config import E2ESettings
from tests.support.csv_batches import PaymentBatch
from tests.support.database import DispatchDatabase
from tests.support.waiters import (
    wait_for_dispatch_rows,
    wait_for_file_to_leave_inbox,
    wait_for_processed_dispatch_rows,
    wait_for_registry_completion,
    wait_for_response_file,
)


DEFAULT_PROGRESSIVE_RECORD_COUNTS = (5, 50, 100, 1000)
RESPONSE_CSV_HEADERS = [
    "TransferId",
    "TransactionId",
    "Status",
    "ResponseCode",
    "ResponseMessage",
    "ProcessedTimestamp",
]


def _parse_progressive_record_counts(raw_counts: str | None) -> tuple[int, ...]:
    if raw_counts is None:
        return DEFAULT_PROGRESSIVE_RECORD_COUNTS

    counts: list[int] = []
    for raw_count in raw_counts.split(","):
        stripped_count = raw_count.strip()
        if not stripped_count:
            continue

        try:
            count = int(stripped_count)
        except ValueError as exc:
            raise pytest.UsageError(
                "--progressive-record-counts must contain comma-separated "
                f"integers, got {raw_count!r}."
            ) from exc

        if count <= 0:
            raise pytest.UsageError(
                "--progressive-record-counts values must be positive integers, "
                f"got {count}."
            )

        counts.append(count)

    if not counts:
        raise pytest.UsageError(
            "--progressive-record-counts must include at least one positive integer."
        )

    return tuple(counts)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "record_count" not in metafunc.fixturenames:
        return

    record_counts = _parse_progressive_record_counts(
        metafunc.config.getoption("--progressive-record-counts")
    )
    metafunc.parametrize(
        "record_count",
        record_counts,
        ids=[f"{record_count}-records" for record_count in record_counts],
    )


def _as_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise AssertionError(f"Expected an int-compatible value, got {type(value).__name__}.")


def test_fwcsv_progressively_processes_shared_inbox_files(
    record_count: int,
    settings: E2ESettings,
    dispatch_database: DispatchDatabase,
) -> None:
    batch = PaymentBatch.create(record_count)
    start_time = time.perf_counter()

    assert len(set(batch.transfer_ids)) == record_count

    inbox_file = batch.publish_to_inbox(settings)

    wait_for_file_to_leave_inbox(
        inbox_file,
        timeout_seconds=settings.processing_timeout_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
    )

    dispatch_rows = wait_for_dispatch_rows(
        dispatch_database,
        transfer_ids=batch.transfer_ids,
        expected_count=record_count,
        timeout_seconds=settings.processing_timeout_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
    )
    assert {str(row["transfer_id"]) for row in dispatch_rows} == set(batch.transfer_ids)

    registry_entry = wait_for_registry_completion(
        dispatch_database,
        filename=batch.filename,
        expected_row_count=record_count,
        timeout_seconds=settings.processing_timeout_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
    )
    assert registry_entry["status"] == "COMPLETED"
    assert _as_int(registry_entry["row_count"]) == record_count

    processed_rows = wait_for_processed_dispatch_rows(
        dispatch_database,
        transfer_ids=batch.transfer_ids,
        timeout_seconds=settings.processing_timeout_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
    )

    assert len(processed_rows) == record_count
    assert all(row["status"] == "PROCESSED" for row in processed_rows)

    response_file = wait_for_response_file(
        dispatch_database,
        filename=batch.filename,
        response_dir=settings.response_dir,
        timeout_seconds=settings.processing_timeout_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
    )
    assert response_file.parent == settings.response_dir

    with response_file.open("r", encoding="utf-8", newline="") as response_handle:
        reader = csv.DictReader(response_handle)
        response_rows = list(reader)

    assert reader.fieldnames == RESPONSE_CSV_HEADERS
    assert len(response_rows) == record_count
    assert {row["TransferId"] for row in response_rows} == set(batch.transfer_ids)
    assert all(row["Status"] in {"PROCESSED", "FAILED"} for row in response_rows)

    elapsed_seconds = time.perf_counter() - start_time
    print(
        f"Batch {batch.filename} with {record_count} records processed in "
        f"{elapsed_seconds:.2f} seconds."
    )
