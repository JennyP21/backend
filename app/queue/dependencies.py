from functools import lru_cache

from app.queue.base import TaskQueue
from app.queue.celery import CeleryTaskQueue


@lru_cache
def get_task_queue() -> TaskQueue:
    return CeleryTaskQueue()