import asyncio
from typing import Dict

class MultiResourceServer:
    """
    High-concurrency microservice managing multiple disjoint state dictionaries.
    Exhibits independent read-modify-write hazard windows on both `sessions` and `counters`.
    """
    def __init__(self):
        self.sessions: Dict[str, int] = {}
        self.counters: Dict[str, int] = {}

    async def handle_request(self, client_id: str):
        # Hazard 1: Read session
        curr_sess = self.sessions.get(client_id, 0)
        # Hazard 2: Read counter
        curr_count = self.counters.get(client_id, 0)

        # Microtask yield point (interleaving hazard window)
        await asyncio.sleep(0.0001)

        # Write steps
        self.sessions[client_id] = curr_sess + 1
        self.counters[client_id] = curr_count + 10
