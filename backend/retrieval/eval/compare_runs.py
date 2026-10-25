"""Compare retrieval evaluation runs against a baseline over non-routed questions.
Run from repo root:
    python retrieval/eval/compare_runs.py --baseline retrieval/eval/results/bge-m3_dense.json retrieval/eval/results/bge-m3_hybrid.json ...
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding="utf-8")


def paired_bootstrap_ci(diffs: list[float], n_resamples: int = 10000, seed: int = 42, ci: float = 95.0):
    """Compute paired bootstrap confidence interval of mean difference."""
    arr = np.asarray(diffs, dtype=float)
    n = len(arr)
    if n == 0:
        return 0.0, 0.0, 0.0
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n, size=(n_resamples, n))
    resampled_means = np.mean(arr[indices], axis=1)
    mean_diff = float(np.mean(arr))
    alpha = (100.0 - ci) / 2.0
    ci_lower = float(np.percentile(resampled_means, alpha))
    ci_upper = float(np.percentile(resampled_means, 100.0 - alpha))
    return mean_diff, ci_lower, ci_upper


def compute_wins_losses_ties(cfg_vals: list[float], base_vals: list[float], eps: float = 1e-9):
    wins, losses, ties = 0, 0, 0
    for c, b in zip(cfg_vals, base_vals):
        if c > b + eps:
            wins += 1
        elif c < b - eps:
            losses += 1
        else:
            ties += 1
    return wins, losses, ties


def summarize_rows(title: str, rows: list[dict]):
    groups = defaultdict(list)
    for r in rows:
        groups[r["type"]].append(r)
        groups["ALL"].append(r)
    print(f"\n=== {title} (n={len(rows)} non-routed) ===")
    print(f"{'type':<20}{'n':>3}  {'hit@5':>6}  {'recall@5':>8}  {'MRR@10':>6}")
    for t in [*sorted(g for g in groups if g != "ALL"), "ALL"]:
        g = groups[t]
        n = len(g)
        print(f"{t:<20}{n:>3}  {sum(x['hit'] for x in g)/n:>6.2f}  "
              f"{sum(x['recall'] for x in g)/n:>8.2f}  {sum(x['rr'] for x in g)/n:>6.2f}")


def compare_runs(baseline_path: Path, run_paths: list[Path]):
    with open(baseline_path, encoding="utf-8") as f:
        base_all = json.load(f)
    base_qs = [r["q"] for r in base_all]

    # Verify all files contain the same question set
    runs_data = []
    for p in run_paths:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        qs = [r["q"] for r in data]
        if qs != base_qs:
            raise ValueError(
                f"Question set mismatch between baseline ({baseline_path.name}) and {p.name}:\n"
                f"Baseline has {len(base_qs)} questions, {p.name} has {len(qs)} questions."
            )
        runs_data.append((p.name, data))

    # Filter non-routed questions
    base_non_routed = [r for r in base_all if not r.get("routed")]
    print(f"Loaded baseline: {baseline_path.name} ({len(base_non_routed)} non-routed questions)")
    summarize_rows(f"BASELINE: {baseline_path.name}", base_non_routed)

    base_hit = [r["hit"] for r in base_non_routed]
    base_rec = [r["recall"] for r in base_non_routed]
    base_rr = [r["rr"] for r in base_non_routed]

    for name, data in runs_data:
        cfg_non_routed = [r for r in data if not r.get("routed")]
        summarize_rows(f"CONFIG: {name}", cfg_non_routed)

        cfg_hit = [r["hit"] for r in cfg_non_routed]
        cfg_rec = [r["recall"] for r in cfg_non_routed]
        cfg_rr = [r["rr"] for r in cfg_non_routed]

        # Paired comparisons vs baseline
        hit_w, hit_l, hit_t = compute_wins_losses_ties(cfg_hit, base_hit)
        rec_w, rec_l, rec_t = compute_wins_losses_ties(cfg_rec, base_rec)

        diff_rec = [c - b for c, b in zip(cfg_rec, base_rec)]
        diff_rr = [c - b for c, b in zip(cfg_rr, base_rr)]

        mean_diff_rec, ci_rec_low, ci_rec_high = paired_bootstrap_ci(diff_rec)
        mean_diff_rr, ci_rr_low, ci_rr_high = paired_bootstrap_ci(diff_rr)

        print(f"\n--- Paired Comparison vs Baseline: {name} vs {baseline_path.name} ---")
        print(f"  hit@5:    wins={hit_w:<2} losses={hit_l:<2} ties={hit_t:<2}")
        print(f"  recall@5: wins={rec_w:<2} losses={rec_l:<2} ties={rec_t:<2}")
        print(f"  recall@5 delta: {mean_diff_rec:+.4f} (95% CI: [{ci_rec_low:+.4f}, {ci_rec_high:+.4f}])")
        print(f"  MRR@10   delta: {mean_diff_rr:+.4f} (95% CI: [{ci_rr_low:+.4f}, {ci_rr_high:+.4f}])")


def main():
    ap = argparse.ArgumentParser(description="Compare retrieval eval runs against baseline over non-routed questions.")
    ap.add_argument("--baseline", type=Path, required=True, help="Baseline JSON result file.")
    ap.add_argument("runs", nargs="+", type=Path, help="One or more JSON result files to compare.")
    args = ap.parse_args()

    compare_runs(args.baseline, args.runs)


if __name__ == "__main__":
    main()
