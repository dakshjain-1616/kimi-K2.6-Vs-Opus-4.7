#!/usr/bin/env python3
"""Generate SVG charts from benchmark outputs/."""

import json
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
CHARTS = ROOT / "charts"
CHARTS.mkdir(exist_ok=True)

OPUS = "#C96442"  # Anthropic orange
KIMI = "#5B8DEF"  # Moonshot blue
BG = "#FAFAFA"
FG = "#222"
GRID = "#E5E5E5"


def load():
    tasks = []
    for rec_path in sorted(OUT.glob("*.json")):
        if rec_path.name.endswith(".judge.json"):
            continue
        rec = json.load(open(rec_path))
        jud_path = OUT / f"{rec['task_id']}.judge.json"
        jud = json.load(open(jud_path)) if jud_path.exists() else None
        tasks.append({"rec": rec, "jud": jud})
    return tasks


def avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else 0


def judge_scores(entry):
    """Return (opus_score, kimi_score, winner) or (None, None, None)."""
    if not entry["jud"] or not entry["jud"]["result"]["parsed"]:
        return None, None, None
    p = entry["jud"]["result"]["parsed"]
    asn = entry["jud"]["assignment"]
    scores = p.get("scores", {})

    def mean(d):
        vals = [v for v in d.values() if isinstance(v, (int, float))]
        return sum(vals) / len(vals) if vals else None

    a_avg = mean(scores.get("A", {}))
    b_avg = mean(scores.get("B", {}))
    mapping = {asn["A"]: a_avg, asn["B"]: b_avg}
    w = p.get("winner")
    winner_model = {"A": asn["A"], "B": asn["B"], "tie": "tie"}.get(w, "unknown")
    return mapping.get("opus"), mapping.get("kimi"), winner_model


