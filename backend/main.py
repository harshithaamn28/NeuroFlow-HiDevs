from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from redis.asyncio import Redis

from config import Settings
from db.pool import create_pool, close_pool
from health import check_postgres, check_redis, check_mlflow
from migrations import ensure_schema

REQUEST_COUNT = Counter(
    "neuroflow_request_count",
    "Number of HTTP requests received"
)

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # PostgreSQL
    app.state.pool = await create_pool(settings)

    # Redis
    app.state.redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True
    )

    # Create tables if needed
    await ensure_schema(app.state.pool)

    yield

    # Cleanup
    await close_pool(app.state.pool)
    await app.state.redis.close()


app = FastAPI(
    title="NeuroFlow API",
    lifespan=lifespan
)


@app.middleware("http")
async def count_requests(request, call_next):
    REQUEST_COUNT.inc()
    response = await call_next(request)
    return response


@app.get("/")
async def root():
    return {
        "message": "NeuroFlow API is running"
    }


@app.get("/health")
async def health():

    postgres_ok = await check_postgres(app.state.pool)
    redis_ok = await check_redis(app.state.redis)
    mlflow_ok = await check_mlflow(settings.mlflow_url)

    if not (postgres_ok and redis_ok and mlflow_ok):
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "checks": {
                    "postgres": postgres_ok,
                    "redis": redis_ok,
                    "mlflow": mlflow_ok,
                },
            },
        )

    return {
        "status": "ok",
        "checks": {
            "postgres": postgres_ok,
            "redis": redis_ok,
            "mlflow": mlflow_ok,
        },
    }


@app.get("/metrics")
async def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )