(#) NeuroFlow-HiDevs — API Contracts

This document defines the REST API surface for NeuroFlow-HiDevs. Each endpoint lists:

- HTTP method and path
- Request body schema (JSON)
- Response body schema (JSON)
- Error codes and meanings
- Authentication requirement
- Rate limit (per tenant/user)

Auth
- Bearer token (JWT) in Authorization header: `Authorization: Bearer <token>`
- Scopes: `ingest:write`, `ingest:read`, `query:read`, `generate:write`, `eval:read`, `admin:*`

Common error fields

{
	"error": {
		"code": "string",
		"message": "string",
		"details": null | { ... }
	}
}

Rate limits
- Default: 60 requests/minute per tenant for non-streaming endpoints
- Ingestion upload: 10 uploads/minute per tenant (larger payloads may be rate-limited differently)
- Generation streaming: concurrent streams limit 5 per user

---

1) Health

- GET /health

Request: none

Response 200

{
	"status": "ok",
	"version": "string",
	"uptime_seconds": number
}

Errors
- 500 internal server error

Auth: none
Rate limit: 1000/min

---

2) Ingestion

- POST /v1/documents

Create a document upload record; returns an upload URL or accepts multipart upload.

Request (JSON) - option A (metadata-only, server returns pre-signed URL):

{
	"file_name": "string",
	"content_type": "application/pdf" | "application/vnd.openxmlformats-officedocument.wordprocessingml.document" | "text/csv" | "image/*",
	"source_url": "string|null",
	"metadata": { "tags": ["string"], "uploader_id": "string" }
}

Response 201

{
	"document_id": "string",
	"upload_url": "string",
	"expires_in": 3600
}

Errors
- 400 bad_request — invalid content_type or missing fields
- 401 unauthorized — missing/invalid token (requires `ingest:write`)
- 429 rate_limited — exceeded upload rate
- 500 server_error

Auth: required (`ingest:write`)
Rate limit: 10 uploads/min per tenant

---

- POST /v1/documents/{document_id}/complete

Call when upload completes to enqueue ingestion pipeline.

Request:

{
	"document_id": "string",
	"size_bytes": number
}

Response 200

{
	"document_id": "string",
	"status": "enqueued",
	"ingestion_job_id": "string"
}

Errors
- 404 not_found — document_id unknown
- 409 conflict — already enqueued
- 401 unauthorized (`ingest:write`)

Rate limit: 60/min

---

- GET /v1/documents/{document_id}

Get document manifest and ingestion status.

Response 200

{
	"document_id": "string",
	"status": "pending|enqueued|processing|completed|failed",
	"chunks_count": number,
	"metadata": { ... },
	"created_at": "ISO8601",
	"updated_at": "ISO8601"
}

Errors: 404 not_found

Auth: `ingest:read` or owner
Rate limit: 120/min

---

3) Retrieval / Query

- POST /v1/query

Run a query through the retrieval pipeline and return a ranked context window.

Request body:

{
	"user_id": "string",
	"query": "string",
	"filters": { "doc_ids": ["string"], "tags": ["string"], "date_range": {"from":"ISO","to":"ISO"} },
	"k": 5,
	"use_lexical": true,
	"use_semantic": true
}

Response 200

{
	"query_id": "string",
	"results": [
		{
			"chunk_id": "string",
			"text": "string",
			"score": number,
			"source": { "document_id": "string", "file_name": "string", "page": number },
			"provenance": { "by": ["semantic","lexical"], "score_breakdown": {"semantic": number, "lexical": number} }
		}
	],
	"timing": { "ann_ms": 123, "bm25_ms": 20, "rerank_ms": 100 }
}

Errors
- 400 bad_request — invalid filters
- 401 unauthorized (`query:read`)
- 429 rate_limited — default 60/min

Auth: `query:read`
Rate limit: 60/min

---

4) Generation

- POST /v1/generate

Request body:

{
	"user_id": "string",
	"query": "string",
	"context_chunk_ids": ["string"],
	"model_hint": "string|null",    // optional preference
	"stream": false
}

Response 200 (non-streaming)

{
	"generation_id": "string",
	"model": "string",
	"model_version": "string",
	"response": "string",
	"tokens": number
}

