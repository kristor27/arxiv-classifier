"""The judges. Same paper, same questions: Jev answers with calibrated probabilities, an LLM generates JSON.

This file is the heart of the demo — read it first.
"""

import json
import time

import anthropic
from google import genai
from google.genai import types
from typesafe_sdk import AsyncTypeSafeClient, Choice

from arxiv_classifier.arxiv import CATEGORIES
from arxiv_classifier.config import CLAUDE_PRICE_IN, CLAUDE_PRICE_OUT, GEMINI_PRICE_IN, GEMINI_PRICE_OUT, JEV_PRICE_IN, settings

PAPER_TYPES = {
    "method": "Proposes a new model, algorithm or technique",
    "benchmark": "Introduces a dataset, benchmark or evaluation protocol",
    "empirical": "Studies or analyses existing methods, with experiments",
    "system": "Describes a system, tool, library or deployed application",
    "theory": "Mainly proofs, bounds or formal analysis",
    "survey": "Reviews or surveys a field",
    "position": "Argues a viewpoint or proposes a research agenda",
}


def paper_state(paper: dict) -> dict:
    """What both judges see: the title and abstract only. Never the authors' own category labels."""
    return {"title": paper["title"], "abstract": paper["abstract"]}


class JevJudge:
    name = "jev"

    def __init__(self):
        self.client = AsyncTypeSafeClient(api_key=settings.typesafe_api_key, model=settings.jev_model)

    async def judge(self, paper: dict) -> dict:
        start = time.perf_counter()
        r = await self.client.system_one(
            state=paper_state(paper),
            questions={  # two typed questions, one call, one forward pass
                "category": Choice(instructions="Which arXiv category is this paper's primary subject?", criteria=CATEGORIES),
                "paper_type": Choice(instructions="What kind of contribution does this paper make?", criteria=PAPER_TYPES),
            },
        )
        ms = (time.perf_counter() - start) * 1000
        c, t = r.answers["category"], r.answers["paper_type"]
        tokens_in = r.usage.input_tokens or 0
        return {
            "engine": "jev", "model": r.model, "label": "Jev",
            "category": c.choice, "confidence": c.confidence, "probabilities": c.probabilities,
            "paper_type": t.choice, "ms": round(ms),
            "tokens_in": tokens_in, "tokens_out": r.usage.output_tokens or 0,
            "cost": tokens_in * JEV_PRICE_IN / 1e6,
        }


LLM_PROMPT = """You sort new arXiv papers. Read the paper below and answer.

category (the paper's primary arXiv category) — one of:
{categories}

paper_type (the kind of contribution) — one of:
{types}

confidence — how sure you are that the category is right, from 0 to 100.

Paper:
{paper}"""


def llm_prompt(paper: dict) -> str:
    """The same definitions Jev gets, written out as a prompt for a generative model."""
    return LLM_PROMPT.format(
        categories="\n".join(f"- {k}: {v}" for k, v in CATEGORIES.items()),
        types="\n".join(f"- {k}: {v}" for k, v in PAPER_TYPES.items()),
        paper=json.dumps(paper_state(paper), ensure_ascii=False, indent=1),
    )


def llm_result(judge, out: dict, ms: float, tokens_in: int, tokens_out: int, cost: float) -> dict:
    return {
        "engine": "llm", "model": judge.model, "label": judge.label,
        # The LLM's confidence is self-reported, so the dashboard can check whether it means anything.
        "category": out["category"], "confidence": out["confidence"] / 100, "probabilities": None,
        "paper_type": out["paper_type"], "ms": round(ms),
        "tokens_in": tokens_in, "tokens_out": tokens_out, "cost": cost,
    }


# Claude's structured outputs need every field required and no extra properties.
CLAUDE_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(CATEGORIES)},
        "paper_type": {"type": "string", "enum": list(PAPER_TYPES)},
        "confidence": {"type": "integer"},
    },
    "required": ["category", "paper_type", "confidence"],
    "additionalProperties": False,
}


class ClaudeJudge:
    model = "claude-sonnet-5-5"
    label = "Claude Sonnet 5.5"

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def judge(self, paper: dict) -> dict:
        start = time.perf_counter()
        # Fair fight: thinking off and low effort (the fastest Sonnet 5.5 can go), plus a strict JSON schema.
        # No refusal fallback on purpose: it would quietly answer with a different model and skew the comparison.
        r = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            thinking={"type": "between_tools"},
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": CLAUDE_SCHEMA}},
            messages=[{"role": "user", "content": llm_prompt(paper)}],
        )
        ms = (time.perf_counter() - start) * 1000
        if r.stop_reason == "refusal":
            raise RuntimeError(f"Claude declined ({r.stop_details.category if r.stop_details else 'no category'})")
        out = json.loads(next(b.text for b in r.content if b.type == "text"))
        out["confidence"] = min(max(out["confidence"], 0), 100)  # the schema can't bound integers, so clamp here
        tokens_in, tokens_out = r.usage.input_tokens, r.usage.output_tokens
        return llm_result(self, out, ms, tokens_in, tokens_out,
                          tokens_in * CLAUDE_PRICE_IN / 1e6 + tokens_out * CLAUDE_PRICE_OUT / 1e6)


GEMINI_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(CATEGORIES)},
        "paper_type": {"type": "string", "enum": list(PAPER_TYPES)},
        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
    },
    "required": ["category", "paper_type", "confidence"],
}


class GeminiJudge:
    model = "gemini-3.8-flash"
    label = "Gemini 3.8 Flash"

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        # Fair fight: thinking at its minimum and a strict JSON schema, so Gemini is as fast as it can be.
        self.config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
            response_mime_type="application/json",
            response_schema=GEMINI_SCHEMA,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    async def judge(self, paper: dict) -> dict:
        start = time.perf_counter()
        r = await self.client.aio.models.generate_content(model=self.model, contents=llm_prompt(paper), config=self.config)
        ms = (time.perf_counter() - start) * 1000
        out = json.loads(r.text)  # can raise: generative models can still return broken JSON
        u = r.usage_metadata
        tokens_in = u.prompt_token_count or 0
        tokens_out = (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)  # thinking is billed as output
        return llm_result(self, out, ms, tokens_in, tokens_out,
                          tokens_in * GEMINI_PRICE_IN / 1e6 + tokens_out * GEMINI_PRICE_OUT / 1e6)


def llm_judge() -> ClaudeJudge | GeminiJudge | None:
    """The comparison model, picked by LLM_PROVIDER. None when its key is missing."""
    if settings.llm_provider == "gemini":
        return GeminiJudge() if settings.gemini_api_key else None
    return ClaudeJudge() if settings.anthropic_api_key else None
