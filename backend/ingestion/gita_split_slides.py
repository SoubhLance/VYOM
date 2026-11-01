#!/usr/bin/env python3
"""
gita_split_slides.py - verse boundaries from the video's slide changes.

Why: pause-based splitting failed on this recording, but the slides change about once per
verse (interior gaps are 11-24 s). Each chapter has a few extra changes at its edges (a title
card before verse 1, a closing/colophon slide after the last verse), so just counting changes
is not enough. For each chapter this picks the run of N consecutive slides that best fits
"one verse per slide, 10.5-24 s each, verse 1 near the chapter marker", and reports how close
the runner-up was.

Inputs : scene_all.txt (ffmpeg select+metadata log from the probe) and chapters.csv
Outputs: cuts_slides.csv   (columns gita_split.py `split` reads)
         verify_points.csv (where to look to confirm first/last verse of each chapter)

  python gita_split_slides.py plan scene_all.txt chapters.csv --media lecture.mp4
  python gita_split_slides.py sheet lecture.mp4 verify_points.csv --out verify
      -> verify/chNN_v1_to_vN.png: LEFT = end of the chapter's first verse, RIGHT = end of its
         last verse. The verse number printed on screen must read 1 on the left and N on the
         right. If both ends are right and the interior gaps were normal, every verse between
         them is right too.
  python gita_split.py split lecture.mp4 cuts_slides.csv --chapters chapters.csv --out assets

Needs Python 3.8+ and ffmpeg/ffprobe on PATH. No pip packages.
"""
import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path
from shutil import which

VERSE_COUNTS = [47, 72, 43, 42, 29, 47, 30, 28, 34, 42, 55, 20, 35, 27, 20, 24, 28, 78]
LO, HI, HI_LAST = 10.5, 24.0, 32.0   # plausible seconds for one verse slide (last one may carry a closing line)


# ---------------------------------------------------------------- utilities
def need(tool):
    if not which(tool):
        sys.exit(f"'{tool}' not found on PATH.")


def parse_time(s):
    s = str(s).strip()
    if not s:
        raise ValueError("empty time")
    secs = 0.0
    for part in s.split(":"):
        secs = secs * 60 + float(part)
    return secs


def media_duration(path):
    need("ffprobe")
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def read_markers(path):
    marks = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if (r.get("start") or "").strip():
                marks[int(r["chapter"])] = parse_time(r["start"])
    missing = [c for c in range(1, 19) if c not in marks]
    if missing:
        sys.exit(f"{path}: no start time for chapters {missing}")
    return marks


def read_scenes(path, min_score, merge_gap):
    """Parse ffmpeg `metadata=print` output; merge changes closer than merge_gap seconds."""
    raw, cur = [], None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.search(r"pts_time:([\d.]+)", line)
            if m:
                cur = float(m.group(1))
                continue
            m = re.search(r"lavfi\.scene_score=([\d.]+)", line)
            if m and cur is not None:
                if float(m.group(1)) >= min_score:
                    raw.append((cur, float(m.group(1))))
                cur = None
    raw.sort()
    merged = []
    for t, sc in raw:
        if merged and t - merged[-1][0] < merge_gap:
            if sc > merged[-1][1]:
                merged[-1] = (merged[-1][0], sc)
        else:
            merged.append((t, sc))
    if not merged:
        sys.exit(f"{path}: no scene changes parsed - is it the ffmpeg metadata=print log?")
    return [t for t, _ in merged]


# --------------------------------------------------------------------- plan
def slide_penalty(d, last):
    hi = HI_LAST if last else HI
    if d < LO:
        return LO - d
    if d > hi:
        return (d - hi) * 0.5
    return 0.0


def rank_windows(changes, marker, n):
    """Score every run of n consecutive slides; lower is better. Returns [(score, offset)]."""
    out = []
    for o in range(0, len(changes) - n):          # changes[o+n] must exist: it ends the last verse
        score = sum(slide_penalty(changes[o + k + 1] - changes[o + k], k == n - 1) for k in range(n))
        s = changes[o]
        if s < marker - 1.5:                      # verse 1 should start near the chapter marker
            score += (marker - 1.5 - s) * 0.5
        if s > marker + 12:
            score += (s - (marker + 12)) * 0.5
        out.append((score, o))
    out.sort()
    return out


