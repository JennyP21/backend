from celery import Celery

from app.config import settings

celery_app = Celery(
    "raglab",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True
)

celery_app.autodiscover_tasks([
    "app.worker",
])