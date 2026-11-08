#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reproduce the human validation (paper Table 4) from the committed, anonymized rating CSVs.
Computes: Kimi-K3 human-accepted accuracy per human rater (population-reweighted), and the
4-rater agreement matrix (rater1, rater2 = the two human experts; opus, fable = the two LLM
judges) as three-way and binary Cohen's kappa. No Excel and no external data required.

    python code/reproduce_human_validation.py
Inputs: results/human_ratings/sheetA_k3_validation.csv, results/human_ratings/sheetB_judge_pairs.csv
"""
import csv, os, statistics

BM = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(BM, "..", "results", "human_ratings")
K3_ACC = 0.629                       # exact Kimi-K3 main-category accuracy (paper Table 2)
CATS = ["same", "related", "different"]

def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig"), delimiter=';'))

A = rd(os.path.join(R, "sheetA_k3_validation.csv"))
B = rd(os.path.join(R, "sheetB_judge_pairs.csv"))

def kappa(a, b, cats):
    n = len(a); po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa = {c: a.count(c) / n for c in cats}; pb = {c: b.count(c) / n for c in cats}
    pe = sum(pa[c] * pb[c] for c in cats)
    return po, ((po - pe) / (1 - pe) if pe < 1 else 0.0)

# --- Panel A: Kimi-K3 human acceptance (reweighted to observed agree/disagree frequency) ---
print("=" * 66)
print("K3 human-accepted accuracy (population-reweighted)")
print("=" * 66)
for rc in ["rater1", "rater2"]:
    ag, dis = [], []
    for r in A:
        v = r[rc + "_verdict"].strip().lower()
        acc = 1 if v in ("ja", "vertretbar") else (0 if v == "nein" else None)
        if acc is None:
            continue
        (ag if r["gold_main"] == r["k3_main"] else dis).append(acc)
    rew = K3_ACC * statistics.mean(ag) + (1 - K3_ACC) * statistics.mean(dis)
    print(f"  {rc}: accept|agree={statistics.mean(ag)*100:.0f}%  accept|disagree={statistics.mean(dis)*100:.0f}%"
          f"  ->  reweighted accuracy {rew*100:.1f}%  (vs. exact match {K3_ACC*100:.1f}%)")

# --- Panel B: 4-rater agreement on the 100 Task B label pairs ---
print("\n" + "=" * 66)
print("4-rater agreement on 100 label pairs (three-way kappa | binary kappa)")
print("=" * 66)
raters = {}
for col, name in [("rater1_verdict", "rater1"), ("rater2_verdict", "rater2"),
                  ("opus_verdict", "opus"), ("fable_verdict", "fable")]:
    raters[name] = [r[col].strip().lower() for r in B]
idx = [i for i in range(len(B)) if all(raters[n][i] in CATS for n in raters)]
for n in raters:
    raters[n] = [raters[n][i] for i in idx]
print(f"  n = {len(idx)} pairs (all four raters present)")
binv = lambda v: ["match" if x in ("same", "related") else "no" for x in v]
pairs = [("rater1", "rater2"), ("rater1", "opus"), ("rater1", "fable"),
         ("rater2", "opus"), ("rater2", "fable"), ("opus", "fable")]
res = {}
for a, b in pairs:
    _, k3 = kappa(raters[a], raters[b], CATS)
    _, kb = kappa(binv(raters[a]), binv(raters[b]), ["match", "no"])
    res[(a, b)] = (k3, kb)
    tag = "  <- inter-human" if (a, b) == ("rater1", "rater2") else (
          "  <- inter-judge" if (a, b) == ("opus", "fable") else "")
    print(f"  {a:6} vs {b:6}: {k3:6.3f} | {kb:6.3f}{tag}")
ih = res[("rater1", "rater2")]
jh = [res[p] for p in [("rater1", "opus"), ("rater1", "fable"), ("rater2", "opus"), ("rater2", "fable")]]
print(f"\n  inter-human kappa:            three-way {ih[0]:.3f} | binary {ih[1]:.3f}")
print(f"  judge-vs-human kappa (mean):  three-way {statistics.mean(x[0] for x in jh):.3f} | "
      f"binary {statistics.mean(x[1] for x in jh):.3f}")
