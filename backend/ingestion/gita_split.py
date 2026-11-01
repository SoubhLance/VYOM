#!/usr/bin/env python3
"""
gita_split.py - split one long Bhagavad Gita recitation into chapter files and
per-verse clips (audio, optionally video), with QA flags and a review page.

Needs: Python 3.8+, ffmpeg and ffprobe on PATH. No pip packages.

WORKFLOW
  1. python gita_split.py init
        writes chapters.csv (chapter,start,end) - fill it in by hand:
        start = where the FIRST VERSE of the chapter begins (mm:ss or h:mm:ss)
        end   = optional; where the LAST VERSE ends, if the chapter closes with a
                colophon / outro you don't want. Blank = next chapter's start.
  2. python gita_split.py detect lecture.mp4 chapters.csv
        finds pauses, proposes verse boundaries -> cuts_draft.csv + console QA
  3. Open cuts_draft.csv, fix rows with a non-empty `flags` column by hand
        (times may be seconds like 83.5 or mm:ss.s), save as cuts.csv
  4. python gita_split.py split lecture.mp4 cuts.csv --chapters chapters.csv --out assets [--video]
        -> assets/audio/verses/bg_02_47.mp3, assets/audio/chapters/bg_02.mp3,
           assets/manifest.json, assets/review.html
  5. Open assets/review.html, hit "flagged only", listen, fix cuts.csv, re-run step 4.

HOW THE DETECTION WORKS (so you know when to distrust it)
  For a chapter with N verses it finds all pauses, keeps the N-1 LONGEST as verse
  boundaries, and assumes the pauses inside a verse (between its two lines) are
  shorter. Where that assumption is shaky the verse gets a flag:
    SHORT / LONG          clip is much shorter / longer than the chapter median
    WEAK_BOUNDARY         a chosen boundary barely beat the longest pause that was NOT chosen
    MAYBE_SPLIT_HERE      an unchosen pause inside this verse is nearly as long as the
                          weakest chosen one (verse may really be two)
  Unflagged does not mean verified - it means the heuristic was confident.
"""
import argparse
import csv
import html
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path
from shutil import which

# 701-verse numbering (ch13 = 35, where 13.1 is Arjuna's question).
VERSE_COUNTS = [47, 72, 43, 42, 29, 47, 30, 28, 34, 42, 55, 20, 35, 27, 20, 24, 28, 78]


# ---------------------------------------------------------------- utilities
def need(tool):
    if not which(tool):
        sys.exit(f"'{tool}' not found on PATH. Install ffmpeg (Windows: `winget install Gyan.FFmpeg`) "
                 "and open a new terminal.")


def parse_time(s):
    """'83.5' | '1:23.5' | '1:02:03' -> seconds."""
    s = str(s).strip()
    if not s:
        raise ValueError("empty time")
    secs = 0.0
    for part in s.split(":"):
        secs = secs * 60 + float(part)
    return secs


