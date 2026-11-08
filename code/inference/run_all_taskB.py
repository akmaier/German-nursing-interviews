# NOTE (release): reference inference/provenance script used to GENERATE the released data.
# It needs model access (configure config/llm_api.example.toml) and expects the original project
# layout. The released results reproduce WITHOUT it via code/reproduce_*.py.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task B, part 1 (B1): INDUCTIVE labeling. Each model reads a passage (NO codebook) and coins its
own German fine-category label — Mayring inductive category formation. Top-2 models × 685 × 5 seeds
(temperature 0.7). Parallel across (model,seed), per-model throttle, retry/backoff, resumable.
The semantic comparison to Rita's labels is done separately by the Opus judge (B2).

  python benchmark/run_all_taskB.py            # top-2 × 685 × 5
  python benchmark/run_all_taskB.py --n 3 --seeds 1   # smoke
Output: benchmark/results/taskB_<model>_seed<k>.csv  (passage_id;gold_fine_id;gold_fine_title;gold_main;model_label)
Do not reduce seeds/models/passages — research (Andreas).
"""
import csv, os, io, sys, time, argparse, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import client
BM=os.path.dirname(os.path.abspath(__file__)); RES=os.path.join(BM,"results")

MODELS=["deepseek-ai/DeepSeek-V4-Flash","RedHatAI/gemma-4-31B-it-FP8-block"]
TEMPERATURE=0.7; PER_MODEL_CONC=6; GLOBAL_WORKERS=20

SYS=("Du bist eine erfahrene Codiererin nach Mayrings qualitativer Inhaltsanalyse "
     "(induktive Kategorienbildung). Lies die Interview-Passage und formuliere EINE prägnante "
     "Feinkategorie auf Deutsch — ein kurzer Kategorienname (2–6 Wörter), der den zentralen "
     "Inhalt der Passage auf den Punkt bringt. Gib AUSSCHLIESSLICH den Kategorienamen zurück: "
     "keine Anführungszeichen, keine Erklärung, kein ganzer Satz, keine Nummerierung.")

_lock=threading.Lock()
def log(m):
    with _lock: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def clean_label(txt):
    if not txt: return ""
    line=[l.strip() for l in txt.splitlines() if l.strip()]
    s=line[0] if line else ""
    for ch in ['"','„','“','”','`','*','#']: s=s.replace(ch,"")
    s=s.lstrip("-–•0123456789. )").strip().rstrip(".")
    return s[:120]

def label(text, model, seed, temp):
    msgs=[{"role":"system","content":SYS},{"role":"user","content":f'Passage: "{text}"'}]
    toks=200
    for attempt in range(6):
        try:
            try:
                r=client.chat(msgs,model=model,temperature=temp,max_tokens=toks,seed=seed)
            except RuntimeError as e:
                if "400" in str(e):
                    try: r=client.chat(msgs,model=model,temperature=temp,max_tokens=toks)
                    except RuntimeError: r=client.chat(msgs,model=model)
                else: raise
            ch=r["choices"][0]; content=ch["message"].get("content") or ""
            lab=clean_label(content)
            if lab: return lab
            if ch.get("finish_reason")=="length" and toks<800: toks*=2; continue
            return lab or "(leer)"
        except Exception:
            time.sleep(min(2**attempt+attempt*0.4,40))
    return "(fehler)"

def unit_path(model,seed): return os.path.join(RES,f"taskB_{model.replace('/','_')}_seed{seed}.csv")
def unit_done(model,seed,n):
    p=unit_path(model,seed)
    return os.path.exists(p) and (sum(1 for _ in open(p,encoding="utf-8-sig"))-1>=n)

_sem={}; _prog={}
def run_unit(model,seed,rows,temp):
    if unit_done(model,seed,len(rows)):
        log(f"resume taskB {model} seed{seed} (fertig)"); return (model,seed,True)
    sem=_sem[model]; out=[]; t0=time.time()
    for r in rows:
        with sem:
            lab=label(r["marked_text"],model,seed,temp)
        out.append([r["passage_id"],r["fine_id"],r["fine_title"],r["main_id"],lab])
        with _lock: _prog[model]=_prog.get(model,0)+1; tot=sum(_prog.values())
        if tot%1000==0: log(f"... {tot} Labels erzeugt")
    buf=io.StringIO(); w=csv.writer(buf,delimiter=';',lineterminator='\r\n')
    w.writerow(["passage_id","gold_fine_id","gold_fine_title","gold_main","model_label"]); [w.writerow(x) for x in out]
    os.makedirs(RES,exist_ok=True); open(unit_path(model,seed),"w",encoding="utf-8-sig",newline="").write(buf.getvalue())
    log(f"DONE taskB {model} seed{seed}  ({(time.time()-t0)/len(rows):.2f}s/it)")
    return (model,seed,True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--models",default=",".join(MODELS)); ap.add_argument("--n",type=int,default=0)
    ap.add_argument("--seeds",type=int,default=5); ap.add_argument("--temp",type=float,default=TEMPERATURE)
    a=ap.parse_args()
    models=[x.strip() for x in a.models.split(",") if x.strip()]; seeds=list(range(1,a.seeds+1))
    rows=list(csv.DictReader(open(os.path.join(BM,"eval_set.csv"),encoding="utf-8-sig"),delimiter=';'))
    if a.n: rows=rows[:a.n]
    for m in models: _sem[m]=threading.Semaphore(PER_MODEL_CONC)
    log(f"START Task B1 (induktive Labels): {len(models)} Modelle × {len(rows)} × {len(seeds)} Seeds = {len(models)*len(rows)*len(seeds)} Calls")
    with ThreadPoolExecutor(max_workers=GLOBAL_WORKERS) as ex:
        futs=[ex.submit(run_unit,m,s,rows,a.temp) for m in models for s in seeds]
        for f in as_completed(futs):
            try: f.result()
            except Exception as e: log(f"UNIT FAIL: {e}")
    log("B1 fertig — bereit für Opus-Judge (B2).")

if __name__=="__main__": main()
