import asyncio
import random
from typing import Dict, List

class SharedSessionStore:
    def __init__(self):
        self.sessions: Dict[str, List[str]] = {}

    async def update_session(self, user_id: str, token: str):
        current = self.sessions.get(user_id, [])
        # True intermittent yield: only collides when both tasks draw overlapping delay windows
        if random.random() < 0.45:
            await asyncio.sleep(random.uniform(0.0002, 0.0008))
        else:
            await asyncio.sleep(0.00001)
        current.append(token)
        self.sessions[user_id] = current
