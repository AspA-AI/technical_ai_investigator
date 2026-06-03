"""Historical incident generation and seeding (Phase 4)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from utils.logger import get_logger
from vectorstore.incident_store import IncidentVectorStore

log = get_logger(__name__)

NASA_COLUMN_NAMES = [
    "unit_id",
    "cycle",
    "op_setting_1",
    "op_setting_2",
    "op_setting_3",
    *[f"sensor_{i}" for i in range(1, 22)],
]

NASA_DATASET_METADATA: dict[str, dict[str, str]] = {
    "FD001": {
        "failure": "NASA C-MAPSS FD001 turbofan degradation trajectory",
        "root_cause": "HPC degradation",
        "resolution": "Inspect and replace high-pressure compressor components",
        "condition": "sea level operating conditions",
    },
    "FD002": {
        "failure": "NASA C-MAPSS FD002 turbofan degradation trajectory",
        "root_cause": "HPC degradation under multiple operating conditions",
        "resolution": "Inspect compressor health and validate operating-condition effects",
        "condition": "multiple operating conditions",
    },
    "FD003": {
        "failure": "NASA C-MAPSS FD003 turbofan degradation trajectory",
        "root_cause": "HPC degradation and fan degradation",
        "resolution": "Inspect compressor and fan assemblies",
        "condition": "sea level operating conditions",
    },
    "FD004": {
        "failure": "NASA C-MAPSS FD004 turbofan degradation trajectory",
        "root_cause": "HPC degradation and fan degradation under multiple operating conditions",
        "resolution": "Inspect compressor and fan assemblies across operating regimes",
        "condition": "multiple operating conditions",
    },
}


class HistoricalIncidentService:
    def __init__(self, db: Session, vector_store: IncidentVectorStore | None = None) -> None:
        self._db = db
        self._vector_store = vector_store or IncidentVectorStore(db)

    def seed_nasa_dataset(self, dataset_dir: str | Path = "datasets/raw/nasa") -> int:
        """Convert NASA C-MAPSS training trajectories into incident records."""

        dataset_path = Path(dataset_dir)
        train_files = sorted(dataset_path.glob("train_FD*.txt"))
        if not train_files:
            raise FileNotFoundError(f"No NASA training files found in {dataset_path}")

        seeded = 0
        for file_path in train_files:
            fd_code = self._extract_fd_code(file_path.name)
            metadata = NASA_DATASET_METADATA.get(fd_code)
            if metadata is None:
                log.warning("Skipping unknown NASA dataset file: %s", file_path.name)
                continue

            df = pd.read_csv(
                file_path,
                sep=r"\s+",
                header=None,
                names=NASA_COLUMN_NAMES,
                engine="python",
            )
            if df.empty:
                log.warning("Skipping empty NASA dataset file: %s", file_path.name)
                continue

            for unit_id, unit_df in df.groupby("unit_id"):
                unit_df = unit_df.sort_values("cycle")
                incident_id = int(f"{fd_code[2:]}{int(unit_id):03d}")
                summary_text = self._build_summary_text(
                    fd_code=fd_code,
                    unit_id=int(unit_id),
                    unit_df=unit_df,
                    metadata=metadata,
                )
                self._vector_store.upsert_incident(
                    incident_id=incident_id,
                    summary_text=summary_text,
                    failure=metadata["failure"],
                    root_cause=metadata["root_cause"],
                    resolution=metadata["resolution"],
                )
                seeded += 1

        log.service("Seeded %s NASA historical incidents", seeded)
        return seeded

    @staticmethod
    def _extract_fd_code(filename: str) -> str:
        match = re.search(r"(FD\d{3})", filename)
        if match is None:
            raise ValueError(f"Could not determine NASA dataset code from: {filename}")
        return match.group(1)

    @staticmethod
    def _build_summary_text(
        *,
        fd_code: str,
        unit_id: int,
        unit_df: pd.DataFrame,
        metadata: dict[str, str],
    ) -> str:
        first_row = unit_df.iloc[0]
        last_row = unit_df.iloc[-1]

        sensor_deltas: list[tuple[str, float]] = []
        for sensor_name in [f"sensor_{i}" for i in range(1, 22)]:
            delta = float(last_row[sensor_name]) - float(first_row[sensor_name])
            sensor_deltas.append((sensor_name, delta))

        top_changes = sorted(sensor_deltas, key=lambda item: abs(item[1]), reverse=True)[:3]
        change_text = ", ".join(
            f"{sensor} {delta:+.2f}" for sensor, delta in top_changes
        )

        cycles = int(unit_df["cycle"].max())
        return (
            f"NASA C-MAPSS {fd_code} unit {unit_id} ran for {cycles} cycles under "
            f"{metadata['condition']}. End-of-life sensor changes were strongest in "
            f"{change_text}. The run-to-failure pattern is consistent with "
            f"{metadata['root_cause']}."
        )
