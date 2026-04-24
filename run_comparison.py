#!/usr/bin/env python3
"""Kimi K2.6 vs Claude Opus 4.7 benchmark via OpenRouter."""

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from tasks import TASKS  # noqa: E402

load_dotenv(ROOT / ".env")

OUT_DIR = ROOT / "outputs"
REPORT_PATH = ROOT / "REPORT.md"
BASE_URL = "https://openrouter.ai/api/v1"

KIMI_HINTS = ["kimi-k2.6", "kimi-k2-thinking", "kimi-k2"]
OPUS_HINTS = ["opus-4.7", "opus-4-7"]


def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def get_key():
    k = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not k or "REPLACE_ME" in k:
        die("OPENROUTER_API_KEY not set (or still a placeholder). Put a real key in tasks/kimi_vs_opus/.env")
    return k


def resolve_slugs(client):
    import httpx
    r = httpx.get(f"{BASE_URL}/models", headers={"Authorization": f"Bearer {client.api_key}"}, timeout=30)
    r.raise_for_status()
    ids = [m["id"] for m in r.json()["data"]]

    def pick(namespace, hints):
        ns = [i for i in ids if i.startswith(namespace + "/")]
        for hint in hints:
            for i in ns:
                if hint in i:
                    return i
        return None

    opus = pick("anthropic", OPUS_HINTS)
    kimi = pick("moonshotai", KIMI_HINTS)

    if not opus or not kimi:
        print("Could not resolve both slugs. Candidates:", file=sys.stderr)
        print("  anthropic/*:", [i for i in ids if i.startswith("anthropic/")][:10], file=sys.stderr)
        print("  moonshotai/*:", [i for i in ids if i.startswith("moonshotai/")][:10], file=sys.stderr)
        die("Slug resolution failed")
    return opus, kimi


def make_client():
    from openai import OpenAI
    key = get_key()
    client = OpenAI(
        base_url=BASE_URL,
        api_key=key,
        default_headers={
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://localhost"),
            "X-Title": os.getenv("OPENROUTER_SITE_TITLE", "Benchmakr"),
        },
    )
    client.api_key = key  # stash for httpx calls
    return client


def call_model(client, slug, prompt, max_tokens=6000, temperature=0.3, reasoning_max=2500):
    t0 = time.time()
    try:
        kwargs = dict(
            model=slug,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # Cap reasoning budget for thinking models (kimi-k2.6) so they actually emit content
        kwargs["extra_body"] = {"reasoning": {"max_tokens": reasoning_max}}
        resp = client.chat.completions.create(**kwargs)
        latency = (time.time() - t0) * 1000
        usage = resp.usage
        msg = resp.choices[0].message
        content = msg.content or ""
        reasoning = getattr(msg, "reasoning", None) or ""
        # If content is empty (reasoning model hit limit before emitting), surface reasoning
        text = content if content.strip() else (f"[NOTE: only reasoning returned, no final content]\n\n{reasoning}" if reasoning else "")
        return {
            "slug": slug,
            "text": text,
            "content": content,
            "reasoning": reasoning,
            "finish_reason": resp.choices[0].finish_reason,
            "latency_ms": round(latency, 1),
            "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
            "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
            "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
            "error": None,
        }
    except Exception as e:
        return {
            "slug": slug,
            "text": "",
            "content": "",
            "reasoning": "",
            "finish_reason": None,
            "latency_ms": round((time.time() - t0) * 1000, 1),
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "error": f"{type(e).__name__}: {e}",
        }


JUDGE_PROMPT = """You are a strict, impartial evaluator comparing two anonymized AI responses.

TASK CATEGORY: {category}
TASK PROMPT:
---
{prompt}
---

RESPONSE A:
---
{a}
---

RESPONSE B:
---
{b}
---

Score each response 1-10 on correctness, depth, and clarity. Then pick a winner.
Respond with ONLY a single JSON object, no prose, no code fences:

{{"scores": {{"A": {{"correctness": 0, "depth": 0, "clarity": 0}}, "B": {{"correctness": 0, "depth": 0, "clarity": 0}}}}, "winner": "A" | "B" | "tie", "reasoning": "one short paragraph"}}
"""


def judge(client, slug, task, resp_a_text, resp_b_text):
    prompt = JUDGE_PROMPT.format(
        category=task.get("category", ""),
        prompt=task["prompt"],
        a=resp_a_text or "[no response]",
        b=resp_b_text or "[no response]",
    )
    result = call_model(client, slug, prompt, max_tokens=3000, temperature=0.0, reasoning_max=1500)
    parsed = None
    raw = result["text"]
    # Extract JSON
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(0))
        except json.JSONDecodeError:
            parsed = None
    return {
        "raw": raw,
        "parsed": parsed,
        "error": result["error"],
        "latency_ms": result["latency_ms"],
    }