def svg_header(w, h, title):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">
<rect width="{w}" height="{h}" fill="{BG}"/>
<text x="{w/2}" y="28" text-anchor="middle" font-size="18" font-weight="600" fill="{FG}">{title}</text>
'''


def svg_footer():
    return "</svg>\n"


def bar_chart_simple(title, labels, values_opus, values_kimi, ylabel, fname, fmt="{:.0f}"):
    """Grouped bar chart: one group per label, two bars (opus, kimi)."""
    W, H = 720, 380
    pad_l, pad_r, pad_t, pad_b = 70, 30, 55, 80
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    n = len(labels)
    group_w = plot_w / n
    bar_w = group_w * 0.35
    max_v = max(max(values_opus + values_kimi), 1)
    # Round up max to nice number
    import math
    magnitude = 10 ** int(math.log10(max_v))
    nice_max = math.ceil(max_v / magnitude) * magnitude

    svg = [svg_header(W, H, title)]
    # Y axis gridlines
    for i in range(5):
        y = pad_t + plot_h - (plot_h * i / 4)
        v = nice_max * i / 4
        svg.append(f'<line x1="{pad_l}" y1="{y}" x2="{W-pad_r}" y2="{y}" stroke="{GRID}" stroke-width="1"/>')
        svg.append(f'<text x="{pad_l-8}" y="{y+4}" text-anchor="end" font-size="11" fill="{FG}">{fmt.format(v)}</text>')
    # Bars
    for i, label in enumerate(labels):
        gx = pad_l + group_w * i + group_w / 2
        vo = values_opus[i]
        vk = values_kimi[i]
        ho = plot_h * (vo / nice_max) if nice_max else 0
        hk = plot_h * (vk / nice_max) if nice_max else 0
        xo = gx - bar_w - 2
        xk = gx + 2
        yo = pad_t + plot_h - ho
        yk = pad_t + plot_h - hk
        svg.append(f'<rect x="{xo}" y="{yo}" width="{bar_w}" height="{ho}" fill="{OPUS}"/>')
        svg.append(f'<rect x="{xk}" y="{yk}" width="{bar_w}" height="{hk}" fill="{KIMI}"/>')
        svg.append(f'<text x="{xo+bar_w/2}" y="{yo-4}" text-anchor="middle" font-size="10" fill="{FG}">{fmt.format(vo)}</text>')
        svg.append(f'<text x="{xk+bar_w/2}" y="{yk-4}" text-anchor="middle" font-size="10" fill="{FG}">{fmt.format(vk)}</text>')
        # Rotated label
        svg.append(f'<text x="{gx}" y="{pad_t+plot_h+15}" text-anchor="end" font-size="10" fill="{FG}" transform="rotate(-35 {gx} {pad_t+plot_h+15})">{label}</text>')
    # Axes
    svg.append(f'<line x1="{pad_l}" y1="{pad_t+plot_h}" x2="{W-pad_r}" y2="{pad_t+plot_h}" stroke="{FG}" stroke-width="1.5"/>')
    svg.append(f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+plot_h}" stroke="{FG}" stroke-width="1.5"/>')
    # Y label
    svg.append(f'<text x="15" y="{pad_t+plot_h/2}" text-anchor="middle" font-size="12" fill="{FG}" transform="rotate(-90 15 {pad_t+plot_h/2})">{ylabel}</text>')
    # Legend
    lx, ly = W - pad_r - 180, pad_t + 8
    svg.append(f'<rect x="{lx}" y="{ly}" width="14" height="14" fill="{OPUS}"/><text x="{lx+20}" y="{ly+11}" font-size="12" fill="{FG}">Opus 4.7</text>')
    svg.append(f'<rect x="{lx+90}" y="{ly}" width="14" height="14" fill="{KIMI}"/><text x="{lx+110}" y="{ly+11}" font-size="12" fill="{FG}">Kimi K2.6</text>')
    svg.append(svg_footer())
    (CHARTS / fname).write_text("\n".join(svg))


def summary_bar(title, pairs, fname, fmt="{:.1f}"):
    """pairs: [(metric_label, opus_val, kimi_val)]"""
    W, H = 640, 320
    pad_l, pad_r, pad_t, pad_b = 120, 30, 55, 50
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    n = len(pairs)
    row_h = plot_h / n

    # Normalize each row (side-by-side bars, separate max per row)
    svg = [svg_header(W, H, title)]
    for i, (label, vo, vk) in enumerate(pairs):
        cy = pad_t + row_h * i + row_h / 2
        max_v = max(vo, vk, 1)
        scale = plot_w / max_v * 0.88
        ho = 18
        # Opus bar (top half)
        yo = cy - ho - 2
        yk = cy + 2
        svg.append(f'<rect x="{pad_l}" y="{yo}" width="{vo*scale}" height="{ho}" fill="{OPUS}"/>')
        svg.append(f'<rect x="{pad_l}" y="{yk}" width="{vk*scale}" height="{ho}" fill="{KIMI}"/>')
        svg.append(f'<text x="{pad_l-8}" y="{cy+4}" text-anchor="end" font-size="12" fill="{FG}" font-weight="500">{label}</text>')
        svg.append(f'<text x="{pad_l+vo*scale+6}" y="{yo+13}" font-size="11" fill="{FG}">{fmt.format(vo)}</text>')
        svg.append(f'<text x="{pad_l+vk*scale+6}" y="{yk+13}" font-size="11" fill="{FG}">{fmt.format(vk)}</text>')

    # Legend
    lx, ly = pad_l, H - 25
    svg.append(f'<rect x="{lx}" y="{ly}" width="14" height="14" fill="{OPUS}"/><text x="{lx+20}" y="{ly+11}" font-size="12" fill="{FG}">Opus 4.7</text>')
    svg.append(f'<rect x="{lx+100}" y="{ly}" width="14" height="14" fill="{KIMI}"/><text x="{lx+120}" y="{ly+11}" font-size="12" fill="{FG}">Kimi K2.6</text>')
    svg.append(svg_footer())
    (CHARTS / fname).write_text("\n".join(svg))


def wins_chart(opus_wins, kimi_wins, ties, unknown, fname):
    W, H = 520, 260
    total = opus_wins + kimi_wins + ties + unknown
    svg = [svg_header(W, H, f"Judge-decided wins (n={total})")]
    items = [("Opus 4.7 wins", opus_wins, OPUS),
             ("Kimi K2.6 wins", kimi_wins, KIMI),
             ("Ties", ties, "#888"),
             ("Unresolved", unknown, "#BBB")]
    pad_l, pad_t = 160, 60
    plot_w = W - pad_l - 60
    max_v = max(total, 1)
    for i, (lbl, v, color) in enumerate(items):
        y = pad_t + i * 38
        w = plot_w * (v / max_v)
        svg.append(f'<rect x="{pad_l}" y="{y}" width="{w}" height="24" fill="{color}"/>')
        svg.append(f'<text x="{pad_l-8}" y="{y+17}" text-anchor="end" font-size="13" fill="{FG}" font-weight="500">{lbl}</text>')
        svg.append(f'<text x="{pad_l+w+6}" y="{y+17}" font-size="13" fill="{FG}" font-weight="600">{v}</text>')
    svg.append(svg_footer())
    (CHARTS / fname).write_text("\n".join(svg))


def main():
    data = load()
    task_ids = [e["rec"]["task_id"] for e in data]

    opus_lat = [e["rec"]["by_model"]["opus"]["latency_ms"] / 1000 for e in data]
    kimi_lat = [e["rec"]["by_model"]["kimi"]["latency_ms"] / 1000 for e in data]
    opus_tok_raw = [e["rec"]["by_model"]["opus"]["total_tokens"] for e in data]
    kimi_tok_raw = [e["rec"]["by_model"]["kimi"]["total_tokens"] for e in data]
    opus_tok = [t or 0 for t in opus_tok_raw]
    kimi_tok = [t or 0 for t in kimi_tok_raw]

    opus_scores, kimi_scores, winners = [], [], []
    for e in data:
        o, k, w = judge_scores(e)
        opus_scores.append(o if o is not None else 0)
        kimi_scores.append(k if k is not None else 0)
        winners.append(w)

    ow = sum(1 for w in winners if w == "opus")
    kw = sum(1 for w in winners if w == "kimi")
    tw = sum(1 for w in winners if w == "tie")
    uw = sum(1 for w in winners if w in (None, "unknown"))

    # Chart 1: wins breakdown
    wins_chart(ow, kw, tw, uw, "wins.svg")

    # Chart 2: summary (avg score, latency, tokens)
    valid_scores_o = [s for s, w in zip(opus_scores, winners) if w is not None]
    valid_scores_k = [s for s, w in zip(kimi_scores, winners) if w is not None]
    summary_bar(
        "Averages — Opus 4.7 vs Kimi K2.6",
        [
            ("Avg judge score (/10)", avg(valid_scores_o), avg(valid_scores_k)),
            ("Avg latency (s)", avg(opus_lat), avg(kimi_lat)),
            ("Avg total tokens", avg(opus_tok_raw), avg(kimi_tok_raw)),
        ],
        "summary.svg",
        fmt="{:.1f}",
    )

    # Chart 3: per-task latency
    bar_chart_simple("Latency per task (seconds)", task_ids, opus_lat, kimi_lat,
                     "seconds", "per_task_latency.svg", fmt="{:.0f}")

    # Chart 4: per-task judge scores
    bar_chart_simple("Judge score per task (/10)", task_ids, opus_scores, kimi_scores,
                     "score", "per_task_scores.svg", fmt="{:.1f}")

    # Chart 5: per-task tokens
    bar_chart_simple("Total tokens per task", task_ids, opus_tok, kimi_tok,
                     "tokens", "per_task_tokens.svg", fmt="{:.0f}")

    print(f"Wrote {len(list(CHARTS.glob('*.svg')))} SVGs to {CHARTS}")
    for f in sorted(CHARTS.glob("*.svg")):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()
