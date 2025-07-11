import asyncio
from collections import defaultdict


class JobLock:
    """Async context manager providing in-process locking per job."""

    _locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, job_id: str):
        self.job_id = job_id
        self._lock = self._locks[job_id]

    async def __aenter__(self):
        await self._lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._lock.release()

    async def acquire(self):
        await self._lock.acquire()

    def release(self):
        if self._lock.locked():
            self._lock.release()
