#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from collections import Counter,defaultdict
from pathlib import Path
MIN_PRECISION=.90;MIN_RECALL=.80;MIN_SPECIFICITY=.95;MIN_BALLOON=.95;MIN_DRONE=100;MIN_NEGATIVE=200;MIN_GROUPS={"BIRD":10,"AIRPLANE":10,"HELICOPTER":10,"BALLOON":30}
def finite(v,name):
 if isinstance(v,bool):raise ValueError(f"invalid {name}: boolean")
 x=float(v)
 if not math.isfinite(x):raise ValueError(f"invalid {name}: {x}")
 return x
def disjoint(c):
 d={}
 for r in c.get("items") or []:d.setdefault((str(r.get("source_id") or ""),str(r.get("source_group_id") or "")),set()).add(str(r.get("split") or ""))
 overlap=[f"{s}/{g}" for (s,g),v in sorted(d.items()) if len(v&{"train","validation","test"})>1];return not overlap,overlap
def evaluate(c,p):
 if p.get("threshold_frozen_before_eval") is not True:raise ValueError("threshold not frozen")
 t=finite(p.get("threshold",-2),"threshold");kind=str(p.get("score_kind") or "prob_drone")
 if kind not in {"prob_drone","drone_margin"}:raise ValueError("bad score kind")
 lo,hi=(0,1) if kind=="prob_drone" else (-1,1)
 if not lo<=t<=hi:raise ValueError("threshold range")
 test=[r for r in c.get("items") or [] if str(r.get("split"))=="test"];truth={str(r["id"]):r for r in test};pred={}
 for r in p.get("predictions") or []:
  if not isinstance(r,dict):raise ValueError("prediction row")
  iid=str(r.get("id") or "")
  if not iid or iid in pred:raise ValueError("prediction ids")
  pred[iid]=r
 if set(pred)!=set(truth):raise ValueError("prediction/test mismatch")
 tp=fp=fn=tn=0;counts=Counter();groups=defaultdict(set);neg=Counter();negfp=Counter();negg=defaultdict(set);negfpg=defaultdict(set)
 for iid,r in truth.items():
  label=str(r.get("label") or "OTHER").upper();g=(str(r.get("source_id") or ""),str(r.get("source_group_id") or ""));counts[label]+=1;groups[label].add(g);score=finite(pred[iid].get(kind,lo-1),f"{kind} {iid}")
  if not lo<=score<=hi:raise ValueError("score range")
  a=score>=t;dr=label=="DRONE"
  if dr and a:tp+=1
  elif dr:fn+=1
  elif a:fp+=1;neg[label]+=1;negfp[label]+=1;negg[label].add(g);negfpg[label].add(g)
  else:tn+=1;neg[label]+=1;negg[label].add(g)
 precision=tp/max(1,tp+fp);recall=tp/max(1,tp+fn);spec=tn/max(1,tn+fp);ok,overlap=disjoint(c);C={k:int(v) for k,v in sorted(counts.items())};C["NEGATIVE"]=sum(v for k,v in counts.items() if k!="DRONE");G={k:len(v) for k,v in sorted(groups.items())};G["NEGATIVE"]=len(set().union(*(v for k,v in groups.items() if k!="DRONE")))
 conf={}
 for l in neg:conf[l]={"negative_samples":int(neg[l]),"unique_source_groups":len(negg[l]),"false_positives":int(negfp[l]),"specificity":1-negfp[l]/max(1,neg[l]),"false_positive_source_groups":len(negfpg[l]),"source_group_specificity":1-len(negfpg[l])/max(1,len(negg[l]))}
 b=[]
 if not ok:b.append("source overlap")
 if C.get("DRONE",0)<MIN_DRONE:b.append("DRONE count")
 if C.get("NEGATIVE",0)<MIN_NEGATIVE:b.append("NEGATIVE count")
 if G.get("DRONE",0)<10:b.append("DRONE source groups")
 for l,n in MIN_GROUPS.items():
  if G.get(l,0)<n:b.append(f"{l} source groups")
 if precision<.90:b.append("precision")
 if recall<.80:b.append("recall")
 if spec<.95:b.append("specificity")
 bal=conf.get("BALLOON",{})
 if int(bal.get("negative_samples",0))<30:b.append("balloon count")
 if float(bal.get("specificity",0))<.95:b.append("balloon specificity")
 if float(bal.get("source_group_specificity",0))<.95:b.append("balloon group specificity")
 return {"schema_version":4,"candidate_id":p.get("candidate_id"),"source_disjoint":ok,"source_overlap":overlap,"threshold_frozen_before_eval":True,"score_kind":kind,"threshold":t,"counts":C,"source_group_counts":G,"metrics":{"drone_precision":precision,"drone_recall":recall,"negative_specificity":spec},"confusion_counts":{"tp":tp,"fp":fp,"fn":fn,"tn":tn},"confounders":conf,"quality_pass":not b,"quality_blockers":b}
def main():
 a=argparse.ArgumentParser();a.add_argument("corpus",type=Path);a.add_argument("predictions",type=Path);a.add_argument("--out",type=Path);x=a.parse_args();r=evaluate(json.loads(x.corpus.read_text()),json.loads(x.predictions.read_text()));text=json.dumps(r,indent=2,sort_keys=True)+"\n";print(text,end="");
 if x.out:x.out.write_text(text)
 raise SystemExit(0 if r["quality_pass"] else 2)
if __name__=="__main__":main()
