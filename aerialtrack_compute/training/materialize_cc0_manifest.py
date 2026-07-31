#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,random,urllib.request,zipfile
from collections import Counter
from pathlib import Path
import cv2,numpy as np
from mcos_decoder import load_groundtruth
SEED=1337; LICENSE="CC0-1.0"; RECORD="https://zenodo.org/records/5500576"; URL="https://zenodo.org/records/5500576/files/DroneDetectionThesis/Drone-detection-dataset-v1.0.0.zip?download=1"; MD5="5d9b891a87857b3d9ee8872e8a1f0f0f"
CLASSES=["DRONE","BIRD","AIRPLANE","HELICOPTER"]; FRAMES=24; MAX_TRAIN=64; VAL=10; TEST=14
def digest(p,algo="sha256"):
 h=hashlib.new(algo)
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()
def download(url,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists() and dst.stat().st_size>0:return
 req=urllib.request.Request(url,headers={"User-Agent":"AerialTrack-ReuseFirst/1.0"})
 with urllib.request.urlopen(req,timeout=300) as r,dst.open("wb") as o:
  while True:
   c=r.read(1024*1024)
   if not c:break
   o.write(c)
def ensure(cache):
 a=cache/"drone-detection-dataset-v1.0.0.zip"; download(URL,a)
 if digest(a,"md5")!=MD5: raise RuntimeError("dataset archive MD5 mismatch")
 e=cache/"dataset-v1.0.0"; marker=e/".complete"
 if not marker.exists():
  e.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(a) as z:z.extractall(e)
  marker.write_text(MD5)
 c=[p for p in e.rglob("Video_V") if p.is_dir() and p.parent.name=="Data"]
 if not c:raise RuntimeError("Data/Video_V not found")
 return c[0]
def bbox(v):
 if v is None:return None
 try:
  a=np.asarray(v).reshape(-1)
  if len(a)<4 or not np.isfinite(a[:4]).all() or a[2]<=0 or a[3]<=0:return None
  return [float(x) for x in a[:4]]
 except Exception:return None
def sequences(d):
 out={l:[] for l in CLASSES}
 for l in CLASSES:
  for v in sorted(d.glob(f"V_{l}_*.mp4")):
   lab=v.with_name(v.stem+"_LABELS.mat")
   if lab.is_file():out[l].append((v.stem,v,lab))
  if len(out[l])<VAL+TEST+1:raise RuntimeError(f"insufficient visible source sequences {l}:{len(out[l])}")
 return out
def split(by):
 rng=random.Random(SEED); out={"train":[],"validation":[],"test":[]}
 for l in CLASSES:
  rows=list(by[l]);rng.shuffle(rows);te=rows[:TEST];va=rows[TEST:TEST+VAL];tr=rows[TEST+VAL:TEST+VAL+MAX_TRAIN]
  for s,g in (("test",te),("validation",va),("train",tr)):out[s].extend((l,*r) for r in g)
 return out
def indices(boxes,n):
 p=[i for i,b in enumerate(boxes) if bbox(b) is not None]
 if len(p)<=n:return p
 return [p[i] for i in np.linspace(0,len(p)-1,n).astype(int)]
def materialize(s,l,g,v,lab,root):
 boxes=load_groundtruth(str(lab));cap=cv2.VideoCapture(str(v));total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));rows=[]
 if not cap.isOpened():raise RuntimeError(f"cannot open {v}")
 try:
  for i in [x for x in indices(boxes,FRAMES) if x<total]:
   b=bbox(boxes[i]);cap.set(cv2.CAP_PROP_POS_FRAMES,i);ok,frame=cap.read()
   if b is None or not ok or frame.size==0:continue
   rel=Path(s)/l/f"{g}_{i:06d}.jpg";dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True)
   if not cv2.imwrite(str(dest),frame,[int(cv2.IMWRITE_JPEG_QUALITY),94]):raise RuntimeError("write failed")
   rows.append({"id":f"{g}:{i}","source_id":"drone_detection_thesis_cc0","source_group_id":g,"split":s,"label":l,"source_url":RECORD,"license":LICENSE,"sha256":digest(dest),"path":str(rel),"bbox":b,"source_frame_index":i})
 finally:cap.release()
 return rows
def main():
 p=argparse.ArgumentParser();p.add_argument("--cache",required=True,type=Path);p.add_argument("--out-root",required=True,type=Path);p.add_argument("--manifest",required=True,type=Path);a=p.parse_args()
 d=ensure(a.cache);sp=split(sequences(d));items=[]
 for s in ("train","validation","test"):
  for l,g,v,lab in sp[s]:items.extend(materialize(s,l,g,v,lab,a.out_root))
 m={"schema_version":1,"dataset":"DroneDetectionThesis/Drone-detection-dataset","dataset_version":"v1.0.0","dataset_record":RECORD,"archive_md5":MD5,"license":LICENSE,"source_disjoint":True,"seed":SEED,"items":items}
 a.manifest.parent.mkdir(parents=True,exist_ok=True);a.manifest.write_text(json.dumps(m,indent=2)+"\n")
 c=Counter((r["split"],r["label"]) for r in items);print(json.dumps({"items":len(items),"counts":{f"{x}:{y}":n for (x,y),n in sorted(c.items())}},indent=2));print("AERIALTRACK_CC0_MANIFEST_MATERIALIZED_FULLFRAME")
if __name__=="__main__":main()
