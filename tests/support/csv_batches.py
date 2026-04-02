from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from tests.support.config import E2ESettings


def _schema_headers() -> list[str]:
    schema_path = (
        Path(__file__).resolve().parents[3]
        / "paytrace-file-ingest-csv"
        / "src"
        / "domain"
        / "payment_instruction.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return list(schema["properties"].keys())


CSV_HEADERS = _schema_headers()


@dataclass(frozen=True)
class PaymentBatch:
    record_count: int
    batch_id: str
    filename: str
    transfer_ids: tuple[str, ...]

    @classmethod
    def create(cls, record_count: int) -> "PaymentBatch":
        batch_id = uuid.uuid4().hex[:8]
        filename = f"payments_{record_count}_{batch_id}.csv"
        transfer_ids = tuple(_build_transfer_id(batch_id, index) for index in range(1, record_count + 1))
        if len(set(transfer_ids)) != record_count:
            raise ValueError("Transfer ids must be unique within a generated batch.")
        return cls(
            record_count=record_count,
            batch_id=batch_id,
            filename=filename,
            transfer_ids=transfer_ids,
        )

    def publish_to_inbox(self, settings: E2ESettings) -> Path:
        temp_path = settings.generated_dir / self.filename
        inbox_path = settings.inbox_dir / self.filename

        with temp_path.open("w", encoding="utf-8", newline="") as csv_handle:
            writer = csv.DictWriter(csv_handle, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for index, transfer_id in enumerate(self.transfer_ids, start=1):
                writer.writerow(_build_payment_record(index=index, transfer_id=transfer_id))

        temp_path.replace(inbox_path)
        return inbox_path


def _build_transfer_id(batch_id: str, index: int) -> str:
    return f"E2E-{batch_id}-{index:04d}"


def _build_payment_record(*, index: int, transfer_id: str) -> dict[str, str]:
    transaction_timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "transfer_id": transfer_id,
        "transfer_type": "DOMESTIC",
        "transaction_datetime": transaction_timestamp,
        "requested_execution_date": "2026-04-03",
        "amount": f"{1000 + index:.2f}",
        "currency": "AED",
        "purpose_code": "SUPP",
        "charge_bearer": "SHAR",
        "exchange_rate": "",
        "debtor_name": "Sharjah Trading LLC",
        "debtor_country": "AE",
        "debtor_account_scheme": "IBAN",
        "debtor_account_id": f"AE07033123456789012{index:03d}",
        "debtor_bank_id_scheme": "BIC",
        "debtor_bank_id": "SIBUAEAD",
        "creditor_name": f"Desert Supplies FZC {index:03d}",
        "creditor_country": "AE",
        "creditor_account_scheme": "IBAN",
        "creditor_account_id": f"AE17054012345678901{index:03d}",
        "creditor_bank_id_scheme": "BIC",
        "creditor_bank_id": "EBILAEAD",
        "intermediary_bank_bic": "",
        "remittance_unstructured": f"E2E invoice {index:03d}",
        "remittance_reference": f"INV-{index:05d}",
    }
