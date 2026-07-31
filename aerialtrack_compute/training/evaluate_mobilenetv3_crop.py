#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,importlib.util,json
from pathlib import Path
import torch
from torch.utils.data import DataLoader
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=load("base",ROOT/"training"/"train_mobilenetv3_crop.py");prov=load("prov",ROOT/"research"/"reuse_first"/"validate_training_provenance.py");ev=load("ev",ROOT/"research"/"reuse_first"/"evaluate_predictions.py")
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--corpus",required=True,type=Path);p.add_argument("--data-root",required=True,type=Path);p.add_argument("--candidate-state",required=True,type=Path);p.add_argument("--selection-report",required=True,type=Path);p.add_argument("--out-dir",required=True,type=Path);a=p.parse_args();reg=prov.read_json(prov.DEFAULT_SOURCES);corp=prov.read_json(a.corpus);fail=prov.validate_source_registry(reg)+prov.validate_corpus(corp,reg,verify_local_files=False,root=a.data_root)
 if fail:raise SystemExit("held-out metadata refused:\n- "+"\n- ".join(fail))
 sel=json.loads(a.selection_report.read_text());csha=digest(a.corpus);ssha=digest(a.candidate_state)
 assert sel["corpus_manifest_sha256"]==csha and sel["candidate_state_sha256"]==ssha and sel["threshold_frozen_before_final_eval"] is True and sel["checkpoint_selected_on_validation_only"] is True and sel["final_test_used_for_checkpoint_or_threshold_selection"] is False and sel["selection_process_loaded_final_test_media"] is False
 payload=torch.load(a.candidate_state,map_location="cpu",weights_only=False);assert payload["architecture"]=="torchvision_mobilenet_v3_small" and payload["pretrained_weights"] is None and payload["corpus_manifest_sha256"]==csha and payload["final_test_used_for_checkpoint_or_threshold_selection"] is False
 t=float(payload["frozen_drone_margin_threshold"]);assert abs(t-float(sel["drone_margin_threshold"]))<=1e-12
 fail=prov.validate_local_items(corp,splits={"test"},root=a.data_root)
 if fail:raise SystemExit("held-out media refused:\n- "+"\n- ".join(fail))
 items=[r for r in corp["items"] if r["split"]=="test"];ds=base.CropDataset(items,a.data_root,False);loader=DataLoader(ds,batch_size=128,shuffle=False,num_workers=2);m=base.build_model().eval();m.load_state_dict(payload["state_dict"],strict=True);logits,_,ids=base.collect(m,loader,torch.device("cpu"));probs=torch.softmax(logits,dim=1);margins=(probs[:,0]-probs[:,1]).numpy().tolist();dp=probs[:,0].numpy().tolist();pred={"schema_version":2,"candidate_id":sel["candidate_id"],"candidate_state_sha256":ssha,"corpus_manifest_sha256":csha,"threshold_frozen_before_eval":True,"checkpoint_selected_on_validation_only":True,"final_test_used_for_checkpoint_or_threshold_selection":False,"selection_process_loaded_final_test_media":False,"final_test_local_files_verified_after_freeze":True,"score_kind":"drone_margin","threshold":t,"predictions":[{"id":str(i),"drone_margin":float(x),"prob_drone":float(y)} for i,x,y in zip(ids,margins,dp)]};bench=ev.evaluate(corp,pred);bench.update({"candidate_state_sha256":ssha,"corpus_manifest_sha256":csha,"frozen_drone_margin_threshold":t,"checkpoint_selected_on_validation_only":True,"final_test_used_for_checkpoint_or_threshold_selection":False,"selection_process_loaded_final_test_media":False,"final_test_local_files_verified_after_freeze":True});a.out_dir.mkdir(parents=True,exist_ok=True);(a.out_dir/"final_test_predictions.json").write_text(json.dumps(pred,indent=2)+"\n");(a.out_dir/"final_test_benchmark.json").write_text(json.dumps(bench,indent=2,sort_keys=True)+"\n");print(json.dumps(bench,indent=2));print("AERIALTRACK_MOBILENET_FINAL_TEST_COMPLETE");raise SystemExit(0 if bench["quality_pass"] else 2)
if __name__=="__main__":main()
