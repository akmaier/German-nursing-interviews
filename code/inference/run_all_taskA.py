# NOTE (release): reference inference/provenance script used to GENERATE the released data.
# It needs model access (configure config/llm_api.example.toml) and expects the original project
# layout. The released results reproduce WITHOUT it via code/reproduce_*.py.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task A research run: 8 coder models × 685 passages × 5 seeds (temperature>0) so we get a
DISTRIBUTION per model for statistical analysis. Parallel across models (each model has its own
rate limit); per-model concurrency capped; retry/backoff; RESUMABLE per (model,seed).

  python benchmark/run_all_taskA.py                      # full research matrix
  python benchmark/run_all_taskA.py --n 4 --seeds 2      # tiny smoke
Outputs:
  benchmark/results/taskA_<model>_seed<k>.csv            per (model,seed) per-passage
  benchmark/results/leaderboard_taskA.csv                mean±std across seeds + per-seed
Never reduce seeds/models/passages for cost — this is research (Andreas).
"""
import csv, os, io, json, re, sys, time, argparse, threading, statistics
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import client
BM=os.path.dirname(os.path.abspath(__file__)); RES=os.path.join(BM,"results")

CODERS=["gpt-oss-120b","deepseek-ai/DeepSeek-V4-Flash","GaleneAI/Magistral-Small-2509-FP8-Dynamic",
        "Qwen/Qwen3.6-35B-A3B-FP8","RedHatAI/gemma-4-31B-it-FP8-block",
        "RedHatAI/Mistral-Small-3.2-24B-Instruct-2506-FP8","google/gemma-4-E4B-it","Microsoft/Phi-4-mini-instruct"]
TEMPERATURE=0.7
PER_MODEL_CONC=6          # concurrent requests per model (respect its own limit; backoff on 429)
GLOBAL_WORKERS=24

cb=json.load(open(os.path.join(BM,"codebook.json"),encoding="utf-8"))
MAIN2DIM={c["id"]:c["dimension"] for c in cb}; VALID=set(MAIN2DIM)
def _sys():
    L=["Du bist eine erfahrene Codiererin nach Mayrings qualitativer Inhaltsanalyse.",
       "Ordne die vorgelegte Interview-Passage GENAU EINER der folgenden Hauptkategorien zu.",
       "Wähle die inhaltlich am besten passende Kategorie.","","Hauptkategorien:"]
    for c in cb:
        L.append(f'{c["id"]} — {c["name"]} [{c["dimension"]}]: {(c["definition"] or "").strip()} Beispiele: {"; ".join(c["anchors"][:3])}')
    L+=["","Antworte AUSSCHLIESSLICH als JSON, ohne weiteren Text:", '{"main_id": "RQ1-Mxx"}']
    return "\n".join(L)
SYS=_sys()
def parse_id(t):
    if not t: return None
    m=re.findall(r'RQ1-M\d{2}', t); return m[-1] if m else None

_lock=threading.Lock()
def log(m):
    with _lock: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def predict(text, model, seed, temp):
    msgs=[{"role":"system","content":SYS},{"role":"user","content":f'Passage: "{text}"'}]
    toks=700
    for attempt in range(6):
        try:
            try:
                r=client.chat(msgs,model=model,temperature=temp,max_tokens=toks,seed=seed)
            except RuntimeError as e:
                if "400" in str(e):        # seed/params unsupported -> drop seed, then minimal
                    try: r=client.chat(msgs,model=model,temperature=temp,max_tokens=toks)
                    except RuntimeError: r=client.chat(msgs,model=model)
                else: raise
            ch=r["choices"][0]; content=ch["message"].get("content") or ""
            pid=parse_id(content)
            if pid in VALID: return pid,"ok"
            if ch.get("finish_reason")=="length" and toks<2400: toks*=2; continue
            m2=msgs+[{"role":"assistant","content":content[:200]},
                     {"role":"user","content":"Gib NUR die ID als JSON zurück: {\"main_id\": \"RQ1-Mxx\"}"}]
            r=client.chat(m2,model=model,temperature=temp,max_tokens=toks)
            pid=parse_id(r["choices"][0]["message"].get("content") or "")
            return (pid if pid in VALID else "?"),"reprompt"
        except Exception as e:
            time.sleep(min(2**attempt+attempt*0.4,40))
    return "?","fail"

def unit_path(model,seed): return os.path.join(RES,f"taskA_{model.replace('/','_')}_seed{seed}.csv")
def unit_done(model,seed,n):
    p=unit_path(model,seed)
    if not os.path.exists(p): return False
    try: return sum(1 for _ in open(p,encoding="utf-8-sig"))-1>=n
    except: return False

def metrics(rowsout):
    gold=[r[1] for r in rowsout]; pred=[r[2] for r in rowsout]; n=len(gold)
    accM=sum(1 for g,p in zip(gold,pred) if g==p)/n
    accD=sum(r[6] for r in rowsout)/n
    labels=sorted(VALID); fs=[]
    for L in labels:
        tp=sum(1 for g,p in zip(gold,pred) if g==L and p==L); fp=sum(1 for g,p in zip(gold,pred) if g!=L and p==L); fn=sum(1 for g,p in zip(gold,pred) if g==L and p!=L)
        pr=tp/(tp+fp) if tp+fp else 0; rc=tp/(tp+fn) if tp+fn else 0; fs.append(2*pr*rc/(pr+rc) if pr+rc else 0)
    f1=sum(fs)/len(fs)
    po=accM; pe=sum((gold.count(l)/n)*(pred.count(l)/n) for l in set(gold)|set(pred)); kap=(po-pe)/(1-pe) if pe<1 else 0
    inv=sum(1 for p in pred if p=="?")
    return {"acc_main":accM,"acc_dim":accD,"macro_f1":f1,"kappa":kap,"invalid":inv}

_prog=defaultdict(int); _sem={}
def run_unit(model,seed,rows,temp):
    if unit_done(model,seed,len(rows)):
        out=[]
        for r in csv.DictReader(open(unit_path(model,seed),encoding="utf-8-sig"),delimiter=';'):
            out.append([r["passage_id"],r["gold_main"],r["pred_main"],r["gold_dim"],r["pred_dim"],int(r["main_ok"]),int(r["dim_ok"])])
        log(f"resume {model} seed{seed} (schon fertig)")
        return (model,seed,metrics(out))
    sem=_sem[model]; out=[]; t0=time.time()
    for r in rows:
        with sem:
            pid,note=predict(r["marked_text"],model,seed,temp)
        pdim=MAIN2DIM.get(pid,"?")
        out.append([r["passage_id"],r["main_id"],pid,r["dimension"],pdim,int(pid==r["main_id"]),int(pdim==r["dimension"]),note,r["marked_text"][:80]])
        with _lock:
            _prog[model]+=1
            tot=sum(_prog.values())
        if tot%1000==0: log(f"... {tot} Calls fertig")
    buf=io.StringIO(); w=csv.writer(buf,delimiter=';',lineterminator='\r\n')
    w.writerow(["passage_id","gold_main","pred_main","gold_dim","pred_dim","main_ok","dim_ok","note","text"]); [w.writerow(x) for x in out]
    os.makedirs(RES,exist_ok=True); open(unit_path(model,seed),"w",encoding="utf-8-sig",newline="").write(buf.getvalue())
    mm=metrics([o[:7] for o in out])
    log(f"DONE {model} seed{seed}  acc_main={mm['acc_main']:.3f} f1={mm['macro_f1']:.3f} kappa={mm['kappa']:.3f} inv={mm['invalid']} ({(time.time()-t0)/len(rows):.2f}s/it)")
    return (model,seed,mm)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--models",default=",".join(CODERS)); ap.add_argument("--n",type=int,default=0)
    ap.add_argument("--seeds",type=int,default=5); ap.add_argument("--temp",type=float,default=TEMPERATURE)
    a=ap.parse_args()
    models=[x.strip() for x in a.models.split(",") if x.strip()]; seeds=list(range(1,a.seeds+1))
    rows=list(csv.DictReader(open(os.path.join(BM,"eval_set.csv"),encoding="utf-8-sig"),delimiter=';'))
    if a.n: rows=rows[:a.n]
    for m in models: _sem[m]=threading.Semaphore(PER_MODEL_CONC)
    from collections import Counter
    maj=Counter(r["main_id"] for r in rows).most_common(1)[0]
    log(f"START Task A: {len(models)} Modelle × {len(rows)} Passagen × {len(seeds)} Seeds (temp={a.temp}) = {len(models)*len(rows)*len(seeds)} Calls. Majority={maj[1]/len(rows):.3f}")
    per=defaultdict(dict)
    with ThreadPoolExecutor(max_workers=GLOBAL_WORKERS) as ex:
        futs=[ex.submit(run_unit,m,s,rows,a.temp) for m in models for s in seeds]
        for f in as_completed(futs):
            try:
                model,seed,mm=f.result(); per[model][seed]=mm
            except Exception as e: log(f"UNIT FAIL: {e}")
    # aggregate
    buf=io.StringIO(); w=csv.writer(buf,delimiter=';',lineterminator='\r\n')
    w.writerow(["model","seeds","acc_main_mean","acc_main_std","acc_dim_mean","macro_f1_mean","macro_f1_std","kappa_mean","invalid_mean","per_seed_acc_main"])
    table=[]
    for m in models:
        ms=[per[m][s] for s in seeds if s in per[m]]
        if not ms: continue
        am=[x["acc_main"] for x in ms]
        row={"model":m,"acc_main_mean":statistics.mean(am),"acc_main_std":(statistics.pstdev(am) if len(am)>1 else 0),
             "acc_dim_mean":statistics.mean(x["acc_dim"] for x in ms),
             "f1_mean":statistics.mean(x["macro_f1"] for x in ms),"f1_std":(statistics.pstdev([x["macro_f1"] for x in ms]) if len(am)>1 else 0),
             "kappa_mean":statistics.mean(x["kappa"] for x in ms),"inv_mean":statistics.mean(x["invalid"] for x in ms),"per_seed":am}
        table.append(row)
    table.sort(key=lambda r:-r["acc_main_mean"])
    for r in table:
        w.writerow([r["model"],len(r["per_seed"]),f"{r['acc_main_mean']:.4f}",f"{r['acc_main_std']:.4f}",f"{r['acc_dim_mean']:.4f}",
                    f"{r['f1_mean']:.4f}",f"{r['f1_std']:.4f}",f"{r['kappa_mean']:.4f}",f"{r['inv_mean']:.2f}",
                    ",".join(f"{x:.4f}" for x in r["per_seed"])])
    open(os.path.join(RES,"leaderboard_taskA.csv"),"w",encoding="utf-8-sig",newline="").write(buf.getvalue())
    log("\n=== LEADERBOARD Task A (acc_main mean±std über Seeds) ===")
    for r in table: log(f"  {r['acc_main_mean']:.3f}±{r['acc_main_std']:.3f}  f1={r['f1_mean']:.3f} kappa={r['kappa_mean']:.3f}  {r['model']}")

if __name__=="__main__": main()
