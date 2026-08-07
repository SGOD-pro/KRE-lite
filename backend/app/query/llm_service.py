"""
llm_service.py — AWS Bedrock Nova text generation.

Provides a structured JSON output containing the answer and citations.
"""
from __future__ import annotations

import json
from typing import Any, List, Optional

from app.shared.config import NOVA_LLM_MODEL_ID, get_boto3_client

SYSTEM_PROMPT = """You are a strict, factual assistant. You answer questions based ONLY on the provided Context. 
You must never hallucinate, guess, or use outside knowledge. 

If the Context does not contain the answer, you must return a refusal.
You must output your response in valid JSON format matching this schema:

{
  "answer_draft": "Your detailed answer here. If you cannot answer based on the context, say 'I cannot answer this question based on the provided documents.'",
  "citations": [
    {
      "chunk_id": "The chunk_id of the source text",
      "page": 12,
      "section": "The section_title of the source text",
      "quote": "The exact verbatim text from the context that supports this part of the answer."
    }
  ]
}

Rules for citations:
1. `quote` MUST be a word-for-word substring copied directly from the Context. Do not summarize or alter it.
2. If you cannot answer the question, return an empty list `[]` for citations.
"""


def generate_answer(question: str, context_chunks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Calls Bedrock Nova to generate an answer and citations.
    Returns a dict with 'answer_draft' (str) and 'citations' (list of dicts).
    """
    if not context_chunks:
        return {
            "answer_draft": "I cannot answer this question based on the provided documents.",
            "citations": []
        }

    # Build context string
    context_text = "Context chunks:\n"
    for chunk_id, chunk in context_chunks.items():
        context_text += (
            f"--- Chunk ID: {chunk_id} ---\n"
            f"Page: {chunk.get('page', 'unknown')}\n"
            f"Section: {chunk.get('section', 'unknown')}\n"
            f"Text: {chunk.get('text', '')}\n\n"
        )

    user_prompt = f"{context_text}\n\nQuestion: {question}"

    client = get_boto3_client("bedrock-runtime")
    
    try:
        response = client.converse(
            modelId=NOVA_LLM_MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_prompt}]
                }
            ],
            system=[{"text": SYSTEM_PROMPT}],
            inferenceConfig={
                "temperature": 0.1,  # Keep it deterministic
            }
        )
        
        # Extract the text response
        output_text = response["output"]["message"]["content"][0]["text"]
        
        # The LLM might wrap the JSON in ```json ... ``` markdown blocks, so clean it
        clean_text = output_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        return json.loads(clean_text.strip())
        
    except Exception as e:
        print(f"LLM Generation error: {e}")
        # Fallback to safe refusal
        return {
            "answer_draft": "I encountered an error while generating the response.",
            "citations": []
        }
