# ADR 001 — Vector store: choose pgvector for MVP

Date: 2026-05-28

Context
-------
We need a vector storage solution to persist embeddings produced by our ingestion pipeline and support hybrid retrieval (semantic similarity + metadata filtering). Candidates considered: pgvector (Postgres extension), Pinecone (managed), Weaviate, and Qdrant (open-source, production-ready). Constraints: small core team, existing Postgres usage for metadata, local/dev reproducibility, cost sensitivity, requirement for metadata joins and transactional guarantees, and a plan for eventual scale.

Decision
--------
Adopt pgvector as the primary vector store for the project MVP and initial production rollout.

Rationales:
- Operational simplicity: reuses existing Postgres knowledge, tooling, IAM, backups, and monitoring.
- Data model alignment: easy SQL joins between vector records and document metadata (provenance, access control, ingestion state).
- Cost and local dev: zero additional managed service cost and easy to run locally for development and CI.
- Indexing and performance: pgvector supports ANN indexes (IVFFlat/HNSW depending on build), and Postgres can be tuned and scaled (replicas, connection pooling).
- ACID and auditability: use Postgres transactional guarantees for ingests and consistent chunk manifests.

Consequences
------------
Pros:
- Fast MVP iteration with one datastore to manage (less operational overhead).
- Simplified joins and queries for retrieval filters and analytics; no cross-system consistency problems.
- Local reproducibility and straightforward backup/restore using Postgres tooling.

Cons / Trade-offs:
- Performance ceiling: at very large scale (hundreds of millions of vectors or extremely low latency SLAs) dedicated vector systems (Pinecone, Qdrant, Weaviate) can be more efficient.
- Features: managed services provide built-in multi-region replication, automatic scaling, and advanced vector search features (index selection, hybrid search) that may be richer out-of-the-box.

Migration / mitigation plan:
- Monitor volume, latency, and cost. Define objective thresholds (for example: >200M vectors or 95th-percentile query latency > 300ms under typical load) to evaluate migration.
- Keep export tooling (periodic dumps of chunk_id, metadata, and embeddings in ndjson/JSONL) to allow importing into Qdrant/Weaviate/Pinecone.
- Consider hybrid approach: keep metadata in Postgres, index hot vectors in a managed vector DB for low-latency retrieval, and fall back to Postgres for cold vectors.

Operational notes
-----------------
- Ensure Postgres instance has sufficient RAM and SSD IO for ANN indexes; use connection pooling and tune work_mem and maintenance_work_mem.
- Use partitioning and/or schema-per-tenant for multi-tenant isolation where needed.
- Add monitoring for index bloat, query latency, and cardinality; add alerts for storage growth and slow queries.

Status: Adopted for MVP; revisit as load and latency metrics justify a migration.
