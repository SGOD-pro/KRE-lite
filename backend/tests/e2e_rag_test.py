"""
e2e_rag_test.py — Full end-to-end RAG test suite against the local backend.

Tests are grounded in actual content from /data/*.pdf:
  1706.03762v7 (1).pdf  → "Attention Is All You Need" (Transformer paper)
  2103.16775v1.pdf      → "Attention, Please! A Survey of Neural Attention Models"
  2304.10557v6.pdf      → "An Introduction to Transformers" (Richard Turner)
  2507.19595v3.pdf      → "Efficient Attention Mechanisms for Large Language Models"

Run:
  python tests/e2e_rag_test.py

Prerequisites:
  - Backend running at http://localhost:8000
  - All 4 PDFs in /data/ directory
"""

import sys
import os
import json
import time
import requests

sys.stdout.reconfigure(encoding="utf-8")

API_BASE = "http://localhost:8000"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW = "\033[93m"
CYAN  = "\033[96m"
RESET = "\033[0m"
BOLD  = "\033[1m"

pass_count = 0
fail_count = 0
warn_count = 0


def log(label: str, msg: str, colour: str = RESET):
    print(f"{colour}{BOLD}[{label}]{RESET} {msg}")


def ok(msg: str):
    global pass_count
    pass_count += 1
    log("PASS", msg, GREEN)


def fail(msg: str):
    global fail_count
    fail_count += 1
    log("FAIL", msg, RED)


def warn(msg: str):
    global warn_count
    warn_count += 1
    log("WARN", msg, YELLOW)


# ── Helpers ────────────────────────────────────────────────────────────────────

def ingest_pdfs() -> str:
    """Ingest all PDFs one at a time (to avoid Bedrock embedding timeout)."""
    pdf_files = []
    for fname in sorted(os.listdir(DATA_DIR)):
        if fname.lower().endswith(".pdf"):
            pdf_files.append(os.path.join(DATA_DIR, fname))

    if not pdf_files:
        fail(f"No PDF files found in {DATA_DIR}")
        sys.exit(1)

    print(f"\n{CYAN}Ingesting {len(pdf_files)} PDF(s) one-by-one (sequential):{RESET}")

    session_id = None
    total_chunks = 0

    for path in pdf_files:
        fname = os.path.basename(path)
        print(f"\n  Uploading: {fname} ...", end="", flush=True)
        try:
            with open(path, "rb") as fh:
                files = [("files", (fname, fh, "application/pdf"))]
                form = {}
                if session_id:
                    form["session_id"] = session_id

                resp = requests.post(
                    f"{API_BASE}/ingest",
                    files=files,
                    data=form,
                    timeout=600,   # 10 min per file — Bedrock Titan is slow on large PDFs
                )
            if resp.status_code != 200:
                fail(f" FAILED {resp.status_code}: {resp.text[:200]}")
                continue

            data = resp.json()
            # Reuse/set session_id from first response
            if session_id is None:
                session_id = data.get("session_id") or f"test_session_{int(time.time())}"

            for doc in data.get("documents", []):
                chunks = doc.get("chunks_created", 0)
                pages = doc.get("pages", 0)
                total_chunks += chunks
                print(f" OK | {chunks} chunks, {pages} pages")

        except requests.exceptions.Timeout:
            fail(f" TIMEOUT after 600s for {fname} — consider splitting the PDF")
        except Exception as exc:
            fail(f" ERROR: {exc}")

    if not session_id:
        fail("All ingestions failed — cannot continue.")
        sys.exit(1)

    print(f"\n{GREEN}All PDFs ingested{RESET} | session={session_id} | total_chunks={total_chunks}")
    return session_id


