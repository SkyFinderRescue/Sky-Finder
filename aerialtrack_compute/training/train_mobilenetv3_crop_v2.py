#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,importlib.util,json
from pathlib import Path
import numpy as np,torch
from torch import nn
from torch.utils.data import DataLoader,WeightedRandomSampler
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=load("base",ROOT/"training"/"train_mobilenetv3_crop.py");prov=load("prov",ROOT/"research"/"reuse_first"/"validate_training_provenance.py")
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--corpus",required=True,type=Path);p.add_argument("--data-root",required=True,type=Path);p.add_argument("--out-dir",required=True,type=Path);p.add_argument("--epochs",type=int,default=24);p.add_argument("--batch-size",type=int,default=64);p.add_argument("--seed",type=int,default=1337);a=p.parse_args();base.seed_everything(a.seed)
 reg=prov.read_json(prov.DEFAULT_SOURCES);corp=prov.read_json(a.corpus);fail=prov.validate_source_registry(reg)+prov.validate_corpus(corp,reg,verify_local_files=False,root=a.data_root)+prov.validate_local_items(corp,splits={"train","validation"},root=a.data_root)
 if fail:raise SystemExit("training corpus refused:\n- "+"\n- ".join(fail))
 sp=base.split_items(corp);tr=base.CropDataset(sp["train"],a.data_root,True);va=base.CropDataset(sp["validation"],a.data_root,False);ys=np.array([base.label_index(i["label"]) for i in sp["train"]]);cnt=np.bincount(ys,minlength=2).astype(float);w=np.array([1/max(1,cnt[y]) for y in ys]);sam=WeightedRandomSampler(torch.as_tensor(w,dtype=torch.double),len(w),replacement=True,generator=torch.Generator().manual_seed(a.seed));dev=torch.device("cpu");tl=DataLoader(tr,batch_size=a.batch_size,sampler=sam,num_workers=2);vl=DataLoader(va,batch_size=max(a.batch_size,128),shuffle=False,num_workers=2);m=base.build_model().to(dev);lossfn=nn.CrossEntropyLoss(label_smoothing=.02);opt=torch.optim.AdamW(m.parameters(),lr=1.5e-3,weight_decay=2e-4);sch=torch.optim.lr_scheduler.CosineAnnealingLR(opt,T_max=a.epochs);best=None;score=-1e9;hist=[]
 for e in range(a.epochs):
  m.train();ls=0.;seen=0
  for x,y,_ in tl:
   x,y=x.to(dev),y.to(dev);opt.zero_grad(set_to_none=True);loss=lossfn(m(x),y);loss.backward();opt.step();ls+=float(loss.detach())*len(y);seen+=len(y)
  sch.step();lg,ly,_=base.collect(m,vl,dev);t=base.choose_threshold(lg,ly);met=base.metrics_from(lg,ly,t);sc=base.checkpoint_score(met);row={"epoch":e+1,"train_loss":ls/max(1,seen),"threshold":t,"val_drone_precision":met["drone_precision"],"val_drone_recall":met["drone_recall"],"val_negative_specificity":met["negative_specificity"],"val_drone_f1":met["drone_f1"]};hist.append(row);print(json.dumps(row),flush=True)
  if sc>score:score=sc;best={k:v.detach().cpu().clone() for k,v in m.state_dict().items()}
 if best is None:raise RuntimeError("no candidate")
 m.load_state_dict(best);m.eval();lg,ly,ids=base.collect(m,vl,dev);t=base.choose_threshold(lg,ly);met=base.metrics_from(lg,ly,t);a.out_dir.mkdir(parents=True,exist_ok=True);state=a.out_dir/"candidate_state.pt";csha=digest(a.corpus);payload={"state_dict":best,"architecture":"torchvision_mobilenet_v3_small","architecture_license":"BSD-3-Clause","pretrained_weights":None,"classes":base.CLASSES,"image_size":base.IMAGE_SIZE,"context_fraction":base.CONTEXT_FRACTION,"normalization":{"scale":1/127.5,"bias":[-1,-1,-1]},"seed":a.seed,"corpus_manifest_sha256":csha,"validation_ids_sha256":hashlib.sha256("\n".join(ids).encode()).hexdigest(),"frozen_drone_margin_threshold":t,"local_media_splits_verified_by_selection_process":["train","validation"],"final_test_used_for_checkpoint_or_threshold_selection":False,"selection_process_loaded_final_test_media":False};torch.save(payload,state);sel={"schema_version":1,"candidate_id":"mobilenetv3_small_clean_crop","architecture":payload["architecture"],"architecture_license":"BSD-3-Clause","pretrained_weights":None,"corpus_manifest_sha256":csha,"candidate_state_sha256":digest(state),"checkpoint_selected_on_validation_only":True,"threshold_frozen_before_final_eval":True,"drone_margin_threshold":t,"validation_metrics":met,"validation_ids_sha256":payload["validation_ids_sha256"],"training_history":hist,"local_media_splits_verified_by_selection_process":["train","validation"],"final_test_used_for_checkpoint_or_threshold_selection":False,"selection_process_loaded_final_test_media":False};(a.out_dir/"selection_report.json").write_text(json.dumps(sel,indent=2)+"\n");print(json.dumps(sel,indent=2));print("AERIALTRACK_MOBILENET_SELECTION_FROZEN_TEST_NOT_USED")
if __name__=="__main__":main()
