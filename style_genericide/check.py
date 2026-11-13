"""Check the style-genericide simulation. Run after run.py:

    python3 check.py            # a few minutes
    python3 check.py --rebuild  # also rebuild everything and compare checksums (about an hour more)

Each check prints PASS or FAIL. The field check compares the simulation with
what Kim, Jin and Lee (2026) measured on Pixiv, in direction only. The
published-model checks put the simulation's learning agents into two published
models and compare where they end with the papers' results.
"""

import csv
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from genericide.model import Params, Market  # noqa: E402
from genericide.world import OWNER_RATE, BORROW_RATE  # noqa: E402
from genericide.experiments import regime_grid, best_response_gaps, play  # noqa: E402
from genericide.published import report  # noqa: E402

OUT = Path(os.environ.get("STYLE_GENERICIDE_OUT", HERE / "output"))
failures = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def code_matches_outputs():
    """The code now in the folder is the code the saved outputs were made with."""
    from run import code_lines
    saved = [l for l in (OUT / "MANIFEST.sha256").read_text().splitlines() if "  code/" in l]
    now = code_lines()
    return saved == now, sorted({l.split("  ")[1] for l in set(saved) ^ set(now)})


def no_ai_is_flat():
    m = Market(Params(), "no_ai", 1)
    recs = m.run()
    r_ok = all(abs(a["recognizability"] - 1.0) < 1e-12 for x in recs for a in x["artists"])
    income_ok = all(abs(a["income"] - a["baseline"]) < 1e-9 for x in recs for a in x["artists"])
    still = all(a["active"] and not a["renewed"] for x in recs for a in x["artists"])
    return r_ok and income_ok and still


def recognizability_matches_formula():
    """With artists who never change and a fixed AI strategy, every artist's
    recognizability must equal the formula worked out by hand: of the works in the
    window that carry the signature, the share the artist made, over its value before AI."""
    p = Params()
    phi, vol, generic = 0.7, 960, 0.3
    m = Market(p, "fair_use", 1, artist_policy="keep", ai_policy=(phi, vol, generic))
    recs = m.run()
    weights = {a.idx: a.popularity ** p.ai_concentration for a in m.artists}
    total = sum(weights.values())
    w = p.window
    cue0 = (w * 10 * OWNER_RATE) / (w * 10 * OWNER_RATE + w * BORROW_RATE * 110)
    worst = 0.0
    for a in m.artists:
        own = w * 10 * OWNER_RATE
        others = w * (BORROW_RATE * 110 + (1 - generic) * vol * weights[a.idx] / total * phi * OWNER_RATE)
        expected = own / (own + others) / cue0
        worst = max(worst, abs(expected - recs[-1]["artists"][a.idx]["recognizability"]))
    return worst < 1e-9, worst


def demand_matches_formula():
    """Before AI, a fan buys the artist's work with logit probability e^V / (1 + e^V),
    and a decorator buys a human work with e^U / (1 + e^U)."""
    p = Params()
    m = Market(p, "no_ai", 1)
    v = p.fan_quality + p.identity_value + p.human_premium - p.price_human
    u = p.decor_quality + p.human_premium - p.price_human
    fan_p = math.exp(v) / (1 + math.exp(v))
    decor_p = math.exp(u) / (1 + math.exp(u))
    worst = 0.0
    for a in m.artists:
        expected = (p.n_buyers * p.fan_share * a.popularity * fan_p
                    + p.n_buyers * (1 - p.fan_share) * decor_p * a.popularity)
        worst = max(worst, abs(expected - (a.baseline_income + p.work_cost * 10) / p.price_human))
    return worst < 1e-9, worst


def deterministic():
    p = Params()
    a = Market(p, "attribution", 7).run()
    b = Market(p, "attribution", 7).run()
    one, _ = regime_grid(p, ["fair_use", "opt_out"], [1, 2], series=False, processes=1)
    many, _ = regime_grid(p, ["fair_use", "opt_out"], [1, 2], series=False, processes=2)
    return a == b and one == many


def saved_runs_match():
    rows = {(r["regime"], r["artists"], r["stage"], r["seed"]): r for r in csv.DictReader(open(OUT / "runs.csv"))}
    fresh, _ = regime_grid(Params(), ["fair_use", "license_shapley"], [1, 2], series=False, processes=1)
    for f in fresh:
        saved = rows[(f["regime"], f["artists"], f["stage"], str(f["seed"]))]
        for k, v in f.items():
            if isinstance(v, float) and not math.isnan(v) and abs(round(v, 6) - float(saved[k])) > 1e-9:
                return False, k
    return True, ""


