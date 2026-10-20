import pandas as pd
from typing import List
from .schema import ExecutionRecord

class TelemetryCollector:
    def __init__(self):
        self._records: List[ExecutionRecord] = []

    def record(self, record: ExecutionRecord) -> None:
        self._records.append(record)

    def to_dataframe(self) -> pd.DataFrame:
        if not self._records:
            return pd.DataFrame()
        return pd.DataFrame([r.to_dict() for r in self._records])

    def clear(self) -> None:
        self._records.clear()

    @property
    def total_runs(self) -> int:
        return len(self._records)

    @property
    def failure_count(self) -> int:
        return sum(r.is_race_condition for r in self._records)
