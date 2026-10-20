import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class DelaySchedule:
    task_a_delay_s: float = 0.0
    task_b_delay_s: float = 0.0

class ChaosScheduler:
    """
    Injects microsecond-level calibrated pauses at async yield boundaries
    to force deterministic thread-interleaving states without modifying source code.
    """
    def __init__(self, schedule: Optional[DelaySchedule] = None):
        self.schedule = schedule or DelaySchedule()
        self.active_tasks: Dict[str, float] = {}

    def set_schedule(self, schedule: DelaySchedule) -> None:
        self.schedule = schedule

    async def yield_point(self, task_name: str) -> float:
        t0 = time.perf_counter()
        delay = 0.0
        if "alpha" in task_name.lower() or "task_1" in task_name.lower():
            delay = self.schedule.task_a_delay_s
        elif "beta" in task_name.lower() or "task_2" in task_name.lower():
            delay = self.schedule.task_b_delay_s

        if delay > 0:
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(0)  # Standard event-loop cooperative yield

        elapsed_us = (time.perf_counter() - t0) * 1e6
        return elapsed_us
