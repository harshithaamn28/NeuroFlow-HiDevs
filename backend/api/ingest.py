import hashlib
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()


documents = {}


@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):

    content = await file.read()

    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File exceeds 100MB limit."
        )

    content_hash = hashlib.sha256(content).hexdigest()

    for doc_id, doc in documents.items():
        if doc["content_hash"] == content_hash:
            return {
                "document_id": doc_id,
                "status": doc["status"],
                "duplicate": True,
            }

    document_id = str(uuid.uuid4())

    documents[document_id] = {
        "status": "queued",
        "content_hash": content_hash,
        "chunk_count": 0,
        "metadata": {
            "filename": file.filename
        },
    }

    # TODO:
    # enqueue ARQ job here

    return {
        "document_id": document_id,
        "status": "queued",
        "duplicate": False,
    }


@router.get("/documents/{document_id}")
async def get_document(document_id: str):

    if document_id not in documents:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    return documents[document_id]