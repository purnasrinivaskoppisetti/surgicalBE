from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    HTTPException,
    Request
)

from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine
from app.models.models import Base
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )

    yield


app = FastAPI(
    title="Surgical World API",
    version="1.0.0",
    lifespan=lifespan
)

# ==========================
# CORS Middleware
# ==========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",                            
        "http://127.0.0.1:5173",
        "https://admin.surgicalworld.org",
        "https://surgicalworld.org",
        "*",
        
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# Exception Handlers
# ==========================

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException
):

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "status_code": exc.status_code,
            "message": exc.detail,
            "data": None
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):

    return JSONResponse(
        status_code=500,
        content={
            
            "success": False,
            "status_code": 500,
            "message": "Internal Server Error",
            "data": None
        }
    )


@app.get("/")
async def root():

    return {
        "success": True,
        "status_code": 200,
        "message": "Surgical World API is running",
        "data": None
    }



app.include_router(

    api_router,
    prefix="/api/v1"
)