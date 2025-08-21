from .celery_app import celery_app as celery
from .extensions import cache
from time import sleep

@celery.task(name="tasks.heavy_compute")
def heavy_compute(x: int, y: int) -> int:
    sleep(2)
    result = x + y
    cache_key = f"sum:{x}:{y}"
    cache.set(cache_key, result, timeout=600)
    return result
