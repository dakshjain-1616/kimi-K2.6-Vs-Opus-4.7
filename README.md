# Kimi K2.6 vs Claude Opus 4.7 — Benchmark

> Built autonomously using **[NEO — Your Autonomous AI Engineering Agent](https://heyneo.com)**.
>
> [![VS Code extension](https://img.shields.io/badge/VS_Code-NEO_extension-007ACC?logo=visualstudiocode&logoColor=white)](https://marketplace.visualstudio.com/items?itemName=NeoResearchInc.heyneo)
> [![Cursor extension](https://img.shields.io/badge/Cursor-NEO_extension-000000?logo=cursor&logoColor=white)](https://marketplace.cursorapi.com/items/?itemName=NeoResearchInc.heyneo)

Head-to-head comparison of `moonshotai/kimi-k2.6` against `anthropic/claude-opus-4.7`, both served via OpenRouter. 10 hard discriminating tasks, anonymized A/B judging, **independent third-party judge** (`openai/gpt-5.4`) — neither contestant judges itself.

## Results (latest run: 2026-04-24)

### Judge-decided wins

![wins](charts/wins.svg)

| Metric | Opus 4.7 | Kimi K2.6 |
|---|---:|---:|
| Judge wins | 8 | 2 |
| Ties | 0 | — |
| Unresolved (judge JSON parse failed) | 0 | — |
| Avg judge score (/10) | 8.1 | 5.2 |
| Avg latency | 32.6 s | 155.0 s |
| Avg total tokens | 3,497 | 5,682 |

Per-task winners (GPT-5.4 judge): **Opus** — `analysis_001`, `analysis_002`, `analysis_003`, `coding_001`, `coding_002`, `coding_003`, `coding_004`, `reasoning_002`. **Kimi** — `reasoning_001`, `reasoning_003`.

### Averages

![summary](charts/summary.svg)

### Per-task latency

![latency](charts/per_task_latency.svg)

### Per-task judge scores

![scores](charts/per_task_scores.svg)

### Per-task token usage

![tokens](charts/per_task_tokens.svg)

### Caveats

1. **Kimi reasoning-budget exhaustion.** Kimi K2.6 is a thinking model. On **7/10 tasks** it hit `finish_reason=length` after consuming the 6,000-token completion budget on internal reasoning and never emitted a final `content` field. In those cases the judge was shown the raw reasoning trace as a fallback (prefixed `[NOTE: only reasoning returned...]`). The OpenRouter `reasoning.max_tokens` hint (2,500 tokens) is not strictly enforced by the Moonshot upstream. Opus hit `finish_reason=length` on 1/10 (`coding_001`) but still emitted complete content. This is a real disadvantage for Kimi under the current budget — raising `max_tokens` would likely improve its scores.
2. **Judge independence.** The judge is `openai/gpt-5.4`, which is neither contestant. A prior run used Opus 4.7 as judge; swapping to an independent judge flipped exactly one verdict (`reasoning_001`: opus → kimi) and narrowed Opus's avg-score lead slightly. The ordering is stable across judges.
3. **Anonymization.** A/B assignment is randomized per task so the judge sees neutral labels.
4. **Small n.** 10 tasks. Treat this as a qualitative sanity check, not a statistically rigorous eval.

Full per-task reasoning, scores, and truncated responses are in [`REPORT.md`](REPORT.md).

## Run it yourself

```bash
pip install -r requirements.txt
# put your key in .env
echo "OPENROUTER_API_KEY=sk-or-v1-..." > .env

python run_comparison.py --dry-run                          # validate setup & resolve slugs
python run_comparison.py                                    # full run (~25 min)
python run_comparison.py --only coding_001                  # single task
python run_comparison.py --skip-judge                       # responses only, no judge
python run_comparison.py --rejudge-only                     # reuse outputs/*.json, re-run judge only
python run_comparison.py --judge anthropic/claude-opus-4.7  # swap the judge (any OpenRouter slug)
python make_charts.py                                       # regenerate charts/*.svg
```

### What the script does

1. Loads `.env`, instantiates an OpenAI SDK client pointed at `https://openrouter.ai/api/v1`.
2. Calls `GET /models` and resolves the exact slugs containing `opus-4.7`/`opus-4-7` under `anthropic/` and `kimi-k2.6`/`kimi-k2` under `moonshotai/`. Aborts if either is missing — no silent fallback.
3. For each task: randomizes A/B assignment, calls both models, records `content`, `reasoning`, `finish_reason`, latency, prompt/completion/total tokens.
4. Writes `outputs/<task_id>.json`.
5. Judge pass (unless `--skip-judge`): calls the judge model (default `openai/gpt-5.4`, override with `--judge`) with an anonymized A/B prompt demanding a single JSON object `{scores, winner, reasoning}`. Writes `outputs/<task_id>.judge.json`.
6. Assembles `REPORT.md`.

## Task set (10 tasks)

| id | category | gist |
|---|---|---|
| `reasoning_001` | logical_reasoning | Zebra / Einstein's riddle variant |
| `reasoning_002` | mathematical_reasoning | St. Petersburg paradox, bounded rationality |
| `reasoning_003` | causal_reasoning | Ice-cream-drownings confounding; study design |
| `coding_001` | algorithm_design | Thread-safe token-bucket rate limiter w/ Redis fallback |
| `coding_002` | system_design | Distributed 64-bit K-sortable ID generator (Snowflake-class) |
| `coding_003` | debugging | uWSGI + SQLAlchemy production memory leak diagnosis |
| `coding_004` | code_optimization | O(N·M·P) Python join → optimized under constraints |
| `analysis_001` | ethical_reasoning | Self-driving-car trolley problem variant |
| `analysis_002` | scientific_reasoning | Critique a flawed Alzheimer's trial |
| `analysis_003` | strategic_reasoning | Repeated duopoly w/ collapse + trembling hand |

Full prompts are in [`tasks.py`](tasks.py).

## CLI

```
--dry-run           Resolve slugs, list tasks, exit without calling models
--only <id>         Run a single task by id
--skip-judge        Skip the judge pass
--judge <slug>      OpenRouter slug for the judge model (default: openai/gpt-5.4)
--rejudge-only      Reuse existing outputs/<id>.json responses, only re-run judge
```

## Files

```
tasks/kimi_vs_opus/
├── .env                 # OPENROUTER_API_KEY
├── .env.example
├── .gitignore
├── README.md            # this file
├── REPORT.md            # auto-generated per-task report
├── requirements.txt     # openai, python-dotenv, httpx
├── tasks.py             # 10 task prompts + metadata
├── run_comparison.py    # runner
├── make_charts.py       # SVG chart generator
├── charts/              # *.svg (wins, summary, per_task_*)
└── outputs/             # <id>.json, <id>.judge.json
```

## Cost

A full run is 30 model calls (10 Opus + 10 Kimi + 10 judge). A rejudge-only pass is 10 judge calls. Empirical cost for a full run is in the **$5–10** range; rejudge-only is well under **$1**.
