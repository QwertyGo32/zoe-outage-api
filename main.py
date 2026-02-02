from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys

from api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ZOE Outage API",
    description="""
    API для отримання графіків відключень електроенергії з сайту ZOE.COM.UA

    ## Основні можливості

    * **Отримання актуальних графіків** - найсвіжіші дані про відключення
    * **Графіки по чергах** - інформація для конкретної черги (1.1, 1.2, тощо)
    * **Кешування** - швидкий доступ до даних (кеш на 30 хвилин)
    * **REST API** - зручна інтеграція з мобільними додатками

    ## Використання

    Для iPhone віджету використовуйте endpoint `/api/schedules/queue/{queue_id}`

    Приклад: `/api/schedules/queue/1.1`
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - для доступу з веб-додатків та мобільних пристроїв
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшені обмежити конкретними доменами
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальний обробник помилок"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc)
        }
    )


@app.on_event("startup")
async def startup_event():
    """Виконується при запуску додатку"""
    logger.info("=" * 60)
    logger.info("ZOE Outage API Starting...")
    logger.info("=" * 60)
    logger.info("API Documentation: http://localhost:8000/docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Виконується при зупинці додатку"""
    logger.info("ZOE Outage API Shutting down...")


if __name__ == "__main__":
    import uvicorn
    import os

    # Railway sets PORT environment variable
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    )
