"""
Factual Accuracy — uses the same LLM endpoint as judge (works with Ollama)
"""
import json
from dataclasses import dataclass
from typing import Optional

from app.models.orm import ModelEndpoint
from app.services.llm_client import call_llm


@dataclass
class FactualResult:
    factual_score: float
    verdict: str
    judge_reasoning: str
    missing_facts: list
    extra_facts: list


FACTUAL_PROMPT = """\
Rate the factual accuracy of the RESPONSE compared to the EXPECTED answer.

QUESTION: {question}
EXPECTED: {expected}
RESPONSE: {actual}

Reply ONLY with this JSON (no markdown):
{{"factual_score": 0.0 to 1.0, "verdict": "correct" or "partial" or "incorrect", "judge_reasoning": "brief explanation", "missing_facts": [], "extra_facts": []}}"""

NO_EXPECTED_PROMPT = """\
Is this AI response factually coherent?

QUESTION: {question}
RESPONSE: {actual}

Reply ONLY with this JSON (no markdown):
{{"factual_score": 0.0 to 1.0, "verdict": "correct" or "partial" or "incorrect", "judge_reasoning": "brief explanation", "missing_facts": [], "extra_facts": []}}"""


async def check_factual_accuracy(
    question: str,
    actual_output: str,
    endpoint: ModelEndpoint,
    expected_output: Optional[str] = None,
) -> FactualResult:
    try:
        if expected_output:
            prompt = FACTUAL_PROMPT.format(
                question=question, expected=expected_output, actual=actual_output)
        else:
            prompt = NO_EXPECTED_PROMPT.format(question=question, actual=actual_output)

        result = await call_llm(
            prompt, endpoint,
            system_override="You are an evaluator. You must reply with ONLY a JSON object. No explanations. No markdown. No code blocks. Start your response with { and end with }."
        )
        raw = result.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        return FactualResult(
            factual_score=float(data.get("factual_score", 0.5)),
            verdict=data.get("verdict", "unclear"),
            judge_reasoning=data.get("judge_reasoning", ""),
            missing_facts=data.get("missing_facts", []),
            extra_facts=data.get("extra_facts", []),
        )
    except Exception as e:
        return FactualResult(
            factual_score=0.0, verdict="incorrect",
            judge_reasoning=f"Eval error: {e}",
            missing_facts=[], extra_facts=[],
        )
