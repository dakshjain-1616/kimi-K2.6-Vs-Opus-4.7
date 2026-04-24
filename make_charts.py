#!/usr/bin/env python3
"""Generate SVG charts from benchmark outputs/."""

import json
import math
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
CHARTS = ROOT / "charts"
CHARTS.mkdir(exist_ok=True)

# Palette
OPUS = "#D97757"          # Anthropic-ish warm
OPUS_SOFT = "#F4D4C5"
KIMI = "#4F7CF7"          # Moonshot blue
KIMI_SOFT = "#D6E2FC"
BG = "#FFFFFF"
CARD = "#FBFBFB"
FG = "#1F2328"
MUTED = "#6A737D"
GRID = "#EEF0F3"
ACCENT_TIE = "#94A3B8"
ACCENT_UNK = "#CBD5E1"

FONT = '-apple-system,Segoe UI,Helvetica,Arial,sans-serif'


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


def svg_start(w, h, title, subtitle=None):
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="{FONT}">',
        f'<rect width="{w}" height="{h}" fill="{BG}"/>',
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="10" fill="{CARD}" stroke="{GRID}" stroke-width="1"/>',
        f'<text x="28" y="34" font-size="16" font-weight="700" fill="{FG}">{title}</text>',
    ]
    if subtitle:
        s.append(f'<text x="28" y="54" font-size="12" fill="{MUTED}">{subtitle}</text>')
    return "\n".join(s) + "\n"


def legend(x, y):
    return (
        f'<circle cx="{x+6}" cy="{y}" r="6" fill="{OPUS}"/>'
        f'<text x="{x+18}" y="{y+4}" font-size="12" fill="{FG}">Opus 4.7</text>'
        f'<circle cx="{x+88}" cy="{y}" r="6" fill="{KIMI}"/>'
        f'<text x="{x+100}" y="{y+4}" font-size="12" fill="{FG}">Kimi K2.6</text>'
    )


def nice_ceil(v, steps=4):
    if v <= 0:
        return 1
    mag = 10 ** int(math.log10(v))
    for mult in (1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 7.5, 10):
        cand = mult * mag
        if cand >= v:
            # round to multiple of steps
            return cand
    return v


def fmt_num(v, fmt="{:.1f}"):
    if v >= 10000:
        return f"{v/1000:.1f}k"
    return fmt.format(v)


# -------- Wins chart --------
def wins_chart(opus_w, kimi_w, ties, unknown, fname, n):
    W, H = 680, 280
    svg = [svg_start(W, H, "Judge-decided wins",
                     f"n = {n} tasks · independent judge: openai/gpt-5.4")]
    items = [
        ("Kimi K2.6", kimi_w, KIMI, KIMI_SOFT),
        ("Opus 4.7",  opus_w, OPUS, OPUS_SOFT),
        ("Ties",      ties,   ACCENT_TIE, "#E2E8F0"),
        ("Unresolved", unknown, ACCENT_UNK, "#F1F5F9"),
    ]
    pad_l, pad_t = 170, 80
    plot_w = W - pad_l - 70
    max_v = max(n, 1)
    row_h = 32
    for i, (lbl, v, fg, soft) in enumerate(items):
        y = pad_t + i * (row_h + 14)
        track_w = plot_w
        bar_w = plot_w * (v / max_v)
        # label
        svg.append(f'<text x="{pad_l-14}" y="{y+row_h/2+5}" text-anchor="end" font-size="13" fill="{FG}" font-weight="600">{lbl}</text>')
        # track (full width light)
        svg.append(f'<rect x="{pad_l}" y="{y}" width="{track_w}" height="{row_h}" rx="6" fill="{soft}"/>')
        # bar
        if bar_w > 0:
            svg.append(f'<rect x="{pad_l}" y="{y}" width="{bar_w}" height="{row_h}" rx="6" fill="{fg}"/>')
        # value
        tx = pad_l + bar_w + 10 if bar_w < track_w - 40 else pad_l + bar_w - 10
        anchor = "start" if bar_w < track_w - 40 else "end"
        tcolor = FG if bar_w < track_w - 40 else "#FFFFFF"
        svg.append(f'<text x="{tx}" y="{y+row_h/2+5}" text-anchor="{anchor}" font-size="14" font-weight="700" fill="{tcolor}">{v}</text>')
    svg.append("</svg>")
    (CHARTS / fname).write_text("\n".join(svg))


# -------- Summary chart --------
def summary_chart(rows, fname):
    """rows: [(label, opus_val, kimi_val, fmt)]"""
    W, H = 720, 360
    svg = [svg_start(W, H, "Averages — Opus 4.7 vs Kimi K2.6",
                     "Each row is scaled to its own maximum (metrics have different units)")]
    pad_l, pad_t = 180, 90
    plot_w = W - pad_l - 90
    n = len(rows)
    row_block = 68
    bar_h = 18
    for i, (label, vo, vk, fmt) in enumerate(rows):
        cy = pad_t + i * row_block
        max_v = max(vo, vk, 1)
        scale = plot_w / max_v
        # label
        svg.append(f'<text x="{pad_l-14}" y="{cy+bar_h+4}" text-anchor="end" font-size="13" fill="{FG}" font-weight="600">{label}</text>')
        # opus bar
        yo = cy
        wo = vo * scale
        svg.append(f'<rect x="{pad_l}" y="{yo}" width="{wo}" height="{bar_h}" rx="5" fill="{OPUS}"/>')
        svg.append(f'<text x="{pad_l+wo+8}" y="{yo+bar_h-4}" font-size="12" font-weight="600" fill="{FG}">{fmt_num(vo, fmt)}</text>')
        # kimi bar
        yk = cy + bar_h + 6
        wk = vk * scale
        svg.append(f'<rect x="{pad_l}" y="{yk}" width="{wk}" height="{bar_h}" rx="5" fill="{KIMI}"/>')
        svg.append(f'<text x="{pad_l+wk+8}" y="{yk+bar_h-4}" font-size="12" font-weight="600" fill="{FG}">{fmt_num(vk, fmt)}</text>')
    # legend
    svg.append(legend(pad_l, H - 28))
    svg.append("</svg>")
    (CHARTS / fname).write_text("\n".join(svg))


