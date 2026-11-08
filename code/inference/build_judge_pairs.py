# NOTE (release): reference inference/provenance script used to GENERATE the released data.
# It needs model access (configure config/llm_api.example.toml) and expects the original project
# layout. The released results reproduce WITHOUT it via code/reproduce_*.py.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare the Opus-judge input for Task B: collect (model_label, rita_fine_label) pairs from the
B1 outputs and DEDUPLICATE (identical pairs are judged once). Writes benchmark/judge_pairs.json:
  {"pairs":[{id, model_label, rita_label}...],
   "occurrences":[{model, seed, passage_id, pair_id, gold_main}...]}
Data minimization: only category LABELS go to the judge — no raw interview text.
"""
import csv, os, glob, re, json
BM=os.path.dirname(os.path.abspath(__file__)); RES=os.path.join(BM,"results")

occ=[]; pair_id={}; pairs=[]
def norm(s): return re.sub(r'\s+',' ',(s or '').strip()).lower()
for f in sorted(glob.glob(os.path.join(RES,"taskB_*_seed*.csv"))):
    b=os.path.basename(f); m=re.search(r'taskB_(.+)_seed(\d+)\.csv',b); model=m.group(1); seed=int(m.group(2))
    for r in csv.DictReader(open(f,encoding="utf-8-sig"),delimiter=';'):
        ml=r["model_label"]; rl=r["gold_fine_title"]
        key=(norm(ml),norm(rl))
        if key not in pair_id:
            pair_id[key]=len(pairs); pairs.append({"id":len(pairs),"model_label":ml,"rita_label":rl})
        occ.append({"model":model,"seed":seed,"passage_id":r["passage_id"],"pair_id":pair_id[key],"gold_main":r["gold_main"]})
json.dump({"pairs":pairs,"occurrences":occ},open(os.path.join(BM,"judge_pairs.json"),"w",encoding="utf-8"),ensure_ascii=False)
print(f"occurrences: {len(occ)} | unique pairs (zu bewerten): {len(pairs)}")
