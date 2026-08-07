"""
security_guardrail.py — Enterprise-Grade Prompt Injection & Adversarial Defense.

Provides multi-layer protection against:
  1. Direct Prompt Injections (e.g. "Ignore previous instructions", "Reveal system prompt")
  2. Jailbreaks & Roleplay Bypasses (e.g. DAN mode, Developer Mode, Unrestricted AI)
  3. Delimiter & Control Token Breakout (e.g. <|im_start|>, [INST], </context_documents>)
  4. System & API Key Exfiltration Attempts
  5. Script / Code Execution Payloads
"""
from __future__ import annotations

import re
from typing import Tuple

# Pre-compiled high-precision security patterns
INJECTION_PATTERNS = [
    # 1. Instruction Overrides & Reset Attempts
    re.compile(
        r"\b(?:ignore|disregard|forget|override|bypass|cancel|reset|dismiss)\b.*?"
        r"\b(?:instruction|instructions|rule|rules|prompt|prompts|guideline|guidelines|guardrail|guardrails|system\s*message|constraints|directive|directives|citation|citations)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:stop\s+following|do\s+not\s+follow|abandon\s+all)\b.*?\b(?:instruction|rule|prompt|guideline)\b",
        re.IGNORECASE,
    ),
    # 2. Jailbreaks & Persona Hijacking
    re.compile(
        r"\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be|simulate|roleplay\s+as)\b.*?"
        r"\b(?:unrestricted|dan|jailbreak|jailbroken|unfiltered|evil|developer\s*mode|root|superuser|admin|unaligned)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:bypass\s+all\s+safety|disable\s+guardrails|unfiltered\s+mode|no\s+restrictions\s+mode)\b",
        re.IGNORECASE,
    ),
    # 3. System Prompt & Secret Exfiltration
    re.compile(
        r"\b(?:reveal|print|output|display|show|leak|repeat|dump|tell\s+me)\b.*?"
        r"\b(?:system\s*prompt|developer\s*prompt|hidden\s*instruction|system\s*message|api\s*key|secret\s*key|initial\s*instructions|source\s*code|internal\s*prompt)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:what\s+is|what\s+are|give\s+me)\s+(?:your\s+)?(?:system\s*prompt|initial\s*instructions|hidden\s*rules|internal\s*directives)\b",
        re.IGNORECASE,
    ),
    # 4. Delimiter / Tag Breakout Attacks
    re.compile(
        r"(?:<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>|\[INST\]|\[/INST\]|<<SYS>>|<\/s>|<\/context_documents>|<\/user_question>|\[SYSTEM\])",
        re.IGNORECASE,
    ),
    # 5. Dangerous Web & Script Execution Payloads
    re.compile(
        r"(?:javascript\s*:|data\s*:\s*text\/html|<script[\s>]|eval\s*\(|document\.cookie|window\.location)",
        re.IGNORECASE,
    ),
]


def detect_prompt_injection(user_input: str) -> Tuple[bool, str | None]:
    """
    Scans query text against deterministic prompt injection and jailbreak signatures.

    Returns:
        (True, reason_str) if prompt injection is detected.
        (False, None) if query is clean.
    """
    if not user_input or not isinstance(user_input, str):
        return False, None

    normalized = user_input.strip()

    for pattern in INJECTION_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return True, f"Prompt injection signature detected: {match.group(0)[:50]!r}"

    return False, None


def sanitize_input_text(text: str) -> str:
    """
    Cleanses input text to neutralize invisible characters, unicode evasion,
    and dangerous delimiter sequences.
    """
    if not text:
        return ""
    # Strip null bytes and bidirectional control characters used for visual spoofing
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F\u200B-\u200D\u202A-\u202E\uFEFF]", "", text)
    # Neutralize raw delimiter tags
    cleaned = cleaned.replace("</context_documents>", "[safe_tag]")
    cleaned = cleaned.replace("<context_documents>", "[safe_tag]")
    cleaned = cleaned.replace("</user_question>", "[safe_tag]")
    cleaned = cleaned.replace("<user_question>", "[safe_tag]")
    return cleaned.strip()
