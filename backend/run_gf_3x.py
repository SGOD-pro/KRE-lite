import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.query.planner import answer_question
from benchmark_evaluation import GROUNDED_FACT_SET

def run_grounded_fact_suite(run_number: int):
    print(f"\n{'='*80}")
    print(f"GROUNDED FACT EVALUATION — RUN {run_number}")
    print(f"{'='*80}")
    
    passed_count = 0
    total = len(GROUNDED_FACT_SET)
    results = []
    
    for item in GROUNDED_FACT_SET:
        qid = item["id"]
        q = item["question"]
        expected = item["expected_status"]
        
        t0 = time.perf_counter()
        res = answer_question(q)
        lat_ms = (time.perf_counter() - t0) * 1000
        
        actual_status = res.get("status")
        citations = res.get("citations", [])
        answer = res.get("answer", "")
        
        is_pass = (actual_status == expected) and (len(citations) > 0 if expected == "answered" else True)
        if is_pass:
            passed_count += 1
            
        print(f"[{qid}] Expected: {expected:<8} | Actual: {actual_status:<8} | Citations: {len(citations)} | Latency: {lat_ms:6.1f}ms | {'PASS' if is_pass else 'FAIL'}")
        if not is_pass:
            print(f"   Question: {q}")
            print(f"   Reason/Answer: {res.get('reason') or res.get('message') or answer[:100]}")
        else:
            if citations:
                print(f"   Verified Quote: p.{citations[0].get('page')} [{citations[0].get('section')}]: {citations[0].get('quote')[:80]}...")
                
        results.append({
            "id": qid,
            "question": q,
            "expected": expected,
            "actual": actual_status,
            "passed": is_pass,
            "citations_count": len(citations),
        })
        
    print(f"\nRun {run_number} Total: {passed_count}/{total} ({(passed_count/total)*100:.1f}%)")
    return passed_count, total, results

if __name__ == "__main__":
    run_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    passed, total, _ = run_grounded_fact_suite(run_num)
    sys.exit(0 if passed == total else 1)
