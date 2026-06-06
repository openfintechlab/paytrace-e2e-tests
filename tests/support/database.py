from __future__ import annotations

from collections.abc import Sequence

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from tests.support.config import E2ESettings


class DispatchDatabase:
    def __init__(self, settings: E2ESettings) -> None:
        self._settings = settings

    def fetch_dispatch_rows(self, transfer_ids: Sequence[str]) -> list[dict[str, object]]:
        if not transfer_ids:
            return []
        query = """
            SELECT transfer_id, file_id, row_number, request_queue, status, error_message
            FROM oftl_fwcsv_row_dispatch
            WHERE transfer_id = ANY(%s)
            ORDER BY row_number
        """
        return self._fetch_all(query, (list(transfer_ids),))

    def fetch_registry_entry(self, filename: str) -> dict[str, object] | None:
        rows = self._fetch_all(
            """
            SELECT
                file_id,
                filename,
                row_count,
                status,
                error_message,
                response_status,
                response_file_name,
                response_file_generated_at
            FROM oftl_fwcsv_registry
            WHERE filename = %s
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (filename,),
        )
        return rows[0] if rows else None

    def _fetch_all(self, query: str, params: tuple[object, ...]) -> list[dict[str, object]]:
        with psycopg2.connect(
            host=self._settings.db_host,
            port=self._settings.db_port,
            user=self._settings.db_username,
            password=self._settings.db_password,
            dbname=self._settings.db_name,
        ) as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    sql.SQL("SET search_path TO {}").format(
                        sql.Identifier(self._settings.db_schema)
                    )
                )
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
