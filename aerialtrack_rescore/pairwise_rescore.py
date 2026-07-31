#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,importlib.util,json
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np,torch
from torch.utils.data import DataLoader
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);assert s.loader is not None;s.loader.exec_module(m);return m
multi=load('multi',ROOT/'aerialtrack_alt'/'train_multiclass.py');prov=multi.prov
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
def verify(items,root):
 for r in items:
  p=(root/str(r['path'])).resolve()
  if not p.is_file():raise SystemExit(f'missing exact media {r["id"]}: {p}')
  if sha(p).lower()!=str(r['sha256']).lower():raise SystemExit(f'exact media checksum mismatch {r["id"]}')
def scores(logits):
 d=logits[:,multi.IDX['DRONE']];mask=[i for i in range(len(multi.CLASSES)) if i!=multi.IDX['DRONE']];n=logits[:,mask].max(dim=1).values;pair=torch.softmax(torch.stack([d,n],1),1);return (pair[:,0]-pair[:,1]).numpy(),pair[:,0].numpy()
def metrics(margin,labels,t):
 truth=np.asarray(labels)==multi.IDX['DRONE'];pred=np.asarray(margin)>=t;tp=int(np.sum(pred&truth));fp=int(np.sum(pred&~truth));fn=int(np.sum(~pred&truth));tn=int(np.sum(~pred&~truth));p=tp/max(1,tp+fp);r=tp/max(1,tp+fn);s=tn/max(1,tn+fp);return {'drone_precision':p,'drone_recall':r,'negative_specificity':s,'drone_f1':2*p*r/max(1e-12,p+r),'confusion_counts':{'tp':tp,'fp':fp,'fn':fn,'tn':tn}}
def choose(margin,labels):
 passing=[];precision=[];fallback=[]
 for t in np.arange(0,.991,.0025):
  t=float(t);m=metrics(margin,labels,t);p,r,s,f=m['drone_precision'],m['drone_recall'],m['negative_specificity'],m['drone_f1'];fallback.append((f,r,p,s,-t,t))
  if p>=.90:
   precision.append((r,s,p,-t,t))
   if r>=.80 and s>=.95:passing.append((r,s,p,-t,t))
 return max(passing)[-1] if passing else max(precision)[-1] if precision else max(fallback)[-1]
def run_split(model,items,root):
 ds=multi.DS(items,root,False);loader=DataLoader(ds,batch_size=128,shuffle=False,num_workers=2);lg,y,ids=multi.collect(model,loader,torch.device('cpu'));margin,p=scores(lg);return margin,p,y.numpy(),ids