Streaming mode
- If `stream=true`, the server will return a 200 and then stream token events via SSE or WebSocket.

Errors
- 400 bad_request — missing query
- 401 unauthorized (`generate:write`)
- 429 too_many_requests — concurrent streams limit
- 503 model_unavailable — upstream LLM error

Auth: `generate:write`
Rate limit: 60/min (5 concurrent streams)

---

5) Generation Logs (read)

- GET /v1/generations/{generation_id}

Response 200

{
	"generation_id": "string",
	"user_id": "string",
	"query": "string",
	"prompt": "string",
	"model": "string",
	"response": "string",
	"context_chunk_ids": ["string"],
	"created_at": "ISO"
}

Auth: `generate:read` or owner
Rate limit: 120/min

---

6) Evaluation (write/read)

- POST /v1/evaluations

Submit or update evaluation for a generation (used by workers/humans).

Request body:

{
	"generation_id": "string",
	"evaluator_id": "string|null",
	"scores": { "faithfulness": 0.0-1.0, "relevance": 0.0-1.0, "precision": 0.0-1.0, "recall": 0.0-1.0 },
	"notes": "string|null",
	"user_rating": number|null
}

Response 201

{
	"evaluation_id": "string",
	"generation_id": "string",
	"created_at": "ISO"
}

Errors: 400 bad_request, 401 unauthorized (`eval:write`)

Rate limit: 120/min

---

- GET /v1/evaluations/{generation_id}

Response 200

{
	"generation_id": "string",
	"scores": { ... },
	"aggregates": { "rolling_mean_faith": number }
}

Auth: `eval:read` or owner

---

7) Fine-tuning

- POST /v1/fine-tunes

Trigger a fine-tune job from curated dataset.

Request body:

{
	"dataset_uri": "string",   // where JSONL is stored
	"base_model": "string",
	"params": { "epochs": 1, "batch_size": 32 },
	"notify_webhook": "string|null"
}

Response 202

{
	"fine_tune_id": "string",
	"status": "queued",
	"submitted_at": "ISO"
}

Errors: 400, 401 admin required (`admin:*` or `fine_tune:write`)

Rate limit: 10/min per tenant

---

8) Admin / model routing

- GET /v1/models

List available base and fine-tuned models.

Response 200

{
	"models": [ { "id":"string","name":"string","version":"string","type":"base|fine_tuned","metrics":{}} ]
}

Auth: `admin:*` or `generate:read`

---

9) Webhook for generation events

- POST /v1/hooks/generation

Used by internal event bus to notify other services (idempotent).

Request body:

{
	"event": "generation.created|generation.completed",
	"payload": { ... }
}

Auth: internal token

Rate limit: 1000/min

---

Errors (global)

- 400 Bad Request — invalid JSON or schema
- 401 Unauthorized — missing/invalid token
- 403 Forbidden — insufficient scope
- 404 Not Found — resource not found
- 409 Conflict — resource state conflict
- 429 Too Many Requests — rate limit exceeded
- 500 Internal Server Error — unexpected error

---

Versioning and extension notes
- All API paths are versioned under `/v1/` (future: `/v2/` for breaking changes)
- Use standard pagination for list endpoints (cursor-based); currently omitted for brevity

Document last updated: 2026-05-28

---

## Minimum endpoints (as requested)

Note: the canonical API is versioned under `/v1/...`. Below are the exact minimal paths you listed; in the implementation they map to `/v1/...` equivalents (for example `/ingest` -> `/v1/ingest`).

1) POST /ingest
- HTTP: POST /ingest
- Purpose: file upload or URL ingestion; enqueue ingestion pipeline.
- Auth: Bearer token, scope `ingest:write`
- Rate limit: 10 uploads/min per tenant

Request (multipart/form-data or JSON for URL):
 - file (multipart) OR
 - { "file_name":"string","source_url":"string","content_type":"string","metadata":{...} }

Response 201
{
	"document_id":"string",
	"ingest_status":"uploaded|enqueued",
	"upload_url":"string|null",
	"expires_in":3600
}

Errors: 400,401,413,429,500

