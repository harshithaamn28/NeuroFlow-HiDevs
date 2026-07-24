import httpx
from asyncpg.pool import Pool
from redis.asyncio import Redis


async def check_postgres(pool: Pool) -> bool:
    try:
        return await pool.fetchval("SELECT 1") == 1
    except Exception as e:
        print("POSTGRES ERROR:", e)
        return False


async def check_redis(redis_client: Redis) -> bool:
    try:
        return await redis_client.ping()
    except Exception as e:
        print("REDIS ERROR:", e)
        return False


async def check_mlflow(mlflow_url: str) -> bool:
    """
    Check whether the MLflow server is reachable.

    MLflow may return:
    - 200 OK
    - 302 Redirect
    - 401 Unauthorized
    - 403 Forbidden (security middleware enabled)

    Any of these means the server is alive.
    """
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
        ) as client:

            response = await client.get(
                mlflow_url,
                headers={
                    "Host": "localhost"
                }
            )

            print("MLFLOW STATUS:", response.status_code)

            if response.status_code in (200, 302, 401, 403):
                return True

            return False

    except Exception as e:
        print("MLFLOW ERROR:", e)
        return False