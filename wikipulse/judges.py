"""The judges. Same edit, same questions: Jev answers with calibrated probabilities, an LLM generates JSON.

This file is the heart of the demo — read it first.
"""

import json
import time

import anthropic
from google import genai
from google.genai import types
from typesafe_sdk import AsyncTypeSafeClient, Choice, Score

from wikipulse.config import CLAUDE_PRICE_IN, CLAUDE_PRICE_OUT, GEMINI_PRICE_IN, GEMINI_PRICE_OUT, JEV_PRICE_IN, settings

VERDICTS = {
    "disruptive": "Deliberately damages the article: insults, nonsense, jokes, false claims, "
                  "blanking without reason, spam or promotion",
    "good_faith_error": "An honest attempt to help that makes the article worse: unsourced claims, "
                        "broken formatting, wrong facts, original research",
    "improvement": "Makes the article better or is neutral maintenance: copyedits, new sourced content, "
                   "fixes, formatting, references",
}
KINDS = {
    "content": "Adds, removes or rewrites encyclopedic content",
    "copyedit": "Spelling, grammar, wording or style",
    "references": "Adds or fixes citations, links or templates",
    "removal": "Mostly deletes existing text",
    "nonsense": "Inserts text unrelated to the topic",
}
TOPICS = {
    "people": "Biographies of living or dead people",
    "sports": "Sports, athletes, teams, competitions",
    "entertainment": "Film, television, music, video games, celebrities",
    "politics": "Politics, government, elections, law, military",
    "history": "History, historical events, wars, royalty",
    "geography": "Places, countries, cities, buildings, transport",
    "science": "Science, technology, mathematics, medicine, nature",
    "business": "Companies, economy, products, brands",
    "culture": "Arts, literature, religion, philosophy, education, food",
}
SEVERITY = ["no harm", "minor issue", "noticeable damage", "severe damage that misleads readers"]


def edit_state(edit: dict) -> dict:
    """What both judges see. Jev can't do arithmetic, so we turn numbers into words here."""
    delta = edit["byte_delta"]
    size = "tiny" if abs(delta) < 50 else "small" if abs(delta) < 500 else "large"
    return {
        "article": edit["title"],
        "editor": "anonymous (IP address or temporary account)" if edit["anonymous"] else "registered account",
        "edit_summary": edit["comment"] or "(none)",
        "size_change": f"{size} {'addition' if delta >= 0 else 'removal'} ({delta:+d} bytes)",
        "removed_text": edit["removed"] or "(nothing)",
        "added_text": edit["added"] or "(nothing)",
        "changed_lines_after_edit": edit["context"] or "(none)",
    }


class JevJudge:
    name = "jev"

    def __init__(self):
        self.client = AsyncTypeSafeClient(api_key=settings.typesafe_api_key, model=settings.jev_model)

    async def judge(self, edit: dict) -> dict:
        start = time.perf_counter()
        r = await self.client.system_one(
            state=edit_state(edit),
            questions={  # three typed questions, one call, one forward pass
                "verdict": Choice(instructions="What is the intent and effect of this Wikipedia edit?", criteria=VERDICTS),
                "kind": Choice(instructions="What kind of change is this?", criteria=KINDS),
                "topic": Choice(instructions="What is the article about?", criteria=TOPICS),
                "severity": Score(instructions="How much does this edit harm what readers will see?", criteria=SEVERITY),
            },
        )
        ms = (time.perf_counter() - start) * 1000
        v, k, t, s = (r.answers[q] for q in ("verdict", "kind", "topic", "severity"))
        tokens_in = r.usage.input_tokens or 0
        return {
            "engine": self.name, "model": r.model, "verdict": v.choice, "confidence": v.confidence,
            "probabilities": v.probabilities, "kind": k.choice, "topic": t.choice, "severity": s.score, "ms": round(ms),
            "tokens_in": tokens_in, "tokens_out": r.usage.output_tokens or 0,
            "cost": tokens_in * JEV_PRICE_IN / 1e6,
        }


LLM_PROMPT = """You review Wikipedia edits. Classify the edit below.

verdict — one of:
{verdicts}

kind — one of:
{kinds}

topic (what the article is about) — one of:
{topics}

severity — 0 to 3: {severity}

Edit:
{edit}"""


def llm_prompt(edit: dict) -> str:
    """The same definitions Jev gets, written out as a prompt for a generative model."""
    return LLM_PROMPT.format(
        verdicts="\n".join(f"- {k}: {v}" for k, v in VERDICTS.items()),
        kinds="\n".join(f"- {k}: {v}" for k, v in KINDS.items()),
        topics="\n".join(f"- {k}: {v}" for k, v in TOPICS.items()),
        severity=", ".join(f"{i} = {s}" for i, s in enumerate(SEVERITY)),
        edit=json.dumps(edit_state(edit), ensure_ascii=False, indent=1),
    )


def llm_result(judge, out: dict, ms: float, tokens_in: int, tokens_out: int, cost: float) -> dict:
    return {
        "engine": "llm", "model": judge.model, "label": judge.label, "verdict": out["verdict"], "confidence": None,
        "probabilities": None, "kind": out["kind"], "topic": out["topic"], "severity": float(out["severity"]),
        "ms": round(ms), "tokens_in": tokens_in, "tokens_out": tokens_out, "cost": cost,
    }


# Claude's structured outputs need every field required and no extra properties.
CLAUDE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "kind": {"type": "string", "enum": list(KINDS)},
        "topic": {"type": "string", "enum": list(TOPICS)},
        "severity": {"type": "integer", "enum": [0, 1, 2, 3]},
    },
    "required": ["verdict", "kind", "topic", "severity"],
    "additionalProperties": False,
}


class ClaudeJudge:
    model = "claude-sonnet-5-5"
    label = "Claude Sonnet 5.5"

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def judge(self, edit: dict) -> dict:
        start = time.perf_counter()
        # Fair fight: thinking off and low effort (the fastest Sonnet 5.5 can go), plus a strict JSON schema.
        # No refusal fallback on purpose: it would quietly answer with a different model and skew the comparison.
        r = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            thinking={"type": "between_tools"},
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": CLAUDE_SCHEMA}},
            messages=[{"role": "user", "content": llm_prompt(edit)}],
        )
        ms = (time.perf_counter() - start) * 1000
        if r.stop_reason == "refusal":
            raise RuntimeError(f"Claude declined ({r.stop_details.category if r.stop_details else 'no category'})")
        out = json.loads(next(b.text for b in r.content if b.type == "text"))
        tokens_in, tokens_out = r.usage.input_tokens, r.usage.output_tokens
        return llm_result(self, out, ms, tokens_in, tokens_out,
                          tokens_in * CLAUDE_PRICE_IN / 1e6 + tokens_out * CLAUDE_PRICE_OUT / 1e6)


GEMINI_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "kind": {"type": "string", "enum": list(KINDS)},
        "topic": {"type": "string", "enum": list(TOPICS)},
        "severity": {"type": "integer", "minimum": 0, "maximum": 3},
    },
    "required": ["verdict", "kind", "topic", "severity"],
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

    async def judge(self, edit: dict) -> dict:
        start = time.perf_counter()
        r = await self.client.aio.models.generate_content(model=self.model, contents=llm_prompt(edit), config=self.config)
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
