# 1. Jev: decisions, not text

## The call

One HTTP request does everything: `POST https://api.typesafe.ai/v1/systemone`, with
`Authorization: Bearer $TYPESAFE_API_KEY`. The Python SDK (`typesafe-sdk`) wraps it:

```python
from typesafe_sdk import AsyncTypeSafeClient, Choice, Score

client = AsyncTypeSafeClient(model="jev-1.13.0")    # pin the version: thresholds depend on it
r = await client.system_one(
    state={"article": "Paris", "added_text": "lol paris sucks", ...},   # text or JSON
    questions={
        "verdict":  Choice(instructions="...", criteria={"disruptive": "...", "good_faith_error": "...", "improvement": "..."}),
        "kind":     Choice(instructions="...", criteria={...}),
        "severity": Score(instructions="...", criteria=["no harm", "minor", "noticeable", "severe"]),
    },
)
r.answers["verdict"].choice          # "disruptive"
r.answers["verdict"].probabilities   # {"disruptive": 1.0, "good_faith_error": 0.0, "improvement": 0.0}
r.answers["severity"].score          # 2.66: a probability-weighted position on the rubric
r.usage.input_tokens                 # you pay for input only
```

There are three question types:

- **Choice** picks one label from a set.
- **Score** places the answer on an ordered rubric of 2–10 levels.
- **Noul** is yes/no, returned as a probability.

All three questions in a single request are answered in the same forward pass.

## Designing good questions

- **The criteria are the prompt.** Every label carries a one-line definition (see `VERDICTS` in
  `judges.py`). Jev answers exactly what you wrote, so vague criteria give vague probabilities.
- **Jev can't do arithmetic or dates.** Don't give it `old_length=6033, new_length=6052`. Compute
  the difference in code and pass words: `"size_change": "small addition (+19 bytes)"` (see
  `edit_state()`).
- **Use the probabilities.** A 0.55 / 0.45 split is Jev telling you it's unsure. The dashboard
  shows the full distribution under each edit instead of just the top label.
- **Thresholds don't carry over between question types.** The same question can return 0.22 as a
  Noul and 0.01 as a Choice, so calibrate each one on its own.

## A fair comparison

`ClaudeJudge` (or `GeminiJudge`) receives the same `edit_state()`, the same definitions and a strict JSON schema,
with thinking off (Claude: `between_tools` at low effort; Gemini: minimal) so it runs as fast as it can. The worker starts both calls with
`asyncio.gather` on the same input, so they're judged at the same moment. Costs come from each
response's real token counts (see the prices in `config.py`).

## Is Jev right?

Agreement with an LLM isn't ground truth. Wikipedia provides one: when editors undo an edit,
MediaWiki tags it `mw-reverted`. `reverts.py` checks every edit 30 minutes after it was judged.
The "Confirmed by humans" tile shows the share of Jev's *disruptive* flags that people later
reverted.
