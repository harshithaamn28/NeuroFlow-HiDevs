# NeuroFlow-HiDevs Architecture

## Overview

NeuroFlow-HiDevs is an enterprise-grade Retrieval-Augmented Generation (RAG) platform designed for intelligent document ingestion, retrieval, generation, evaluation, and fine-tuning workflows.

The system processes multimodal data sources such as PDFs, DOCX files, images, CSV files, and web URLs. Extracted content is converted into embeddings and stored in a vector database for semantic retrieval and AI-powered response generation.

---

# 1. Ingestion Subsystem

## Description

The ingestion subsystem accepts raw files and converts them into searchable vector embeddings.

## Supported Inputs

- PDF files
- DOCX files
- Images
- CSV files
- Web URLs

## Responsibilities

- File upload handling
- Content extraction
        user_id: string,
        query: string,
        filters?: { doc_ids?: string[], tags?: string[], date_range?: {from,to} },
        k?: number
    }

- GenerationLogEntry

    {
        id: uuid,
        user_id, query, prompt, model, model_version,
        context_chunk_ids: [string],
        response: string,
        tokens_streamed: int,
        timestamp
    }

---

## 1) Ingestion Subsystem

Purpose: accept raw inputs (PDF/DOCX/images/CSV/URLs), extract modality-specific content, normalize and chunk text, compute embeddings, and persist chunks to the vector store with metadata so they are queryable.

High-level flow (ASCII):

    Upload Endpoint
            │
            ├─> Validation & virus-scan
            │
            └─> Preprocessor Router
                         ├─> PDF / DOCX parser  (pdfplumber, python-docx)
                         ├─> Image OCR pipeline   (Tesseract, easyocr)
                         ├─> CSV reader + schema extractor
                         └─> Web crawler + HTML cleaner
                                    │
                                    └─> Text Normalizer (unicode, whitespace, dedupe)
                                                    │
                                                    └─> Chunker (sliding/window, anchors: headings, tables)
                                                                    │
                                                                    └─> Embedding worker (batch up chunks) → Embedding API / model
                                                                                    │
                                                                                    └─> Vector DB write (chunk + embedding + metadata)

Data contracts
- Input: binary file or URL + metadata (uploader, source tags)
- Output: persisted `Chunk` records in vector DB and a document manifest in Postgres or object store

Responsibilities & components
- API / ingestion service (FastAPI) — accepts uploads, returns document_id
- Workers (Celery / RQ / Kubernetes Jobs) — run extraction, OCR, chunking, dedup
- Embedding service — calls local or remote embedding model (batching, retries)
- Vector DB (FAISS/Chroma/HNSW/Weaviate/Pinecone) — stores vectors and metadata
- Document store (S3 or DB) — long-term raw file retention and manifest
- Postgres — document metadata, chunk manifests, ingestion events

Edge cases & failure modes
- OCR failures: mark pages as OCR_failed and fall back to human review pipeline
- Large files: stream processing to avoid memory spikes; chunk and checkpoint progress
- Duplicate content: compute content hash and skip re-ingestion or mark as duplicate
- Embedding service rate-limits: implement exponential backoff and retry queue

Scaling notes
- Use workers and batching for embeddings
- Shard vector DB or use multiple indexes by tenant/project
- Provide idempotent ingestion (document hash + dedupe)

---

## 2) Retrieval Subsystem

Purpose: given a `QueryPayload`, concurrently run hybrid retrieval (semantic + lexical + metadata), fuse ranked lists with Reciprocal Rank Fusion (RRF), then apply a cross-encoder reranker to produce a final ranked context window.

Legend: <span style="color:red">r</span> = Reciprocal Rank Fusion (RRF), <span style="color:green">r</span> = Cross-Encoder Reranker

Pipeline (ASCII):

    Query -> Query Preprocessor (normalize, expand acronyms)
            │
            ├─> Embed Query -> Vector Search (ANN) -> Results A
            │
            ├─> Keyword Search (BM25) -> Results B
            │
            └─> Metadata Filter -> Results C
                         │
                         └─> Merge (RRF) <span style="color:red">r</span> -> Candidate Set (N)
                                             │
                                             └─> Cross-Encoder Reranker <span style="color:green">r</span> (pairwise or pointwise) -> Top-K context window

