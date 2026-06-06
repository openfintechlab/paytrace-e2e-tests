from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        os.environ.setdefault(key.strip(), _strip_wrapping_quotes(raw_value.strip()))


def _resolve_path(value: str, *, base_dir: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path).resolve()


@dataclass(frozen=True)
class E2ESettings:
    project_root: Path
    generated_dir: Path
    fwcsv_rootdir: Path
    inbox_dir: Path
    response_dir: Path
    db_username: str
    db_password: str
    db_host: str
    db_port: int
    db_name: str
    db_schema: str
    poll_interval_seconds: float
    processing_timeout_seconds: float

    @classmethod
    def load(cls) -> "E2ESettings":
        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")

        fwcsv_rootdir = _resolve_path(
            os.environ.get("OFTL_E2E_FWCSV_ROOTDIR", "../fwcsv"),
            base_dir=project_root,
        )
        return cls(
            project_root=project_root,
            generated_dir=project_root / ".generated",
            fwcsv_rootdir=fwcsv_rootdir,
            inbox_dir=fwcsv_rootdir / "inbox",
            response_dir=fwcsv_rootdir / "response",
            db_username=os.environ.get("OFTL_POSTGRESDB_USERNAME", "admin"),
            db_password=os.environ.get("OFTL_POSTGRESDB_PASSWORD", ""),
            db_host=os.environ.get("OFTL_POSTGRESDB_HOST", "localhost"),
            db_port=int(os.environ.get("OFTL_POSTGRESDB_PORT", "5432")),
            db_name=os.environ.get("OFTL_POSTGRESDB_NAME", "paytrace"),
            db_schema=os.environ.get("OFTL_POSTGRESDB_SCHEMA", "public"),
            poll_interval_seconds=float(os.environ.get("OFTL_E2E_POLL_INTERVAL_SECONDS", "1")),
            processing_timeout_seconds=float(
                os.environ.get("OFTL_E2E_PROCESSING_TIMEOUT_SECONDS", "180")
            ),
        )
