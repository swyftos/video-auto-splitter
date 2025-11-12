#!/usr/bin/env python3
import argparse, os, sys, subprocess, shutil, json, re, math
from pathlib import Path

def require_bin(name):
    if not shutil.which(name):
        print(f"ERROR: '{name}' not found"); sys.exit(1)

def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

def human_to_bytes(s):
    s=s.strip().lower().replace(" ",""); m=re.match(r"^([0-9]*\.?[0-9]+)\s*([kmgt]?b?)?$",s)
    if not m: raise ValueError(s)
    v=float(m.group(1)); u=(m.group(2) or "").replace("b",""); mult={"":1,"k":1024,"m":1024**2,"g":1024**3,"t":1024**4}[u]
    return int(v*mult)

def ffprobe_json(p):
    r=run(["ffprobe","-v","error","-print_format","json","-show_format","-show_streams",p])
    if r.returncode!=0: raise RuntimeError("ffprobe"); return {}
    return json.loads(r.stdout.decode("utf-8","ignore"))

def duration(p):
    try:
        f=ffprobe_json(p).get("format",{}); return float(f.get("duration",0.0)) if f.get("duration") else 0.0
    except: return 0.0

def split_copy(infile, limit_bytes, outdir, prefix):
    outdir.mkdir(parents=True, exist_ok=True)
    d=duration(str(infile))
    if d<=0: return
    i=1; off=0.0
    while True:
        out=outdir/f"{prefix}_part{i:02d}{infile.suffix}"
        r=run(["ffmpeg","-y","-ss",f"{off}","-i",str(infile),"-c","copy","-fs",f"{limit_bytes}",str(out)])
        if r.returncode!=0: break
        cd=duration(str(out))
        if cd<=0.2: 
            try: out.unlink()
            except: pass
            break
        print(f"{out.name}  ({out.stat().st_size} bytes ~ {cd:.2f}s)")
        off+=cd; i+=1
        if off+0.2>=d: break

def is_video(path):
    exts={".mp4",".mov",".m4v",".mkv",".avi",".wmv",".webm",".ts",".m2ts",".flv",".mpg",".mpeg"}
    return path.suffix.lower() in exts

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--size-limit",default="2G")
    ap.add_argument("--outroot",default="splits")
    ap.add_argument("--recursive",action="store_true")
    ap.add_argument("--skip-existing",action="store_true")
    args=ap.parse_args()
    require_bin("ffmpeg"); require_bin("ffprobe")
    base=Path(args.folder).expanduser().resolve()
    outroot=Path(args.outroot).expanduser().resolve()
    limit=human_to_bytes(args.size_limit)
    if not base.exists(): sys.exit(1)
    files=[]
    if args.recursive:
        for p in base.rglob("*"):
            if p.is_file() and is_video(p): files.append(p)
    else:
        for p in base.iterdir():
            if p.is_file() and is_video(p): files.append(p)
    if not files:
        print("No videos found."); return
    for f in files:
        rel=f.relative_to(base)
        outdir=outroot/rel.parent
        prefix=f.stem
        first_part=outdir/f"{prefix}_part01{f.suffix}"
        if args.skip-existing and first_part.exists():
            print(f"Skip (exists): {f}")
            continue
        print(f"Processing: {f}")
        split_copy(f, limit, outdir, prefix)
    print("Done.")

if __name__=="__main__":
    main()
