#!/usr/bin/env python3
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

def require_bin(name: str):
    if not shutil.which(name):
        print(f"ERROR: '{name}' not found in PATH.")
        sys.exit(1)

def run_cmd(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

def human_to_bytes(s: str) -> int:
    s = s.strip().lower().replace(" ", "")
    m = re.match(r"^([0-9]*\.?[0-9]+)\s*([kmgt]?b?)?$", s)
    if not m:
        raise ValueError(f"Invalid size: {s}")
    val = float(m.group(1))
    unit = (m.group(2) or "").replace("b", "")
    mult = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3, "t": 1024**4}.get(unit, None)
    if mult is None:
        raise ValueError(f"Unknown unit: {s}")
    return int(val * mult)

def bytes_to_human(n: int) -> str:
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024 or unit == "TB":
            return f"{n:.2f} {unit}"
        n /= 1024

def ffprobe_json(path: str) -> dict:
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path]
    p = run_cmd(cmd)
    if p.returncode != 0:
        raise RuntimeError("ffprobe failed")
    return json.loads(p.stdout.decode("utf-8", "ignore"))

def get_media_info(path: str):
    meta = ffprobe_json(path)
    fmt = meta.get("format", {})
    duration = float(fmt.get("duration", 0.0)) if fmt.get("duration") else 0.0
    total_bitrate = 0
    for s in meta.get("streams", []):
        br = s.get("bit_rate")
        if br:
            try:
                total_bitrate += int(br)
            except:
                pass
    if total_bitrate == 0 and fmt.get("bit_rate"):
        total_bitrate = int(fmt["bit_rate"])
    return duration, total_bitrate

def estimate_size_bytes(duration_s: float, bitrate_bps: int) -> int:
    if duration_s <= 0 or bitrate_bps <= 0:
        return 0
    return int(duration_s * bitrate_bps / 8)

def ffprobe_duration(path: str) -> float:
    try:
        meta = ffprobe_json(path)
        fmt = meta.get("format", {})
        return float(fmt.get("duration", 0.0)) if fmt.get("duration") else 0.0
    except:
        return 0.0

def split_by_size_copy(infile: Path, size_limit_bytes: int, outdir: Path, prefix: str):
    outdir.mkdir(parents=True, exist_ok=True)
    duration, _ = get_media_info(str(infile))
    if duration <= 0:
        sys.exit(2)
    part_idx = 1
    offset = 0.0
    while True:
        outfile = outdir / f"{prefix}_part{part_idx:02d}{infile.suffix}"
        cmd = ["ffmpeg", "-y", "-ss", f"{offset}", "-i", str(infile), "-c", "copy", "-fs", f"{size_limit_bytes}", str(outfile)]
        p = run_cmd(cmd)
        if p.returncode != 0:
            sys.exit(3)
        chunk_dur = ffprobe_duration(str(outfile))
        if chunk_dur <= 0.2:
            outfile.exists() and outfile.unlink(missing_ok=True)
            break
        print(f"Created: {outfile.name} ({bytes_to_human(outfile.stat().st_size)} ≈ {chunk_dur:.2f}s)")
        offset += chunk_dur
        part_idx += 1
        if offset + 0.2 >= duration:
            break

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--size-limit", default="2G")
    parser.add_argument("--outdir", default="splits")
    parser.add_argument("--prefix", default=None)
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--reencode", action="store_true")
    parser.add_argument("--video-bitrate", default=None)
    parser.add_argument("--audio-bitrate", default="128k")
    args = parser.parse_args()
    require_bin("ffprobe")
    require_bin("ffmpeg")
    infile = Path(args.input).expanduser().resolve()
    if not infile.exists():
        sys.exit(1)
    size_limit_bytes = human_to_bytes(args.size_limit)
    outdir = Path(args.outdir).expanduser().resolve()
    prefix = args.prefix or infile.stem
    duration, src_bitrate = get_media_info(str(infile))
    if duration <= 0:
        sys.exit(2)
    if args.reencode:
        def parse_br(s):
            s = s.lower().strip()
            if s.endswith("k"):
                return int(float(s[:-1]) * 1000)
            if s.endswith("m"):
                return int(float(s[:-1]) * 1000_000)
            return int(s)
        if args.video_bitrate is None:
            v_bps = 2_500_000
        else:
            v_bps = parse_br(args.video_bitrate)
        a_bps = parse_br(args.audio_bitrate)
        est_size = estimate_size_bytes(duration, v_bps + a_bps)
        mode = f"re-encode (v={v_bps}bps, a={a_bps}bps)"
    else:
        est_size = estimate_size_bytes(duration, src_bitrate) if src_bitrate > 0 else 0
        mode = "stream copy (no re-encode)"
    print("== Preview ==")
    print(f"Input: {infile.name}")
    print(f"Duration: {duration:.2f} s")
    print(f"Mode: {mode}")
    if est_size > 0:
        print(f"Estimated size: {bytes_to_human(est_size)}")
        parts_est = max(1, math.ceil(est_size / size_limit_bytes))
        print(f"Estimated parts: ~{parts_est}")
    else:
        print("Estimated size: N/A")
    if args.simulate:
        print("Simulation only.")
        return
    if not args.reencode:
        split_by_size_copy(infile, size_limit_bytes, outdir, prefix)
    else:
        outdir.mkdir(parents=True, exist_ok=True)
        remaining = duration
        start = 0.0
        part_idx = 1
        total_target_bps = v_bps + a_bps
        approx_part_seconds = max(1, int((size_limit_bytes * 8) / total_target_bps))
        while remaining > 0.2:
            outfile = outdir / f"{prefix}_part{part_idx:02d}{infile.suffix}"
            cmd = [
                "ffmpeg", "-y", "-ss", f"{start}", "-i", str(infile),
                "-map", "0:v:0", "-map", "0:a:0?",
                "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{v_bps}",
                "-c:a", "aac", "-b:a", f"{a_bps}",
                "-t", f"{approx_part_seconds}", str(outfile)
            ]
            p = run_cmd(cmd)
            if p.returncode != 0:
                sys.exit(4)
            actual = ffprobe_duration(str(outfile))
            print(f"Created: {outfile.name} ({bytes_to_human(outfile.stat().st_size)} ≈ {actual:.2f}s)")
            start += actual
            remaining -= actual
            part_idx += 1

if __name__ == "__main__":
    main()
