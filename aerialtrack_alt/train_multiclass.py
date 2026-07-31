#!/usr/bin/env python3
"""Validation-selected 5-way MobileNetV3-Small semantic learner.

The model learns DRONE/BIRD/AIRPLANE/HELICOPTER/BALLOON as separate visual classes,
then collapses the softmax into the production binary DRONE vs NON_DRONE contract.
Checkpoint and binary margin threshold are selected using validation sources only.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,random
from pathlib import Path
import numpy as np, torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader,Dataset,WeightedRandomSampler
from torchvision import models
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);assert s.loader is not None;s.loader.exec_module(m);return m
base=load('base',ROOT/'aerialtrack_compute'/'training'/'train_mobilenetv3_crop.py');prov=load('prov',ROOT/'aerialtrack_compute'/'research'/'reuse_first'/'validate_training_provenance.py')
CLASSES=['DRONE','BIRD','AIRPLANE','HELICOPTER','BALLOON'];IDX={v:i for i,v in enumerate(CLASSES)}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
class DS(Dataset):
 def __init__(self,items,root,train):self.items=items;self.root=root;self.tf=base.train_transform() if train else base.eval_transform()
 def __len__(self):return len(self.items)
 def __getitem__(self,i):
  r=self.items[i];label=str(r['label']).upper()
  if label not in IDX:raise ValueError(f'unsupported label {label}')
  with Image.open((self.root/r['path']).resolve()) as im:
   im=im.convert('RGB');crop=im.crop(base.padded_bbox(r.get('bbox'),im.width,im.height));x=self.tf(crop)
  return x,IDX[label],str(r['id'])
def build():
 m=models.mobilenet_v3_small(weights=None);m.classifier[-1]=nn.Linear(m.classifier[-1].in_features,len(CLASSES));return m
def collect(m,loader,dev):
 L=[];Y=[];I=[];m.eval()
 with torch.inference_mode():
  for x,y,ids in loader:L.append(m(x.to(dev)).cpu());Y.append(y.cpu());I.extend(map(str,ids))
 return torch.cat(L),torch.cat(Y),I
def binary_metrics(logits,y,t):
 probs=torch.softmax(logits,1).numpy();truth=y.numpy()==IDX['DRONE'];p=probs[:,IDX['DRONE']];margin=p-(1-p);pred=margin>=float(t);tp=int(np.sum(pred&truth));fp=int(np.sum(pred&~truth));fn=int(np.sum(~pred&truth));tn=int(np.sum(~pred&~truth));pr=tp/max(1,tp+fp);re=tp/max(1,tp+fn);sp=tn/max(1,tn+fp);return {'drone_precision':pr,'drone_recall':re,'negative_specificity':sp,'drone_f1':2*pr*re/max(1e-12,pr+re),'binary_accuracy':(tp+tn)/max(1,len(truth)),'confusion_counts':{'tp':tp,'fp':fp,'fn':fn,'tn':tn}}
def threshold(logits,y):
 passing=[];precision=[];fallback=[]
 for t in np.arange(-.2,.981,.005):
  t=float(t);m=binary_metrics(logits,y,t);p,r,s,f=m['drone_precision'],m['drone_recall'],m['negative_specificity'],m['drone_f1'];fallback.append((f,r,p,s,-abs(t),t))
  if p>=.90:
   precision.append((r,s,p,-abs(t),t))
   if r>=.80 and s>=.95:passing.append((r,s,p,-abs(t),t))
 return max(passing)[-1] if passing else max(precision)[-1] if precision else max(fallback)[-1]
def score(m):
 p,r,s,f=m['drone_precision'],m['drone_recall'],m['negative_specificity'],m['drone_f1']
 if p>=.90 and r>=.80 and s>=.95:return 1000+r+.2*p+.05*s
 if p>=.90:return 100+r+.2*p+.05*s
 return f+.05*s
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--corpus',required=True,type=Path);ap.add_argument('--data-root',required=True,type=Path);ap.add_argument('--out-dir',required=True,type=Path);ap.add_argument('--epochs',type=int,default=36);ap.add_argument('--batch-size',type=int,default=64);ap.add_argument('--seed',type=int,default=1337);a=ap.parse_args();base.seed_everything(a.seed);reg=prov.read_json(prov.DEFAULT_SOURCES);corp=prov.read_json(a.corpus);fail=prov.validate_source_registry(reg)+prov.validate_corpus(corp,reg,verify_local_files=False,root=a.data_root)+prov.validate_local_items(corp,splits={'train','validation'},root=a.data_root)
 if fail:raise SystemExit('corpus refused:\n- '+'\n- '.join(fail))
 sp=base.split_items(corp);tr=DS(sp['train'],a.data_root,True);va=DS(sp['validation'],a.data_root,False);ys=np.array([IDX[str(r['label']).upper()] for r in sp['train']]);cnt=np.bincount(ys,minlength=len(CLASSES)).astype(float);weights=np.array([1/max(1,cnt[y]) for y in ys]);sam=WeightedRandomSampler(torch.tensor(weights,dtype=torch.double),len(weights),replacement=True,generator=torch.Generator().manual_seed(a.seed));tl=DataLoader(tr,batch_size=a.batch_size,sampler=sam,num_workers=2);vl=DataLoader(va,batch_size=128,shuffle=False,num_workers=2);dev=torch.device('cpu');m=build().to(dev);lossfn=nn.CrossEntropyLoss(label_smoothing=.02);opt=torch.optim.AdamW(m.parameters(),lr=1e-3,weight_decay=2e-4);sch=torch.optim.lr_scheduler.CosineAnnealingLR(opt,T_max=a.epochs);best=None;bestscore=-1e9;hist=[]
 for e in range(a.epochs):
  m.train();ls=0.;seen=0
  for x,y,_ in tl:
   opt.zero_grad(set_to_none=True);loss=lossfn(m(x.to(dev)),y.to(dev));loss.backward();opt.step();ls+=float(loss.detach())*len(y);seen+=len(y)
  sch.step();lg,ly,_=collect(m,vl,dev);t=threshold(lg,ly);met=binary_metrics(lg,ly,t);sc=score(met);row={'epoch':e+1,'train_loss':ls/max(1,seen),'threshold':t,**{f'val_{k}':v for k,v in met.items() if k!='confusion_counts'}};hist.append(row);print(json.dumps(row),flush=True)
  if sc>bestscore:bestscore=sc;best={k:v.detach().cpu().clone() for k,v in m.state_dict().items()}
 if best is None:raise RuntimeError('no candidate')
 m.load_state_dict(best);lg,ly,ids=collect(m,vl,dev);t=threshold(lg,ly);met=binary_metrics(lg,ly,t);a.out_dir.mkdir(parents=True,exist_ok=True);state=a.out_dir/'candidate_state.pt';csha=sha(a.corpus);payload={'state_dict':best,'architecture':'torchvision_mobilenet_v3_small_5way_collapse','architecture_license':'BSD-3-Clause','pretrained_weights':None,'internal_classes':CLASSES,'production_classes':['DRONE','NON_DRONE'],'image_size':base.IMAGE_SIZE,'context_fraction':base.CONTEXT_FRACTION,'corpus_manifest_sha256':csha,'frozen_drone_margin_threshold':t,'validation_ids_sha256':hashlib.sha256('\n'.join(ids).encode()).hexdigest(),'final_test_used_for_checkpoint_or_threshold_selection':False,'selection_process_loaded_final_test_media':False,'local_media_splits_verified_by_selection_process':['train','validation']};torch.save(payload,state);sel={'schema_version':2,'candidate_id':'mobilenetv3_small_5way_collapse','architecture':payload['architecture'],'pretrained_weights':None,'corpus_manifest_sha256':csha,'candidate_state_sha256':sha(state),'checkpoint_selected_on_validation_only':True,'threshold_frozen_before_final_eval':True,'drone_margin_threshold':t,'validation_metrics':met,'training_history':hist,'final_test_used_for_checkpoint_or_threshold_selection':False,'selection_process_loaded_final_test_media':False,'local_media_splits_verified_by_selection_process':['train','validation']};(a.out_dir/'selection_report.json').write_text(json.dumps(sel,indent=2)+'\n');print(json.dumps(sel,indent=2));print('AERIALTRACK_MULTICLASS_SELECTION_FROZEN')
if __name__=='__main__':main()
