from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class MemoryAccessEvent:
    coroutine_id: str
    access_type: str  # 'READ' or 'WRITE'
    variable_name: str
    clock: Dict[str, int]

class VectorClockEngine:
    """
    Implements Leslie Lamport's Happens-Before Relation: e1 ≺ e2
    Detects concurrent unsynchronized access mathematically across coroutines.
    """
    def __init__(self):
        self.clocks: Dict[str, Dict[str, int]] = {}
        self.access_history: Dict[str, List[MemoryAccessEvent]] = {}

    def tick(self, coroutine_id: str) -> Dict[str, int]:
        if coroutine_id not in self.clocks:
            self.clocks[coroutine_id] = {coroutine_id: 0}
        self.clocks[coroutine_id][coroutine_id] += 1
        return self.clocks[coroutine_id].copy()

    def record_access(self, coroutine_id: str, var_name: str, access_type: str) -> bool:
        clock = self.tick(coroutine_id)
        current_event = MemoryAccessEvent(coroutine_id, access_type, var_name, clock)

        if var_name not in self.access_history:
            self.access_history[var_name] = []

        collision_detected = False
        # Audit against past events for unsynchronized concurrency
        for past in self.access_history[var_name]:
            if past.coroutine_id != current_event.coroutine_id:
                if past.access_type == "WRITE" or current_event.access_type == "WRITE":
                    c1 = past.clock.get(past.coroutine_id, 0)
                    c2 = current_event.clock.get(past.coroutine_id, 0)
                    # Neither event strictly precedes the other
                    if c1 > c2:
                        collision_detected = True

        self.access_history[var_name].append(current_event)
        return collision_detected