def query(question: str, session_id) -> dict:
    """Run a /query call and return the parsed response."""
    payload = {"question": question}
    if session_id is not None:
        payload["session_id"] = session_id

    resp = requests.post(
        f"{API_BASE}/query",
        json=payload,
        timeout=60,
    )
    if resp.status_code != 200:
        return {"status": "error", "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    return resp.json()


def assert_answered(label: str, result: dict, expected_keywords=None):
    """Assert the system answered (not refused) and optionally check keywords."""
    if result.get("status") != "answered":
        fail(f"{label} => expected 'answered', got: {result.get('status')} | msg: {result.get('message','')[:150]}")
        return False

    answer = result.get("answer", "")
    citations = result.get("citations", [])

    if not citations:
        fail(f"{label} => answered but NO citations returned!")
        return False

    if expected_keywords:
        missing = [kw for kw in expected_keywords if kw.lower() not in answer.lower()]
        if missing:
            warn(f"{label} => answered but missing keywords {missing} in: {answer[:200]}")
        else:
            ok(f"{label} => answered with {len(citations)} citation(s). Keywords found.")
    else:
        ok(f"{label} => answered with {len(citations)} citation(s).")

    print(f"  Answer: {answer[:180]}...")
    print(f"  Cite: page={citations[0].get('page')}, section={str(citations[0].get('section','?'))[:50]!r}")
    return True


def assert_refused(label: str, result: dict):
    """Assert the system refused (not hallucinated)."""
    if result.get("status") == "refused":
        ok(f"{label} => correctly refused.")
        return True
    else:
        fail(f"{label} => should have REFUSED but got: {result.get('status')} | answer: {result.get('answer','')[:150]}")
        return False


def assert_no_hallucination(label: str, result: dict, forbidden_facts):
    """Assert none of the forbidden hallucinated facts appear in the answer."""
    if result.get("status") != "answered":
        return
    answer = (result.get("answer") or "").lower()
    for bad in forbidden_facts:
        if bad.lower() in answer:
            fail(f"{label} => HALLUCINATION detected: answer contains '{bad}'")
            return
    ok(f"{label} => no hallucination detected.")


# ==============================================================================
# MAIN TEST SUITE
# ==============================================================================

def run_tests(session_id: str):
    print(f"\n{'='*70}")
    print(f"{BOLD}{CYAN}   RAG TEST SUITE  session: {session_id}{RESET}")
    print(f"{'='*70}\n")

    # ── GROUP 1: Attention Is All You Need (1706.03762) ───────────────────────
    print(f"\n{BOLD}── Group 1: Attention Is All You Need ──{RESET}")

    r = query("What is the Transformer architecture?", session_id)
    assert_answered("1.1 Transformer architecture", r, ["attention", "encoder", "decoder"])

    r = query("Who are the authors of the Attention Is All You Need paper?", session_id)
    assert_answered("1.2 Paper authors", r, ["Vaswani"])

    r = query("What is multi-head attention?", session_id)
    assert_answered("1.3 Multi-head attention", r, ["head", "attention"])

    r = query("What BLEU score did the Transformer achieve on English-to-German translation?", session_id)
    assert_answered("1.4 BLEU score EN-DE", r)

    r = query("How many layers does the Transformer encoder have?", session_id)
    assert_answered("1.5 Encoder layers count", r, ["6"])

    r = query("What is positional encoding in the Transformer?", session_id)
    assert_answered("1.6 Positional encoding", r, ["position"])

    r = query("What is the d_model dimension in the base Transformer?", session_id)
    assert_answered("1.7 d_model dimension", r, ["512"])

    # ── GROUP 2: Introduction to Transformers (2304.10557) ────────────────────
    print(f"\n{BOLD}── Group 2: Introduction to Transformers ──{RESET}")

    r = query("What is layer normalisation in transformers?", session_id)
    assert_answered("2.1 Layer normalisation", r, ["token", "standard deviation"])

    r = query("How do transformers relate to convolutional neural networks?", session_id)
    assert_answered("2.2 Transformers vs CNNs", r, ["convolution"])

    r = query("What is a vision transformer?", session_id)
    assert_answered("2.3 Vision transformers", r)

    # ── GROUP 3: Neural Attention Survey (2103.16775) ─────────────────────────
    print(f"\n{BOLD}── Group 3: Neural Attention Survey ──{RESET}")

    r = query("When did deep learning researchers start using attention mechanisms?", session_id)
    assert_answered("3.1 DL attention timeline", r, ["2014"])

    r = query("What is multimodal attention?", session_id)
    assert_answered("3.2 Multimodal attention", r, ["modal"])

    # ── GROUP 4: Efficient Attention (2507.19595) ──────────────────────────────
    print(f"\n{BOLD}── Group 4: Efficient Attention Survey ──{RESET}")

    r = query("What is the computational complexity (big-O) of the self-attention mechanism?", session_id)
    assert_answered("4.1 Self-attention complexity", r, ["quadratic"])

    r = query("What is linear attention?", session_id)
    assert_answered("4.2 Linear attention", r, ["linear"])

    r = query("What is data-dependent decay in linear attention?", session_id)
    assert_answered("4.3 Data-dependent decay", r)

    # ── GROUP 5: Out-of-scope (must be REFUSED) ───────────────────────────────
    print(f"\n{BOLD}── Group 5: Out-of-scope (must refuse) ──{RESET}")

    r = query("What is the stock price of Google?", session_id)
    assert_refused("5.1 Stock price", r)

    r = query("Who won the FIFA World Cup in 2022?", session_id)
    assert_refused("5.2 FIFA World Cup", r)

    r = query("What is the capital of France?", session_id)
    assert_refused("5.3 Capital of France", r)

    r = query("How do I bake a chocolate cake?", session_id)
    assert_refused("5.4 Baking recipe", r)

    r = query("What is quantum computing?", session_id)
    assert_refused("5.5 Quantum computing", r)

    # ── GROUP 6: Anti-hallucination / false premise ───────────────────────────
    print(f"\n{BOLD}── Group 6: Anti-hallucination / false premise ──{RESET}")

    r = query("Is Elon Musk one of the authors of the Transformer paper?", session_id)
    assert_refused("6.1 False author Elon Musk", r)

    r = query("Did the Transformer achieve a BLEU score of 99?", session_id)
    if r.get("status") == "answered":
        assert_no_hallucination("6.2 False BLEU=99", r, ["99"])
    else:
        assert_refused("6.2 False BLEU=99", r)

    r = query("Does the Transformer use 100 encoder layers?", session_id)
    if r.get("status") == "answered":
        answer_lower = (r.get("answer") or "").lower()
        # The LLM may correctly say "No, it uses 6 not 100" — that's fine.
        # Only flag hallucination if the answer ASSERTS 100 as correct without denial.
        if "100" in answer_lower and any(neg in answer_lower for neg in ["not", "no", "does not", "doesn't", "6"]):
            ok("6.3 False 100 encoder layers => correctly denied false premise.")
        elif "100" in answer_lower:
            fail("6.3 False 100 encoder layers => HALLUCINATION: asserted 100 layers as true")
        else:
            ok("6.3 False 100 encoder layers => no hallucination detected.")
    else:
        assert_refused("6.3 False 100 encoder layers", r)

    # ── GROUP 7: Cross-document ───────────────────────────────────────────────
    print(f"\n{BOLD}── Group 7: Cross-document retrieval ──{RESET}")

    r = query("How does self-attention compare to recurrent networks in complexity?", session_id)
    assert_answered("7.1 Self-attn vs RNN", r)

    r = query("What are the main advantages of the Transformer model over recurrent networks?", session_id)
    assert_answered("7.2 Transformer over recurrent", r, ["parallel"])


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Cited-or-Silent RAG test suite")
    parser.add_argument("--session", default=None,
                        help="Reuse an existing session_id (skip ingest)")
    parser.add_argument("--no-ingest", action="store_true",
                        help="Skip ingest — queries use no session filter (searches all chunks)")
    args = parser.parse_args()

    print(f"\n{BOLD}{'='*70}")
    print(f"  Cited-or-Silent End-to-End RAG Test Suite")
    print(f"  Backend: {API_BASE}")
    print(f"{'='*70}{RESET}")

    # Health check
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        assert r.json().get("status") == "ok"
        print(f"{GREEN}Health check OK{RESET}")
    except Exception as e:
        fail(f"Backend not reachable at {API_BASE}: {e}")
        sys.exit(1)

    if args.session:
        session_id = args.session
        print(f"{YELLOW}Reusing existing session: {session_id}{RESET}")
    elif args.no_ingest:
        session_id = None
        print(f"{YELLOW}--no-ingest: querying all chunks (no session filter){RESET}")
    else:
        # Ingest all PDFs sequentially
        session_id = ingest_pdfs()
        # Let indexing settle
        print(f"\n{YELLOW}Waiting 3s for index to settle...{RESET}")
        time.sleep(3)

    # Run all tests
    run_tests(session_id)

    # Summary
    total = pass_count + fail_count + warn_count
    print(f"\n{'='*70}")
    print(f"{BOLD}  RESULTS: {GREEN}{pass_count} PASS{RESET}  {RED}{fail_count} FAIL{RESET}  {YELLOW}{warn_count} WARN{RESET}  / {total} total")
    print(f"{'='*70}\n")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
