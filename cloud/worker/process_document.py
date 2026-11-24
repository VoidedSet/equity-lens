"""Single-document lakehouse worker: chunks, Bedrock/Featherless facts, MiniLM embeddings, and quarantine."""

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from cloud.common.companies import normalize_company_id
from cloud.common.config import REPO_ROOT, CloudConfig, get_config
from cloud.common.hashing import make_chunk_id
from cloud.common.llm import LLMProvider, get_llm_provider
from cloud.common.manifest import DocumentManifest, ManifestStore, utc_now_iso
from cloud.common.quarantine import QuarantineWriter
from cloud.common.schemas import ChunkRecord, EmbeddingRecord, validate_fact
from cloud.common.storage import StorageBackend, get_storage

PIPELINE_DIR = REPO_ROOT / "pdf extraction pipeline"

KNOWN_MGMT_NAMES = {
    "puneet chhatwal", "giridhar sanjeevi",
    "sanjay sethi", "milind wagh", "rajeev newar",
    "patanjali keswani", "rattan keswani", "kapil sharma",
    "vikram oberoi", "vikramjit oberoi", "vikramjit singh oberoi", "kallol kundu",
    "varun chandra", "anurag bhatia",
}

MGMT_TITLE_RE = re.compile(
    r"\b(MD|CEO|CFO|COO|CRO|President|Chairman|Managing Director|"
    r"Chief Executive|Chief Financial|Chief Operating|Director|Head of|VP|Vice President)\b",
    re.IGNORECASE,
)
NON_MGMT_RE = re.compile(
    r"\b(Moderator|Operator|Participant|Analyst|Research|Capital|Securities|Asset Management|Fund)\b",
    re.IGNORECASE,
)
SKIP_SPEAKERS = {"moderator", "operator", "conference call operator", "host"}

_EMBED_MODEL_CACHE: Dict[str, Any] = {}


def _load_pipeline_module(module_name: str) -> Any:
    pipeline_str = str(PIPELINE_DIR)
    if pipeline_str not in sys.path:
        sys.path.insert(0, pipeline_str)
    return __import__(module_name)


def _clean_extracted_text(text: str) -> Optional[str]:
    """Strip PDF control glyphs and filter noisy non-textual lines."""
    if not text:
        return None
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    cleaned = cleaned.replace("\xa0", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) < 20:
        return None
    alpha_count = sum(1 for ch in cleaned if ch.isalpha())
    if alpha_count / len(cleaned) < 0.30:
        return None
    return cleaned


def _chunk_text_block(text: str, chunk_chars: int, overlap: int) -> List[str]:
    if not text.strip():
        return []
    if len(text) <= chunk_chars:
        return [text.strip()]
    step = max(1, chunk_chars - overlap)
    chunks: List[str] = []
    start = 0
    while start < len(text):
        piece = text[start : start + chunk_chars].strip()
        if piece:
            chunks.append(piece)
        if start + chunk_chars >= len(text):
            break
        start += step
    return chunks


def _is_management_speaker(speaker: str) -> bool:
    low = speaker.strip().lower()
    if not low or low in SKIP_SPEAKERS:
        return False
    if NON_MGMT_RE.search(low) and low not in KNOWN_MGMT_NAMES:
        return False
    if low in KNOWN_MGMT_NAMES:
        return True
    if MGMT_TITLE_RE.search(low):
        return True
    return True


