from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import logging

from models.schedule import (
    ScheduleResponse,
    Schedule,
    QueueSchedule,
    OutageTime,
    HealthResponse
)
from services.scraper import ScraperService
from services.cache import CacheService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
scraper = ScraperService()
cache = CacheService(ttl_minutes=30)


@router.get("/", tags=["Info"])
async def root():
    """Root endpoint з інформацією про API"""
    return {
        "name": "ZOE Outage API",
        "version": "1.0.0",
        "description": "API для отримання графіків відключень електроенергії",
        "endpoints": {
            "health": "/health",
            "latest_schedule": "/api/schedules/latest",
            "queue_schedule": "/api/schedules/queue/{queue_id}",
            "all_queues": "/api/queues",
            "cache_info": "/api/cache/info"
        },
        "documentation": "/docs"
    }


@router.get("/health", response_model=HealthResponse, tags=["Info"])
async def health_check():
    """Перевірка здоров'я API"""
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@router.get("/api/schedules/latest", response_model=ScheduleResponse, tags=["Schedules"])
async def get_latest_schedule(
    force_refresh: bool = Query(False, description="Примусово оновити дані, ігноруючи кеш")
):
    """
    Отримати найсвіжіший актуальний графік відключень

    Args:
        force_refresh: Якщо True, ігнорує кеш і завантажує свіжі дані
    """
    try:
        cache_key = "latest_schedule"
        cache_hit = False

        # Try to get from cache first
        if not force_refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                cache_hit = True
                return ScheduleResponse(
                    success=True,
                    data=Schedule(**cached_data),
                    cache_hit=cache_hit,
                    updated_at=datetime.now()
                )

        # Fetch fresh data
        logger.info("Fetching latest schedule from ZOE website")
        schedule_data = scraper.get_latest_schedule()

        if not schedule_data:
            raise HTTPException(
                status_code=404,
                detail="Не вдалося знайти актуальний графік"
            )

        # Cache the result
        cache.set(cache_key, schedule_data)

        return ScheduleResponse(
            success=True,
            data=Schedule(**schedule_data),
            cache_hit=cache_hit,
            updated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_latest_schedule: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Помилка отримання графіку: {str(e)}"
        )


@router.get("/api/schedules/queue/{queue_id}", response_model=ScheduleResponse, tags=["Schedules"])
async def get_queue_schedule(
    queue_id: str,
    force_refresh: bool = Query(False, description="Примусово оновити дані")
):
    """
    Отримати графік для конкретної черги

    Args:
        queue_id: Номер черги (наприклад, 1.1, 2.2, тощо)
        force_refresh: Якщо True, ігнорує кеш
    """
    try:
        # Validate queue_id format
        if not queue_id or not queue_id.replace('.', '').isdigit():
            raise HTTPException(
                status_code=400,
                detail="Невірний формат черги. Приклад: 1.1, 2.2, тощо"
            )

        cache_key = f"queue_{queue_id}"
        cache_hit = False

        # Try cache first
        if not force_refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                cache_hit = True
                return ScheduleResponse(
                    success=True,
                    queue_data=QueueSchedule(
                        queue=cached_data['queue'],
                        outages=[OutageTime(**o) for o in cached_data.get('outages', [])],
                        status=cached_data.get('status', 'unknown')
                    ),
                    cache_hit=cache_hit,
                    updated_at=datetime.now()
                )

        # Fetch fresh data
        logger.info(f"Fetching schedule for queue {queue_id}")
        queue_data = scraper.get_queue_schedule(queue_id)

        if not queue_data:
            raise HTTPException(
                status_code=404,
                detail=f"Графік для черги {queue_id} не знайдено"
            )

        # Cache the result
        cache.set(cache_key, queue_data)

        outages = [OutageTime(**o) for o in queue_data.get('outages', [])]

        return ScheduleResponse(
            success=True,
            queue_data=QueueSchedule(
                queue=queue_data['queue'],
                outages=outages,
                status=queue_data.get('status', 'active')
            ),
            message=queue_data.get('message'),
            cache_hit=cache_hit,
            updated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_queue_schedule: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Помилка отримання графіку для черги {queue_id}: {str(e)}"
        )


@router.get("/api/queues", tags=["Queues"])
async def get_all_queues():
    """
    Отримати список всіх доступних черг
    """
    try:
        cache_key = "all_queues"

        # Try cache
        cached_data = cache.get(cache_key)
        if cached_data:
            return {
                "success": True,
                "queues": cached_data,
                "cache_hit": True
            }

        # Fetch fresh data
        queues = scraper.get_all_queues()
        cache.set(cache_key, queues)

        return {
            "success": True,
            "queues": queues,
            "cache_hit": False
        }

    except Exception as e:
        logger.error(f"Error in get_all_queues: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Помилка отримання списку черг: {str(e)}"
        )


@router.get("/api/cache/info", tags=["Cache"])
async def get_cache_info():
    """
    Отримати інформацію про кеш
    """
    try:
        info = cache.get_cache_info()
        return {
            "success": True,
            "cache_info": info
        }
    except Exception as e:
        logger.error(f"Error in get_cache_info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Помилка отримання інформації про кеш: {str(e)}"
        )


@router.delete("/api/cache/clear", tags=["Cache"])
async def clear_cache(key: Optional[str] = Query(None, description="Ключ для очищення (або весь кеш)")):
    """
    Очистити кеш

    Args:
        key: Опціонально - конкретний ключ для очищення. Якщо не вказано, очищається весь кеш
    """
    try:
        cache.clear(key)
        return {
            "success": True,
            "message": f"Кеш {'для ключа ' + key if key else 'повністю'} очищено"
        }
    except Exception as e:
        logger.error(f"Error in clear_cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Помилка очищення кешу: {str(e)}"
        )
