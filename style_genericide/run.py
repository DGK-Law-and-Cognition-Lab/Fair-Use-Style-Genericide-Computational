"""Run 1 of the style-genericide simulation (second version).

    python3 run.py

writes, into output/ (or the folder named by STYLE_GENERICIDE_OUT):

  params.json               every setting, and the ranges used by the analyses
  runs.csv                  one row per regime, artist behavior, stage (learned, settled) and seed
  regimes.csv               the same, averaged over seeds, with the 2.5th to 97.5th percentile of seeds
  timeseries.csv            recognizability, income and artists working, period by period
  best_response_gaps.csv    how much any agent could gain by switching alone, where learning ended
  sensitivity.csv           which behavioral settings each outcome depends on (Sobol indices)
  sensitivity_samples.csv   the settings and outcomes behind those indices
  noise.csv                 how much of each outcome's variation is chance rather than the settings
  screening.csv             every setting, behavioral or not, screened for influence (Morris)
  robustness.csv            the share of settings at which each claim holds
  robustness_points.csv     the settings and the yes or no for each claim
  robustness_by_setting.csv for each claim and setting, how often it holds in each half of the range
  published_models.csv      the learning agents inside two published models, against the papers' results
  fig1_recognizability.png, fig2_regimes.png, fig3_sensitivity.png, fig4_robustness.png
  MANIFEST.sha256           a checksum for every file above, and for the code that made them

Set SOBOL_N (default 512), MORRIS_R (default 12) or ROBUSTNESS_N (default 160) to
change the size of the analyses.

    python3 run.py --figures

redraws only the figures, from the saved tables, and updates MANIFEST.sha256. The
full run draws them the same way, so both give the same files.
"""

import csv
import dataclasses
import hashlib
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from genericide.model import Params, REGIMES  # noqa: E402
from genericide.experiments import (regime_grid, describe, mean_series, sobol, noise_share, morris,  # noqa: E402
                                    robustness_map, robustness_by_setting, gap_grid, RANGES, STRUCTURAL,
                                    SENSITIVITY_OUTCOMES, CLAIMS)
from genericide.published import report  # noqa: E402

SEEDS = list(range(1, 31))
KEYS = ["recognizability", "recognizability_top", "recognizability_others", "diagnostic_ratio",
        "income_median", "income_top3", "income_bottom3", "artists_left", "renewals_per_artist",
        "opted_out", "human_sales", "buyer_gain", "artist_income_change", "ai_profit", "welfare_change",
        "ai_closeness", "ai_volume", "ai_generic"]
LABELS = {"no_ai": "No AI", "fair_use": "Fair use", "opt_out": "Opt-out",
          "license_loo": "Licence, leave-one-out", "license_shapley": "Licence, Shapley",
          "license_participation": "Licence, participation", "attribution": "Credit the artist"}
SETTING_LABELS = {
    "nest": "How swappable AI and real works are", "human_premium": "Premium for human-made",
    "identity_value": "Value of a recognizable style", "credit_effect": "Credit's pull on buyers",
    "credit_memory": "Memory for credits", "fan_share": "Share of buyers who are fans",
    "learn_lag": "Time for AI to learn a style", "familiarity_growth": "Speed fans learn a new style",
    "renewal_cost": "Cost of a new signature"}


def write_csv(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})


def read_csv(path):
    """A saved table's rows, with numbers read back as numbers."""
    def value(v):
        try:
            return float(v)
        except ValueError:
            return v
    with open(path, newline="") as fh:
        return [{k: value(v) for k, v in r.items()} for r in csv.DictReader(fh)]


def percent(v):
    """A share as a whole percentage, halves rounded up (92.5 becomes 93, as in the README)."""
    return f"{math.floor(v * 100 + 0.5 + 1e-9):.0f}%"


def style_axes(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors="#555555", labelsize=8)
    ax.grid(color="#ececec", linewidth=0.6, zorder=0)


