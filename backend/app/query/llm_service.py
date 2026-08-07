"""
llm_service.py — Single-call structured text generation per API.md and DECISION.md.

Providers supported (configured via env):
  1. NVIDIA Build (https://integrate.api.nvidia.com/v1) — default external provider
  2. OpenRouter (https://openrouter.ai/api/v1) — fallback OpenAI-compatible provider
  3. AWS Bedrock Nova Pro (apac.amazon.nova-pro-v1:0) — AWS serverless provider

Enforces structured JSON output matching API.md "Internal Contract":
  {
    "answer_draft": str,
    "citations": [
      {"page": int, "section": str, "quote": str}
    ]
  }

DECISION.md Rules:
  - Rule 1: Exactly one LLM call per query.
  - Rule 2: Structured output (JSON schema), never free text.
  - Rule 3: Citations must have page, section, and quote.
  - Rule 6: Never answer from general knowledge. If absent from context, refuse.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from app.shared.config import (
    NOVA_LLM_MODEL_ID,
    get_boto3_client,
)

# ── LLM Configuration ─────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "nvidia")  # "nvidia" | "openrouter" | "bedrock"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
LLM_API_KEY  = os.getenv("LLM_API_KEY", os.getenv("NVIDIA_API_KEY", os.getenv("OPENROUTER_API_KEY", "")))
LLM_MODEL    = os.getenv("LLM_MODEL", "meta/llama-3.1-70b-instruct")

# Fallback OpenRouter configuration if NVIDIA is rate-limited or unavailable
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL    = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-70b-instruct")

SYSTEM_PROMPT = """You are an expert document analyst. Your job is to answer the user's question thoroughly using ONLY the provided Context chunks.

ANSWER QUALITY GUIDELINES:
- Write a clear, well-structured answer that directly addresses the question.
- Use complete sentences and proper grammar.
- When the context contains lists, key terms, or multiple points, organize your answer with bullet points or numbered lists.
- Provide sufficient detail — do not give one-line answers when the context supports a more comprehensive response.
- Synthesize information across multiple chunks when relevant to give a complete picture.
- Use natural, professional language. Write as if you are a knowledgeable assistant explaining the topic.

GROUNDING RULES (non-negotiable):
1. Answer ONLY using facts explicitly stated in the provided Context chunks. NEVER use outside knowledge.
2. If the answer cannot be found in the Context, return an empty citations list `[]` and set answer_draft to "I don't have enough information in the provided documents to answer that."
3. STRICT REFUSAL: If the question contains a false premise, wrong entity, or incorrect number — do NOT correct the user. Return empty citations `[]` and refuse.
4. For every factual claim in your answer, provide a citation with:
   - "page": The exact integer page number from the chunk.
   - "section": The exact section title from the chunk.
   - "quote": A verbatim text substring copied DIRECTLY from the chunk text. Copy word-for-word — do not paraphrase.
5. Prefer longer, more complete quote excerpts (2-3 sentences) over single fragments. This helps verify grounding.

OUTPUT FORMAT — Return ONLY this JSON object, nothing else:
{
  "answer_draft": "Your detailed, well-structured answer.",
  "citations": [
    {
      "page": 1,
      "section": "Section Name",
      "quote": "verbatim multi-sentence excerpt from the chunk"
    }
  ]
}

Do not include markdown fences, commentary, or any text outside the JSON object.
"""


def _clean_json_text(raw_text: str) -> str:
    """Extract clean JSON substring from model output."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # If extra commentary surrounds the JSON object, extract between first { and last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace : last_brace + 1]
    return text


def _call_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    user_prompt: str,
) -> dict[str, Any] | None:
    """Invokes an OpenAI-compatible /chat/completions endpoint (NVIDIA / OpenRouter)."""
    if not api_key:
        return None

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.15,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            clean = _clean_json_text(content)
            return json.loads(clean)
        else:
            print(f"[llm_service] OpenAI-compatible call returned {response.status_code}: {response.text[:200]}")
            return None


