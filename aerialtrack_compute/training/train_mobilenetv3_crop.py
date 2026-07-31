#!/usr/bin/env python3
from __future__ import annotations
import hashlib,importlib.util,math,random
from collections import Counter
from pathlib import Path
import numpy as np,torch
from PIL import Image
from torch import nn
from torch.utils.data import Dataset
from torchvision import models,transforms
ROOT=Path(__file__).resolve().parents[1];IMAGE_SIZE=160;CLASSES=["DRONE","NON_DRONE"];DRONE_INDEX=0;MIN_VAL_PRECISION=.90;MIN_VAL_RECALL=.80;MIN_VAL_SPECIFICITY=.95;CONTEXT_FRACTION=.25
def seed_everything(seed):
 random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
 if torch.backends.mps.is_available():torch.mps.manual_seed(seed)
def padded_bbox(bbox,width,height):
 if not bbox:return 0,0,width,height
 x,y,w,h=map(float,bbox);pad=max(w,h)*CONTEXT_FRACTION;x0=max(0,int(math.floor(x-pad)));y0=max(0,int(math.floor(y-pad)));x1=min(width,int(math.ceil(x+w+pad)));y1=min(height,int(math.ceil(y+h+pad)))
 if x1<=x0 or y1<=y0:raise ValueError(f"bbox collapsed {bbox!r}")
 return x0,y0,x1,y1
def label_index(label):return DRONE_INDEX if str(label).upper()=="DRONE" else 1
def train_transform():return transforms.Compose([transforms.RandomResizedCrop(IMAGE_SIZE,scale=(.72,1.0),ratio=(.85,1.18),antialias=True),transforms.RandomHorizontalFlip(.5),transforms.RandomApply([transforms.ColorJitter(brightness=.25,contrast=.25,saturation=.15)],p=.65),transforms.RandomApply([transforms.GaussianBlur(3,sigma=(.1,1.2))],p=.20),transforms.RandomPerspective(distortion_scale=.12,p=.18),transforms.ToTensor(),transforms.Normalize((.5,.5,.5),(.5,.5,.5))])
def eval_transform():return transforms.Compose([transforms.Resize((IMAGE_SIZE,IMAGE_SIZE),antialias=True),transforms.ToTensor(),transforms.Normalize((.5,.5,.5),(.5,.5,.5))])
class CropDataset(Dataset):
 def __init__(self,items,root,train):self.items=items;self.root=root;self.transform=train_transform() if train else eval_transform()
 def __len__(self):return len(self.items)
 def __getitem__(self,idx):
  item=self.items[idx];path=(self.root/str(item["path"])).resolve()
  with Image.open(path) as im:im=im.convert("RGB");crop=im.crop(padded_bbox(item.get("bbox"),im.width,im.height));x=self.transform(crop)
  return x,label_index(item["label"]),str(item["id"])
def build_model():
 m=models.mobilenet_v3_small(weights=None);m.classifier[-1]=nn.Linear(m.classifier[-1].in_features,2);return m
def collect(model,loader,device):
 logits=[];labels=[];ids=[];model.eval()
 with torch.inference_mode():
  for x,y,bids in loader:logits.append(model(x.to(device)).cpu());labels.append(y.cpu());ids.extend(map(str,bids))
 return torch.cat(logits),torch.cat(labels),ids
def metrics_from(logits,labels,threshold):
 probs=torch.softmax(logits,dim=1).numpy();truth=labels.numpy()==0;margin=probs[:,0]-probs[:,1];pred=(probs[:,0]>=probs[:,1])&(margin>=float(threshold));tp=int(np.sum(pred&truth));fp=int(np.sum(pred&~truth));fn=int(np.sum(~pred&truth));tn=int(np.sum(~pred&~truth));p=tp/max(1,tp+fp);r=tp/max(1,tp+fn);s=tn/max(1,tn+fp)
 return {"drone_precision":p,"drone_recall":r,"negative_specificity":s,"drone_f1":2*p*r/max(1e-12,p+r),"binary_accuracy":(tp+tn)/max(1,tp+fp+fn+tn),"confusion_counts":{"tp":tp,"fp":fp,"fn":fn,"tn":tn}}
def choose_threshold(logits,labels):
 passing=[];precision=[];fallback=[]
 for raw in np.arange(0,.901,.005):
  t=float(raw);m=metrics_from(logits,labels,t);p,r,s,f=m["drone_precision"],m["drone_recall"],m["negative_specificity"],m["drone_f1"];fallback.append((f,r,p,s,-t,t))
  if p>=MIN_VAL_PRECISION:
   precision.append((r,s,p,-t,t))
   if r>=MIN_VAL_RECALL and s>=MIN_VAL_SPECIFICITY:passing.append((r,s,p,-t,t))
 return max(passing)[-1] if passing else max(precision)[-1] if precision else max(fallback)[-1]
def checkpoint_score(m):
 p,r,s,f=m["drone_precision"],m["drone_recall"],m["negative_specificity"],m["drone_f1"]
 if p>=.9 and r>=.8 and s>=.95:return 100+r+.2*p+.05*s
 if p>=.9:return 10+r+.2*p+.05*s
 return f+.05*s
def split_items(corpus):
 out={"train":[],"validation":[],"test":[]}
 for i in corpus["items"]:out[str(i["split"])].append(i)
 if any(not out[n] for n in out):raise ValueError("train/validation/test non-empty required")
 return out
