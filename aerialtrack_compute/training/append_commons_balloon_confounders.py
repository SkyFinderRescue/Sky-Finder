#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,html,json,math,random,shutil,tempfile,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
from PIL import Image,ImageOps
API="https://commons.wikimedia.org/w/api.php";UA="AerialTrack-ReuseFirst/1.1 (https://github.com/SkyFinderRescue/Sky-Finder; rights-cleared model evaluation)";SEED=1337;Q=94
CATS=["Category:Hot air balloons","Category:Weather balloons","Category:Weather balloons in the United States"]
LM={"CC0":"CC0-1.0","Public domain":"Public-Domain","CC BY 4.0":"CC-BY-4.0"}
CROPS=(("full",(0,0,1,1)),("center60",(.2,.2,.8,.8)),("center35",(.325,.325,.675,.675)),("top_left65",(0,0,.65,.65)),("top_right65",(.35,0,1,.65)),("bottom_left65",(0,.35,.65,1)),("bottom_right65",(.35,.35,1,1)))
def open_retry(req,timeout=90):
 last=None
 for attempt in range(10):
  try:return urllib.request.urlopen(req,timeout=timeout)
  except urllib.error.HTTPError as e:
   last=e
   if e.code not in (429,500,502,503,504):raise
   wait=int(e.headers.get("Retry-After") or min(60,8*(attempt+1)));print("AERIALTRACK_HTTP_RETRY",e.code,wait,flush=True);time.sleep(wait)
  except urllib.error.URLError as e:
   last=e;wait=min(60,5*(attempt+1));print("AERIALTRACK_URL_RETRY",wait,flush=True);time.sleep(wait)
 raise last
def api(p):
 q=urllib.parse.urlencode({**p,"format":"json","formatversion":"2","maxlag":"5"});req=urllib.request.Request(f"{API}?{q}",headers={"User-Agent":UA,"Accept":"application/json"})
 with open_retry(req,60) as x:return json.load(x)
def rows(cat,limit):
 out=[];cont={}
 while len(out)<limit:
  pay=api({"action":"query","generator":"categorymembers","gcmtitle":cat,"gcmtype":"file","gcmlimit":"100","prop":"imageinfo","iiprop":"url|extmetadata|sha1|mime|size","iiurlwidth":"1280",**cont})
  for page in pay.get("query",{}).get("pages",[]):
   info=(page.get("imageinfo") or [{}])[0];meta=info.get("extmetadata") or {};mime=str(info.get("mime") or "").lower();lic=LM.get((meta.get("LicenseShortName") or {}).get("value",""))
   if not mime.startswith("image/") or not lic:continue
   source=info.get("descriptionurl");url=info.get("thumburl") or info.get("url");credit=((meta.get("Attribution") or {}).get("value") or (meta.get("Artist") or {}).get("value") or (meta.get("Credit") or {}).get("value"))
   if source and url and credit:out.append({"pageid":int(page["pageid"]),"source_page":source,"media_url":url,"commons_sha1":str(info.get("sha1") or ""),"license":lic,"credit":html.unescape(str(credit)),"source_category":cat,"source_mime":mime})
   if len(out)>=limit:break
  c=pay.get("continue")
  if not c:break
  cont={k:str(v) for k,v in c.items() if k!="continue"};time.sleep(2)
 return out
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
 return h.hexdigest()
def dl(url,p):
 req=urllib.request.Request(url,headers={"User-Agent":UA})
 with open_retry(req,90) as x,p.open("wb") as f:
  for c in iter(lambda:x.read(1024*1024),b""):f.write(c)
def box(w,h,f):
 x0,y0,x1,y1=f;L=max(0,min(w-1,int(math.floor(x0*w))));T=max(0,min(h-1,int(math.floor(y0*h))));R=max(L+1,min(w,int(math.ceil(x1*w))));B=max(T+1,min(h,int(math.ceil(y1*h))));return L,T,R,B
