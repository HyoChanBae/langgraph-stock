from celery import Celery

from app.config.settings import REDIS_URL


celery_app = Celery(
    "trading_worker",
    broker=f"{REDIS_URL}/0",
    backend=f"{REDIS_URL}/1",
    include=[
        "app.tasks"
    ],
)