def figures(out, series, table, sens, robust, params):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans"})
    colours = {"No AI": "#999999", "Fair use, artists never change": "#D55E00",
               "Fair use": "#E69F00", "Credit the artist": "#0072B2", "Opt-out": "#009E73"}

    # Figure 1: does each style still point to its artist, while agents learn?
    fig, ax = plt.subplots(figsize=(6.2, 3.6), dpi=200)
    lines = [("No AI", series[("no_ai", "learn")]),
             ("Fair use, artists never change", series[("fair_use", "keep")]),
             ("Fair use", series[("fair_use", "learn")]),
             ("Opt-out", series[("opt_out", "learn")]),
             ("Credit the artist", series[("attribution", "learn")])]
    ends = []
    for name, s in lines:
        xs = [r["t"] for r in s]
        raw = [r["recognizability"] for r in s]
        ys = []
        for i in range(len(raw)):
            window = [v for v in raw[max(0, i - params.epoch + 1):i + 1] if not math.isnan(v)]
            ys.append(sum(window) / len(window) if window else float("nan"))
        ax.plot(xs, ys, color=colours[name], linewidth=1.4, zorder=3)
        ends.append([ys[-1], name, xs[-1]])
    ends.sort(reverse=True)
    for i in range(1, len(ends)):
        ends[i][0] = min(ends[i][0], ends[i - 1][0] - 0.06)
    for y, name, x in ends:
        ax.annotate(name, (x, y), xytext=(5, 0), textcoords="offset points",
                    va="center", fontsize=7.5, color=colours[name])
    ax.axvline(params.ai_arrives, color="#bbbbbb", linewidth=0.8, linestyle="--", zorder=1)
    ax.annotate("AI arrives", (params.ai_arrives, 0.02), xytext=(3, 0), textcoords="offset points",
                fontsize=7, color="#777777")
    ax.axvspan(params.ai_arrives + params.learn_periods, params.periods, color="#f4f4f4", zorder=0)
    ax.set_ylim(0, 1.15)
    ax.set_xlim(0, params.periods * 1.35)
    ax.set_xlabel("Period (while agents learn; averaged over each 48-period epoch and 30 seeds)",
                  color="#444444")
    ax.set_ylabel("Share of works with the signature\nthat are the artist's (1 = as before AI)",
                  color="#444444")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out / "fig1_recognizability.png", metadata={"Software": None})
    plt.close(fig)

    # Figure 2: what each regime does once agents have settled; open circles show where learning ended.
    order = ["no_ai", "fair_use", "opt_out", "license_loo", "license_shapley", "license_participation",
             "attribution"]
    rows = {(r["regime"], r["stage"]): r for r in table if r["artists"] == "learn"}
    panels = [("recognizability", "Styles point to\ntheir artists"),
              ("income_median", "Median artist's income\n(1 = as before AI)"),
              ("artists_left", "Artists still\nworking (of 12)"),
              ("welfare_change", "Change in total welfare\n(per period, money)")]
    fig, axes = plt.subplots(1, len(panels), figsize=(7.6, 3.0), dpi=200, sharey=True)
    for ax, (key, title) in zip(axes, panels):
        for y, reg in enumerate(order):
            s, l = rows[(reg, "settled")], rows[(reg, "learned")]
            if not math.isnan(s[key]):
                ax.plot([s[key + "_lo"], s[key + "_hi"]], [y, y], color="#9db7d5", linewidth=2.2, zorder=2)
                ax.scatter([s[key]], [y], color="#0072B2", s=18, zorder=4)
            if not math.isnan(l[key]):
                ax.scatter([l[key]], [y], facecolors="none", edgecolors="#555555", s=18, linewidths=0.8, zorder=3)
        ax.set_title(title, fontsize=8, color="#444444")
        style_axes(ax)
    axes[0].set_yticks(range(len(order)), [LABELS[r] for r in order])
    axes[0].invert_yaxis()
    fig.tight_layout()
    fig.savefig(out / "fig2_regimes.png", metadata={"Software": None})
    plt.close(fig)

    # Figure 3: which behavioral settings each outcome depends on (total Sobol index).
    outcomes = list(SENSITIVITY_OUTCOMES)
    names = list(RANGES)
    grid = [[next(r["total"] for r in sens if r["outcome"] == o and r["parameter"] == p) for o in outcomes]
            for p in names]
    fig, ax = plt.subplots(figsize=(6.4, 3.9), dpi=200)
    ax.imshow([[max(0.0, min(1.0, v)) for v in row] for row in grid], cmap="Blues", vmin=0, vmax=1,
              aspect="auto")
    for i, row in enumerate(grid):
        for j, v in enumerate(row):
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7,
                    color="white" if v > 0.55 else "#333333")
    col_labels = ["Styles point\nto artists", "Median\nincome", "Artists\nleft", "Credit's cut\nin renewals",
                  "Licence's gain\nin income"]
    ax.set_xticks(range(len(outcomes)), col_labels, fontsize=7.5)
    ax.set_yticks(range(len(names)), [SETTING_LABELS[n] for n in names], fontsize=7.5)
    ax.tick_params(length=0, colors="#444444")
    ax.set_xlabel("Share of each outcome's spread that the setting is involved in, alone or with others\n"
                  "(total Sobol index, 512 base samples)", color="#444444", fontsize=7.5)
    for side in ax.spines.values():
        side.set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "fig3_sensitivity.png", metadata={"Software": None})
    plt.close(fig)

    # Figure 4: the share of settings at which each claim holds.
    fig, ax = plt.subplots(figsize=(8.6, 3.9), dpi=200)
    claims = [r["claim"] for r in robust]
    shares = [r["share_holding"] for r in robust]
    ys = list(range(len(claims)))
    ax.barh(ys, shares, color="#9db7d5", zorder=3, height=0.6)
    for y, v in zip(ys, shares):
        ax.annotate(percent(v), (v, y), xytext=(4, 0), textcoords="offset points", va="center",
                    fontsize=7, color="#444444")
    ax.set_yticks(ys, [c[0].upper() + c[1:] for c in claims], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.12)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1], ["0", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Share of sampled settings at which the claim holds", color="#444444", fontsize=8)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out / "fig4_robustness.png", metadata={"Software": None}, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def draw(out, params):
    """The figures, drawn from the saved tables, so that redrawing them alone
    (run.py --figures) gives the same files as a full run."""
    series = {}
    for r in read_csv(out / "timeseries.csv"):
        series.setdefault((r["regime"], r["artists"]), []).append(r)
    figures(out, series, read_csv(out / "regimes.csv"), read_csv(out / "sensitivity.csv"),
            read_csv(out / "robustness.csv"), params)


def code_files():
    """The files the outputs are made from."""
    return sorted([*HERE.glob("*.py"), *HERE.glob("genericide/*.py"), HERE / "requirements.txt"])


def code_lines():
    return [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  code/{p.relative_to(HERE).as_posix()}"
            for p in code_files()]


def manifest(out):
    """A checksum for every output, and for every code file the outputs were made with,
    so check.py can tell when code and outputs no longer belong together (for example,
    after a file-sync program restores an old copy of one of them)."""
    lines = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.sha256":
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(out).as_posix()}")
    (out / "MANIFEST.sha256").write_text("\n".join(lines + code_lines()) + "\n")


