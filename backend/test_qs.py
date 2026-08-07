import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
session = 'reingest_1786120796'
qs = [
    'What is the dimension of the model (d_model) used in the base Transformer architecture?',
    'what is transformers'
]

for q in qs:
    print(f'Q: {q}')
    resp = requests.post('http://localhost:8000/query', json={'question': q, 'session_id': session})
    data = resp.json()
    print(f'Status: {data.get("status")}')
    print(f'Answer: {data.get("answer", data.get("message"))}')
    if data.get('citations'):
        print(f'Citations: {len(data["citations"])}')
    print('-'*40)
