import requests
import sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://localhost:8000'

# Simulate the exact scenario: user has a session_id that has partial or no docs
# Previously this would fail, now it should use global search + session boost
TEST_CASES = [
    # (question, session_id, expected_status)
    ("What is the main characteristic of multi-head attention?", None, "answered"),
    ("What is the main characteristic of multi-head attention?", "session_72dd54020e87", "answered"),
    ("What is the main characteristic of multi-head attention?", "session_fake_empty_123", "answered"),
    ("How many parallel attention layers (heads) are employed in the base Transformer?", None, "answered"),
    ("What is the dimension of the model (d_model) used in the base Transformer?", None, "answered"),
    # Out of domain - must always refuse
    ("What is the stock price of Apple?", None, "refused"),
    ("Who won the FIFA World Cup 2022?", "reingest_1786120796", "refused"),
]

for q, sid, expected in TEST_CASES:
    resp = requests.post(f'{BASE}/query', json={'question': q, 'session_id': sid})
    data = resp.json()
    status = data.get('status')
    ok = "[PASS]" if status == expected else "[FAIL]"
    ans = data.get('answer', data.get('message', ''))[:80]
    print(f"{ok} session={str(sid)[:25]!r} | expected={expected} got={status}")
    print(f"   Answer: {ans}")
    print()