def fmt_time(t):
    h, m, s = int(t // 3600), int((t % 3600) // 60), t % 60
    return f"{h}:{m:02d}:{s:06.3f}"


def media_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def run(cmd, dry=False):
    if dry:
        print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        return
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{' '.join(cmd)}\n{r.stderr[-800:]}")


# ------------------------------------------------------------- chapters.csv
def read_chapters(path, total):
    starts, ends = {}, {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            c = int(r["chapter"])
            if not (r.get("start") or "").strip():
                continue
            starts[c] = parse_time(r["start"])
            if (r.get("end") or "").strip():
                ends[c] = parse_time(r["end"])
    missing = [c for c in range(1, 19) if c not in starts]
    if missing:
        sys.exit(f"{path}: no start time for chapters {missing}")
    out = []
    for c in range(1, 19):
        end = ends.get(c, starts[c + 1] if c < 18 else total)
        if end <= starts[c]:
            sys.exit(f"{path}: chapter {c} ends before it starts")
        if c < 18 and starts[c + 1] < starts[c]:
            sys.exit(f"{path}: chapter {c + 1} starts before chapter {c}")
        out.append((c, starts[c], end))
    return out


def cmd_init(args):
    p = Path(args.path)
    if p.exists():
        sys.exit(f"{p} already exists - not overwriting.")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["chapter", "start", "end"])
        for c in range(1, 19):
            w.writerow([c, "", ""])
    print(f"Wrote {p}. Fill the 'start' column (and 'end' only if needed).")


# ------------------------------------------------------------------- detect
SIL_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
SIL_END = re.compile(r"silence_end:\s*(-?[\d.]+)")


def detect_silences(media, noise_db, min_sil, total):
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(media), "-vn", "-ac", "1",
           "-af", f"silencedetect=noise={noise_db}dB:d={min_sil}", "-f", "null", "-"]
    print("Scanning audio for pauses (a few minutes for a multi-hour file)...")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{r.stderr[-800:]}")
    sil, cur = [], None
    for line in r.stderr.splitlines():
        m = SIL_START.search(line)
        if m:
            cur = max(0.0, float(m.group(1)))
            continue
        m = SIL_END.search(line)
        if m and cur is not None:
            sil.append((cur, float(m.group(1))))
            cur = None
    if cur is not None:
        sil.append((cur, total))
    return sil


def draft_chapter(start, end, n, sil, pad):
    """Return (cuts, flags, margin) or (None, reason, None)."""
    # interior pauses only: ignore the pause touching the chapter's end (it is the gap to the
    # next chapter / outro, not a verse boundary); one touching the start is excluded by s >= start
    cand = [(e - s, s, e) for s, e in sil if s >= start and e < end - 0.05]
    if len(cand) < n - 1:
        return None, f"only {len(cand)} pauses found, need {n - 1}", None
    ranked = sorted(cand, reverse=True)
    chosen = sorted(ranked[:n - 1], key=lambda x: x[1])
    weakest = ranked[n - 2][0]
    runner_up = ranked[n - 1][0] if len(ranked) > n - 1 else 0.0
    margin = weakest / runner_up if runner_up > 0 else float("inf")

    v_start = start
    for s, e in sil:                       # trim leading silence
        if s <= start < e:
            v_start = max(start, e - pad)
            break
    cuts = []
    for dur, s, e in chosen:
        p = min(pad, dur / 2)
        cuts.append((v_start, s + p))
        v_start = e - p
    v_end = end
    for s, e in sil:                       # trim trailing silence
        if s < end <= e + 0.05:
            v_end = max(v_start + 0.5, min(end, s + pad))
            break
    cuts.append((v_start, v_end))

    flags = [set() for _ in range(n)]
    med = statistics.median(b - a for a, b in cuts)
    for i, (a, b) in enumerate(cuts):
        if b - a < 0.5 * med:
            flags[i].add("SHORT")
        if b - a > 1.8 * med:
            flags[i].add("LONG")
    for dur, s, e in ranked[n - 1:]:       # unchosen pauses that nearly qualified
        if dur >= weakest * 0.85:
            mid = (s + e) / 2
            for i, (a, b) in enumerate(cuts):
                if a <= mid <= b:
                    flags[i].add("MAYBE_SPLIT_HERE")
    for k, (dur, s, e) in enumerate(chosen):  # chosen pauses that barely won
        if runner_up > 0 and dur <= runner_up * 1.15:
            flags[k].add("WEAK_BOUNDARY")
            flags[k + 1].add("WEAK_BOUNDARY")
    return cuts, flags, margin


