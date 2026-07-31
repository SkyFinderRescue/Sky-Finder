#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,math,statistics,time
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image
import coremltools as ct
IMAGE_SIZE=160;CONTEXT=.25
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
def padded_bbox(bbox,w,h):
 if not bbox:return (0,0,w,h)
 x,y,bw,bh=map(float,bbox);pad=max(bw,bh)*CONTEXT;L=max(0,int(math.floor(x-pad)));T=max(0,int(math.floor(y-pad)));R=min(w,int(math.ceil(x+bw+pad)));B=min(h,int(math.ceil(y+bh+pad)))
 if R<=L or B<=T:raise ValueError(f'collapsed bbox {bbox}')
 return L,T,R,B
def percentile(values,p):
 if not values:return None
 s=sorted(values);i=min(len(s)-1,max(0,int(math.ceil(p*len(s)))-1));return s[i]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--model',required=True,type=Path);ap.add_argument('--policy',required=True,type=Path);ap.add_argument('--corpus',required=True,type=Path);ap.add_argument('--heldout-root',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();policy=json.loads(a.policy.read_text());corp=json.loads(a.corpus.read_text())
 if sha(a.model)!=policy.get('model_sha256'):raise SystemExit('model checksum mismatch')
 threshold=float(policy['drone_margin_threshold']);model=ct.models.MLModel(str(a.model),compute_units=ct.ComputeUnit.ALL);spec=model.get_spec();prob_name=spec.description.predictedProbabilitiesName
 if not prob_name:raise SystemExit('Core ML classifier probability output missing')
 test=[r for r in corp.get('items',[]) if r.get('split')=='test'];tp=fp=fn=tn=0;counts=Counter();groups=defaultdict(set);neg=Counter();negfp=Counter();negg=defaultdict(set);negfpg=defaultdict(set);lat=[];preds=[]
 for n,row in enumerate(test,1):
  path=a.heldout_root/row['path']
  if not path.is_file():raise SystemExit(f'missing heldout file {path}')
  if sha(path).lower()!=str(row['sha256']).lower():raise SystemExit(f'heldout checksum mismatch {row["id"]}')
  with Image.open(path) as im:
   im=im.convert('RGB');crop=im.crop(padded_bbox(row.get('bbox'),im.width,im.height)).resize((IMAGE_SIZE,IMAGE_SIZE),Image.Resampling.BILINEAR)
   t0=time.perf_counter();out=model.predict({'image':crop});lat.append((time.perf_counter()-t0)*1000.)
  probs=out.get(prob_name)
  if not isinstance(probs,dict):raise SystemExit(f'probability output is not dictionary: {type(probs)} keys={list(out)}')
  pd=float(probs.get('DRONE',0.));pn=float(probs.get('NON_DRONE',0.));margin=pd-pn;assert math.isfinite(margin) and -1.000001<=margin<=1.000001
  asserted=margin>=threshold;label=str(row.get('label') or 'OTHER').upper();g=(str(row.get('source_id') or ''),str(row.get('source_group_id') or ''));counts[label]+=1;groups[label].add(g)
  if label=='DRONE' and asserted:tp+=1
  elif label=='DRONE':fn+=1
  elif asserted:fp+=1;neg[label]+=1;negfp[label]+=1;negg[label].add(g);negfpg[label].add(g)
  else:tn+=1;neg[label]+=1;negg[label].add(g)
  preds.append({'id':row['id'],'prob_drone':pd,'prob_non_drone':pn,'drone_margin':margin,'asserted_drone':asserted})
  if n%100==0:print('AERIALTRACK_COREML_PROGRESS',n,'/',len(test),flush=True)
 precision=tp/max(1,tp+fp);recall=tp/max(1,tp+fn);specificity=tn/max(1,tn+fp);conf={}
 for label,total in neg.items():conf[label]={'negative_samples':int(total),'unique_source_groups':len(negg[label]),'false_positives':int(negfp[label]),'specificity':1-negfp[label]/max(1,total),'false_positive_source_groups':len(negfpg[label]),'source_group_specificity':1-len(negfpg[label])/max(1,len(negg[label]))}
 blockers=[]
 if precision<.90:blockers.append('precision < .90')
 if recall<.80:blockers.append('recall < .80')
 if specificity<.95:blockers.append('specificity < .95')
 bal=conf.get('BALLOON',{})
 if int(bal.get('unique_source_groups',0))<30:blockers.append('balloon groups < 30')
 if float(bal.get('specificity',0))<.95:blockers.append('balloon specificity < .95')
 if float(bal.get('source_group_specificity',0))<.95:blockers.append('balloon group specificity < .95')
 report={'schema_version':1,'model_sha256':sha(a.model),'architecture':__import__('platform').machine(),'items':len(test),'threshold':threshold,'metrics':{'drone_precision':precision,'drone_recall':recall,'negative_specificity':specificity},'confusion_counts':{'tp':tp,'fp':fp,'fn':fn,'tn':tn},'counts':dict(counts),'source_group_counts':{k:len(v) for k,v in groups.items()},'confounders':conf,'latency_ms':{'median':statistics.median(lat),'p95':percentile(lat,.95),'max':max(lat),'samples':len(lat)},'quality_pass':not blockers,'quality_blockers':blockers,'classifier_probability_contract_verified':True}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps({'report':report,'predictions':preds},indent=2,sort_keys=True)+'\n');print(json.dumps(report,indent=2,sort_keys=True));print('AERIALTRACK_COREML_RUNTIME_AND_HELDOUT_GATE', 'PASS' if not blockers else 'FAIL');raise SystemExit(0 if not blockers else 2)
if __name__=='__main__':main()
