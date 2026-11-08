#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reproduce the Task A leaderboard (paper Table 2) and the two key significance contrasts,
from the released per-model, per-seed prediction files. Pure standard library.

    python code/reproduce_taskA.py
Inputs: results/taskA/taskA_<model>_seed<k>.csv, data/codebook.json
Metrics: main/dimension accuracy (mean +/- std over 5 seeds), macro-F1, Cohen's kappa.
Significance: passage-clustered paired bootstrap (3000 resamples) of the acc_main difference.
"""
import csv, os, glob, re, math, random, statistics
from collections import defaultdict

random.seed(42)
BM = os.path.dirname(os.path.abspath(__file__))
LABELS = sorted(c["id"] for c in __import__("json").load(
    open(os.path.join(BM, "..", "data", "codebook.json"), encoding="utf-8")))
NICE = {"k3": "Kimi-K3", "glm-fp8": "GLM-5.2-FP8", "glm-w4a16": "GLM-5.2-W4A16"}

def disp(m):
    if m in NICE: return NICE[m]
    return m.replace("_", "/", 1) if m.startswith((
        "deepseek", "google", "RedHatAI", "GaleneAI", "Microsoft", "Qwen")) else m

data = defaultdict(dict)   # model -> {(pid,seed): (main_ok, dim_ok, gold, pred)}
for f in glob.glob(os.path.join(BM, "..", "results", "taskA", "taskA_*_seed*.csv")):
    m = re.search(r'taskA_(.+)_seed(\d+)\.csv', os.path.basename(f))
    model, seed = m.group(1), int(m.group(2))
    for r in csv.DictReader(open(f, encoding="utf-8-sig"), delimiter=';'):
        data[model][(r["passage_id"], seed)] = (int(r["main_ok"]), int(r["dim_ok"]),
                                                 r["gold_main"], r["pred_main"])

PIDS = sorted({k[0] for k in next(iter(data.values()))})
SEEDS = sorted({k[1] for k in next(iter(data.values()))})

def per_seed(m, idx): return [statistics.mean(data[m][(p, s)][idx] for p in PIDS) for s in SEEDS]

def f1_kappa(m):
    f1s, kaps = [], []
    for s in SEEDS:
        gold = [data[m][(p, s)][2] for p in PIDS]; pred = [data[m][(p, s)][3] for p in PIDS]; n = len(gold)
        fs = []
        for L in LABELS:
            tp = sum(1 for g, p in zip(gold, pred) if g == L and p == L)
            fp = sum(1 for g, p in zip(gold, pred) if g != L and p == L)
            fn = sum(1 for g, p in zip(gold, pred) if g == L and p != L)
            pr = tp / (tp + fp) if tp + fp else 0; rc = tp / (tp + fn) if tp + fn else 0
            fs.append(2 * pr * rc / (pr + rc) if pr + rc else 0)
        f1s.append(statistics.mean(fs))
        po = sum(1 for g, p in zip(gold, pred) if g == p) / n
        from collections import Counter
        cg = Counter(gold); cp = Counter(pred)
        pe = sum((cg[L] / n) * (cp[L] / n) for L in set(gold) | set(pred))
        kaps.append((po - pe) / (1 - pe) if pe < 1 else 0)
    return statistics.mean(f1s), statistics.mean(kaps)

rows = []
for m in data:
    am = per_seed(m, 0); ad = per_seed(m, 1); f1, kap = f1_kappa(m)
    rows.append((disp(m), statistics.mean(am), statistics.stdev(am), statistics.mean(ad), f1, kap, m))
rows.sort(key=lambda r: -r[1])

print(f"{'#':>2}  {'model':40} {'acc_main':>14} {'acc_dim':>8} {'F1':>6} {'kappa':>6}")
for i, r in enumerate(rows, 1):
    print(f"{i:>2}  {r[0]:40} {r[1]:.3f} +/- {r[2]:.3f}   {r[3]:.3f}  {r[4]:.3f}  {r[5]:.3f}")

# write the full leaderboard (all models) so the release carries a current, consistent table
import csv as _csv
_lb = os.path.join(BM, "..", "results", "leaderboard_taskA.csv")
with open(_lb, "w", encoding="utf-8", newline="") as _fh:
    _w = _csv.writer(_fh, delimiter=";", lineterminator="\n")
    _w.writerow(["model", "seeds", "acc_main_mean", "acc_main_std", "acc_dim_mean", "macro_f1_mean", "kappa_mean",
                 "per_seed_acc_main"])
    for r in rows:
        am = per_seed(r[6], 0)
        _w.writerow([r[0], len(SEEDS), f"{r[1]:.4f}", f"{r[2]:.4f}", f"{r[3]:.4f}", f"{r[4]:.4f}", f"{r[5]:.4f}",
                     ",".join(f"{x:.4f}" for x in am)])
print(f"wrote results/leaderboard_taskA.csv ({len(rows)} models)")

def boot_diff(A, B, Bn=3000):
    base = {m: {p: statistics.mean(data[m][(p, s)][0] for s in SEEDS) for p in PIDS} for m in (A, B)}
    obs = statistics.mean(base[A][p] - base[B][p] for p in PIDS)
    ds = []
    for _ in range(Bn):
        samp = [PIDS[random.randrange(len(PIDS))] for _ in PIDS]
        ds.append(statistics.mean(base[A][p] - base[B][p] for p in samp))
    ds.sort(); lo = ds[int(0.025 * Bn)]; hi = ds[int(0.975 * Bn)]
    p = 2 * min(sum(1 for d in ds if d <= 0), sum(1 for d in ds if d >= 0)) / Bn
    return obs, lo, hi, min(p, 1.0)

def contrast(a, b):
    ma = next(k for k in data if disp(k) == a or k == a)
    mb = next(k for k in data if disp(k) == b or k == b)
    o, lo, hi, p = boot_diff(ma, mb)
    print(f"  {a} vs {b}: delta acc_main {o*100:+.1f}pp  95% CI [{lo*100:+.1f},{hi*100:+.1f}]  p={p:.3f}")

print("\nKey contrasts (passage-clustered paired bootstrap, 3000x):")
contrast("Kimi-K3", "deepseek-ai/DeepSeek-V4-Flash")
contrast("GLM-5.2-FP8", "GLM-5.2-W4A16")