def _extract_chunks_from_pdf(manifest: DocumentManifest, raw_bytes: bytes) -> List[Dict[str, Any]]:
    fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw_bytes)
        if manifest.doc_type == "transcript":
            transcript_parser = _load_pipeline_module("transcript_parser")
            period = None if manifest.period == "UNKNOWN" else manifest.period
            parsed = transcript_parser.process_transcript(tmp_path, manifest.company_id, period=period)
            chunks = parsed.get("mgmt_chunks") or parsed.get("all_chunks") or []
            for chunk in chunks:
                chunk["source_document"] = manifest.filename
            return chunks

        pdf_extractor = _load_pipeline_module("pdf_extractor")
        parsed = pdf_extractor.process_annual_report(tmp_path, manifest.company_id, manifest.period)
        chunks = parsed.get("text_chunks") or []
        for chunk in chunks:
            chunk["source_document"] = manifest.filename
            chunk["document_type"] = manifest.doc_type
        return chunks
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _extract_chunks_from_transcript_json(
    manifest: DocumentManifest,
    raw_bytes: bytes,
    config: CloudConfig,
) -> List[Dict[str, Any]]:
    entries = json.loads(raw_bytes.decode("utf-8"))
    if not isinstance(entries, list):
        raise ValueError("Transcript JSON must be a list of {speaker, text} objects")

    chunks: List[Dict[str, Any]] = []
    idx = 0
    for turn_no, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue
        speaker = str(entry.get("speaker") or "").strip() or "Unknown"
        if not _is_management_speaker(speaker):
            continue
        cleaned = _clean_extracted_text(str(entry.get("text") or ""))
        if not cleaned:
            continue
        for piece in _chunk_text_block(cleaned, config.chunk_chars, config.chunk_overlap_chars):
            chunks.append(
                {
                    "company_id": manifest.company_id,
                    "document_type": "transcript",
                    "period": manifest.period,
                    "chunk_index": idx,
                    "section_name": "earnings_call",
                    "source_document": manifest.filename,
                    "source_page": turn_no,
                    "speaker": speaker,
                    "source_timestamp": entry.get("timestamp"),
                    "chunk_text": piece,
                }
            )
            idx += 1
    return chunks


def _extract_chunks_from_extracted_json(
    manifest: DocumentManifest,
    raw_bytes: bytes,
    config: CloudConfig,
) -> List[Dict[str, Any]]:
    payload = json.loads(raw_bytes.decode("utf-8"))
    docs = payload if isinstance(payload, list) else [payload]

    chunks: List[Dict[str, Any]] = []
    idx = 0
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        doc_company = normalize_company_id(str(doc.get("company_id") or manifest.company_id), default=manifest.company_id)
        doc_source = str(doc.get("source_file") or manifest.filename)
        doc_type = str(doc.get("document_type") or manifest.doc_type)
        doc_period = str(doc.get("period") or manifest.period)
        for page in doc.get("pages", []):
            if not isinstance(page, dict):
                continue
            page_num = page.get("page_number")
            paras = []
            for raw_p in page.get("paragraphs", []):
                clean_p = _clean_extracted_text(str(raw_p))
                if clean_p:
                    paras.append(clean_p)
            if not paras:
                continue
            joined = "\n\n".join(paras)
            for piece in _chunk_text_block(joined, config.chunk_chars, config.chunk_overlap_chars):
                chunks.append(
                    {
                        "company_id": doc_company,
                        "document_type": doc_type,
                        "period": doc_period,
                        "chunk_index": idx,
                        "section_name": doc_type,
                        "source_document": doc_source,
                        "source_page": page_num,
                        "speaker": None,
                        "source_timestamp": None,
                        "chunk_text": piece,
                    }
                )
                idx += 1
    return chunks


def _process_screener_csv(
    manifest: DocumentManifest,
    raw_bytes: bytes,
    storage: StorageBackend,
    manifests: ManifestStore,
    ingested_at: str,
) -> Dict[str, Any]:
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = list(csv.reader(io.StringIO(text)))
    if not reader:
        raise ValueError(f"Empty CSV file: {manifest.filename}")

    headers = [h.strip() for h in reader[0]]
    col_headers = headers[1:]
    rows_out: List[Dict[str, Any]] = []
    for row_idx, raw_row in enumerate(reader[1:], start=1):
        if not raw_row or not any(cell.strip() for cell in raw_row):
            continue
        metric_name = raw_row[0].strip()
        if not metric_name:
            continue
        values: Dict[str, str] = {}
        for col_idx, col_name in enumerate(col_headers):
            if not col_name:
                continue
            val = raw_row[col_idx + 1].strip() if (col_idx + 1) < len(raw_row) else ""
            values[col_name] = val
        rows_out.append(
            {
                "doc_id": manifest.doc_id,
                "company_id": manifest.company_id,
                "doc_type": manifest.doc_type,
                "filename": manifest.filename,
                "row_index": row_idx,
                "metric_name": metric_name,
                "values": values,
                "ingested_at": ingested_at,
            }
        )

    out_key = f"processed/screener/company={manifest.company_id}/{Path(manifest.filename).stem}.jsonl"
    storage.write_jsonl(out_key, rows_out)
    outputs = {"screener": out_key}
    manifests.mark_processed(manifest.doc_id, outputs)
    return {
        "doc_id": manifest.doc_id,
        "status": "processed",
        "chunks_count": 0,
        "facts_count": len(rows_out),
        "quarantined_count": 0,
        "outputs": outputs,
    }