def settling_reached():
    """Settling, in which agents in turn switch to best responses, reached a profile in
    which no agent gains more than 1 percent by switching alone, in every run."""
    rows = [r for r in csv.DictReader(open(OUT / "runs.csv")) if r["stage"] == "settled" and r["artists"] == "learn"]
    bad = [f'{r["regime"]} {r["seed"]}' for r in rows if r["settled_fully"] != "True"]
    return not bad, f"{len(bad)} of {len(rows)} runs did not settle: " + ", ".join(bad[:5])


def field_direction():
    """Pixiv (Kim, Jin and Lee, 2026): human illustrators sold less after AI arrived.
    Here: sales of human work fall under fair use in every seed, at both stages."""
    rows = [r for r in csv.DictReader(open(OUT / "runs.csv")) if r["regime"] == "fair_use" and r["artists"] == "learn"]
    return all(float(r["human_sales"]) < 1 for r in rows), ""


def best_responses():
    """The best-response table (how far agents were from their best choices where
    learning ended) matches a fresh replay. The gaps themselves are reported in the
    README, not checked: trial-and-error learning on the market's budget does not
    reliably reach best responses (opt-out especially), which is why the settled
    outcomes, which settling_reached checks, are the main results."""
    rows = list(csv.DictReader(open(OUT / "best_response_gaps.csv")))
    notes = []
    for regime in sorted({r["regime"] for r in rows}):
        rs = [r for r in rows if r["regime"] == regime]
        artists = sorted(float(r["largest_artist_gap"]) for r in rs)
        notes.append(f"{regime}: median largest artist gap {artists[len(rs) // 2]:.3f}")
    fresh = best_response_gaps(Params(), "opt_out", 1)
    saved = next(r for r in rows if r["regime"] == "opt_out" and r["seed"] == "1")
    artists = max(v for k, v in fresh.items() if k != "AI company")
    ai = fresh.get("AI company", 0.0)
    ok = (abs(round(artists, 6) - float(saved["largest_artist_gap"])) < 1e-9
          and abs(round(ai, 6) - float(saved["ai_gap"])) < 1e-9)
    return ok, "; ".join(notes)