def main():
    out = Path(os.environ.get("STYLE_GENERICIDE_OUT", HERE / "output"))
    out.mkdir(parents=True, exist_ok=True)
    params = Params()
    if "--figures" in sys.argv:
        draw(out, params)
        manifest(out)
        print(f"redrew the figures in {out}")
        return
    n_sobol = int(os.environ.get("SOBOL_N", 512))
    n_morris = int(os.environ.get("MORRIS_R", 12))
    n_robust = int(os.environ.get("ROBUSTNESS_N", 160))
    (out / "params.json").write_text(json.dumps({
        "defaults": dataclasses.asdict(params), "periods": params.periods,
        "behavior_ranges": RANGES, "market_law_learning_ranges": STRUCTURAL,
        "sobol_base_samples": n_sobol, "morris_trajectories": n_morris, "robustness_points": n_robust,
        "seeds": SEEDS, "claims": list(CLAIMS)}, indent=1) + "\n")

    rows, series = [], {}
    for policy, regimes in (("learn", REGIMES), ("keep", ["fair_use", "attribution"]),
                            ("random", ["fair_use"])):
        r, s = regime_grid(params, regimes, SEEDS, artist_policy=policy)
        rows += r
        for reg, runs in s.items():
            series[(reg, policy)] = mean_series(runs)
    write_csv(out / "runs.csv", rows)
    table = describe(rows, KEYS)
    write_csv(out / "regimes.csv", table)
    ts_rows = [{"regime": reg, "artists": pol, **row} for (reg, pol), s in series.items() for row in s]
    write_csv(out / "timeseries.csv", ts_rows)

    write_csv(out / "best_response_gaps.csv", gap_grid(params, [r for r in REGIMES if r != "no_ai"], SEEDS))
    write_csv(out / "published_models.csv", report())

    sens, samples = sobol(params, n_sobol)
    write_csv(out / "sensitivity.csv", sens)
    write_csv(out / "sensitivity_samples.csv", samples)
    write_csv(out / "noise.csv", noise_share(params, n_points=24, seeds=tuple(range(1, 7))))
    write_csv(out / "screening.csv", morris(params, trajectories=n_morris))
    robust, points = robustness_map(params, n_points=n_robust)
    write_csv(out / "robustness.csv", robust)
    write_csv(out / "robustness_points.csv", points)
    write_csv(out / "robustness_by_setting.csv", robustness_by_setting(points))

    draw(out, params)
    manifest(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
