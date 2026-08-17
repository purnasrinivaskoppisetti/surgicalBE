# app/main.py

import logging
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.database import engine
from app.models.models import Base
from app.api.router import api_router

from app.services.shipping_tracking_service import (
    ShippingTrackingService,
)


# ============================================================
# LOGGING CONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger("surgical")


# ============================================================
# DATABASE SESSION FACTORY
# ============================================================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


# ============================================================
# SCHEDULER
# ============================================================

scheduler = AsyncIOScheduler()


# ============================================================
# BLUE DART TRACKING JOB
# ============================================================

async def blue_dart_tracking_job():

    logger.info(
        "================================================"
    )

    logger.info(
        "Blue Dart tracking job started"
    )

    logger.info(
        "================================================"
    )

    try:

        async with AsyncSessionLocal() as db:

            result = (
                await ShippingTrackingService
                .update_all_shipments(db)
            )

            logger.info(
                "Blue Dart tracking job completed"
            )

            logger.info(
                "Tracking result: %s",
                result,
            )

    except Exception:

        logger.exception(
            "Blue Dart tracking job failed"
        )

    logger.info(
        "================================================"
    )


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info(
        "Starting Surgical World API..."
    )

    # ========================================================
    # CREATE DATABASE TABLES
    # ========================================================

    try:

        async with engine.begin() as conn:

            await conn.run_sync(
                Base.metadata.create_all
            )

        logger.info(
            "Database tables initialized successfully"
        )

    except Exception:

        logger.exception(
            "Database initialization failed"
        )

        raise

    # ========================================================
    # START BLUE DART SCHEDULER
    # ========================================================

    try:

        scheduler.add_job(

            blue_dart_tracking_job,

            trigger="interval",

            minutes=1,

            id="blue_dart_tracking_job",

            replace_existing=True,

            max_instances=15,

            coalesce=True,
        )

        scheduler.start()

        logger.info(
            "Blue Dart tracking scheduler started"
        )

        logger.info(
            "Tracking interval: every 30 minutes"
        )

    except Exception:

        logger.exception(
            "Failed to start Blue Dart scheduler"
        )

    # ========================================================
    # APPLICATION STARTED
    # ========================================================

    logger.info(
        "Surgical World API startup completed"
    )

    # ========================================================
    # APPLICATION RUNNING
    # ========================================================

    try:

        yield

    # ========================================================
    # APPLICATION SHUTDOWN
    # ========================================================

    finally:

        logger.info(
            "Surgical World API shutting down..."
        )

        # ----------------------------------------------------
        # STOP SCHEDULER
        # ----------------------------------------------------

        try:

            if scheduler.running:

                scheduler.shutdown(
                    wait=False
                )

                logger.info(
                    "Blue Dart scheduler stopped"
                )

        except Exception:

            logger.exception(
                "Error while stopping scheduler"
            )

        # ----------------------------------------------------
        # DISPOSE DATABASE ENGINE
        # ----------------------------------------------------

        try:

            await engine.dispose()

            logger.info(
                "Database engine disposed"
            )

        except Exception:

            logger.exception(
                "Error disposing database engine"
            )

        logger.info(
            "Surgical World API shutdown completed"
        )


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(

    title="Surgical World API",

    version="1.0.0",

    lifespan=lifespan,
)


# ============================================================
# STATIC FILES
# ============================================================

app.mount(

    "/uploads",

    StaticFiles(
        directory="/var/www/surgical/uploads"
    ),

    name="uploads",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",

        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",

        "https://admin.surgicalworld.org",
        "https://surgicalworld.org",

        # If you really need wildcard:
        "*",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# HTTP EXCEPTION HANDLER
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):

    logger.warning(
        "HTTP %s | %s | %s",
        exc.status_code,
        request.method,
        request.url.path,
    )

    return JSONResponse(

        status_code=exc.status_code,

        content={

            "success": False,

            "status_code":
                exc.status_code,

            "message":
                exc.detail,

            "data":
                None,
        },
    )


# ============================================================
# GLOBAL EXCEPTION HANDLER
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):

    logger.exception(
        "Unhandled exception | %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(

        status_code=500,

        content={

            "success": False,

            "status_code": 500,

            "message":
                "Internal Server Error",

            "data":
                None,
        },
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():

    logger.info(
        "Root endpoint accessed"
    )

    return {

        "success": True,

        "status_code": 200,

        "message":
            "Surgical World API is running",

        "data":
            None,
    }


# ============================================================
# API ROUTER
# ============================================================

app.include_router(

    api_router,

    prefix="/api/v1",
)