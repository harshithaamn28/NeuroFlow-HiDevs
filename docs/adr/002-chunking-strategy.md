# ADR 002 — Chunking strategy: hybrid default (sentence-boundary + sliding window)

Date: 2026-05-28

Context
-------
Ingestion must split raw text into chunks suitable for embedding and retrieval. Common strategies: fixed-size (token/character windows), sentence-boundary (split on linguistic boundaries), and semantic chunking (use embeddings / topic segmentation to create semantically coherent chunks). The choice impacts retrieval precision/recall, prompt context cost, and downstream generation quality.

Decision
--------
Use a hybrid default strategy: sentence-boundary chunking with a configurable sliding window and a maximum token size. Augment with semantic chunking in specific cases (long technical documents, books, or when evaluation shows poor retrieval). Use format-aware rules for structured sources (CSV/TSV/table rows, code blocks, tables) to preserve row/table semantics.

Why this choice:
- Sentence-boundary + sliding window preserves natural language boundaries, reducing truncated sentences and improving readability when chunks are shown to users or used as evidence.
- A maximum token size (e.g., 500–1,000 tokens) and a small overlap (e.g., 50–100 tokens) balances context coverage and embedding cost.
- It is simple, deterministic, and cheap to compute at ingest time.
- Semantic chunking is more expensive and brittle to compute at ingest; it is best used selectively after analysis shows it improves retrieval.

Consequences
------------
Immediate consequences:
- Retrieval quality will generally improve over fixed-size chunks because semantic boundaries (sentences/paragraphs) are preserved.
- Prompt construction is simpler: chunk edges align with sentences/paragraphs, making provenance labeling human-readable.
- Some long sentences or domain-specific semantics (tables, code) need special handling; we will add parsers for these cases.

When to switch or augment with semantic chunking:
- If evaluation metrics show low context precision/recall for long, multi-topic documents (e.g., textbooks, long reports), run an experiment with semantic segmentation (embedding-based clustering or TextTiling) for those documents.
- If chunk redundancy causes prompt bloat, use semantic deduplication (embedding similarity) during ingestion or retrieval candidate pruning.

Fallbacks and special handling:
- Structured inputs (CSV, database dumps): chunk by logical row/group rather than sentences.
- Tables: preserve row/column context and include nearby caption/headers when chunking.
- Images / OCR: chunk at page or detected block level and post-process with language heuristics.

Operational notes
-----------------
- Make chunking parameters configurable per pipeline: max_tokens, overlap, sentence_detector (language-aware), semantic_threshold.
- Store original offsets and chunk provenance to enable recomposition and debugging.
- Keep small-scale semantic chunking tooling in a separate worker so we can enable it per-document without impacting baseline ingestion throughput.

Status: Hybrid sentence-boundary + window is the default. Semantic chunking enabled per policy when evaluation justifies it.