def avg_score(scores_dict):
    if not scores_dict:
        return 0.0
    vals = [v for v in scores_dict.values() if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


DEFAULT_JUDGE = "openai/gpt-5.4"


def run(only_id=None, skip_judge=False, dry_run=False, judge_slug=DEFAULT_JUDGE, rejudge_only=False):
    client = make_client()
    opus_slug, kimi_slug = resolve_slugs(client)

    print(f"Resolved slugs:")
    print(f"  opus  = {opus_slug}")
    print(f"  kimi  = {kimi_slug}")
    print(f"  judge = {judge_slug}")

    tasks = [t for t in TASKS if (only_id is None or t["id"] == only_id)]
    if only_id and not tasks:
        die(f"No task with id={only_id}")

    if dry_run:
        print(f"\n[DRY RUN] Would run {len(tasks)} task(s):")
        for t in tasks:
            print(f"  - {t['id']}: {t.get('name', t['category'])}")
        return

    OUT_DIR.mkdir(exist_ok=True)
    per_task = []

    for i, task in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] {task['id']} — {task.get('name', task['category'])}")

        if rejudge_only:
            rec_path = OUT_DIR / f"{task['id']}.json"
            if not rec_path.exists():
                die(f"--rejudge-only: missing {rec_path}. Run without this flag first.")
            record = json.loads(rec_path.read_text())
            a_model = record["assignment"]["A"]
            b_model = record["assignment"]["B"]
            resp_a = record["responses"]["A"]
            resp_b = record["responses"]["B"]
            print(f"  reusing responses (A={a_model}, B={b_model})")
        else:
            flip = random.random() < 0.5
            if flip:
                a_model, a_slug, b_model, b_slug = "kimi", kimi_slug, "opus", opus_slug
            else:
                a_model, a_slug, b_model, b_slug = "opus", opus_slug, "kimi", kimi_slug

            print(f"  calling {a_slug} (as A)...")
            resp_a = call_model(client, a_slug, task["prompt"])
            print(f"    {resp_a['latency_ms']}ms, tokens={resp_a['total_tokens']}, err={resp_a['error']}")

            print(f"  calling {b_slug} (as B)...")
            resp_b = call_model(client, b_slug, task["prompt"])
            print(f"    {resp_b['latency_ms']}ms, tokens={resp_b['total_tokens']}, err={resp_b['error']}")

            record = {
                "task_id": task["id"],
                "category": task.get("category"),
                "name": task.get("name"),
                "prompt": task["prompt"],
                "assignment": {"A": a_model, "B": b_model},
                "responses": {"A": resp_a, "B": resp_b},
                "by_model": {a_model: resp_a, b_model: resp_b},
                "timestamp": utcnow_iso(),
            }
            (OUT_DIR / f"{task['id']}.json").write_text(json.dumps(record, indent=2))

        judge_rec = None
        if not skip_judge:
            print(f"  judging with {judge_slug}...")
            j = judge(client, judge_slug, task, resp_a["text"], resp_b["text"])
            judge_rec = {
                "task_id": task["id"],
                "judge_slug": judge_slug,
                "assignment": {"A": a_model, "B": b_model},
                "result": j,
                "timestamp": utcnow_iso(),
            }
            (OUT_DIR / f"{task['id']}.judge.json").write_text(json.dumps(judge_rec, indent=2))
            if j["parsed"]:
                w = j["parsed"].get("winner")
                real_winner = {"A": a_model, "B": b_model, "tie": "tie"}.get(w, "unknown")
                print(f"    winner: {w} -> {real_winner}")
            else:
                print(f"    judge JSON parse failed (err={j.get('error')})")

        per_task.append({"task": task, "record": record, "judge": judge_rec})

    write_report(per_task, opus_slug, kimi_slug, judge_slug, skip_judge)
    print(f"\nReport written to {REPORT_PATH}")


