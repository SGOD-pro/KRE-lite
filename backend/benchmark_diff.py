#!/usr/bin/env python3
"""
benchmark_diff.py — compares a before/after benchmark snapshot pair
and prints a delta table. Exits non-zero if the adversarial refusal
count regressed, so the "hard gate" can be enforced by CI or by an
agent checking the exit code, not just eyeballing output.

Usage:
    python benchmark_diff.py <baseline.json> <after.json>

Expected JSON shape for each snapshot (matches benchmark_evaluation.py output):

{
  "timestamp": "2026-08-09T14:22:00Z",
  "avg_latency_ms": 3450.2,
  "avg_prompt_tokens": 480,
  "avg_completion_tokens": 90,
  "citation_faithfulness_pct": 100.0,
  "grounded_fact_accuracy_pct": 94.7,
  "adversarial_refusal_count": 8,
  "adversarial_refusal_total": 8,
  "adversarial_failures": []   // list of question strings that
                                // wrongly answered instead of refused
}
"""
import json
import sys
from pathlib import Path


def load_snapshot(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"ERROR: snapshot file not found: {path}")
        sys.exit(2)
    with open(p) as f:
        return json.load(f)


def pct_change(before: float, after: float) -> str:
    if before == 0:
        return "n/a"
    change = ((after - before) / before) * 100
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.1f}%"


def fmt_row(label: str, before, after, unit: str = "", lower_is_better: bool = True) -> str:
    delta = after - before
    delta_str = f"{'+' if delta > 0 else ''}{delta:.2f}{unit}"
    pct = pct_change(before, after)
    arrow = ""
    if lower_is_better:
        arrow = "GOOD" if delta < 0 else ("SAME" if delta == 0 else "WORSE")
    else:
        arrow = "GOOD" if delta > 0 else ("SAME" if delta == 0 else "WORSE")
    return f"  {label:<28} {before:>10.2f}{unit} -> {after:>10.2f}{unit}   ({delta_str}, {pct})   [{arrow}]"


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    baseline = load_snapshot(sys.argv[1])
    after = load_snapshot(sys.argv[2])

    print("=" * 80)
    print("BENCHMARK DIFF REPORT")
    print("=" * 80)
    print(f"Baseline: {sys.argv[1]}  ({baseline.get('timestamp', 'unknown time')})")
    print(f"After:    {sys.argv[2]}  ({after.get('timestamp', 'unknown time')})")
    print("-" * 80)

    print(fmt_row(
        "Avg latency (ms)",
        baseline.get("avg_latency_ms", 0),
        after.get("avg_latency_ms", 0),
        unit="ms",
        lower_is_better=True,
    ))
    print(fmt_row(
        "Avg prompt tokens",
        baseline.get("avg_prompt_tokens", 0),
        after.get("avg_prompt_tokens", 0),
        lower_is_better=True,
    ))
    print(fmt_row(
        "Avg completion tokens",
        baseline.get("avg_completion_tokens", 0),
        after.get("avg_completion_tokens", 0),
        lower_is_better=True,
    ))
    print(fmt_row(
        "Citation faithfulness %",
        baseline.get("citation_faithfulness_pct", 0),
        after.get("citation_faithfulness_pct", 0),
        unit="%",
        lower_is_better=False,
    ))
    print(fmt_row(
        "Grounded fact accuracy %",
        baseline.get("grounded_fact_accuracy_pct", 0),
        after.get("grounded_fact_accuracy_pct", 0),
        unit="%",
        lower_is_better=False,
    ))

    print("-" * 80)

    # --- The hard gate: adversarial refusal count must not regress ---
    b_refused = baseline.get("adversarial_refusal_count", 0)
    b_total = baseline.get("adversarial_refusal_total", 0)
    a_refused = after.get("adversarial_refusal_count", 0)
    a_total = after.get("adversarial_refusal_total", 0)

    print(f"  {'Adversarial refusals':<28} {b_refused}/{b_total}  ->  {a_refused}/{a_total}")

    gate_passed = True
    if a_total != b_total:
        print(
            f"  WARNING: total question count changed ({b_total} -> {a_total}). "
            f"Before/after sets must be IDENTICAL for a valid comparison — "
            f"this diff may not be meaningful."
        )
    if a_refused < b_refused:
        gate_passed = False
        print("\n  *** GATE FAILED: adversarial refusal count REGRESSED. ***")
        new_failures = after.get("adversarial_failures", [])
        if new_failures:
            print("  Questions that now fail (fabricated instead of refused):")
            for q in new_failures:
                print(f"    - {q}")
        else:
            print(
                "  (No 'adversarial_failures' list provided in the after "
                "snapshot — add one to benchmark_evaluation.py's output so "
                "failures are traceable, not just counted.)"
            )

    print("=" * 80)
    if gate_passed:
        print("GATE: PASS — adversarial refusal count held or improved.")
        print("=" * 80)
        sys.exit(0)
    else:
        print("GATE: FAIL — do not keep this change without fixing the regression.")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
