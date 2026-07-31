#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,sys
from pathlib import Path
import torch
from torch import nn
ROOT=Path(__file__).resolve().parents[1]
TRAIN=ROOT/'aerialtrack_compute'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);assert s.loader is not None;s.loader.exec_module(m);return m
base=load('aerialtrack_mobilenet_base',TRAIN/'training'/'train_mobilenetv3_crop.py')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
def finite(v,name):
 if isinstance(v,bool):raise SystemExit(f'invalid {name}')
 x=float(v)
 if not math.isfinite(x):raise SystemExit(f'invalid {name}')
 return x
class ProbabilityClassifier(nn.Module):
 def __init__(self,m):super().__init__();self.m=m
 def forward(self,x):return torch.softmax(self.m(x),dim=1)
def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate-state',required=True,type=Path);p.add_argument('--selection-report',required=True,type=Path);p.add_argument('--benchmark',required=True,type=Path);p.add_argument('--corpus',required=True,type=Path);p.add_argument('--out-dir',required=True,type=Path);a=p.parse_args()
 sel=json.loads(a.selection_report.read_text());bench=json.loads(a.benchmark.read_text());corp=json.loads(a.corpus.read_text());csha=sha(a.corpus);ssha=sha(a.candidate_state)
 if sel.get('corpus_manifest_sha256')!=csha or sel.get('candidate_state_sha256')!=ssha:raise SystemExit('selection hash mismatch')
 if bench.get('corpus_manifest_sha256')!=csha or bench.get('candidate_state_sha256')!=ssha:raise SystemExit('benchmark hash mismatch')
 if bench.get('quality_pass') is not True or bench.get('quality_blockers') not in ([],None):raise SystemExit('heldout quality gate did not pass')
 if sel.get('checkpoint_selected_on_validation_only') is not True or sel.get('threshold_frozen_before_final_eval') is not True:raise SystemExit('selection freeze proof missing')
 if sel.get('final_test_used_for_checkpoint_or_threshold_selection') is not False or sel.get('selection_process_loaded_final_test_media') is not False:raise SystemExit('final-test selection boundary violated')
 if bench.get('final_test_used_for_checkpoint_or_threshold_selection') is not False or bench.get('selection_process_loaded_final_test_media') is not False or bench.get('final_test_local_files_verified_after_freeze') is not True:raise SystemExit('benchmark heldout boundary invalid')
 payload=torch.load(a.candidate_state,map_location='cpu',weights_only=False)
 if payload.get('architecture')!='torchvision_mobilenet_v3_small' or payload.get('pretrained_weights') is not None:raise SystemExit('candidate provenance mismatch')
 t=finite(payload.get('frozen_drone_margin_threshold'),'threshold')
 if abs(t-finite(sel.get('drone_margin_threshold'),'selection threshold'))>1e-12 or abs(t-finite(bench.get('threshold'),'benchmark threshold'))>1e-12:raise SystemExit('threshold mismatch')
 licenses=sorted({str(r.get('license')) for r in corp.get('items',[]) if r.get('license')})
 if not set(licenses)<={'CC0-1.0','Public-Domain','CC-BY-4.0'}:raise SystemExit(f'unsafe license inventory {licenses}')
 if not corp.get('primary_dataset') or corp['primary_dataset'].get('license')!='CC0-1.0':raise SystemExit('primary CC0 provenance missing')
 if not any(isinstance(r,dict) and r.get('source_id')=='wikimedia_vetted' and r.get('per_file_source_credit_license_checksum_required') is True for r in corp.get('supplemental_sources',[])):raise SystemExit('balloon per-file provenance missing')
 try:import coremltools as ct
 except Exception as e:raise SystemExit(f'coremltools unavailable: {e}')
 model=base.build_model().cpu().eval();model.load_state_dict(payload['state_dict'],strict=True);wrapped=ProbabilityClassifier(model).eval();example=torch.zeros(1,3,base.IMAGE_SIZE,base.IMAGE_SIZE);traced=torch.jit.trace(wrapped,example)
 converted=ct.convert(traced,convert_to='neuralnetwork',inputs=[ct.ImageType(name='image',shape=example.shape,scale=1.0/127.5,bias=[-1.,-1.,-1.],color_layout=ct.colorlayout.RGB)],classifier_config=ct.ClassifierConfig(base.CLASSES))
 a.out_dir.mkdir(parents=True,exist_ok=True);out=a.out_dir/'AerialSemantic.mlmodel';converted.author='AerialTrack';converted.license='AerialTrack-approved rights-cleared training corpus; MobileNetV3-Small architecture via Torchvision BSD-3-Clause.';converted.save(str(out));msha=sha(out)
 policy={'schema_version':1,'promoted':False,'candidate_labels':['DRONE'],'drone_margin_threshold':t,'model_sha256':msha,'candidate_state_sha256':ssha,'corpus_manifest_sha256':csha,'primary_dataset_license':'CC0-1.0','source_licenses':licenses,'heldout_quality':bench.get('metrics'),'balloon_quality':bench.get('confounders',{}).get('BALLOON'),'heldout_boundary':{'checkpoint_selected_on_validation_only':True,'threshold_frozen_before_final_eval':True,'final_test_used_for_checkpoint_or_threshold_selection':False,'selection_process_loaded_final_test_media':False,'final_test_local_files_verified_after_freeze':True}}
 (a.out_dir/'AerialSemanticPolicy.json').write_text(json.dumps(policy,indent=2,sort_keys=True)+'\n');(a.out_dir/'candidate_package_manifest.json').write_text(json.dumps({'model_sha256':msha,'policy_sha256':sha(a.out_dir/'AerialSemanticPolicy.json'),'candidate_state_sha256':ssha,'corpus_manifest_sha256':csha,'threshold':t,'quality_pass':True,'promoted':False,'source_licenses':licenses},indent=2,sort_keys=True)+'\n');print('AERIALTRACK_COREML_CANDIDATE_PACKAGED_UNPROMOTED',msha)
if __name__=='__main__':main()