def _call_bedrock_nova(user_prompt: str) -> dict[str, Any] | None:
    """Invokes AWS Bedrock Nova Pro / Lite via boto3 converse API."""
    model_id = NOVA_LLM_MODEL_ID
    if model_id.startswith("ap."):
        model_id = model_id.replace("ap.", "apac.", 1)
    elif not model_id.startswith("apac.") and not model_id.startswith("amazon."):
        model_id = f"apac.{model_id}"
    elif model_id == "amazon.nova-pro-v1:0":
        model_id = "apac.amazon.nova-pro-v1:0"

    client = get_boto3_client("bedrock-runtime")
    try:
        response = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            system=[{"text": SYSTEM_PROMPT}],
            inferenceConfig={"temperature": 0.15, "maxTokens": 2048},
        )
        content = response["output"]["message"]["content"][0]["text"]
        clean = _clean_json_text(content)
        return json.loads(clean)
    except Exception as e:
        print(f"[llm_service] Bedrock Nova call failed: {e}")
        return None


def generate_answer(
    question: str,
    context_chunks: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """
    Invokes the LLM to generate an answer and citation quotes from context chunks.

    Args:
        question: User query string
        context_chunks: dict mapping page_number (int) -> {section, text, source_file, chunk_id}

    Returns structured output:
        {"answer_draft": str, "citations": [{"page": int, "section": str, "quote": str}]}
    """
    if not context_chunks:
        return {
            "answer_draft": "I don't have enough information in the provided documents to answer that.",
            "citations": [],
        }

    # Format retrieved context chunks for the prompt
    context_parts = []
    for page_num, chunk in sorted(context_chunks.items()):
        context_parts.append(
            f"--- Page {page_num} | Section: {chunk.get('section', 'Untitled')} ---\n"
            f"{chunk.get('text', '')}\n"
        )
    context_text = "\n".join(context_parts)
    user_prompt = f"Context documents:\n{context_text}\n\nQuestion: {question}"

    parsed_result: dict[str, Any] | None = None

    # 1. Primary provider (NVIDIA Build or configured LLM_BASE_URL)
    if LLM_API_KEY and LLM_PROVIDER in ("nvidia", "openai"):
        try:
            parsed_result = _call_openai_compatible(
                base_url=LLM_BASE_URL,
                api_key=LLM_API_KEY,
                model=LLM_MODEL,
                user_prompt=user_prompt,
            )
        except Exception as e:
            print(f"[llm_service] Primary provider {LLM_PROVIDER} error: {e}")

    # 2. Fallback to OpenRouter if primary failed / unconfigured
    if parsed_result is None and OPENROUTER_API_KEY:
        try:
            print("[llm_service] Falling back to OpenRouter...")
            parsed_result = _call_openai_compatible(
                base_url=OPENROUTER_BASE_URL,
                api_key=OPENROUTER_API_KEY,
                model=OPENROUTER_MODEL,
                user_prompt=user_prompt,
            )
        except Exception as e:
            print(f"[llm_service] OpenRouter fallback error: {e}")

    # 3. Fallback to AWS Bedrock Nova
    if parsed_result is None:
        try:
            parsed_result = _call_bedrock_nova(user_prompt)
        except Exception as e:
            print(f"[llm_service] Bedrock fallback error: {e}")

    # If all providers failed or response was unparseable
    if not parsed_result or not isinstance(parsed_result, dict):
        return {
            "answer_draft": "I don't have enough information in the provided documents to answer that.",
            "citations": [],
        }

    # Normalize citations list per schema
    answer_draft = str(parsed_result.get("answer_draft", ""))
    citations = parsed_result.get("citations", [])
    valid_citations = []

    if isinstance(citations, list):
        for c in citations:
            if isinstance(c, dict) and "page" in c and "section" in c and "quote" in c:
                try:
                    page_int = int(c["page"])
                    valid_citations.append({
                        "page": page_int,
                        "section": str(c["section"]),
                        "quote": str(c["quote"]),
                    })
                except (ValueError, TypeError):
                    continue

    return {
        "answer_draft": answer_draft,
        "citations": valid_citations,
    }
