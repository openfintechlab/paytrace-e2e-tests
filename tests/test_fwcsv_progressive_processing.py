from __future__ import annotations

import pytest

from tests.support.config import E2ESettings
from tests.support.csv_batches import PaymentBatch
from tests.support.database import DispatchDatabase
from tests.support.waiters import (
    wait_for_dispatch_rows,
    wait_for_file_to_leave_inbox,
    wait_for_processed_dispatch_rows,
    wait_for_registry_completion,
)


PROGRESSIVE_RECORD_COUNTS = (5, 50, 100)


def _as_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise AssertionError(f"Expected an int-compatible value, got {type(value).__name__}.")


@pytest.mark.parametrize("record_count", PROGRESSIVE_RECORD_COUNTS)
def test_fwcsv_progressively_processes_shared_inbox_files(
    record_count: int,
    settings: E2ESettings,
    dispatch_database: DispatchDatabase,
) -> None:
    batch = PaymentBatch.create(record_count)

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
    assert registry_entry["status"] == "completed"
    assert _as_int(registry_entry["row_count"]) == record_count

    processed_rows = wait_for_processed_dispatch_rows(
        dispatch_database,
        transfer_ids=batch.transfer_ids,
        timeout_seconds=settings.processing_timeout_seconds,
        poll_interval_seconds=settings.poll_interval_seconds,
    )

    assert len(processed_rows) == record_count
    assert all(row["status"] == "processed" for row in processed_rows)
