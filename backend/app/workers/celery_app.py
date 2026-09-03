"""Celery application configuration."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "auri",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks",
        "app.workers.retention_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=60 * 30,
    task_time_limit=60 * 45,
    result_expires=60 * 60 * 24,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "retention-purge-daily": {
            "task": "retention.purge_all_orgs",
            "schedule": 86400.0,
            "kwargs": {"dry_run": False},
        },
    },
)
