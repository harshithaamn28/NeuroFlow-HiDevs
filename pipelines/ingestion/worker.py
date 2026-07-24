import json

from arq.connections import RedisSettings
from arq.worker import Worker


async def process_document(ctx, job):

    redis = ctx["redis"]

    document = json.loads(job)

    document_id = document["document_id"]
    file_path = document["file_path"]
    source_type = document["source_type"]

    print(
        f"Processing {document_id} "
        f"({source_type}) from {file_path}"
    )

    await redis.set(
        f"document:{document_id}:status",
        "processing",
    )

    # TODO:
    # - Select extractor
    # - Extract pages
    # - Chunk content
    # - Generate embeddings
    # - Save chunks

    await redis.set(
        f"document:{document_id}:status",
        "complete",
    )


class WorkerSettings:
    redis_settings = RedisSettings()
    functions = [process_document]