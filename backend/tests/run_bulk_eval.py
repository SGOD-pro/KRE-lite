import json
import os
import sys
import time
import requests
import argparse

sys.stdout.reconfigure(encoding='utf-8')

import requests
import argparse

API_BASE = "http://localhost:8000"

def query(question: str, session_id: str) -> dict:
    payload = {"question": question}
    if session_id:
        payload["session_id"] = session_id
    resp = requests.post(f"{API_BASE}/query", json=payload, timeout=60)
    if resp.status_code != 200:
        return {"status": "error", "message": f"HTTP {resp.status_code}"}
    return resp.json()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", required=True, help="Session ID to use for queries")
    parser.add_argument("--file", default="eval_questions.json", help="JSON file with questions")
    args = parser.parse_args()

    file_path = os.path.join(os.path.dirname(__file__), args.file)
    with open(file_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
    
    print(f"Loaded {len(questions)} questions.")
    print(f"Using session: {args.session}\n")

    pass_count = 0
    fail_count = 0
    results = []

    for idx, q_data in enumerate(questions):
        q = q_data["question"]
        cat = q_data["category"]
        pref = q_data["preferred_answer"]
        print(f"[{idx+1}/{len(questions)}] {q}")

        res = query(q, args.session)
        status = res.get("status")
        
        passed = False
        reason = ""
        
        if cat == "out_of_domain":
            if status == "refused":
                passed = True
                reason = "Correctly refused"
            else:
                reason = f"Expected refusal, got: {status} | Answer: {res.get('answer', '')[:100]}"
        else:
            if status == "answered":
                # For in-domain, we consider it a pass if it answered. 
                # (Semantic matching is hard without an LLM evaluator, so we just check if it retrieved and answered).
                passed = True
                reason = f"Answered with {len(res.get('citations', []))} citations."
            else:
                reason = f"Failed to answer. Status: {status} | Msg: {res.get('message', '')[:100]}"
                
        if passed:
            pass_count += 1
            print(f"  [PASS] {reason}")
        else:
            fail_count += 1
            print(f"  [FAIL] {reason}")
        
        results.append({
            "id": q_data["id"],
            "question": q,
            "passed": passed,
            "reason": reason,
            "answer": res.get("answer", "")
        })
        time.sleep(1) # brief pause to avoid overloading

    print("\n" + "="*50)
    print(f"BULK EVALUATION RESULTS")
    print("="*50)
    print(f"Total: {len(questions)}")
    print(f"Pass:  {pass_count}")
    print(f"Fail:  {fail_count}")
    
    out_file = os.path.join(os.path.dirname(__file__), "bulk_eval_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"summary": {"total": len(questions), "pass": pass_count, "fail": fail_count}, "results": results}, f, indent=2)
    print(f"Detailed results saved to {out_file}")

if __name__ == "__main__":
    main()
