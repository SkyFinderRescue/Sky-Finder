#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCES = ROOT / "clean_sources.json"
DIRECT_LICENSES = {"CC0-1.0", "MIT", "BSD-3-Clause", "Apache-2.0", "Public-Domain", "CC-BY-4.0"}
DISALLOWED_TOKENS = ("NC", "NONCOMMERCIAL", "NON-COMMERCIAL", "UNKNOWN", "UNVERIFIED")
REQUIRED_SPLITS = {"train", "validation", "test"}
def read_json(path: Path) -> dict:
    value=json.loads(path.read_text())
    if not isinstance(value,dict): raise ValueError(f"JSON root must be object: {path}")
    return value
def valid_https(value):
    p=urlparse(str(value or "")); return p.scheme=="https" and bool(p.netloc)
def safe_license(value):
    text=str(value or "").upper(); return bool(text) and not any(t in text for t in DISALLOWED_TOKENS)
def validate_source_registry(data):
    failures=[]
    if data.get("schema_version")!=1: failures.append("source registry schema_version must be 1")
    rows=data.get("sources")
    if not isinstance(rows,list) or not rows: return failures+["source registry must contain sources"]
    ids=set()
    for row in rows:
        sid=str(row.get("id") or "")
        if not sid: failures.append("source missing id"); continue
        if sid in ids: failures.append(f"duplicate source id: {sid}")
        ids.add(sid)
        if row.get("production_approved") is not True: failures.append(f"{sid}: source is not production_approved")
        if row.get("whole_source_split_required") is not True: failures.append(f"{sid}: whole_source_split_required must be true")
        if not valid_https(row.get("source_url")): failures.append(f"{sid}: source_url must be HTTPS")
        if not str(row.get("media_rights_basis") or ""): failures.append(f"{sid}: media_rights_basis missing")
        classes=row.get("classes")
        if not isinstance(classes,list) or not classes: failures.append(f"{sid}: classes missing")
        lic=str(row.get("license") or "")
        if lic=="PER_FILE":
            allowed=set(map(str,row.get("allowed_file_licenses") or []))
            if not allowed or not allowed <= DIRECT_LICENSES: failures.append(f"{sid}: invalid per-file license allowlist")
        elif lic not in DIRECT_LICENSES: failures.append(f"{sid}: unapproved source license {lic!r}")
        if not safe_license(lic): failures.append(f"{sid}: unsafe/unclear license token")
    return failures
def sha256_file(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def validate_local_items(data,*,splits,root=Path(".")):
    failures=[]
    if not splits or not set(splits)<=REQUIRED_SPLITS: return ["local verification split set is invalid"]
    items=data.get("items")
    if not isinstance(items,list): return ["corpus manifest contains no items"]
    for item in items:
        if str(item.get("split") or "") not in splits: continue
        iid=str(item.get("id") or "<missing-id>"); rel=item.get("path"); checksum=str(item.get("sha256") or "")
        if not rel: failures.append(f"{iid}: path required for local verification"); continue
        local=(root/str(rel)).resolve()
        if not local.is_file(): failures.append(f"{iid}: local file missing: {local}")
        elif sha256_file(local).lower()!=checksum.lower(): failures.append(f"{iid}: local checksum mismatch")
    return failures
def validate_corpus(data,registry,*,verify_local_files=False,root=Path(".")):
    failures=[]; sources={str(r["id"]):r for r in registry.get("sources") or []}; items=data.get("items")
    if data.get("schema_version")!=1: failures.append("corpus schema_version must be 1")
    if not isinstance(items,list) or not items: return failures+["corpus manifest contains no items"]
    seen=set(); group_splits={}; observed=set()
    for item in items:
        iid=str(item.get("id") or "")
        if not iid: failures.append("corpus item missing id"); continue
        if iid in seen: failures.append(f"duplicate corpus item id: {iid}")
        seen.add(iid); sid=str(item.get("source_id") or ""); source=sources.get(sid)
        if source is None: failures.append(f"{iid}: unregistered source_id {sid!r}"); continue
        split=str(item.get("split") or "")
        if split not in REQUIRED_SPLITS: failures.append(f"{iid}: invalid split {split!r}")
        else: observed.add(split)
        group=str(item.get("source_group_id") or "")
        if not group: failures.append(f"{iid}: source_group_id missing")
        else: group_splits.setdefault((sid,group),set()).add(split)
        if not str(item.get("label") or ""): failures.append(f"{iid}: label missing")
        if not valid_https(item.get("source_url")): failures.append(f"{iid}: canonical source_url must be HTTPS")
        lic=str(item.get("license") or ""); registered=str(source.get("license") or "")
        if registered=="PER_FILE":
            if lic not in set(map(str,source.get("allowed_file_licenses") or [])): failures.append(f"{iid}: per-file license {lic!r} is not approved")
        elif lic!=registered: failures.append(f"{iid}: item license {lic!r} does not match registered source {registered!r}")
        if not safe_license(lic): failures.append(f"{iid}: unsafe/unclear item license")
        if source.get("attribution_required") and not str(item.get("credit") or ""): failures.append(f"{iid}: credit required")
        checksum=str(item.get("sha256") or "")
        if len(checksum)!=64 or any(ch not in "0123456789abcdef" for ch in checksum.lower()): failures.append(f"{iid}: sha256 missing/invalid")
    for (sid,group),splits in sorted(group_splits.items()):
        valid={s for s in splits if s in REQUIRED_SPLITS}
        if len(valid)>1: failures.append(f"source leakage: {sid}/{group} appears in {sorted(valid)}")
    if observed!=REQUIRED_SPLITS: failures.append(f"corpus must contain train/validation/test; found {sorted(observed)}")
    if verify_local_files: failures.extend(validate_local_items(data,splits=REQUIRED_SPLITS,root=root))
    return failures
def main():
    p=argparse.ArgumentParser(); p.add_argument("--sources",type=Path,default=DEFAULT_SOURCES); p.add_argument("--corpus",type=Path); p.add_argument("--verify-local-files",action="store_true"); p.add_argument("--verify-split",action="append",choices=sorted(REQUIRED_SPLITS)); p.add_argument("--root",type=Path,default=Path(".")); a=p.parse_args()
    registry=read_json(a.sources); failures=validate_source_registry(registry)
    if a.corpus:
        corpus=read_json(a.corpus); failures.extend(validate_corpus(corpus,registry,verify_local_files=False,root=a.root))
        if a.verify_local_files and a.verify_split: raise SystemExit("use either --verify-local-files or --verify-split, not both")
        if a.verify_local_files: failures.extend(validate_local_items(corpus,splits=REQUIRED_SPLITS,root=a.root))
        elif a.verify_split: failures.extend(validate_local_items(corpus,splits=set(a.verify_split),root=a.root))
    if failures:
        print("AERIALTRACK_TRAINING_PROVENANCE=FAIL"); [print("-",x) for x in failures]; return 2
    print("AERIALTRACK_TRAINING_PROVENANCE=PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
