"""Data loading helpers for the EV range model."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from random import Random
from typing import Iterable, List, Sequence, Tuple

FEATURES: Sequence[str] = (
    "battery_kwh",
    "efficiency_wh_per_km",
    "curb_weight_kg",
    "drag_coefficient",
    "top_speed_kmh",
)
TARGET = "range_km"


@dataclass(frozen=True)
class Record:
    """Typed representation of a single EV specification row."""

    model: str
    battery_kwh: float
    efficiency_wh_per_km: float
    curb_weight_kg: float
    drag_coefficient: float
    top_speed_kmh: float
    range_km: float

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Record":
        return cls(
            model=row["model"],
            battery_kwh=float(row["battery_kwh"]),
            efficiency_wh_per_km=float(row["efficiency_wh_per_km"]),
            curb_weight_kg=float(row["curb_weight_kg"]),
            drag_coefficient=float(row["drag_coefficient"]),
            top_speed_kmh=float(row["top_speed_kmh"]),
            range_km=float(row["range_km"]),
        )


def load_dataset(path: str | Path) -> List[Record]:
    """Load the EV specification dataset from ``path``."""

    path = Path(path)
    with path.open("r", newline="") as handle:
        reader = csv.DictReader(handle)
        return [Record.from_row(row) for row in reader]


def to_matrix(records: Iterable[Record]) -> Tuple[List[List[float]], List[float]]:
    """Convert ``records`` into a feature matrix and target vector."""

    features: List[List[float]] = []
    target: List[float] = []
    for record in records:
        features.append([getattr(record, name) for name in FEATURES])
        target.append(getattr(record, TARGET))
    return features, target


def train_test_split(
    records: Sequence[Record],
    *,
    test_ratio: float = 0.2,
    seed: int | None = 7,
) -> Tuple[List[Record], List[Record]]:
    """Split ``records`` into train and test partitions."""

    if not 0 < test_ratio < 1:
        raise ValueError("test_ratio must be between 0 and 1")

    indices = list(range(len(records)))
    random = Random(seed)
    random.shuffle(indices)

    cutoff = int(len(records) * (1 - test_ratio))
    train_idx, test_idx = indices[:cutoff], indices[cutoff:]

    train = [records[i] for i in train_idx]
    test = [records[i] for i in test_idx]
    return train, test