def published_models():
    """The learning agents inside Keinan and Ben-Porat (2026) and Yang and Zhang (2025)."""
    fresh = report()
    saved = list(csv.DictReader(open(OUT / "published_models.csv")))
    same = len(fresh) == len(saved) and all(
        (math.isnan(f["simulated"]) and saved_row["simulated"] == "nan")
        or abs(round(f["simulated"], 6) - float(saved_row["simulated"])) < 1e-9
        for f, saved_row in zip(fresh, saved))

    def rows(result=None, case=None, quantity=None):
        return [r for r in fresh if (result is None or r["result"].startswith(result))
                and (case is None or r["case"].startswith(case)) and (quantity is None or r["quantity"] == quantity)]

    def value(case, quantity):
        return next(r["simulated"] for r in fresh if r["case"] == case and r["quantity"] == quantity)

    results = {}
    results["saved table matches a fresh run"] = same
    results["Lemma 2 (share exactly when rho exceeds tau) holds in every profile"] = all(
        r["simulated"] == 0 for r in rows(result="Lemma 2", quantity="profiles where sharing pays but rho <= tau, or the reverse"))
    quality = rows(quantity="mean quality")
    results["quality within one grid step (0.5) of the equilibrium formula"] = all(
        abs(r["simulated"] - r["published"]) <= 0.5 for r in quality)
    results["quality rises with the revenue share (Proposition 7)"] = all(
        b["simulated"] > a["simulated"] for a, b in zip(quality, quality[1:]))
    results["no creator gains more than 2 percent by changing quality alone"] = all(
        r["simulated"] <= 0.02 for r in rows(quantity="largest gain from changing quality alone (share of pay)"))
    results["sharing: nobody at rho 0, everybody at rho 1 (Proposition 4)"] = (
        value("rho = 0.0, qualities fixed", "creators sharing") == 0
        and value("rho = 1.0, qualities fixed", "creators sharing") == 12)
    # At the full learning budget only; the 100-round rows show the market's budget and are reported, not tested.
    results["sharing: no creator gains more than 3 percent by switching alone (1,500 rounds)"] = all(
        r["simulated"] <= 0.03 for r in rows(quantity="largest gain from switching alone (share of pay)")
        if "100 rounds" not in r["result"])
    results["quality and sharing: sharing matches the full-sharing condition (Definition 1)"] = all(
        r["simulated"] == r["published"] for r in rows(result="Definition 1"))
    results["Yang and Zhang thresholds within one skill step (0.005)"] = all(
        abs(r["simulated"] - r["published"]) <= 0.005 + 1e-9 for r in rows(result="Proposition 4.1"))
    yz = rows(case="plenty") + rows(case="no old")
    results["Yang and Zhang outcomes within 0.005 of the paper's equilibrium"] = all(
        abs(r["simulated"] - r["published"]) <= 0.005 + 1e-9 for r in yz)
    plenty = {f: {r["quantity"]: r["simulated"] for r in rows(case=f"plenty of old data, fee {f}")}
              for f in ("0.0", "0.1", "0.2")}
    results["plenty of old data: free training is best for AI quality, creators, consumers and welfare (Proposition 5.1)"] = all(
        plenty["0.0"][q] >= max(plenty["0.1"][q], plenty["0.2"][q])
        for q in ("AI quality, period 2", "high-quality AI works, period 2", "creator income, period 2",
                  "welfare, period 2", "consumer surplus, period 2"))
    scarce = {f: {r["quantity"]: r["simulated"] for r in rows(case=f"no old data, fee {f}")}
              for f in ("0.0", "0.2", "1.0")}
    results["no old data: a moderate fee gives better AI than free training (Proposition 5.5, Figure 7)"] = (
        scarce["0.2"]["AI quality, period 2"] > scarce["0.0"]["AI quality, period 2"])
    results["no old data: a very high fee stops training and leaves period 1 as under free training (Proposition 5.6)"] = (
        abs(scarce["1.0"]["AI quality, period 2"] - 0.4) < 1e-12
        and scarce["1.0"]["lowest skill that makes by hand, period 1"]
        == scarce["0.0"]["lowest skill that makes by hand, period 1"])
    results["no old data: free training beats a very high fee for creators and welfare (Proposition 5.6)"] = (
        scarce["0.0"]["creator income, period 2"] >= scarce["1.0"]["creator income, period 2"]
        and scarce["0.0"]["welfare, period 2"] >= scarce["1.0"]["welfare, period 2"])
    return results


def rebuild_identical():
    """Rebuild everything in a temporary folder; return whether every checksum
    matches the saved manifest, and the names of any files that differ."""
    def sums(text):
        return dict(reversed(line.split("  ", 1)) for line in text.splitlines() if line)
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, STYLE_GENERICIDE_OUT=tmp)
        subprocess.run([sys.executable, str(HERE / "run.py")], env=env, check=True, capture_output=True)
        fresh, saved = sums((Path(tmp) / "MANIFEST.sha256").read_text()), sums((OUT / "MANIFEST.sha256").read_text())
    differ = sorted(name for name in fresh.keys() | saved.keys() if fresh.get(name) != saved.get(name))
    return not differ, differ


def main():
    ok, changed = code_matches_outputs()
    check("the code is the code the saved outputs were made with", ok,
          "differs: " + ", ".join(changed) + "; run run.py")
    check("no AI: recognizability stays 1, incomes stay at baseline, no one renews or quits", no_ai_is_flat())
    ok, worst = recognizability_matches_formula()
    check("recognizability matches the hand-worked formula (fixed strategies)", ok, f"largest gap {worst:.2e}")
    ok, worst = demand_matches_formula()
    check("purchases before AI match the logit formula", ok, f"largest gap {worst:.2e}")
    check("same seed gives the same run; one processor and many give the same rows", deterministic())
    ok, key = saved_runs_match()
    check("saved runs.csv matches a fresh run", ok, key)
    ok, detail = settling_reached()
    check("settling reached a stable profile in every run", ok, detail)
    ok, detail = field_direction()
    check("field direction (Pixiv): sales of human work fall under fair use", ok, detail)
    ok, detail = best_responses()
    check("the best-response table matches a fresh replay", ok, detail)
    print("      where learning ended: " + detail)
    for name, ok in published_models().items():
        check("published models: " + name, ok)
    if "--rebuild" in sys.argv:
        ok, differ = rebuild_identical()
        check("a fresh build gives byte-identical files", ok, "differ: " + ", ".join(differ))
    print(f"\n{len(failures)} failed" if failures else "\nall checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