def views(row,split,root):
 page=root/"commons_balloon"/split/str(row["pageid"]);shutil.rmtree(page,ignore_errors=True)
 with tempfile.TemporaryDirectory() as td:
  raw=Path(td)/"source";dl(row["media_url"],raw);rawsha=sha(raw)
  with Image.open(raw) as im:rgb=ImageOps.exif_transpose(im).convert("RGB")
  w,h=rgb.size
  if w<64 or h<64:raise RuntimeError("image too small")
  out=[]
  for name,frac in CROPS:
   rel=Path("commons_balloon")/split/str(row["pageid"])/f"{name}.jpg";dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);rgb.crop(box(w,h,frac)).save(dest,"JPEG",quality=Q)
   out.append({"id":f"commons-balloon-{row['pageid']}-{name}","source_id":"wikimedia_vetted","source_group_id":f"commons-page-{row['pageid']}","split":split,"label":"BALLOON","source_url":row["source_page"],"source_media_url":row["media_url"],"license":row["license"],"credit":row["credit"],"sha256":sha(dest),"path":str(rel),"bbox":None,"source_category":row["source_category"],"source_mime":row["source_mime"],"commons_sha1":row["commons_sha1"],"source_download_sha256":rawsha,"derived_view":name,"crop_box_fraction":list(frac)})
  return out
def main():
 p=argparse.ArgumentParser();p.add_argument("--manifest",required=True,type=Path);p.add_argument("--data-root",required=True,type=Path);p.add_argument("--train",type=int,default=20);p.add_argument("--validation",type=int,default=10);p.add_argument("--test",type=int,default=30);a=p.parse_args();m=json.loads(a.manifest.read_text());need=a.train+a.validation+a.test
 cand=[]
 for cat in CATS:
  cand+=rows(cat,need)
  unique_now={r["pageid"] for r in cand}
  if len(unique_now)>=need*2:break
 unique={};seen=set()
 for r in cand:
  if r["pageid"] in unique or (r["commons_sha1"] and r["commons_sha1"] in seen):continue
  unique[r["pageid"]]=r
  if r["commons_sha1"]:seen.add(r["commons_sha1"])
 rr=list(unique.values());random.Random(SEED).shuffle(rr)
 if len(rr)<need:raise SystemExit(f"not enough allowlisted independent balloon pages: {len(rr)} < {need}")
 existing={str(i.get("source_group_id")) for i in m["items"]};cur=0;added=[]
 for split,n in (("train",a.train),("validation",a.validation),("test",a.test)):
  got=0
  while got<n and cur<len(rr):
   r=rr[cur];cur+=1;g=f"commons-page-{r['pageid']}"
   if g in existing:continue
   try:v=views(r,split,a.data_root)
   except Exception as e:print("AERIALTRACK_BALLOON_SOURCE_SKIPPED",r["source_page"],e,flush=True);continue
   m["items"]+=v;added+=v;existing.add(g);got+=1;time.sleep(.25)
  if got!=n:raise SystemExit(f"could not materialize {n} {split} pages got {got}")
 test=[i for i in m["items"] if i.get("split")=="test" and str(i.get("label")).upper()=="BALLOON"];groups={i["source_group_id"] for i in test}
 if len(groups)<30:raise SystemExit("balloon independent pages <30")
 m["primary_dataset"]={"dataset":m.get("dataset"),"dataset_version":m.get("dataset_version"),"dataset_record":m.get("dataset_record"),"archive_md5":m.get("archive_md5"),"license":m.get("license")};m["supplemental_sources"]=[{"source_id":"wikimedia_vetted","purpose":"real BALLOON confounders","per_file_source_credit_license_checksum_required":True,"derived_views_share_source_group":True,"seed":SEED}];m["licenses_present"]=sorted({str(i.get("license")) for i in m["items"] if i.get("license")});a.manifest.write_text(json.dumps(m,indent=2)+"\n");print("AERIALTRACK_BALLOON_CONFOUNDERS_APPENDED",len(added));print("AERIALTRACK_BALLOON_HELDOUT",len(test),len(groups))
if __name__=="__main__":main()
