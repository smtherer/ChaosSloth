import asyncio
from collections import defaultdict
from typing import Dict, List, Set, Optional

class LockOrderGraph:
    """
    Dynamically hooks asyncio.Lock to audit Coffman's Circular-Wait Invariant.
    Constructs a dynamic Directed Graph of lock acquisition orders at runtime.
    """
    def __init__(self):
        self.held_locks: Dict[str, List[str]] = defaultdict(list)
        self.edges: Dict[str, Set[str]] = defaultdict(set)
        self.detected_cycles: List[List[str]] = []
        self._original_acquire = None

    def install_hook(self):
        """Monkeypatches asyncio.Lock.acquire to track runtime dependencies."""
        if self._original_acquire is not None:
            return
        self._original_acquire = asyncio.Lock.acquire
        graph = self

        async def hooked_acquire(lock_self):
            task = asyncio.current_task()
            task_name = task.get_name() if task else "unknown_task"
            lock_id = f"Lock_{hex(id(lock_self))[-6:]}"
            
            # Check if this task already holds another lock
            cycle = graph.record_acquire_attempt(task_name, lock_id)
            if cycle:
                graph.detected_cycles.append(cycle)
                
            res = await graph._original_acquire(lock_self)
            graph.record_acquire_success(task_name, lock_id)
            return res

        asyncio.Lock.acquire = hooked_acquire

    def uninstall_hook(self):
        if self._original_acquire is not None:
            asyncio.Lock.acquire = self._original_acquire
            self._original_acquire = None

    def record_acquire_attempt(self, task_name: str, lock_name: str) -> Optional[List[str]]:
        for held in self.held_locks[task_name]:
            self.edges[held].add(lock_name)
            cycle = self._find_cycle(lock_name, held, [lock_name])
            if cycle:
                return cycle
        return None

    def record_acquire_success(self, task_name: str, lock_name: str):
        if lock_name not in self.held_locks[task_name]:
            self.held_locks[task_name].append(lock_name)

    def record_release(self, task_name: str, lock_name: str):
        if lock_name in self.held_locks[task_name]:
            self.held_locks[task_name].remove(lock_name)

    def _find_cycle(self, current: str, target: str, path: List[str]) -> Optional[List[str]]:
        if current == target:
            return path
        for neighbor in self.edges.get(current, []):
            if neighbor not in path:
                res = self._find_cycle(neighbor, target, path + [neighbor])
                if res:
                    return res
        return None
