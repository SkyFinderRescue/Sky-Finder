#!/usr/bin/env python3
"""Parallel validation-only ResNet18 five-way candidate; production score collapses to DRONE/NON_DRONE."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json
from pathlib import Path
import numpy as np,torch
from torch import nn
from torch.utils.data import DataLoader,WeightedRandomSampler
from torchvision import models
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);assert s.loader is not None;s.loader.exec_module(m);return m
multi=load('multi',ROOT/'aerialtrack_alt'/'train_multiclass.py');base=multi.base;prov=multi.prov;CLASSES=multi.CLASSES;IDX=multi.IDX
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
def build():
 m=models.resnet18(weights=None);m.fc=nn.Linear(m.fc.in_features,len(CLASSES));return m
def collect(m,l,d):return multi.collect(m,l,d)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--corpus',required=True,type=Path);ap.add_argument('--data-root',required=True,type=Path);ap.add_argument('--out-dir',required=True,type=Path);ap.add_argument('--epochs',type=int,default=28);ap.add_argument('--batch-size',type=int,default=64);ap.add_argument('--seed',type=int,default=20260730);a=ap.parse_args();base.seed_everything(a.seed);reg=prov.read_json(prov.DEFAULT_SOURCES);corp=prov.read_json(a.corpus);fail=prov.validate_source_registry(reg)+prov.validate_corpus(corp,reg,verify_local_files=False,root=a.data_root)+prov.validate_local_items(corp,splits={'train','validation'},root=a.data_root)
 if fail:raise SystemExit('corpus refused:\n- '+'\n- '.join(fail))
 sp=base.split_items(corp);tr=multi.DS(sp['train'],a.data_root,True);va=multi.DS(sp['validation'],a.data_root,False);ys=np.array([IDX[str(r['label']).upper()] for r in sp['train']]);cnt=np.bincount(ys,minlength=len(CLASSES)).astype(float);w=np.array([1/max(1,cnt[y]) for y in ys]);sam=WeightedRandomSampler(torch.tensor(w,dtype=torch.double),len(w),replacement=True,generator=torch.Generator().manual_seed(a.seed));tl=DataLoader(tr,batch_size=a.batch_size,sampler=sam,num_workers=2);vl=DataLoader(va,batch_size=128,shuffle=False,num_workers=2);dev=torch.device('cpu');m=build();lossfn=nn.CrossEntropyLoss(label_smoothing=.02);opt=torch.optim.AdamW(m.parameters(),lr=8e-4,weight_decay=3e-4);sch=torch.optim.lr_scheduler.CosineAnnealingLR(opt,T_max=a.epochs);best=None;bestsc=-1e9;hist=[]
 for e in range(a.epochs):
  m.train();ls=0.;seen=0
  for x,y,_ in tl:
   opt.zero_grad(set_to_none=True);loss=lossfn(m(x),y);loss.backward();opt.step();ls+=float(loss.detach())*len(y);seen+=len(y)
  sch.step();lg,ly,_=collect(m,vl,dev);t=multi.threshold(lg,ly);met=multi.binary_metrics(lg,ly,t);sc=multi.score(met);row={'epoch':e+1,'train_loss':ls/max(1,seen),'threshold':t,**{f'val_{k}':v for k,v in met.items() if k!='confusion_counts'}};hist.append(row);print(json.dumps(row),flush=True)
  if sc>bestsc:bestsc=sc;best={k:v.detach().cpu().clone() for k,v in m.state_dict().items()}
 m.load_state_dict(best);lg,ly,ids=collect(m,vl,dev);t=multi.threshold(lg,ly);met=multi.binary_metrics(lg,ly,t);a.out_dir.mkdir(parents=True,exist_ok=True);state=a.out_dir/'candidate_state.pt';csha=sha(a.corpus);payload={'state_dict':best,'architecture':'torchvision_resnet18_5way_collapse','architecture_license':'BSD-3-Clause','pretrained_weights':None,'internal_classes':CLASSES,'production_classes':['DRONE','NON_DRONE'],'image_size':base.IMAGE_SIZE,'context_fraction':base.CONTEXT_FRACTION,'corpus_manifest_sha256':csha,'frozen_drone_margin_threshold':t,'validation_ids_sha256':hashlib.sha256('\n'.join(ids).encode()).hexdigest(),'final_test_used_for_checkpoint_or_threshold_selection':False,'selection_process_loaded_final_test_media':False,'local_media_splits_verified_by_selection_process':['train','validation']};torch.save(payload,state);sel={'schema_version':2,'candidate_id':'resnet18_5way_collapse','architecture':payload['architecture'],'pretrained_weights':None,'corpus_manifest_sha256':csha,'candidate_state_sha256':sha(state),'checkpoint_selected_on_validation_only':True,'threshold_frozen_before_final_eval':True,'drone_margin_threshold':t,'validation_metrics':met,'training_history':hist,'final_test_used_for_checkpoint_or_threshold_selection':False,'selection_process_loaded_final_test_media':False,'local_media_splits_verified_by_selection_process':['train','validation']};(a.out_dir/'selection_report.json').write_text(json.dumps(sel,indent=2)+'\n');print(json.dumps(sel,indent=2));print('AERIALTRACK_RESNET_SELECTION_FROZEN')
if __name__=='__main__':main()