# -------- Per-task grouped bar chart --------
def per_task_chart(title, subtitle, labels, values_opus, values_kimi, ylabel, fname, fmt="{:.1f}"):
    W, H = 860, 420
    pad_l, pad_r, pad_t, pad_b = 78, 32, 80, 110
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    n = len(labels)
    group_w = plot_w / n
    bar_w = group_w * 0.36
    max_v = max(max(values_opus + values_kimi), 1)
    nice_max = nice_ceil(max_v)

    svg = [svg_start(W, H, title, subtitle)]

    # Gridlines + y labels
    steps = 5
    for i in range(steps + 1):
        y = pad_t + plot_h - (plot_h * i / steps)
        v = nice_max * i / steps
        svg.append(f'<line x1="{pad_l}" y1="{y}" x2="{W-pad_r}" y2="{y}" stroke="{GRID}" stroke-width="1"/>')
        svg.append(f'<text x="{pad_l-10}" y="{y+4}" text-anchor="end" font-size="10" fill="{MUTED}">{fmt_num(v, fmt)}</text>')

    # Y axis title
    svg.append(f'<text x="22" y="{pad_t+plot_h/2}" text-anchor="middle" font-size="11" fill="{MUTED}" transform="rotate(-90 22 {pad_t+plot_h/2})">{ylabel}</text>')

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
        # opus bar
        svg.append(f'<rect x="{xo}" y="{yo}" width="{bar_w}" height="{max(ho,0.1)}" rx="3" fill="{OPUS}"/>')
        if ho > 14:
            svg.append(f'<text x="{xo+bar_w/2}" y="{yo-4}" text-anchor="middle" font-size="9" fill="{FG}" font-weight="600">{fmt_num(vo, fmt)}</text>')
        else:
            svg.append(f'<text x="{xo+bar_w/2}" y="{yo-4}" text-anchor="middle" font-size="9" fill="{MUTED}">{fmt_num(vo, fmt)}</text>')
        # kimi bar
        svg.append(f'<rect x="{xk}" y="{yk}" width="{bar_w}" height="{max(hk,0.1)}" rx="3" fill="{KIMI}"/>')
        if hk > 14:
            svg.append(f'<text x="{xk+bar_w/2}" y="{yk-4}" text-anchor="middle" font-size="9" fill="{FG}" font-weight="600">{fmt_num(vk, fmt)}</text>')
        else:
            svg.append(f'<text x="{xk+bar_w/2}" y="{yk-4}" text-anchor="middle" font-size="9" fill="{MUTED}">{fmt_num(vk, fmt)}</text>')
        # rotated task label
        lx = gx
        ly = pad_t + plot_h + 14
        svg.append(f'<text x="{lx}" y="{ly}" text-anchor="end" font-size="10" fill="{FG}" transform="rotate(-32 {lx} {ly})">{label}</text>')

    # Baseline
    svg.append(f'<line x1="{pad_l}" y1="{pad_t+plot_h}" x2="{W-pad_r}" y2="{pad_t+plot_h}" stroke="{FG}" stroke-width="1.2"/>')

    # Legend
    svg.append(legend(pad_l, H - 22))
    svg.append("</svg>")
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

    wins_chart(ow, kw, tw, uw, "wins.svg", n=len(data))

    valid_o = [s for s, w in zip(opus_scores, winners) if w is not None]
    valid_k = [s for s, w in zip(kimi_scores, winners) if w is not None]
    summary_chart(
        [
            ("Avg judge score (/10)", avg(valid_o), avg(valid_k), "{:.1f}"),
            ("Avg latency (s)",       avg(opus_lat), avg(kimi_lat), "{:.0f}"),
            ("Avg total tokens",      avg(opus_tok_raw), avg(kimi_tok_raw), "{:.0f}"),
        ],
        "summary.svg",
    )

    per_task_chart(
        "Latency per task",
        "wall-clock seconds — lower is better",
        task_ids, opus_lat, kimi_lat,
        "seconds", "per_task_latency.svg", fmt="{:.0f}")

    per_task_chart(
        "Judge score per task",
        "average of correctness, depth, clarity (scale 1–10)",
        task_ids, opus_scores, kimi_scores,
        "score /10", "per_task_scores.svg", fmt="{:.1f}")

    per_task_chart(
        "Total tokens per task",
        "prompt + completion tokens",
        task_ids, opus_tok, kimi_tok,
        "tokens", "per_task_tokens.svg", fmt="{:.0f}")

    print(f"Wrote {len(list(CHARTS.glob('*.svg')))} SVGs to {CHARTS}")
    for f in sorted(CHARTS.glob("*.svg")):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()