Notes on Reciprocal Rank Fusion (RRF)
- RRF gives simple, robust fusion without heavy parameter tuning. Score item by sum(1/(k+rank_i)) across sources.

Data contracts
- Input: QueryPayload
- Intermediate: lists of Chunk references + scores
- Output: Ordered list of `Chunk` objects for prompt assembly; also return provenance (score breakdown)

Responsibilities & components
- Query API (Lightweight) — returns `context_window` or stream of contexts
- Vector searcher — ANN index (FAISS/HNSW/DB-managed) with metadata filters
- Lexical searcher — BM25 / ElasticSearch for exact matches, table search
- Fusion service — implement RRF and candidate de-duplication
- Reranker — Cross-encoder (e.g., SentenceTransformers CrossEncoder) that consumes (query, chunk.text)

Edge cases & failure modes
- Cold-start queries with no embeddings: fall back to BM25 alone
- Too many candidates: enforce candidate size limits and early stopping
- Long documents that produce many overlapping chunks: apply dedup and context selection heuristics

Scaling notes
- Run ANN search nodes close to the vector store
- Cache popular query embeddings and top-k results
- Batch cross-encoder reranking for throughput; use GPUs when available

---

## 3) Generation Subsystem

Purpose: build the prompt (system + retrieved context + user query), select the appropriate LLM (routing policy), stream tokens to the client, and log the full input/output for evaluation.

Flow (ASCII):

    User Query + Context Window
            │
            └─> Prompt Builder (apply templates, truncation, chunk prioritization)
                            │
                            └─> Model Router (choose model by cost/capability/domain)
                                                │
                                                └─> LLM API (stream tokens back) -> Response Stream to client
                                                                            │
                                                                            └─> Logging Service (persist GenerationLogEntry)

Model routing policy
- Rules-based: domain -> specialized model; cost-tier threshold for non-critical queries
- Performance-based: route to cheaper model, fall back to larger model on timeouts
- A/B and experiment flagging to route traffic to fine-tuned models

Prompt building / context windowing
- Truncate/score chunks by relevance and freshness
- Insert separators and provenance markers: "SOURCE: file.pdf#page=3"
- Include explicit instructions for the LLM to ground answers in provided context

Streaming and safety
- Use token streaming (HTTP/2 server-sent events or WebSockets)
- Enforce response length and rate limits
- Run safety filters (heuristic + classifier) before streaming sensitive content

Responsibilities & components
- Prompt service (template store, truncation logic)
- Model routing service (traffic rules, fallbacks)
- LLM connectors (OpenAI, Anthropic, self-hosted)
- Logging pipeline (Kafka or event bus -> Postgres/Blob store)

Edge cases & failure modes
- Model errors/timeouts: return partial answer with clear indicator and fallback
- Hallucinations: flag for evaluation and show provenance used
- Tokenization mismatches when measuring prompt length: normalize token counting per model

Scaling notes
- Use asynchronous streaming and connection pooling to LLM services
- Cache recent prompts and responses where applicable

---

## 4) Evaluation Subsystem

Purpose: asynchronously evaluate every generated response on faithfulness, relevance, context precision, and context recall, persist scores, and compute rolling aggregates for monitoring and fine-tuning selection.

Pipeline (ASCII):

    GenerationLogEntry -> Evaluation Worker Pool
            │
            ├─> Faithfulness check (QA model, entailment, or token overlap) -> score_faith
            ├─> Relevance check (semantic similarity between query and answer) -> score_rel
            ├─> Context precision (what % of cited chunks are used) -> score_prec
            └─> Context recall (were relevant chunks missing?) -> score_rec
                            │
                            └─> Persist to Postgres (evaluation table) -> Aggregate jobs compute rolling metrics

Scoring approaches (examples)
- Faithfulness: entailment model (cross-encoder) or grounding score using exact evidence check
- Relevance: embedding similarity between query and answer
- Context precision: measure overlap of tokens/semantic similarity between cited chunk and answer
- Context recall: sample retrieval candidate set and measure whether answer references any of them

Data contracts
- Input: GenerationLogEntry
- Output: EvaluationRecord { generation_id, scores: {faith,rel,prec,rec}, derived_flags }

Responsibilities & components
- Evaluation workers (async, GPU for cross-encoders)
- Metrics DB (Postgres) and time-series aggregates (Materialized views)
- Dashboard and alerting (Grafana/Metabase)

