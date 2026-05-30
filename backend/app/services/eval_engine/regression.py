"""
Regression Testing Engine
──────────────────────────
Compares the current eval run's outputs against a pinned baseline.
Flags regressions (outputs got worse) and improvements (got better).
"""
import json
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI
from app.config import settings
from app.services.embeddings import cosine_similarity

judge_client = AsyncOpenAI(api_key=settings.openai_api_key)
JUDGE_MODEL = "gpt-4o-mini"

# Threshold: if semantic similarity drops below this, outputs diverged significantly
DRIFT_THRESHOLD = 0.80


@dataclass
class RegressionResult:
    regression_detected: bool
    improvement_detected: bool
    semantic_drift: float          # 0.0 = identical, 1.0 = completely different
    verdict: str                   # better | same | worse
    reasoning: str


COMPARISON_JUDGE_PROMPT = """\
You are evaluating two AI responses to the same question.

QUESTION: {question}
EXPECTED (ground truth): {expected}

BASELINE RESPONSE (previous version):
{baseline}

CURRENT RESPONSE (new version):
{current}

Compare them. Is the CURRENT response better, the same, or worse than BASELINE?
Focus on: factual accuracy, completeness, and relevance.

Respond ONLY with valid JSON:
{{
  "verdict": "better" or "same" or "worse",
  "reasoning": "one sentence explanation"
}}
"""


async def regression_check(
    question: str,
    expected_output: Optional[str],
    baseline_output: str,
    current_output: str,
    baseline_embedding: Optional[list],
    current_embedding: Optional[list],
) -> RegressionResult:
    """Compare current output to baseline output for a single row."""

    # ── Semantic drift via embeddings ─────────────────────────────────────
    semantic_drift = 0.0
    if baseline_embedding and current_embedding:
        sim = cosine_similarity(baseline_embedding, current_embedding)
        semantic_drift = round(1.0 - sim, 4)

    # ── LLM judge comparison ──────────────────────────────────────────────
    verdict = "same"
    reasoning = "Outputs are semantically similar."

    if semantic_drift > (1.0 - DRIFT_THRESHOLD) or expected_output:
        # Only call judge if outputs diverged OR we have ground truth
        judge_result = await _compare_with_judge(
            question=question,
            expected=expected_output or "No ground truth available.",
            baseline=baseline_output,
            current=current_output,
        )
        verdict = judge_result.get("verdict", "same")
        reasoning = judge_result.get("reasoning", "")

    return RegressionResult(
        regression_detected=(verdict == "worse"),
        improvement_detected=(verdict == "better"),
        semantic_drift=semantic_drift,
        verdict=verdict,
        reasoning=reasoning,
    )


async def _compare_with_judge(question: str, expected: str, baseline: str, current: str) -> dict:
    try:
        completion = await judge_client.chat.completions.create(
            model=JUDGE_MODEL,
            temperature=0.0,
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": COMPARISON_JUDGE_PROMPT.format(
                    question=question,
                    expected=expected,
                    baseline=baseline,
                    current=current,
                ),
            }],
        )
        return json.loads(completion.choices[0].message.content or "{}")
    except Exception as e:
        return {"verdict": "same", "reasoning": f"Judge error: {e}"}
