import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.query.citation_verifier import verify_citations, _quote_matches_chunk
from app.query.planner import answer_question

# In Run 3:
# draft = 'The Transformer base model achieved a BLEU score of 25.8 on the WMT 2014 English-to-German translation task.'
# cite = [{'page': 9, 'section': 'Model Variations', 'quote': 'For the base models, we used a single model obtained by averaging the last 5 che'}]

# Let's test with the actual pipeline:
res = answer_question("In Attention Is All You Need, what BLEU score did the Transformer base model achieve on the WMT 2014 English-to-German translation task?")
print(f"Result status: {res.get('status')}")
print(f"Result answer: {res.get('answer')}")
print(f"Result citations: {res.get('citations')}")
print(f"Result reason: {res.get('reason')} - {res.get('message')}")
