# NOTE (release): reference inference/provenance script used to GENERATE the released data.
# It needs model access (configure config/llm_api.example.toml) and expects the original project
# layout. The released results reproduce WITHOUT it via code/reproduce_*.py.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the Task-A evaluation set (passage -> Dimension/Haupt/Sub/Fein) and the codebook prompt
material, from the hand-coded ground truth. No endpoint calls.

Inputs:
  data/source/ground_truth_political_reps/…-MarkedPassages.csv   (UTF-16-LE) passage -> fine id
  results/political_reps_reduction/Reduction-Mapping.csv          fine -> sub/main/dimension
  results/political_reps_reduction/Summary-Codebook.csv           main -> definition
Outputs:
  benchmark/eval_set.csv    685 rows: passage_id;document;marked_text;fine_id;fine_title;subcategory;main_id;main_name;dimension
  benchmark/codebook.json   27 mains: {id,name,dimension,definition,anchors:[fine titles]}
"""
import csv, os, io, json
from collections import defaultdict, OrderedDict
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MP=os.path.join(ROOT,"data","source","ground_truth_political_reps",
                "- Welche Herausforderungen oder Erfahrungen zeigen-MarkedPassages.csv")
RED=os.path.join(ROOT,"results","political_reps_reduction","Reduction-Mapping.csv")
SCB=os.path.join(ROOT,"results","political_reps_reduction","Summary-Codebook.csv")
OUT=os.path.dirname(os.path.abspath(__file__))

# fine -> (sub, main_id, main_name, dimension) + anchor collection
fine=OrderedDict()
main_anchor=defaultdict(list)  # main_id -> [(count, fine_title)]
for r in csv.DictReader(open(RED,encoding="utf-8-sig"),delimiter=';'):
    fid=r["Fine Category ID"].strip()
    fine[fid]=(r["Subcategory"].strip(), r["Main Category ID"].strip(), r["Main Category"].strip(), r["Dimension"].strip())
    try: c=int(r["Passage Count"] or 0)
    except: c=0
    main_anchor[r["Main Category ID"].strip()].append((c, r["Fine Category Title"].strip()))

# main -> definition + name + dimension
maindef={}; mainname={}; maindim={}
for r in csv.DictReader(open(SCB,encoding="utf-8-sig"),delimiter=';'):
    mid=r["Main Category ID"].strip()
    maindef[mid]=(r.get("Definition") or "").strip()
    mainname[mid]=(r.get("Main Category Name") or "").strip()
    maindim[mid]=(r.get("Dimension") or "").strip()

# eval set
rows=[]; unmapped=0
for i,r in enumerate(csv.reader(open(MP,encoding="utf-16-le"),delimiter=';')):
    if i==0: continue
    if len(r)<4: continue
    doc,fid,ftitle,text=r[0],r[1].strip(),r[2],r[3]
    m=fine.get(fid)
    if not m: unmapped+=1; continue
    sub,mid,mname,dim=m
    rows.append([f"P{i:04d}",doc,text,fid,ftitle,sub,mid,mname,dim])

def wr(path,header,rr):
    buf=io.StringIO(); w=csv.writer(buf,delimiter=';',lineterminator='\r\n'); w.writerow(header); [w.writerow(x) for x in rr]
    open(path,"w",encoding="utf-8-sig",newline="").write(buf.getvalue())
wr(os.path.join(OUT,"eval_set.csv"),
   ["passage_id","document","marked_text","fine_id","fine_title","subcategory","main_id","main_name","dimension"],rows)

# codebook.json (main-level, with up to 3 anchors by frequency)
cb=[]
for mid in sorted(mainname, key=lambda x:int(x.split('M')[-1])):
    anchors=[t for _,t in sorted(main_anchor.get(mid,[]),reverse=True)[:3]]
    cb.append({"id":mid,"name":mainname[mid],"dimension":maindim[mid],
               "definition":maindef.get(mid,""),"anchors":anchors})
json.dump(cb,open(os.path.join(OUT,"codebook.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)

# report
from collections import Counter
cmain=Counter(r[6] for r in rows); cdim=Counter(r[8] for r in rows)
print(f"eval_set.csv: {len(rows)} Passagen (unmapped {unmapped}) · {len(cmain)} Hauptkat · {len(cdim)} Dimensionen")
print("codebook.json:",len(cb),"Hauptkategorien | Definitionen vorhanden:",sum(1 for c in cb if c['definition']),"/",len(cb))
print("größte Hauptkategorien:",cmain.most_common(5))
print("kleinste:",sorted(cmain.items(),key=lambda x:x[1])[:5])
print("Dimensionsverteilung:",dict(cdim))
