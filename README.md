# PayTrace E2E Tests

This project contains pytest-based end-to-end checks for the PayTrace file
ingest pipeline. The first scenario validates progressive processing for CSV
files dropped into the shared `fwcsv/inbox` directory and confirms that every
generated `transfer_id` reaches `status='PROCESSED'` in
`oftl_fwcsv_row_dispatch`. It also verifies that a response CSV is generated in
the shared `fwcsv/response` directory.

## Prerequisites

- Python `3.11+`
- `uv`
- PostgreSQL reachable with the configured schema and tables
- Running PayTrace services for file ingestion and payment processing

## Environment Variables

The project reads configuration from `.env` and supports these variables:

- `OFTL_POSTGRESDB_USERNAME`
- `OFTL_POSTGRESDB_PASSWORD`
- `OFTL_POSTGRESDB_HOST`
- `OFTL_POSTGRESDB_PORT`
- `OFTL_POSTGRESDB_NAME`
- `OFTL_POSTGRESDB_SCHEMA`
- `OFTL_E2E_FWCSV_ROOTDIR`
- `OFTL_E2E_POLL_INTERVAL_SECONDS`
- `OFTL_E2E_PROCESSING_TIMEOUT_SECONDS`

## Startup / Test Command

Install dependencies:

```bash
uv sync
```

Run the e2e test suite:

```bash
uv run pytest tests -v
```

Run progressive CSV checks with custom record counts:

```bash
uv run pytest tests/test_fwcsv_progressive_processing.py -v --progressive-record-counts=5,10,15
```

## Health / Shared Path Expectations

This test project does not expose HTTP health endpoints. It expects the shared
file exchange root to contain `inbox` and `response` directories, typically:

```text
../fwcsv/inbox
../fwcsv/response
```

`response` is always resolved under `OFTL_E2E_FWCSV_ROOTDIR`.

## Current Coverage

- Progressive CSV ingestion checks for `5`, `50`, `100`, and `1000` records by default
- Unique `transfer_id` generation per file
- Database verification that all rows reach `PROCESSED` status
- Response CSV verification under `${OFTL_E2E_FWCSV_ROOTDIR}/response`
