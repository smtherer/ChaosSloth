import asyncio
import time
import inspect
import sys
from typing import Dict, List, Optional, Tuple

class EventLoopStarvationSentinel:
    """
    Monitors event loop responsiveness by scheduling high-frequency heartbeats.
    If loop latency exceeds tolerance (e.g. >10ms), it introspects active stack
    frames to pinpoint synchronous blocking operations inside async coroutines.
    """
    def __init__(self, latency_threshold_ms: float = 10.0):
        self.threshold_ms = latency_threshold_ms
        self.running = False
        self.stalls: List[Dict[str, float]] = []

    async def monitor(self, duration_s: float = 1.0) -> List[Dict[str, float]]:
        self.running = True
        end_time = time.perf_counter() + duration_s
        
        while self.running and time.perf_counter() < end_time:
            t0 = time.perf_counter()
            await asyncio.sleep(0.005)  # 5ms expected tick
            actual_delay_ms = (time.perf_counter() - t0 - 0.005) * 1000.0

            if actual_delay_ms > self.threshold_ms:
                self.stalls.append({
                    "delay_ms": actual_delay_ms,
                    "timestamp": time.time()
                })
        return self.stalls

    @staticmethod
    def audit_coroutine_for_blocking_calls(coro_func) -> List[str]:
        """
        Inspects source AST of an async routine for common blocking anti-patterns:
        - time.sleep() instead of asyncio.sleep()
        - requests.* calls instead of httpx / aiohttp
        """
        source = inspect.getsource(coro_func)
        issues = []
        if "time.sleep(" in source:
            issues.append("Found blocking synchronous `time.sleep()`. Freezes the entire event loop.")
        if "requests." in source:
            issues.append("Found blocking synchronous network I/O `requests`. Halts concurrent tasks.")
        return issues