def cmd_plan(args):
    changes = read_scenes(args.scenes, args.min_score, args.merge_gap)
    marks = read_markers(args.chapters)
    total = media_duration(args.media) if args.media else changes[-1] + 40
    counts = [int(x) for x in args.counts.split(",")] if args.counts else VERSE_COUNTS[:]
    if len(counts) != 18:
        sys.exit("--counts needs 18 numbers")
    first = {c: 1 for c in range(1, 19)}
    if args.std700:                       # 34 verses, numbered 13.2-13.35 to match 701-verse data
        counts[12], first[13] = 34, 2
    only = {int(x) for x in args.only.split(",")} if args.only else None

    rows, verify, nflag = [], [], 0
    for c in range(1, 19):
        if only and c not in only:
            continue
        n, m = counts[c - 1], marks[c]
        nxt = marks[c + 1] if c < 18 else total
        local = [t for t in changes if m - 20 <= t < nxt + 25]
        ranked = rank_windows(local, m, n)
        if not ranked:
            print(f"ch{c:02d}: FAILED - only {len(local)} slide changes near this chapter, need more than {n}")
            continue
        best, o = ranked[0]
        runner = ranked[1][0] if len(ranked) > 1 else float("inf")
        ambiguous = (runner - best) < 3.0
        before = sum(1 for t in local if m - 20 <= t < local[o])
        after = sum(1 for t in local if local[o + n] <= t < nxt - 0.5)
        fl_count = 0
        for k in range(n):
            a, b = local[o + k], local[o + k + 1]
            d, fl = b - a, []
            if d < LO:
                fl.append("SHORT")
            if d > (HI_LAST if k == n - 1 else HI):
                fl.append("LONG")
            if ambiguous and k in (0, n - 1):
                fl.append("CH_AMBIGUOUS")
            fl_count += bool(fl)
            rows.append([c, first[c] + k, f"{a + args.shift:.3f}", f"{b + args.shift:.3f}", f"{d:.1f}", "|".join(fl)])
        nflag += fl_count
        v_first, v_last = first[c], first[c] + n - 1
        verify.append([c, v_first, f"{local[o + 1] - 1.0:.3f}", v_last, f"{local[o + n] - 1.0:.3f}"])
        tag = "AMBIGUOUS" if ambiguous else "ok"
        print(f"ch{c:02d}: {n:>2} verses | {before} change(s) before v{v_first} | {after} after v{v_last} | "
              f"score {best:5.1f} (next best {runner:5.1f}) {tag} | {fl_count} flagged")

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["chapter", "verse", "start", "end", "dur_sec", "flags"])
        w.writerows(rows)
    with open(args.verify_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["chapter", "first_verse", "first_t", "last_verse", "last_t"])
        w.writerows(verify)
    print(f"\nWrote {args.out}: {len(rows)} verses, {nflag} flagged; {args.verify_out}: {len(verify)} chapters")
    print("Next: run `sheet` and check the verse numbers on screen before trusting any chapter.")


# -------------------------------------------------------------------- sheet
def cmd_sheet(args):
    need("ffmpeg")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(args.points, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        c, v1, v2 = int(r["chapter"]), int(r["first_verse"]), int(r["last_verse"])
        t1, t2 = float(r["first_t"]), float(r["last_t"])
        png = out_dir / f"ch{c:02d}_v{v1}_to_v{v2}.png"
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-ss", f"{max(t1, 0):.3f}", "-i", str(args.media), "-ss", f"{max(t2, 0):.3f}", "-i", str(args.media),
               "-filter_complex", f"[0:v]scale={args.width}:-2[a];[1:v]scale={args.width}:-2[b];[a][b]hstack=inputs=2",
               "-frames:v", "1", str(png)]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0:
            sys.exit(f"ffmpeg failed for chapter {c}:\n{p.stderr[-600:]}")
        print(f"  {png}")
    print(f"\n{len(rows)} images. Left = end of first verse, right = end of last verse.")


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Verse boundaries from slide changes.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="choose each chapter's verse slides, write cuts_slides.csv")
    p.add_argument("scenes", help="scene_all.txt from the ffmpeg probe")
    p.add_argument("chapters", help="chapters.csv (chapter,start[,end])")
    p.add_argument("--media", help="lecture.mp4 (gives the video length for the last chapter)")
    p.add_argument("--out", default="cuts_slides.csv")
    p.add_argument("--verify-out", default="verify_points.csv")
    p.add_argument("--min-score", type=float, default=0.01, help="ignore changes below this scene score")
    p.add_argument("--merge-gap", type=float, default=1.0, help="merge changes closer than this (sec)")
    p.add_argument("--shift", type=float, default=0.0,
                   help="add this many seconds to every boundary (negative = earlier) after you listen to a few clips")
    p.add_argument("--counts", help="18 comma-separated verse counts (default: 701-verse numbering)")
    p.add_argument("--std700", action="store_true", help="ch13 has 34 verses, numbered 13.2-13.35")
    p.add_argument("--only", help="comma list of chapters, e.g. 4,13")
    p.set_defaults(fn=cmd_plan)

    s = sub.add_parser("sheet", help="make first/last-verse check images per chapter")
    s.add_argument("media")
    s.add_argument("points", help="verify_points.csv from `plan`")
    s.add_argument("--out", default="verify")
    s.add_argument("--width", type=int, default=800)
    s.set_defaults(fn=cmd_sheet)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
    