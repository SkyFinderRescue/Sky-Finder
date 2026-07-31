#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,tempfile,time,urllib.error,urllib.request
from collections import defaultdict
from pathlib import Path
import cv2
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);assert s.loader is not None;s.loader.exec_module(m);return m
mat=load('mat',ROOT/'aerialtrack_compute'/'training'/'materialize_cc0_manifest.py')
UA='AerialTrack-ReuseFirst/1.3 exact-manifest materializer'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
def open_retry(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA});last=None
 for n in range(8):
  try:return urllib.request.urlopen(req,timeout=90)
  except (urllib.error.HTTPError,urllib.error.URLError) as e:
   last=e
   if isinstance(e,urllib.error.HTTPError) and e.code not in (429,500,502,503,504):raise
   time.sleep(min(45,5*(n+1)))
 raise last
def download(url,dst):
 with open_retry(url) as r,dst.open('wb') as f:
  for c in iter(lambda:r.read(1024*1024),b''):f.write(c)
def cropbox(w,h,f):
 x0,y0,x1,y1=map(float,f);L=max(0,min(w-1,int(math.floor(x0*w))));T=max(0,min(h-1,int(math.floor(y0*h))));R=max(L+1,min(w,int(math.ceil(x1*w))));B=max(T+1,min(h,int(math.ceil(y1*h))));return L,T,R,B
def rebuild_cc0(items,cache,out):
 video_v=mat.ensure(cache);groups=defaultdict(list)
 for r in items:groups[r['source_group_id']].append(r)
 for gi,(g,rows) in enumerate(sorted(groups.items()),1):
  video=video_v/f'{g}.mp4'
  if not video.is_file():raise RuntimeError(f'missing source video {video}')
  cap=cv2.VideoCapture(str(video))
  if not cap.isOpened():raise RuntimeError(f'cannot open {video}')
  try:
   for r in sorted(rows,key=lambda x:int(x['source_frame_index'])):
    idx=int(r['source_frame_index']);cap.set(cv2.CAP_PROP_POS_FRAMES,idx);ok,frame=cap.read()
    if not ok or frame.size==0:raise RuntimeError(f'frame read {g}:{idx}')
    dest=out/r['path'];dest.parent.mkdir(parents=True,exist_ok=True)
    if not cv2.imwrite(str(dest),frame,[int(cv2.IMWRITE_JPEG_QUALITY),94]):raise RuntimeError('jpeg write')
    if sha(dest).lower()!=str(r['sha256']).lower():raise RuntimeError(f'CC0 checksum mismatch {r["id"]}')
  finally:cap.release()
  if gi%20==0:print('AERIALTRACK_REBUILD_CC0_GROUPS',gi,'/',len(groups),flush=True)
def rebuild_balloon(items,out):
 groups=defaultdict(list)
 for r in items:groups[r['source_group_id']].append(r)
 for gi,(g,rows) in enumerate(sorted(groups.items()),1):
  first=rows[0];url=first.get('source_media_url')
  if not url:raise RuntimeError(f'balloon media URL missing {g}')
  with tempfile.TemporaryDirectory() as td:
   raw=Path(td)/'raw';download(url,raw);raw_now=sha(raw).lower();raw_expected=str(first.get('source_download_sha256') or '').lower()
   if raw_expected and raw_now!=raw_expected:print('AERIALTRACK_BALLOON_TRANSPORT_BYTES_CHANGED_VERIFYING_DERIVATIVES',g,flush=True)
   with Image.open(raw) as im:rgb=ImageOps.exif_transpose(im).convert('RGB')
   w,h=rgb.size
   for r in rows:
    frac=r.get('crop_box_fraction')
    if not frac:raise RuntimeError(f'crop metadata missing {r["id"]}')
    dest=out/r['path'];dest.parent.mkdir(parents=True,exist_ok=True);rgb.crop(cropbox(w,h,frac)).save(dest,'JPEG',quality=94)
    actual=sha(dest).lower();expected=str(r['sha256']).lower()
    if actual!=expected:raise RuntimeError(f'balloon derived checksum mismatch {r["id"]}: {actual} != {expected}')
  if gi%10==0:print('AERIALTRACK_REBUILD_BALLOON_GROUPS',gi,'/',len(groups),flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--cache',required=True,type=Path);p.add_argument('--out-root',required=True,type=Path);a=p.parse_args();m=json.loads(a.manifest.read_text());items=m.get('items') or [];cc=[r for r in items if r.get('source_id')=='drone_detection_thesis_cc0'];bb=[r for r in items if r.get('source_id')=='wikimedia_vetted'];rebuild_cc0(cc,a.cache,a.out_root);rebuild_balloon(bb,a.out_root);print('AERIALTRACK_EXACT_MANIFEST_MEDIA_REBUILT',len(cc),len(bb))
if __name__=='__main__':main()
