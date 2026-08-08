import os
import sys
import re
from thefuzz import fuzz

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.query.citation_verifier import _quote_matches_chunk, _normalize, STOPWORDS
from app.query.vector_retriever import vector_search
from app.query.bm25_retriever import bm25_search
from app.query.fusion import reciprocal_rank_fusion

q = "In Attention Is All You Need, what BLEU score did the Transformer base model achieve on the WMT 2014 English-to-German translation task?"
v_res = vector_search(q, top_k=15)
b_res = bm25_search(q, top_k=20)
fused = reciprocal_rank_fusion([b_res, v_res], top_k=15)

context_chunks_by_page = {}
for chunk in fused:
    p = chunk.get("page_number")
    if p is not None:
        t = (chunk.get("text") or "").strip()
        if p in context_chunks_by_page:
            if t not in context_chunks_by_page[p]["text"]:
                context_chunks_by_page[p]["text"] += "\n\n" + t
        else:
            context_chunks_by_page[p] = {
                "page": p,
                "section": chunk.get("section_title", "Untitled"),
                "text": t,
                "source_file": chunk.get("source_file", ""),
                "chunk_id": chunk.get("chunk_id", f"page_{p}"),
            }

all_chunks_text = " ".join(
    f"{c.get('section', '')} {c.get('text', '')}"
    for c in context_chunks_by_page.values()
).lower()

print(f"'2014' in all_chunks_text: {'2014' in all_chunks_text}")
print(f"'wmt 2014' in all_chunks_text: {'wmt 2014' in all_chunks_text}")

# Check quote on page 9 vs other pages
q_run3 = "For the base models, we used a single model obtained by averaging the last 5 che"
print(f"\nTesting quote: '{q_run3}'")
for p, c in context_chunks_by_page.items():
    sec = c.get("section")
    t = c.get("text")
    m = _quote_matches_chunk(q_run3, f"{sec}\n{t}")
    if m:
        print(f"  --> MATCHED on Page {p} [{sec}]")
    else:
        # Check why it failed
        q_norm = _normalize(q_run3)
        t_norm = _normalize(t)
        q_nopunct = re.sub(r"[^\w\s]", "", q_norm)
        t_nopunct = re.sub(r"[^\w\s]", "", t_norm)
        q_words = q_nopunct.split()
        t_words = t_nopunct.split()
        q_nums = re.findall(r"\b\d+\b", q_norm)
        has_nums = all(n in t_norm for n in q_nums)
        # Check window fuzz
        max_ratio = 0
        n = len(q_words)
        for win_len in range(max(1, n - 2), min(len(t_words) + 1, n + 3)):
            for i in range(len(t_words) - win_len + 1):
                window = t_words[i : i + win_len]
                win_str = " ".join(window)
                score = fuzz.ratio(q_nopunct, win_str)
                if score > max_ratio:
                    max_ratio = score
        if max_ratio > 60:
            print(f"  Page {p} [{sec}]: max_ratio={max_ratio}, has_nums={has_nums}")
