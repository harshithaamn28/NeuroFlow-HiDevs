import asyncpg


async def create_pool(settings):
    return await asyncpg.create_pool(
        dsn=settings.postgres_url,
        min_size=1,
        max_size=10,
    )


async def close_pool(pool):
    await pool.close()