def cmd_detect(args):
    need("ffmpeg"), need("ffprobe")
    total = media_duration(args.media)
    chapters = read_chapters(args.chapters, total)
    counts = [int(x) for x in args.counts.split(",")] if args.counts else VERSE_COUNTS[:]
    if len(counts) != 18:
        sys.exit("--counts needs 18 numbers")
    first = {c: 1 for c in range(1, 19)}
    if args.std700:                        # video's ch13 starts at "idam sariram" = 13.2 in 701 numbering
        counts[12], first[13] = 34, 2
    only = {int(x) for x in args.only.split(",")} if args.only else None

    sil = detect_silences(args.media, args.noise, args.min_silence, total)
    print(f"{len(sil)} pauses found.\n")

    rows, problems, flagged = [], [], 0
    for c, start, end in chapters:
        if only and c not in only:
            continue
        n = counts[c - 1]
        cuts, flags, margin = draft_chapter(start, end, n, sil, args.pad)
        if cuts is None:
            problems.append(c)
            print(f"ch{c:02d}: FAILED - {flags}. Try --noise -30 or a smaller --min-silence, with --only {c}")
            continue
        note = "ambiguous - review whole chapter" if margin < 1.15 else "ok"
        nfl = sum(1 for f in flags if f)
        flagged += nfl
        print(f"ch{c:02d}: {n:>2} verses, boundary margin {margin:4.2f} ({note}), {nfl} flagged")
        for i, ((a, b), fl) in enumerate(zip(cuts, flags)):
            rows.append([c, first[c] + i, f"{a:.3f}", f"{b:.3f}", f"{b - a:.1f}", "|".join(sorted(fl))])

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["chapter", "verse", "start", "end", "dur_sec", "flags"])
        w.writerows(rows)
    print(f"\nWrote {args.out}: {len(rows)} verses, {flagged} flagged"
          + (f", chapters failed: {problems}" if problems else ""))
    print("Next: fix flagged rows by hand, save as cuts.csv, then run `split`.")


# -------------------------------------------------------------------- split
def read_cuts(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            a, b = parse_time(r["start"]), parse_time(r["end"])
            if b <= a:
                sys.exit(f"{path}: ch{r['chapter']} v{r['verse']} ends before it starts")
            rows.append((int(r["chapter"]), int(r["verse"]), a, b, (r.get("flags") or "").strip()))
    if not rows:
        sys.exit(f"{path} has no rows")
    return rows


def audio_cmd(media, a, b, out, args):
    codec = ["-c:a", "libopus", "-b:a", args.bitrate] if args.format == "opus" \
        else ["-c:a", "libmp3lame", "-b:a", args.bitrate]
    ch = [] if args.stereo else ["-ac", "1"]
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{a:.3f}", "-i", str(media),
            "-t", f"{b - a:.3f}", "-vn", *ch, *codec, str(out)]


def video_cmd(media, a, b, out, args):
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{a:.3f}", "-i", str(media),
            "-t", f"{b - a:.3f}", "-vf", f"scale=-2:{args.video_height}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
            "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)]


def write_review(out_dir, manifest):
    rows = []
    for vid, m in manifest.items():
        cls = ' class="flag"' if m["flags"] else ""
        rows.append(f'<tr{cls}><td>{vid}</td><td>{m["duration_sec"]}s</td>'
                    f'<td>{html.escape(m["flags"])}</td>'
                    f'<td><audio controls preload="none" src="{html.escape(m["audio"])}"></audio></td></tr>')
    page = ("<!doctype html><meta charset=utf-8><title>Gita split review</title>"
            "<style>body{font:14px sans-serif;margin:20px}td{padding:4px 12px}"
            "tr.flag{background:#fff3cd}button{margin-bottom:12px;padding:6px 12px}</style>"
            "<button onclick=\"var f=this.dataset.on!=='1';this.dataset.on=f?'1':'0';"
            "document.querySelectorAll('tr:not(.flag)').forEach(r=>r.style.display=f?'none':'')\">"
            "Toggle flagged only</button>"
            "<table><tr><th>Verse</th><th>Length</th><th>Flags</th><th>Audio</th></tr>"
            + "".join(rows) + "</table>")
    (out_dir / "review.html").write_text(page, encoding="utf-8")


