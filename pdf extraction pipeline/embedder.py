"""
Embedder — all-MiniLM-L6-v2 → Supabase pgvector document_chunks
- Takes text chunks from pdf_extractor or transcript_parser
- Generates 384-dim embeddings locally (no API cost, no latency)
- Batch-inserts into document_chunks table with full citation metadata
"""

from typing import Dict, List
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
from config import EMBEDDING_MODEL, SUPABASE_URL, SUPABASE_SERVICE_KEY

_model: SentenceTransformer = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"[Embedder] Loading model: {EMBEDDING_MODEL} ...")
        _model = SentenceTransformer(EMBEDDING_MODEL)
        print(f"[Embedder] Model loaded.")
    return _model


def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ─────────────────────────────────────────────────────────────────
# EMBED + STORE
# ─────────────────────────────────────────────────────────────────

def embed_and_store_chunks(
    chunks: List[Dict],
    document_type: str,
    batch_size: int = 64,
    dry_run: bool = False,
) -> int:
    """
    Embed a list of text chunks and insert them into document_chunks.

    Args:
        chunks: list of chunk dicts (from pdf_extractor or transcript_parser)
        document_type: 'annual_report' | 'transcript' | 'quarterly_results' | 'investor_presentation'
        batch_size: embedding batch size (sentence-transformers handles internally)
        dry_run: if True, compute embeddings but do NOT write to Supabase

    Returns:
        number of rows inserted
    """
    if not chunks:
        print("[Embedder] No chunks to embed.")
        return 0

    model = get_model()
    supabase = get_supabase() if not dry_run else None

    texts = [c["chunk_text"] for c in chunks]
    print(f"[Embedder] Embedding {len(texts)} chunks ...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,  # cosine similarity works on normalised vectors
    )

    rows = []
    for chunk, emb in zip(chunks, embeddings):
        row = {
            "company_id":      chunk.get("company_id"),
            "document_type":   document_type,
            "period":          chunk.get("period"),
            "chunk_text":      chunk["chunk_text"],
            "chunk_index":     chunk.get("chunk_index", 0),
            "section_name":    chunk.get("section_name"),
            "source_document": chunk.get("source_document"),
            "source_page":     chunk.get("source_page"),
            "speaker":         chunk.get("speaker"),
            "embedding":       emb.tolist(),  # list[float] for Supabase JSON
        }
        rows.append(row)

    if dry_run:
        print(f"[Embedder] DRY RUN — would insert {len(rows)} rows.")
        return len(rows)

    # Supabase REST has a practical limit per request; insert in batches
    SUPABASE_BATCH = 50
    inserted = 0
    for i in tqdm(range(0, len(rows), SUPABASE_BATCH), desc="Uploading to Supabase"):
        batch = rows[i: i + SUPABASE_BATCH]
        try:
            supabase.table("document_chunks").insert(batch).execute()
            inserted += len(batch)
        except Exception as e:
            print(f"[Embedder] Batch insert error at offset {i}: {e}")

    print(f"[Embedder] Stored {inserted}/{len(rows)} chunks in document_chunks.")
    return inserted


# ─────────────────────────────────────────────────────────────────
# QUERY HELPER (used by Q&A agent later)
# ─────────────────────────────────────────────────────────────────

def embed_query(query_text: str) -> List[float]:
    """Embed a single query string. Used by the Q&A agent."""
    model = get_model()
    vec = model.encode([query_text], normalize_embeddings=True)[0]
    return vec.tolist()


def search_similar_chunks(
    query_text: str,
    company_id: str = None,
    top_k: int = 5,
) -> List[Dict]:
    """
    Search document_chunks by semantic similarity.
    Calls the match_documents RPC function defined in schema.sql.
    Returns list of matching chunks with similarity scores.
    """
    supabase = get_supabase()
    query_vec = embed_query(query_text)

    params = {
        "query_embedding": query_vec,
        "match_count": top_k,
        "filter_company": company_id,
    }
    result = supabase.rpc("match_documents", params).execute()
    return result.data or []
