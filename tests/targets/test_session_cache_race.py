import asyncio
from typing import Dict, List, Any

class SharedSessionStore:
    """
    Demonstration target representing a typical high-throughput web cache.
    Contains an unsynchronized read-modify-write hazard across yield steps.
    """
    def __init__(self):
        self.sessions: Dict[str, List[str]] = {}

    async def update_session(self, user_id: str, token: str):
        # Read step
        current = self.sessions.get(user_id, [])
        # Simulated cooperative I/O yield (where race conditions manifest)
        await asyncio.sleep(0.0001)
        # Write step (Unsynchronized state overwrite)
        current.append(token)
        self.sessions[user_id] = current

async def test_flaky_cache():
    store = SharedSessionStore()
    user = "usr_42"
    t1 = asyncio.create_task(store.update_session(user, "tok_1"))
    t2 = asyncio.create_task(store.update_session(user, "tok_2"))
    await asyncio.gather(t1, t2)
    # Flaky assertion: Under rare collisions, tokens overwrite to length 1
    assert len(store.sessions[user]) == 2