def cmd_split(args):
    need("ffmpeg"), need("ffprobe")
    media, out_dir = Path(args.media), Path(args.out)
    total = media_duration(media)
    ext = "opus" if args.format == "opus" else "mp3"
    rows = read_cuts(args.cuts)
    manifest = {}

    for i, (c, v, a, b, fl) in enumerate(rows, 1):
        if b > total + 0.5:
            sys.exit(f"ch{c} v{v}: end {fmt_time(b)} is past the end of the media ({fmt_time(total)})")
        vid = f"BG_{c:02d}_{v:02d}"
        rel_a = f"audio/verses/bg_{c:02d}_{v:02d}.{ext}"
        entry = {"chapter": c, "verse": v, "audio": rel_a, "video": None,
                 "start": round(a, 3), "end": round(b, 3), "duration_sec": round(b - a, 2), "flags": fl}
        pa = out_dir / rel_a
        pa.parent.mkdir(parents=True, exist_ok=True)
        if not (args.skip_existing and pa.exists()):
            run(audio_cmd(media, a, b, pa, args), args.dry_run)
        if args.video:
            rel_v = f"video/verses/bg_{c:02d}_{v:02d}.mp4"
            pv = out_dir / rel_v
            pv.parent.mkdir(parents=True, exist_ok=True)
            if not (args.skip_existing and pv.exists()):
                run(video_cmd(media, a, b, pv, args), args.dry_run)
            entry["video"] = rel_v
        manifest[vid] = entry
        if i % 25 == 0 or i == len(rows):
            print(f"  {i}/{len(rows)} verses")

    if args.chapters:
        for c, a, b in read_chapters(args.chapters, total):
            pc = out_dir / f"audio/chapters/bg_{c:02d}.{ext}"
            pc.parent.mkdir(parents=True, exist_ok=True)
            if not (args.skip_existing and pc.exists()):
                run(audio_cmd(media, a, b, pc, args), args.dry_run)
        print("  18 chapter files")

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        write_review(out_dir, manifest)
        print(f"\nDone -> {out_dir}  (manifest.json, review.html)")


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Split a Gita recitation into chapter + verse clips.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="write an empty chapters.csv")
    i.add_argument("path", nargs="?", default="chapters.csv")
    i.set_defaults(fn=cmd_init)

    d = sub.add_parser("detect", help="propose verse boundaries from pauses")
    d.add_argument("media")
    d.add_argument("chapters")
    d.add_argument("--out", default="cuts_draft.csv")
    d.add_argument("--noise", type=float, default=-35.0,
                   help="silence threshold in dB; raise toward -30 if music/room noise hides pauses")
    d.add_argument("--min-silence", type=float, default=0.35, help="shortest pause to consider (sec)")
    d.add_argument("--pad", type=float, default=0.25, help="breathing room kept around each verse (sec)")
    d.add_argument("--counts", help="18 comma-separated verse counts (default: 701-verse numbering)")
    d.add_argument("--std700", action="store_true",
                   help="video's ch13 has 34 verses; number them 13.2-13.35 to match 701-verse data")
    d.add_argument("--only", help="comma list of chapters to (re)detect, e.g. 2,5")
    d.set_defaults(fn=cmd_detect)

    s = sub.add_parser("split", help="cut the files using cuts.csv")
    s.add_argument("media")
    s.add_argument("cuts")
    s.add_argument("--chapters", help="chapters.csv - also writes per-chapter audio")
    s.add_argument("--out", default="assets")
    s.add_argument("--format", choices=["mp3", "opus"], default="mp3")
    s.add_argument("--bitrate", default="96k", help="e.g. 96k for mp3, 48k-64k for opus")
    s.add_argument("--stereo", action="store_true", help="keep stereo (default: mono)")
    s.add_argument("--video", action="store_true", help="also cut per-verse mp4 clips")
    s.add_argument("--video-height", type=int, default=480)
    s.add_argument("--skip-existing", action="store_true")
    s.add_argument("--dry-run", action="store_true", help="print ffmpeg commands only")
    s.set_defaults(fn=cmd_split)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()