def _default_embed_fn(model_name: str) -> Callable[[Sequence[str]], List[List[float]]]:
    if model_name not in _EMBED_MODEL_CACHE:
        from sentence_transformers import SentenceTransformer

        _EMBED_MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    model = _EMBED_MODEL_CACHE[model_name]

    def _encode(texts: Sequence[str]) -> List[List[float]]:
        vectors = model.encode(
            list(texts),
            batch_size=64,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return [vec.tolist() for vec in vectors]

    return _encode


def _looks_like_unparseable_json(raw_text: Optional[str], parsed_items: List[Dict[str, Any]]) -> bool:
    if raw_text is None:
        return True
    stripped = raw_text.strip()
    if not stripped:
        return False
    if parsed_items:
        return False
    # Check whether stripped response is literally an empty JSON array "[]"
    cleaned = re.sub(r"```(?:json)?\s*", "", stripped)
    cleaned = re.sub(r"```\s*", "", cleaned).strip()
    return cleaned != "[]"


def process_document(
    doc_id: str,
    storage: StorageBackend,
    manifests: ManifestStore,
    config: Optional[CloudConfig] = None,
    llm_provider: Optional[LLMProvider] = None,
    embed_fn: Optional[Callable[[Sequence[str]], List[List[float]]]] = None,
    force: bool = False,
    skip_llm: bool = False,
    skip_embed: bool = False,
) -> Dict[str, Any]:
    """Process one raw manifest document into processed/ JSONL artifacts (and quarantine on errors)."""
    cfg = config or get_config()
    manifest = manifests.get(doc_id)
    if manifest is None:
        raise FileNotFoundError(f"No manifest found for doc_id={doc_id}")

    if manifest.status == "processed" and not force:
        return {
            "doc_id": doc_id,
            "status": "skipped_already_processed",
            "chunks_count": 0,
            "facts_count": 0,
            "quarantined_count": 0,
            "outputs": manifest.outputs,
        }

    manifests.mark_processing(doc_id)
    quarantine = QuarantineWriter(storage)
    ingested_at = utc_now_iso()

    try:
        raw_bytes = storage.read_bytes(manifest.raw_key)

        if manifest.source_type == "screener_csv":
            return _process_screener_csv(manifest, raw_bytes, storage, manifests, ingested_at)

        if manifest.source_type == "pdf":
            raw_chunks = _extract_chunks_from_pdf(manifest, raw_bytes)
        elif manifest.source_type == "transcript_json":
            raw_chunks = _extract_chunks_from_transcript_json(manifest, raw_bytes, cfg)
        elif manifest.source_type == "extracted_json":
            raw_chunks = _extract_chunks_from_extracted_json(manifest, raw_bytes, cfg)
        else:
            raise ValueError(f"Unsupported source_type: {manifest.source_type}")

        chunk_records: List[Dict[str, Any]] = []
        for idx, chunk in enumerate(raw_chunks):
            chunk_text = str(chunk.get("chunk_text") or "").strip()
            if not chunk_text:
                continue
            record = ChunkRecord(
                chunk_id=make_chunk_id(doc_id, idx),
                doc_id=doc_id,
                company_id=str(chunk.get("company_id") or manifest.company_id),
                document_type=str(chunk.get("document_type") or manifest.doc_type),
                period=str(chunk.get("period") or manifest.period),
                chunk_index=idx,
                section_name=str(chunk.get("section_name") or manifest.doc_type),
                source_document=str(chunk.get("source_document") or manifest.filename),
                source_page=chunk.get("source_page"),
                speaker=chunk.get("speaker"),
                source_timestamp=chunk.get("source_timestamp"),
                chunk_text=chunk_text,
                ingested_at=ingested_at,
            )
            chunk_records.append(record.model_dump(mode="json"))

        chunks_key = f"processed/chunks/company={manifest.company_id}/doc_type={manifest.doc_type}/{doc_id}.jsonl"
        storage.write_jsonl(chunks_key, chunk_records)
        outputs: Dict[str, str] = {"chunks": chunks_key}

        facts_count = 0
        quarantined_errors: List[Dict[str, Any]] = []
        raw_bad_outputs: List[str] = []

        if not skip_llm and chunk_records:
            gemma_extractor = _load_pipeline_module("gemma_extractor")
            provider = llm_provider or get_llm_provider(cfg)
            is_transcript = manifest.doc_type == "transcript"
            prompt_type = "transcript" if is_transcript else "annual"
            system_prompt = gemma_extractor.TRANSCRIPT_SYSTEM if is_transcript else gemma_extractor.ANNUAL_REPORT_SYSTEM

            target_chunks = (
                chunk_records
                if is_transcript
                else [c for c in chunk_records if gemma_extractor.is_high_signal_chunk(c["chunk_text"])]
            )

            facts_by_table: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            batch_size = max(1, cfg.chunks_per_batch)
            for start in range(0, len(target_chunks), batch_size):
                batch = target_chunks[start : start + batch_size]
                items, raw_text = gemma_extractor.extract_batch_with_raw(
                    None,
                    system_prompt,
                    batch,
                    prompt_type=prompt_type,
                    llm_provider=provider,
                )
                if _looks_like_unparseable_json(raw_text, items):
                    quarantined_errors.append(
                        {
                            "type": "llm_json_parse_error",
                            "batch_start": start,
                            "batch_size": len(batch),
                        }
                    )
                    if raw_text is not None:
                        raw_bad_outputs.append(f"=== BATCH {start} ===\n{raw_text}")
                    continue

                for item in items:
                    table, validated_row, err = validate_fact(item, doc_id=doc_id, ingested_at=ingested_at)
                    if err or validated_row is None or table is None:
                        quarantined_errors.append(
                            {
                                "type": "schema_validation_error",
                                "table": table,
                                "error": err,
                                "item": item,
                            }
                        )
                        continue
                    facts_by_table[table].append(validated_row)

            for table, rows in facts_by_table.items():
                if not rows:
                    continue
                fact_key = f"processed/facts/table={table}/company={manifest.company_id}/{doc_id}.jsonl"
                storage.write_jsonl(fact_key, rows)
                outputs[f"facts_{table}"] = fact_key
                facts_count += len(rows)

            if quarantined_errors:
                q_prefix = quarantine.write(
                    stage="extraction",
                    doc_id=doc_id,
                    input_ref={"doc_id": doc_id, "raw_key": manifest.raw_key, "company_id": manifest.company_id},
                    error={"errors": quarantined_errors},
                    raw_llm_output="\n\n".join(raw_bad_outputs) if raw_bad_outputs else None,
                )
                outputs["quarantine_extraction"] = q_prefix

        if not skip_embed and chunk_records:
            encoder = embed_fn or _default_embed_fn(cfg.embedding_model)
            vectors = encoder([c["chunk_text"] for c in chunk_records])
            if len(vectors) != len(chunk_records):
                raise ValueError(f"Embedding count mismatch: {len(vectors)} vs {len(chunk_records)}")
            embedding_records = [
                EmbeddingRecord(
                    **chunk,
                    embedding=[float(x) for x in vec],
                    embedding_model=cfg.embedding_model,
                ).model_dump(mode="json")
                for chunk, vec in zip(chunk_records, vectors)
            ]
            emb_key = f"processed/embeddings/company={manifest.company_id}/{doc_id}.jsonl"
            storage.write_jsonl(emb_key, embedding_records)
            outputs["embeddings"] = emb_key

        manifests.mark_processed(doc_id, outputs)
        return {
            "doc_id": doc_id,
            "status": "processed",
            "chunks_count": len(chunk_records),
            "facts_count": facts_count,
            "quarantined_count": len(quarantined_errors),
            "outputs": outputs,
        }
    except Exception as exc:
        manifests.mark_failed(doc_id, str(exc))
        quarantine.write(
            stage="worker",
            doc_id=doc_id,
            input_ref={"doc_id": doc_id, "raw_key": manifest.raw_key, "company_id": manifest.company_id},
            error={"type": type(exc).__name__, "message": str(exc)},
        )
        raise


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Process a single manifest document into processed/ JSONL.")
    parser.add_argument("--doc-id", required=True, help="Document SHA-256 ID from manifests/documents/.")
    parser.add_argument("--force", action="store_true", help="Re-process even if manifest status is already processed.")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM fact extraction.")
    parser.add_argument("--skip-embed", action="store_true", help="Skip MiniLM embedding generation.")
    args = parser.parse_args(argv)

    cfg = get_config()
    storage = get_storage(cfg)
    manifests = ManifestStore(storage)
    result = process_document(
        doc_id=args.doc_id,
        storage=storage,
        manifests=manifests,
        config=cfg,
        force=args.force,
        skip_llm=args.skip_llm,
        skip_embed=args.skip_embed,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