def write_report(per_task, opus_slug, kimi_slug, judge_slug, skip_judge):
    lines = []
    lines.append(f"# Kimi K2.6 vs Claude Opus 4.7 — Benchmark Report")
    lines.append("")
    lines.append(f"- **Date (UTC):** {utcnow_iso()}")
    lines.append(f"- **Opus slug:** `{opus_slug}`")
    lines.append(f"- **Kimi slug:** `{kimi_slug}`")
    if judge_slug in (opus_slug, kimi_slug):
        lines.append(f"- **Judge:** `{judge_slug}` — **bias caveat:** the judge is also one of the contestants; it may be systematically favored.")
    else:
        lines.append(f"- **Judge:** `{judge_slug}` (independent third-party; neither contestant).")
    lines.append(f"- **Tasks:** {len(per_task)}")
    lines.append("")
    empty_kimi = [e['task']['id'] for e in per_task if not e['record']['by_model']['kimi'].get('content','').strip()]
    empty_opus = [e['task']['id'] for e in per_task if not e['record']['by_model']['opus'].get('content','').strip()]
    if empty_kimi or empty_opus:
        lines.append("### Caveat: thinking-model token exhaustion")
        lines.append("")
        lines.append(f"Kimi K2.6 is a reasoning model. On {len(empty_kimi)}/{len(per_task)} tasks it hit `finish_reason=length` with its reasoning trace but produced no final `content`. For those tasks the judge was shown the raw reasoning trace as a fallback (marked `[NOTE: only reasoning returned...]`). Budget: 6000 max_tokens, with a 2500-token `reasoning.max_tokens` hint (which Moonshot does not strictly enforce).")
        lines.append("")
        if empty_kimi:
            lines.append(f"- Kimi empty-content tasks: `{', '.join(empty_kimi)}`")
        if empty_opus:
            lines.append(f"- Opus empty-content tasks: `{', '.join(empty_opus)}`")
        lines.append("")

    # Aggregates
    wins = {"opus": 0, "kimi": 0, "tie": 0, "unknown": 0}
    latencies = {"opus": [], "kimi": []}
    tokens = {"opus": [], "kimi": []}
    scores = {"opus": [], "kimi": []}

    for entry in per_task:
        rec = entry["record"]
        for m in ("opus", "kimi"):
            r = rec["by_model"][m]
            if r["latency_ms"] is not None:
                latencies[m].append(r["latency_ms"])
            if r["total_tokens"] is not None:
                tokens[m].append(r["total_tokens"])
        j = entry.get("judge")
        if j and j["result"]["parsed"]:
            p = j["result"]["parsed"]
            w_raw = p.get("winner")
            asn = j["assignment"]
            real = {"A": asn["A"], "B": asn["B"], "tie": "tie"}.get(w_raw, "unknown")
            wins[real if real in wins else "unknown"] += 1
            s = p.get("scores", {})
            for label, model in asn.items():
                if model in ("opus", "kimi"):
                    scores[model].append(avg_score(s.get(label, {})))

    def mean(xs):
        return round(sum(xs) / len(xs), 1) if xs else None

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Opus 4.7 | Kimi K2.6 |")
    lines.append("|---|---|---|")
    if not skip_judge:
        lines.append(f"| Judge wins | {wins['opus']} | {wins['kimi']} |")
        lines.append(f"| Ties | {wins['tie']} | — |")
        lines.append(f"| Avg judge score (of 10) | {mean(scores['opus'])} | {mean(scores['kimi'])} |")
    lines.append(f"| Avg latency (ms) | {mean(latencies['opus'])} | {mean(latencies['kimi'])} |")
    lines.append(f"| Avg total tokens | {mean(tokens['opus'])} | {mean(tokens['kimi'])} |")
    lines.append("")

    lines.append("## Per-task results")
    lines.append("")
    for entry in per_task:
        task = entry["task"]
        rec = entry["record"]
        j = entry.get("judge")
        lines.append(f"### {task['id']} — {task.get('name', task['category'])}")
        lines.append(f"*Category:* `{task.get('category')}`")
        lines.append("")
        lines.append("| | Opus | Kimi |")
        lines.append("|---|---|---|")
        lines.append(f"| latency (ms) | {rec['by_model']['opus']['latency_ms']} | {rec['by_model']['kimi']['latency_ms']} |")
        lines.append(f"| total tokens | {rec['by_model']['opus']['total_tokens']} | {rec['by_model']['kimi']['total_tokens']} |")
        lines.append(f"| error | {rec['by_model']['opus']['error']} | {rec['by_model']['kimi']['error']} |")
        lines.append("")
        if j and j["result"]["parsed"]:
            p = j["result"]["parsed"]
            asn = j["assignment"]
            w_raw = p.get("winner")
            real = {"A": asn["A"], "B": asn["B"], "tie": "tie"}.get(w_raw, "unknown")
            lines.append(f"**Judge winner:** `{real}` (raw: `{w_raw}`; A={asn['A']}, B={asn['B']})")
            lines.append("")
            lines.append(f"**Reasoning:** {p.get('reasoning', '')}")
            lines.append("")
        elif j:
            lines.append(f"**Judge:** parse failed. Raw (truncated):")
            lines.append("")
            lines.append("```")
            lines.append((j["result"]["raw"] or "")[:500])
            lines.append("```")
            lines.append("")
        lines.append(f"<details><summary>Opus response (truncated)</summary>\n\n```\n{rec['by_model']['opus']['text'][:2000]}\n```\n\n</details>")
        lines.append("")
        lines.append(f"<details><summary>Kimi response (truncated)</summary>\n\n```\n{rec['by_model']['kimi']['text'][:2000]}\n```\n\n</details>")
        lines.append("")
        lines.append("---")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None, help="Run only the task with this id")
    ap.add_argument("--skip-judge", action="store_true")
    ap.add_argument("--judge", default=DEFAULT_JUDGE, help=f"OpenRouter slug for the judge model (default: {DEFAULT_JUDGE})")
    ap.add_argument("--rejudge-only", action="store_true", help="Reuse existing outputs/<id>.json responses and only re-run the judge")
    args = ap.parse_args()
    run(only_id=args.only, skip_judge=args.skip_judge, dry_run=args.dry_run,
        judge_slug=args.judge, rejudge_only=args.rejudge_only)


if __name__ == "__main__":
    main()