Edge cases & failure modes
- Noisy automatic scores: keep human-in-the-loop for calibration and active learning
- Large volume: sample-based scoring for expensive checks, prioritize high-impact queries for full scoring

Scaling notes
- Use separate GPU worker pool for cross-encoders
- Use incremental aggregation and compact metrics tables

---

## 5) Fine-Tuning Subsystem

Purpose: curate training examples from evaluation logs, run fine-tuning experiments, track experiments, and route traffic to the best performing fine-tuned models.

Flow (ASCII):

    EvaluationRecords (stream) --filter--> HighQualityExamples (faith > 0.8 && user_rating >=4)
            │
            └─> Formatter -> JSONL dataset -> Submit fine-tune job (OpenAI/HF) -> Track run in MLflow
                                                                                 │
                                                                                 └─> When new model outperforms baseline (A/B tests) -> Promote in Model Router

Data selection and formatting
- Selection rule: evaluation.faithfulness >= 0.8 AND user_rating >= 4 AND not flagged for PII
- Format: JSONL with fields {prompt, completion, metadata}

Training and experiments
- Track experiments in MLflow or experiment DB: dataset version, hyperparams, base model
- Keep lineage from example -> evaluation -> model -> experiment

Routing tuned models
- Use experiment results and online A/B tests to route percentage of traffic to fine-tuned model
- Maintain fallback to base model if degradation observed

Edge cases & failure modes
- Overfitting to narrow examples: keep validation holdout and manual review
- Data leakage (PII): filter examples using PII detectors before training

Scaling notes
- Automate dataset versioning and small-step fine-tuning cycles
- Use smaller frequent fine-tunes on domain-specific data and larger infrequent fine-tunes for general improvements

---

## Observability & Operations

- Logging: ingest events into a central event bus (Kafka) — ingestion events, retrieval traces, generation logs, evaluation records
- Tracing: attach trace ids to requests across subsystems
- Metrics: latency (p95), embeddings throughput, vector writes/s, retrieval QPS, eval lag, fine-tune success rate
- Alerts: ingestion failures, vector DB out of space, reranker latency spikes, drift in faithfulness scores

## Security & Compliance

- Access control and tenant isolation in vector DB and model routing
- Data retention policy for raw files and training examples
- PII detection pipeline and redaction prior to storing or using examples for training

## Example: From file upload to first queryable vector (short path)

1. User uploads `terms.pdf` to Ingestion Service → returns document_id `doc:123`.
2. Ingestion worker extracts text, chunks into pieces, computes embeddings (batched) and writes chunk records to vector DB.
3. Vector DB confirms write; manifest saved to Postgres with chunk ids.
4. First query uses Retrieval Subsystem — ANN search returns chunk ids referencing `doc:123` and text; they appear immediately in the context window.

## Example: Retrieval detailed pipeline (short)

Query: "What is the recommended dosage for drug X?"

1. Preprocess query, embed it
2. Run ANN search → top 100 semantic candidates
3. Run BM25 on full text index → top 100 lexical candidates
4. Apply metadata filters (source=FDA guidance)
5. Fuse with RRF and reduce to 50 unique candidates
6. Cross-encoder rerank top 50 → select top 5 chunks for prompt

---

## Next steps / implementation priorities

1. Implement ingestion API + worker skeleton with one parser (PDF) and a local FAISS index to validate flows
2. Add retrieval fusion and a lightweight reranker (use cross-encoder small model for dev)
3. Implement generation logging and an evaluation worker scaffold
4. Wire fine-tuning pipeline with dataset export and MLflow experiment tracking

## Appendix — Suggested technology mapping

- Ingestion API: FastAPI + Celery or RQ
- Extractors: pdfplumber, python-docx, Tesseract
- Embeddings: OpenAI / local SentenceTransformers (for dev)
- Vector DB: FAISS (dev), Chroma/Weaviate/Pinecone in prod
- Lexical search: Elasticsearch or OpenSearch
- Reranker: SentenceTransformers CrossEncoder on GPU
- Model hosting: OpenAI/Anthropic or self-hosted LLMs via Triton/LLM-Engine
- Evaluation storage: Postgres + event bus (Kafka)
- Experiment tracking: MLflow

---

Document last updated: 2026-05-28
