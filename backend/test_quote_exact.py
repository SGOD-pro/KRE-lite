import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.query.citation_verifier import _quote_matches_chunk, _normalize
from app.query.vector_retriever import vector_search
from app.query.bm25_retriever import bm25_search
from app.query.fusion import reciprocal_rank_fusion

q = "In Attention Is All You Need, what BLEU score did the Transformer base model achieve on the WMT 2014 English-to-German translation task?"
v_res = vector_search(q, top_k=15)
b_res = bm25_search(q, top_k=20)
fused = reciprocal_rank_fusion([b_res, v_res], top_k=15)

for c in fused:
    p = c.get("page_number")
    sec = c.get("section_title")
    t = c.get("text", "")
    q_test = "For the base models, we used a single model obtained by averaging the last 5 che"
    m = _quote_matches_chunk(q_test, t)
    print(f"Page {p} [{sec}] match: {m}")
