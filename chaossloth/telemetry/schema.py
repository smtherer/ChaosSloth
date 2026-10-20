from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass(frozen=True)
class ExecutionRecord:
    run_id: int
    task_count: int
    task_a_yield_us: float
    task_b_yield_us: float
    queue_latency_us: float
    context_switches: int
    shared_mutations: int
    is_race_condition: int  # 1 = Bug/Collision triggered, 0 = Clean pass

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