2) POST /query
- HTTP: POST /query
- Purpose: execute retrieval (and optional generation) synchronously.
- Auth: `query:read` (and `generate:write` if generation is requested)
- Rate limit: 60/min per tenant

Request JSON:
{
	"user_id":"string",
	"query":"string",
	"filters":{...},
	"k":5,
	"pipeline":"string|null",
	"generate":false,
	"model_hint":null
}

Response 200
{
	"query_id":"string",
	"results":[ { "chunk_id":"string","text":"string","score":number,"source":{...} } ],
	"generation": null | { "generation_id":"string","model":"string","response":"string","tokens":number },
	"timing":{...}
}

Errors: 400,401,429,500

3) GET /query/{query_id}/stream
- HTTP: GET /query/{query_id}/stream
- Purpose: open an SSE stream for token-by-token generation output for the specified query/generation.
- Auth: `generate:write`
- Rate limit: 5 concurrent streams per user; 20 concurrent streams per tenant

SSE events (token, partial_response, complete, error) as JSON payloads. Initial handshake is a 200 with Content-Type: text/event-stream.

Errors on connect: 401,429,503

4) GET /evaluations
- HTTP: GET /evaluations
- Purpose: paginated evaluations listing
- Auth: `eval:read` or owner
- Rate limit: 120/min

Query params: page_size, cursor, filters (generation_id,user_id,min_faithfulness,from,to)

Response 200
{
	"items":[ { "evaluation_id":"string","generation_id":"string","scores":{...},"user_rating":number|null,"created_at":"ISO" } ],
	"next_cursor":"string|null",
	"page_size":number
}

Errors: 400,401,500

5) GET /evaluations/aggregate
- HTTP: GET /evaluations/aggregate
- Purpose: rolling quality metrics over a window
- Auth: `eval:read` or `admin:*`
- Rate limit: 60/min

Query params: window_days (default 7), group_by (optional)

Response 200
{ "window_days":number, "as_of":"ISO", "metrics":{ "faithfulness_mean":number, ... }, "by_group":{...} }

Errors: 400,401,500

6) POST /pipelines
- HTTP: POST /pipelines
- Purpose: create named pipeline configuration
- Auth: `pipeline:write` (admin)
- Rate limit: 60/min

Request JSON:
{ "name":"string","description":"string|null","stages":[...],"default":boolean }

Response 201
{ "pipeline_id":"string","name":"string","created_at":"ISO" }

Errors: 400,401,403,409

7) GET /pipelines/{id}/runs
- HTTP: GET /pipelines/{id}/runs
- Purpose: pipeline execution history (paginated)
- Auth: `pipeline:read` or owner
- Rate limit: 120/min

Query params: page_size, cursor, status, from, to

Response 200
{ "items":[ { "run_id":"string","status":"queued|running|success|failed","started_at":"ISO","finished_at":"ISO|null","metrics":{...} } ], "next_cursor":"string|null" }

Errors: 404,401

8) POST /finetune/jobs
- HTTP: POST /finetune/jobs
- Purpose: submit a fine-tuning job
- Auth: `fine_tune:write` or `admin:*`
- Rate limit: 10/min

Request JSON:
{ "dataset_uri":"string","base_model":"string","params":{...},"notify_webhook":"string|null" }

Response 202
{ "fine_tune_id":"string","status":"queued","submitted_at":"ISO" }

Errors: 400,401,429,500

9) GET /finetune/jobs/{id}
- HTTP: GET /finetune/jobs/{id}
- Purpose: job status and metrics
- Auth: `fine_tune:write` or owner or admin
- Rate limit: 60/min

Response 200
{ "fine_tune_id":"string","status":"queued|running|completed|failed","progress":{...},"metrics":{...},"model_id":"string|null" }

Errors: 404,401

10) GET /health
- HTTP: GET /health
- Purpose: simple service health
- Auth: none (recommended internal token allowed)
- Rate limit: 1000/min

Response 200
{ "status":"ok|degraded|down","version":"string","uptime_seconds":number,"components":{...} }

Errors: 500

11) GET /metrics
- HTTP: GET /metrics
- Purpose: Prometheus exposition
- Auth: optional (internal token recommended)
- Rate limit: 1000/min

Response: 200 text/plain (Prometheus format)

Errors: 401,500

