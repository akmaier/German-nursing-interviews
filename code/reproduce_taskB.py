#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reproduce Task B (inductive category formation) from the released data — no model access needed.

Task B is inductive: four models generate a fine-category label per passage without the codebook,
and a Claude-Opus judge rates each label against the expert label as same / related / different.
Because the generated labels are passage-derived free text, the release ships the JUDGE VERDICT per
occurrence (not the label text); the verbatim generated labels are shipped only for the released
passages (results/taskB/generated_labels_released.csv). This script reproduces the Table-3 rates,
the gemma-vs-DeepSeek significance test and the judge intra-rater reliability from the verdicts alone.

Inputs (../results/):
  taskB/taskB_<model>_seed{1..5}.csv   — passage_id ; gold_fine_id ; gold_main ; verdict
  judge/taskB_judge_verdicts.json      — rel_passes: 4 judge passes over a 300-pair subset (reliability)

Writes ../results/reproduced_RESULTS_taskB.md and prints the table. SD is over the 5 seeds (sample, n-1).
"""
import csv, json, os, glob, re, statistics, random
from collections import defaultdict, Counter

random.seed(7)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")

def rd(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))

MODELS = [
    ("RedHatAI/gemma-4-31B-it-FP8-block", "taskB_RedHatAI_gemma-4-31B-it-FP8-block_seed*.csv"),
    ("deepseek-ai/DeepSeek-V4-Flash",     "taskB_deepseek-ai_DeepSeek-V4-Flash_seed*.csv"),
    ("nvidia/nemotron-3-ultra-550b-a55b", "taskB_nvidia_nemotron-3-ultra-550b-a55b_seed*.csv"),
    ("Mistral-Large-4.0",                 "taskB_mistral-large-4_browser_seed*.csv"),
]

# model -> passage -> seed -> (is_same, is_same_or_related)
same_by = defaultdict(lambda: defaultdict(dict))
sr_by = defaultdict(lambda: defaultdict(dict))
occ = 0
rows = []
for name, pat in MODELS:
    files = sorted(glob.glob(os.path.join(RES, "taskB", pat)))
    assert len(files) == 5, f"{name}: expected 5 seeds, got {len(files)}"
    strict, them = [], []
    for si, f in enumerate(files, 1):
        rws = rd(f)
        n = len(rws)
        occ += n
        same = rel = 0
        for r in rws:
            v = r["verdict"]
            same_by[name][r["passage_id"]][si] = 1 if v == "same" else 0
            sr_by[name][r["passage_id"]][si] = 1 if v in ("same", "related") else 0
            if v == "same": same += 1; rel += 1
            elif v == "related": rel += 1
        strict.append(100.0 * same / n)
        them.append(100.0 * rel / n)
    rows.append((name, statistics.mean(strict), statistics.stdev(strict),
                 statistics.mean(them), statistics.stdev(them)))

# gemma vs DeepSeek: passage-clustered paired bootstrap (unit = passage, seeds as repeated measures)
def per_passage(mp, m):
    pids = sorted(mp[m]); seeds = sorted(next(iter(mp[m].values())))
    return pids, {p: statistics.mean(mp[m][p][s] for s in seeds) for p in pids}
def boot(mp, B=3000):
    g, d = MODELS[0][0], MODELS[1][0]
    pids, a = per_passage(mp, g); _, b = per_passage(mp, d); n = len(pids)
    obs = sum(a[p] - b[p] for p in pids) / n
    ds = []
    for _ in range(B):
        s = [pids[random.randrange(n)] for _ in range(n)]
        ds.append(sum(a[p] - b[p] for p in s) / n)
    ds.sort(); lo = ds[int(0.025 * B)]; hi = ds[int(0.975 * B)]
    p2 = 2 * min(sum(1 for x in ds if x <= 0), sum(1 for x in ds if x >= 0)) / B
    return obs * 100, lo * 100, hi * 100, min(p2, 1.0)   # percentage points
d_same = boot(same_by); d_sr = boot(sr_by)

# judge intra-rater reliability: 4 passes over the 300-pair subset (verdicts only)
rel_passes = json.load(open(os.path.join(RES, "judge", "taskB_judge_verdicts.json"), encoding="utf-8"))["result"]["rel_passes"]
CATS = ["same", "related", "different"]
passes = [{d["id"]: d["verdict"] for d in p} for p in rel_passes]
ids = [d["id"] for d in rel_passes[0]]
items = [[p.get(i) for p in passes] for i in ids]
items = [r for r in items if all(r) and len(r) == 4]
unan = sum(1 for r in items if len(set(r)) == 1) / len(items)
Nn = len(items); k = 4
pj = {c: 0 for c in CATS}; Pi = []
for r in items:
    cnt = {c: r.count(c) for c in CATS}
    for c in CATS: pj[c] += cnt[c]
    Pi.append((sum(cnt[c] ** 2 for c in CATS) - k) / (k * (k - 1)))
for c in CATS: pj[c] /= (Nn * k)
Pbar = statistics.mean(Pi); Pe = sum(v ** 2 for v in pj.values())
fleiss = (Pbar - Pe) / (1 - Pe)
bin_items = [["m" if x in ("same", "related") else "n" for x in r] for r in items]
unan2 = sum(1 for r in bin_items if len(set(r)) == 1) / len(bin_items)

sh = lambda m: m
L = ["# Task B — reproduced (4 models, 5 seeds) from released judge verdicts", "",
     f"{len(MODELS)} models x 5 seeds x 685 passages = **{occ} label-pair occurrences**. "
     "Strict = share rated *same*; thematic = *same* or *related*. Mean +/- sample SD over 5 seeds.", "",
     "| Model | strict %same | thematic %same+related |", "|---|---|---|"]
for name, sm, ss, tm, ts in rows:
    L.append(f"| {name} | {sm:.1f} ± {ss:.1f} | {tm:.1f} ± {ts:.1f} |")
L += ["", "## Significance (passage-clustered paired bootstrap, 3000x)",
      f"- strict %same: gemma - DeepSeek = {d_same[0]:+.1f} pp, 95% CI [{d_same[1]:+.1f}, {d_same[2]:+.1f}], p={d_same[3]:.3f}",
      f"- thematic: delta = {d_sr[0]:+.1f} pp, 95% CI [{d_sr[1]:+.1f}, {d_sr[2]:+.1f}], p={d_sr[3]:.3f}", "",
      "## Judge intra-rater reliability (4 passes, 300-pair subset)",
      f"- unanimous (3-way): {unan*100:.1f}%  |  Fleiss' kappa: {fleiss:.3f}",
      f"- unanimous (binary same+related vs different): {unan2*100:.1f}%"]
os.makedirs(os.path.join(RES, "reproduced"), exist_ok=True)
open(os.path.join(RES, "reproduced", "RESULTS_taskB.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

print(f"occurrences={occ}")
for name, sm, ss, tm, ts in rows:
    print(f"  {name:40} strict {sm:4.1f} ± {ss:3.1f}   thematic {tm:4.1f} ± {ts:3.1f}")
print(f"  gemma-DeepSeek strict {d_same[0]:+.1f}pp (p={d_same[3]:.3f}) | thematic {d_sr[0]:+.1f}pp (p={d_sr[3]:.3f})")
print(f"  judge reliability: unanimous(3)={unan*100:.1f}%  Fleiss k={fleiss:.3f}  binary unanimous={unan2*100:.1f}%")
print("wrote results/reproduced/RESULTS_taskB.md")
