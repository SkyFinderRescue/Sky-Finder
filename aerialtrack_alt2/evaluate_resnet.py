#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,importlib.util,json
from pathlib import Path
import torch
from torch.utils.data import DataLoader
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);assert s.loader is not None;s.loader.exec_module(m);return m
train=load('resnet_train',ROOT/'aerialtrack_alt2'/'train_resnet_multiclass.py');multi=train.multi;prov=multi.prov;ev=load('ev',ROOT/'aerialtrack_compute'/'research'/'reuse_first'/'evaluate_predictions.py')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--corpus',required=True,type=Path);ap.add_argument('--data-root',required=True,type=Path);ap.add_argument('--candidate-state',required=True,type=Path);ap.add_argument('--selection-report',required=True,type=Path);ap.add_argument('--out-dir',required=True,type=Path);a=ap.parse_args();corp=prov.read_json(a.corpus);reg=prov.read_json(prov.DEFAULT_SOURCES);fail=prov.validate_source_registry(reg)+prov.validate_corpus(corp,reg,verify_local_files=False,root=a.data_root)
 if fail:raise SystemExit('metadata refused:\n- '+'\n- '.join(fail))
 sel=json.loads(a.selection_report.read_text());csha=sha(a.corpus);ssha=sha(a.candidate_state)
 if sel.get('corpus_manifest_sha256')!=csha or sel.get('candidate_state_sha256')!=ssha or sel.get('threshold_frozen_before_final_eval') is not True or sel.get('checkpoint_selected_on_validation_only') is not True or sel.get('final_test_used_for_checkpoint_or_threshold_selection') is not False:raise SystemExit('freeze proof invalid')
 fail=prov.validate_local_items(corp,splits={'test'},root=a.data_root)
 if fail:raise SystemExit('test media refused:\n- '+'\n- '.join(fail))
 payload=torch.load(a.candidate_state,map_location='cpu',weights_only=False);t=float(payload['frozen_drone_margin_threshold']);m=train.build().eval();m.load_state_dict(payload['state_dict'],strict=True);items=[r for r in corp['items'] if r['split']=='test'];ds=multi.DS(items,a.data_root,False);loader=DataLoader(ds,batch_size=128,shuffle=False,num_workers=2);lg,_,ids=train.collect(m,loader,torch.device('cpu'));probs=torch.softmax(lg,1);pd=probs[:,multi.IDX['DRONE']];margin=(pd-(1-pd)).numpy().tolist();pred={'schema_version':2,'candidate_id':sel['candidate_id'],'candidate_state_sha256':ssha,'corpus_manifest_sha256':csha,'threshold_frozen_before_eval':True,'checkpoint_selected_on_validation_only':True,'final_test_used_for_checkpoint_or_threshold_selection':False,'selection_process_loaded_final_test_media':False,'final_test_local_files_verified_after_freeze':True,'score_kind':'drone_margin','threshold':t,'predictions':[{'id':i,'drone_margin':float(x),'prob_drone':float(y)} for i,x,y in zip(ids,margin,pd.numpy().tolist())]};bench=ev.evaluate(corp,pred);bench.update({'candidate_state_sha256':ssha,'corpus_manifest_sha256':csha,'frozen_drone_margin_threshold':t,'checkpoint_selected_on_validation_only':True,'final_test_used_for_checkpoint_or_threshold_selection':False,'selection_process_loaded_final_test_media':False,'final_test_local_files_verified_after_freeze':True});a.out_dir.mkdir(parents=True,exist_ok=True);(a.out_dir/'final_test_predictions.json').write_text(json.dumps(pred,indent=2)+'\n');(a.out_dir/'final_test_benchmark.json').write_text(json.dumps(bench,indent=2,sort_keys=True)+'\n');print(json.dumps(bench,indent=2,sort_keys=True));print('AERIALTRACK_RESNET_FINAL_TEST_COMPLETE');raise SystemExit(0 if bench['quality_pass'] else 2)
if __name__=='__main__':main()
