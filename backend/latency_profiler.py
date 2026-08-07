"""
latency_profiler.py — Measure per-stage latency breakdown across grounded and adversarial queries.
"""
import sys
import time
from typing import Any

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.ingest.embed_service import embed_query
from app.query.vector_retriever import vector_search
from app.query.bm25_retriever import bm25_search
from app.query.fusion import reciprocal_rank_fusion
from app.query.llm_service import generate_answer
from app.query.citation_verifier import verify_citations

SAMPLE_QUERIES = [
    ("What is the attention mechanism used in the Transformer model?", "Grounded Fact"),
    ("In Attention Is All You Need, what BLEU score did the Transformer base model achieve on the WMT 2014 English-to-German translation task?", "Grounded Fact - Exact Number"),
    ("Did Attention Is All You Need achieve a BLEU score of 98.5 on the French translation task?", "Adversarial: Wrong Entity / Number Swap"),
    ("Does the base Transformer model use 128 layers in the encoder stack?", "Adversarial: Wrong Number Swap"),
    ("What were the training costs of the Transformer on AWS EC2 p4de instances in dollars?", "Adversarial: Adjacent-but-Absent"),
    ("Since the Transformer completely avoids using matrix multiplication, how does it compute attention?", "Adversarial: Leading False Premise"),
    ("What was Google's total net revenue in fiscal year 2023?", "Adversarial: Out-of-Corpus"),
]

def profile_query(question: str, session_id: str | None = None):
    timings = {}
    clean_question = question.strip()

    # Stage 1: Embed Query (Titan v2 on Bedrock)
    t0 = time.perf_counter()
    _ = embed_query(clean_question)
    t1 = time.perf_counter()
    timings["1_embed_query_titan_ms"] = round((t1 - t0) * 1000, 2)

    # Stage 2: Qdrant Vector Search
    t0 = time.perf_counter()
    vector_results = vector_search(clean_question, top_k=20, session_id=session_id)
    t1 = time.perf_counter()
    timings["2_qdrant_vector_search_ms"] = round((t1 - t0) * 1000, 2)

    # Stage 3: In-process BM25 Search
    t0 = time.perf_counter()
    bm25_results = bm25_search(clean_question, top_k=20, session_id=session_id)
    t1 = time.perf_counter()
    timings["3_bm25_search_ms"] = round((t1 - t0) * 1000, 2)

    # Stage 4: RRF Fusion
    t0 = time.perf_counter()
    fused_chunks_list = reciprocal_rank_fusion([bm25_results, vector_results], top_k=5)
    t1 = time.perf_counter()
    timings["4_rrf_fusion_ms"] = round((t1 - t0) * 1000, 2)

    # Format context chunks
    t0 = time.perf_counter()
    context_chunks_by_page: dict[int, dict[str, Any]] = {}
    for chunk in fused_chunks_list:
        page_num = chunk.get("page_number")
        if page_num is not None:
            if page_num in context_chunks_by_page:
                context_chunks_by_page[page_num]["text"] += "\n" + chunk.get("text", "")
            else:
                context_chunks_by_page[page_num] = {
                    "page": page_num,
                    "section": chunk.get("section_title", "Untitled"),
                    "text": chunk.get("text", ""),
                    "source_file": chunk.get("source_file", ""),
                    "chunk_id": chunk.get("chunk_id", f"page_{page_num}"),
                }
    t1 = time.perf_counter()
    timings["5_format_context_ms"] = round((t1 - t0) * 1000, 2)

    # Stage 6: LLM Generation (AWS Bedrock Nova Pro Converse API)
    t0 = time.perf_counter()
    llm_output = generate_answer(clean_question, context_chunks=context_chunks_by_page)
    t1 = time.perf_counter()
    timings["6_llm_nova_pro_converse_ms"] = round((t1 - t0) * 1000, 2)

    # Stage 7: Deterministic Citation Verification & Guardrail
    t0 = time.perf_counter()
    final_output = verify_citations(llm_output, context_chunks_by_page, question=clean_question)
    t1 = time.perf_counter()
    timings["7_citation_verifier_ms"] = round((t1 - t0) * 1000, 2)

    total_ms = sum(timings.values())
    timings["TOTAL_QUERY_PIPELINE_MS"] = round(total_ms, 2)

    return timings, final_output

if __name__ == "__main__":
    print("=" * 80)
    print("PER-STAGE PIPELINE LATENCY PROFILE")
    print("=" * 80)
    
    stage_totals = {}
    
    for q, qtype in SAMPLE_QUERIES:
        print(f"\n[{qtype}]")
        print(f"  Q: \"{q}\"")
        timings, final_output = profile_query(q)
        status = final_output.get("status")
        cits = len(final_output.get("citations", []))
        print(f"  Result: status={status}, citations={cits}")
        for stage, ms in timings.items():
            print(f"    {stage:35s} : {ms:8.2f} ms")
            if stage not in stage_totals:
                stage_totals[stage] = []
            stage_totals[stage].append(ms)

    print("\n" + "=" * 80)
    print("AVERAGE LATENCY PER STAGE ACROSS ALL QUERIES")
    print("=" * 80)
    for stage, values in stage_totals.items():
        avg_ms = sum(values) / len(values)
        pct = (avg_ms / (sum(stage_totals["TOTAL_QUERY_PIPELINE_MS"]) / len(stage_totals["TOTAL_QUERY_PIPELINE_MS"]))) * 100 if stage != "TOTAL_QUERY_PIPELINE_MS" else 100.0
        print(f"  {stage:35s} : {avg_ms:8.2f} ms  ({pct:5.1f}%)")