def test_report(items,margin,labels,t):
 m=metrics(margin,labels,t);groups=defaultdict(set);counts=Counter();neg=Counter();negfp=Counter();negg=defaultdict(set);negfpg=defaultdict(set)
 for r,sc in zip(items,margin):
  label=str(r['label']).upper();g=(str(r.get('source_id') or ''),str(r.get('source_group_id') or ''));counts[label]+=1;groups[label].add(g)
  if label!='DRONE':neg[label]+=1;negg[label].add(g)
  if label!='DRONE' and sc>=t:negfp[label]+=1;negfpg[label].add(g)
 conf={l:{'negative_samples':int(neg[l]),'unique_source_groups':len(negg[l]),'false_positives':int(negfp[l]),'specificity':1-negfp[l]/max(1,neg[l]),'false_positive_source_groups':len(negfpg[l]),'source_group_specificity':1-len(negfpg[l])/max(1,len(negg[l]))} for l in neg};b=[]
 if m['drone_precision']<.90:b.append('precision')
 if m['drone_recall']<.80:b.append('recall')
 if m['negative_specificity']<.95:b.append('specificity')
 bal=conf.get('BALLOON',{})
 if len(groups.get('BALLOON',set()))<30:b.append('balloon groups')
 if float(bal.get('specificity',0))<.95:b.append('balloon specificity')
 if float(bal.get('source_group_specificity',0))<.95:b.append('balloon group specificity')
 return {'metrics':m,'counts':dict(counts),'source_group_counts':{k:len(v) for k,v in groups.items()},'confounders':conf,'quality_pass':not b,'quality_blockers':b}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--corpus',required=True,type=Path);ap.add_argument('--data-root',required=True,type=Path);ap.add_argument('--candidate-state',required=True,type=Path);ap.add_argument('--out-dir',required=True,type=Path);a=ap.parse_args();corp=json.loads(a.corpus.read_text());payload=torch.load(a.candidate_state,map_location='cpu',weights_only=False);model=multi.build().eval();model.load_state_dict(payload['state_dict'],strict=True)
 # Threshold selection is intentionally confined to exact CC0 validation sources. Balloon images remain an independent held-out confounder gate and are never used to choose the threshold.
 val=[r for r in corp['items'] if r['split']=='validation' and str(r['label']).upper()!='BALLOON'];test=[r for r in corp['items'] if r['split']=='test'];verify(val,a.data_root);vm,vp,vy,vids=run_split(model,val,a.data_root);t=choose(vm,vy);vmet=metrics(vm,vy,t);vg=vmet['drone_precision']>=.90 and vmet['drone_recall']>=.80 and vmet['negative_specificity']>=.95;print('AERIALTRACK_PAIRWISE_VALIDATION',json.dumps({'threshold':t,'validation_gate_pass':vg,**vmet},sort_keys=True),flush=True)
 a.out_dir.mkdir(parents=True,exist_ok=True);frozen=a.out_dir/'pairwise_candidate_state.pt';new=dict(payload);new['architecture']='torchvision_mobilenet_v3_small_5way_pairwise_collapse';new['production_scoring_contract']='binary_softmax(drone_logit,max(non_drone_logits))';new['frozen_drone_margin_threshold']=t;new['original_candidate_state_sha256']=sha(a.candidate_state);new['validation_ids_sha256']=hashlib.sha256('\n'.join(vids).encode()).hexdigest();new['validation_source_policy']='CC0 validation only; BALLOON reserved for independent final confounder gate';new['final_test_used_for_checkpoint_or_threshold_selection']=False;new['selection_process_loaded_final_test_media']=False;torch.save(new,frozen);selection={'schema_version':4,'candidate_id':'mobilenetv3_small_5way_pairwise_collapse','architecture':new['architecture'],'production_scoring_contract':new['production_scoring_contract'],'pretrained_weights':None,'corpus_manifest_sha256':sha(a.corpus),'candidate_state_sha256':sha(frozen),'original_candidate_state_sha256':sha(a.candidate_state),'checkpoint_selected_on_validation_only':True,'threshold_frozen_before_final_eval':True,'drone_margin_threshold':t,'validation_metrics':vmet,'validation_gate_pass':vg,'validation_source_policy':new['validation_source_policy'],'final_test_used_for_checkpoint_or_threshold_selection':False,'selection_process_loaded_final_test_media':False};(a.out_dir/'selection_report.json').write_text(json.dumps(selection,indent=2)+'\n')
 verify(test,a.data_root);tm,tp,ty,tids=run_split(model,test,a.data_root);report=test_report(test,tm,ty,t);report.update({'schema_version':6,'candidate_id':selection['candidate_id'],'threshold':t,'score_kind':'pairwise_drone_margin','threshold_frozen_before_eval':True,'checkpoint_selected_on_validation_only':True,'final_test_used_for_checkpoint_or_threshold_selection':False,'selection_process_loaded_final_test_media':False,'final_test_local_files_verified_after_freeze':True,'corpus_manifest_sha256':sha(a.corpus),'candidate_state_sha256':sha(frozen),'validation_gate_pass':vg,'validation_source_policy':new['validation_source_policy']});pred={'candidate_id':selection['candidate_id'],'threshold':t,'score_kind':'pairwise_drone_margin','threshold_frozen_before_eval':True,'predictions':[{'id':i,'drone_margin':float(s),'prob_drone':float(p)} for i,s,p in zip(tids,tm,tp)]};(a.out_dir/'final_test_benchmark.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');(a.out_dir/'final_test_predictions.json').write_text(json.dumps(pred,indent=2)+'\n');print(json.dumps(report,indent=2,sort_keys=True));ok=report['quality_pass'] and vg;print('AERIALTRACK_PAIRWISE_FINAL','PASS' if ok else 'FAIL');raise SystemExit(0 if ok else 2)
if __name__=='__main__':main()
