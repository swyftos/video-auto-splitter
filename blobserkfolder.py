#!/usr/bin/env python3
import argparse, os, sys, subprocess, shutil, json, re, math, time, threading, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------- Utils ----------
def require_bin(name):
    if not shutil.which(name):
        print(f"ERROR: '{name}' not found"); sys.exit(1)

def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

def human_to_bytes(s):
    s=s.strip().lower().replace(" ","")
    m=re.match(r"^([0-9]*\.?[0-9]+)\s*([kmgt]?b?)?$",s)
    if not m: raise ValueError(s)
    v=float(m.group(1)); u=(m.group(2) or "").replace("b","")
    mult={"":1,"k":1024,"m":1024**2,"g":1024**3,"t":1024**4}[u]
    return int(v*mult)

def ffprobe_json(p):
    r=run(["ffprobe","-v","error","-print_format","json","-show_format","-show_streams",p])
    if r.returncode!=0: return {}
    return json.loads(r.stdout.decode("utf-8","ignore"))

def duration(p):
    try:
        f=ffprobe_json(p).get("format",{}); return float(f.get("duration",0.0)) if f.get("duration") else 0.0
    except: return 0.0

def is_video(path):
    exts={".mp4",".mov",".m4v",".mkv",".avi",".wmv",".webm",".ts",".m2ts",".flv",".mpg",".mpeg"}
    return path.suffix.lower() in exts

# ---------- Fancy console animations ----------
class Animator:
    STYLES = ("spinner","snake","bounce","dots","earth","none")
    def __init__(self, style="auto", label="Processing"):
        self.label = label
        if style in ("auto","random"):
            self.style = random.choice([s for s in self.STYLES if s!="none"])
        else:
            self.style = style if style in self.STYLES else "spinner"
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        try: sys.stdout.write("\x1b[?25l")
        except: pass
        self.thread.start()

    def stop(self, suffix_msg=""):
        self.stop_flag.set()
        self.thread.join(timeout=1.0)
        try:
            sys.stdout.write("\r" + " " * 140 + "\r")
            sys.stdout.write("\x1b[?25h")
            if suffix_msg:
                sys.stdout.write(suffix_msg + "\n")
            sys.stdout.flush()
        except: pass

    def _run(self):
        if self.style == "none": return
        elif self.style == "snake": self._snake()
        elif self.style == "bounce": self._bounce()
        elif self.style == "dots": self._dots()
        elif self.style == "earth": self._earth()
        else: self._spinner()

    def _spinner(self):
        frames = ["|","/","-","\\"]
        i=0
        while not self.stop_flag.is_set():
            sys.stdout.write(f"\r{self.label}  {frames[i%len(frames)]}")
            sys.stdout.flush(); i+=1; time.sleep(0.08)

    def _snake(self):
        width = 38; body = "o~~~"
        pos=0; direction=1
        while not self.stop_flag.is_set():
            line = " " * pos + body
            line = line[:width]
            sys.stdout.write(f"\r{self.label}  [{line:<{width}}]")
            sys.stdout.flush()
            pos += direction
            if pos <= 0: direction = 1
            if pos + len(body) >= width: direction = -1
            time.sleep(0.05)

    def _bounce(self):
        width = 20; pos = 0; dir = 1
        while not self.stop_flag.is_set():
            bar = " " * pos + "●" + " " * (width-pos)
            sys.stdout.write(f"\r{self.label}  [{bar}]")
            sys.stdout.flush()
            pos += dir
            if pos<=0: dir=1
            if pos>=width: dir=-1
            time.sleep(0.04)

    def _dots(self):
        i=0
        while not self.stop_flag.is_set():
            dots = "." * (i%4)
            sys.stdout.write(f"\r{self.label}  {dots:<3}")
            sys.stdout.flush(); i+=1; time.sleep(0.3)

    def _earth(self):
        frames = ["🌍","🌎","🌏","🌍","🌎","🌏"]
        i=0
        while not self.stop_flag.is_set():
            sys.stdout.write(f"\r{self.label}  {frames[i%len(frames)]}")
            sys.stdout.flush(); i+=1; time.sleep(0.15)

def run_with_animation(cmd_list, anim_style, label):
    p = subprocess.Popen(cmd_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    anim = Animator(anim_style, label)
    anim.start()
    p.wait()
    anim.stop()
    return p.returncode

# ---------- Split logic ----------
def split_copy(infile, limit_bytes, outdir, prefix, anim_style):
    outdir.mkdir(parents=True, exist_ok=True)
    d=duration(str(infile))
    if d<=0: 
        print(f"Skip (no duration): {infile}")
        return
    i=1; off=0.0
    while True:
        outfile = outdir / f"{prefix}_part{i:02d}{infile.suffix}"
        cmd = ["ffmpeg","-y","-ss",f"{off}","-i",str(infile),"-c","copy","-fs",f"{limit_bytes}",str(outfile)]
        rc = run_with_animation(cmd, anim_style, f"{infile.name} → part {i:02d}")
        if rc!=0:
            print(f"ERROR ffmpeg ({infile.name} part {i:02d})"); break
        cd = duration(str(outfile))
        if cd<=0.2:
            try: outfile.unlink()
            except: pass
            break
        size = outfile.stat().st_size
        print(f"✓ {outfile.name}  ({size} bytes ~ {cd:.2f}s)")
        off += cd; i += 1
        if off+0.2 >= d: break

# ---------- Batch driver ----------
def gather_files(base: Path, recursive: bool):
    files=[]
    if recursive:
        for p in base.rglob("*"):
            if p.is_file() and is_video(p): files.append(p)
    else:
        for p in base.iterdir():
            if p.is_file() and is_video(p): files.append(p)
    return files

def process_one(f, base, outroot, limit, skip_existing, anim):
    rel=f.relative_to(base)
    outdir=outroot/rel.parent
    prefix=f.stem
    first_part=outdir/f"{prefix}_part01{f.suffix}"
    if skip_existing and first_part.exists():
        return f"Skip (exists): {f}"
    split_copy(f, limit, outdir, prefix, anim)
    return f"Done: {f}"

def main():
    ap=argparse.ArgumentParser(description="Batch split videos by size with console animations.")
    ap.add_argument("folder")
    ap.add_argument("--size-limit",default="2G")
    ap.add_argument("--outroot",default="splits")
    ap.add_argument("--recursive",action="store_true")
    ap.add_argument("--skip-existing",action="store_true")
    ap.add_argument("--jobs",type=int,default=1,help="parallel workers")
    ap.add_argument("--anim",default="auto",choices=["auto","random","spinner","snake","bounce","dots","earth","none"])
    args=ap.parse_args()

    require_bin("ffmpeg"); require_bin("ffprobe")

    base=Path(args.folder).expanduser().resolve()
    outroot=Path(args.outroot).expanduser().resolve()
    if not base.exists(): 
        print("Input folder not found."); sys.exit(1)
    limit=human_to_bytes(args.size_limit)

    files=gather_files(base,args.recursive)
    if not files:
        print("No videos found."); return

    print(f"Found {len(files)} video(s). Output root: {outroot}")
    outroot.mkdir(parents=True, exist_ok=True)

    if args.jobs<=1:
        for f in files:
            print(f"Processing: {f}")
            msg = process_one(f, base, outroot, limit, args.skip_existing, args.anim)
            print(msg)
    else:
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            futures = {ex.submit(process_one,f,base,outroot,limit,args.skip_existing,args.anim): f for f in files}
            for fut in as_completed(futures):
                print(fut.result())
    print("All done.")

if __name__=="__main__":
    main()
