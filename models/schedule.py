from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class OutageTime(BaseModel):
    """Час відключення"""
    start: str = Field(..., description="Час початку відключення (HH:MM)")
    end: str = Field(..., description="Час кінця відключення (HH:MM)")

    class Config:
        json_schema_extra = {
            "example": {
                "start": "03:00",
                "end": "08:00"
            }
        }


class QueueSchedule(BaseModel):
    """Графік для конкретної черги"""
    queue: str = Field(..., description="Номер черги (наприклад, 1.1)")
    outages: List[OutageTime] = Field(default_factory=list, description="Список відключень")
    status: str = Field(default="unknown", description="Статус: active, cancelled, unknown")

    class Config:
        json_schema_extra = {
            "example": {
                "queue": "1.1",
                "outages": [
                    {"start": "03:00", "end": "08:00"},
                    {"start": "12:00", "end": "17:00"}
                ],
                "status": "active"
            }
        }


class Schedule(BaseModel):
    """Повний графік відключень"""
    title: str = Field(..., description="Заголовок графіку")
    date: Optional[str] = Field(None, description="Дата графіку")
    content_text: str = Field(..., description="Текстовий вміст")
    queues: List[str] = Field(default_factory=list, description="Список черг")
    times: List[List[str]] = Field(default_factory=list, description="Часи відключень")
    created_at: Optional[datetime] = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "title": "25 СІЧНЯ ПО ЗАПОРІЗЬКІЙ ОБЛАСТІ ДІЯТИМУТЬ ГПВ",
                "date": "2025-01-25",
                "content_text": "Години відсутності електропостачання...",
                "queues": ["1.1", "1.2", "2.1"],
                "times": [["03:00", "08:00"], ["12:00", "17:00"]]
            }
        }


class ScheduleResponse(BaseModel):
    """Відповідь API з графіком"""
    success: bool = Field(default=True)
    data: Optional[Schedule] = None
    queue_data: Optional[QueueSchedule] = None
    message: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.now)
    cache_hit: bool = Field(default=False, description="Чи дані взяті з кешу")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "title": "25 СІЧНЯ ПО ЗАПОРІЗЬКІЙ ОБЛАСТІ ДІЯТИМУТЬ ГПВ",
                    "queues": ["1.1", "1.2"],
                    "times": [["03:00", "08:00"]]
                },
                "updated_at": "2025-01-25T10:30:00Z",
                "cache_hit": False
            }
        }


class HealthResponse(BaseModel):
    """Статус здоров'я API"""
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
