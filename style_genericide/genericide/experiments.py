"""Running the market many times: regimes, null models, best responses, settling,
and three analyses of how much the results depend on the settings.

Every run is seeded, and runs are collected in a fixed order, so results are
identical whether they run on one processor or many.
"""

import copy
import math
import statistics as st
from multiprocessing import Pool

from .model import Market, with_params, AI_STRATEGIES
from .world import Rng

# How people behave, and how fast things happen. Run 1 sets each across a range;
# Papers 2 and 3 will measure the behavioral ones. The Sobol analysis varies these.
RANGES = {
    "nest": (0.2, 1.0),
    "human_premium": (0.0, 2.0),
    "identity_value": (0.0, 2.0),
    "credit_effect": (-1.0, 1.0),
    "credit_memory": (0.0, 1.0),
    "fan_share": (0.2, 0.8),
    "learn_lag": (1, 6),
    "familiarity_growth": (0.05, 0.3),
    "renewal_cost": (0.25, 4.0),
}
# How the market, the law and the learning work. Fixed in the main runs; the
# screening analysis and the robustness map vary these together with RANGES.
STRUCTURAL = {
    "royalty": (0.05, 0.4),
    "price_ai": (0.2, 1.5),
    "ai_cost": (0.01, 0.2),
    "max_closeness": (0.4, 1.0),
    "variety": (0.0, 0.6),
    "outdated_factor": (0.0, 1.0),
    "ai_concentration": (0.0, 2.0),
    "opt_out_leak": (0.0, 0.5),
    "reservation_share": (0.2, 0.9),
    "switch_familiarity": (0.1, 0.9),
    "window": (3, 10),
    "popularity_exponent": (0.3, 1.5),
    "explore_floor": (0.02, 0.1),
    "step": (0.1, 0.4),
}
ALL_RANGES = {**RANGES, **STRUCTURAL}
INTEGER = {"learn_lag", "window"}


def _nan_mean(values):
    vals = [v for v in values if not math.isnan(v)]
    return sum(vals) / len(vals) if vals else float("nan")


def summarize(m, records):
    """Outcomes over the measured periods, when agents act on what they learned.
    Money outcomes are per period, in the same units as prices. Outcomes about
    working artists are missing (NaN) when every artist has quit."""
    meas = [x for x in records if x["measuring"]]
    n = len(m.artists)

    def mean_over(f):
        return _nan_mean([f(x) for x in meas])

    def weighted(x, key, active_only=True):
        act = [a for a in x["artists"] if a["active"] or not active_only]
        w = sum(a["popularity"] for a in act)
        return sum(a[key] * a["popularity"] for a in act) / w if w else float("nan")

    top = max(range(n), key=lambda i: m.artists[i].popularity)
    income_ratio = [mean_over(lambda x, i=i: x["artists"][i]["income"]) / m.artists[i].baseline_income
                    for i in range(n)]
    by_pop = sorted(range(n), key=lambda i: -m.artists[i].popularity)
    base_human = sum(a.baseline_income + m.p.work_cost * 10 for a in m.artists) / m.p.price_human
    baseline_income = sum(a.baseline_income for a in m.artists)
    end = meas[-1]["artists"]
    active = [a for a in end if a["active"]]
    renewals = sum(1 for x in meas for a in x["artists"] if a["renewed"])
    buyer_gain = mean_over(lambda x: x["surplus"]) - m.baseline_surplus
    artist_change = mean_over(lambda x: sum(a["income"] for a in x["artists"])) - baseline_income
    ai_profit = mean_over(lambda x: x["ai_profit"])
    others = [i for i in range(n) if i != top]
    return {
        "recognizability": mean_over(lambda x: weighted(x, "recognizability")),
        "recognizability_top": mean_over(lambda x: x["artists"][top]["recognizability"]),
        "recognizability_others": mean_over(lambda x: sum(x["artists"][i]["recognizability"] for i in others) / len(others)),
        "diagnostic_ratio": mean_over(lambda x: weighted(x, "diagnostic_ratio")),
        "income_median": st.median(income_ratio),
        "income_top3": st.mean(income_ratio[i] for i in by_pop[:3]),
        "income_bottom3": st.mean(income_ratio[i] for i in by_pop[-3:]),
        "artists_left": len(active),
        "renewals_per_artist": renewals / len(active) * 100 / len(meas) if active else float("nan"),
        "opted_out": sum(a["opted_out"] for a in active),
        "human_sales": mean_over(lambda x: sum(a["human_sales"] for a in x["artists"])) / base_human,
        "buyer_gain": buyer_gain,
        "artist_income_change": artist_change,
        "ai_profit": ai_profit,
        "welfare_change": buyer_gain + artist_change + ai_profit,
        "artist_income_baseline": baseline_income,
        "ai_closeness": meas[-1]["phi"] or 0.0,
        "ai_volume": meas[-1]["volume"],
        "ai_generic": meas[-1]["generic"],
    }


def timeseries(m, records):
    out = []
    for x in records:
        act = [a for a in x["artists"] if a["active"]]
        w = sum(a["popularity"] for a in act)
        ratios = sorted(a["income"] / a["baseline"] for a in x["artists"])
        out.append({
            "t": x["t"],
            "recognizability": sum(a["recognizability"] * a["popularity"] for a in act) / w if w else float("nan"),
            "income_median": ratios[len(ratios) // 2 - 1] / 2 + ratios[len(ratios) // 2] / 2,
            "artists_left": len(act),
            "renewals": sum(1 for a in x["artists"] if a["renewed"]),
        })
    return out


def play(params, regime, seed, artist_policy="learn", settle_it=True, want_series=False):
    """One run. Agents learn; the measured periods are then played with the learned
    strategies held fixed ("learned"), and from the same point agents settle on
    best responses to one another ("settled"). Agents who never change, or who pick
    at random, have nothing to settle, so for them the two are the same."""
    m = Market(params, regime, seed, artist_policy)
    while not m.measuring():
        m.step()
    m.new_epoch()
    history, m.records = m.records, []
    _, _, c = replay(m, current_profile(m))
    learned = summarize(c, c.records)
    out = {"learned": learned, "settled": learned, "rounds": 0, "converged": True}
    if settle_it and artist_policy == "learn" and regime != "no_ai":
        out["settled"], out["rounds"], out["converged"] = settle_from(m)
    if want_series:
        out["series"] = timeseries(c, history + c.records)
    return out


def _run(job):
    params, regime, seed, artist_policy, settle_it, want_series = job
    return play(params, regime, seed, artist_policy, settle_it, want_series)


def run_jobs(jobs, processes=None, worker=_run):
    if processes == 1:
        return [worker(j) for j in jobs]
    with Pool(processes) as pool:
        return pool.map(worker, jobs, chunksize=2)


def regime_grid(params, regimes, seeds, artist_policy="learn", series=True, processes=None):
    """Every regime and seed: one row each for the learned and the settled outcomes."""
    jobs = [(params, r, s, artist_policy, True, series) for r in regimes for s in seeds]
    results = run_jobs(jobs, processes)
    rows, series_out = [], {}
    for (p, r, s, pol, _, _), res in zip(jobs, results):
        for stage in ("learned", "settled"):
            rows.append({"regime": r, "artists": pol, "stage": stage, "seed": s,
                         "settle_rounds": res["rounds"], "settled_fully": res["converged"], **res[stage]})
        if series:
            series_out.setdefault(r, []).append(res["series"])
    return rows, series_out


def mean_series(runs):
    """Average time series over seeds."""
    out = []
    for t in range(len(runs[0])):
        pts = [run[t] for run in runs]
        row = {"t": t}
        for k in pts[0]:
            if k != "t":
                row[k] = _nan_mean([p[k] for p in pts])
        out.append(row)
    return out


def percentile(sorted_values, q):
    """Linear interpolation between order statistics (the usual definition)."""
    pos = q * (len(sorted_values) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def describe(rows, keys, by=("regime", "artists", "stage")):
    """Mean and the middle 95% of seeds (2.5th to 97.5th percentile) for each outcome."""
    groups = {}
    for r in rows:
        groups.setdefault(tuple(r[b] for b in by), []).append(r)
    out = []
    for g, rs in groups.items():
        line = dict(zip(by, g))
        line["seeds"] = len(rs)
        for k in keys:
            vals = sorted(r[k] for r in rs if not math.isnan(r[k]))
            line[k] = sum(vals) / len(vals) if vals else float("nan")
            line[k + "_lo"] = percentile(vals, 0.025) if vals else float("nan")
            line[k + "_hi"] = percentile(vals, 0.975) if vals else float("nan")
        out.append(line)
    return out


# ----- best responses and settling -----------------------------------------------

def end_of_learning(params, regime, seed):
    """The market when learning ends, with every agent's first measured choice made."""
    m = Market(params, regime, seed)
    while not m.measuring():
        m.step()
    m.new_epoch()
    m.records = []              # not needed from here on; keeps copies small
    return m


def apply_profile(c, profile):
    """Put a profile of strategies into a market: the AI company's strategy, and for
    each artist a strategy index or "quit". An artist who had quit and is given a
    strategy comes back with a new signature."""
    if profile.get("ai") is not None:
        c.ai.current = profile["ai"]
    for i, s in profile.get("artists", {}).items():
        a = c.artists[i]
        if s == "quit":
            if a.active:
                a.active, a.exited_at = False, c.t
            continue
        if not a.active:
            c.come_back(a)
            a.returning = False
        a.strategy = s
        a.opted_out = c.strategies[s][1]


def replay(m, profile, frozen="actions"):
    """Play the measured periods from the end of learning with a profile in place.
    Returns each artist's mean income, the AI company's mean profit, and the records."""
    c = copy.deepcopy(m)
    c.frozen = frozen
    apply_profile(c, profile)
    for _ in range(m.p.measure_periods):
        c.step()
    n = m.p.measure_periods
    incomes = [sum(x["artists"][i]["income"] for x in c.records) / n for i in range(len(c.artists))]
    return incomes, sum(x["ai_profit"] for x in c.records) / n, c


def current_profile(m):
    return {"ai": m.ai.current,
            "artists": {a.idx: (a.strategy if a.active else "quit") for a in m.artists}}


def _options(m, a):
    return list(range(len(m.strategies))) + ["quit"]


def best_response_gaps(params, regime, seed):
    """How far the learned strategies are from best responses.

    Run the market to the end of learning, then replay the measured periods with
    one agent switched to each alternative. For an artist everyone else keeps
    their strategy; quitting is an alternative, and an artist who quit may come
    back. For the AI company, artists respond as they have learned to respond to
    whatever it does. A gap is what the agent would gain by switching alone: for
    an artist, as a share of its income before AI; for the AI company, as a share
    of the most it could earn."""
    m = end_of_learning(params, regime, seed)
    base = current_profile(m)
    base_incomes, _, _ = replay(m, base)
    gaps = {}
    for a in m.artists:
        best = base_incomes[a.idx]
        for opt in _options(m, a):
            if opt == base["artists"][a.idx]:
                continue
            prof = {"ai": base["ai"], "artists": {**base["artists"], a.idx: opt}}
            best = max(best, replay(m, prof)[0][a.idx])
        gaps[a.name] = (best - base_incomes[a.idx]) / a.baseline_income
    if m.ai_present() and m.ai_policy == "learn":
        _, base_ai, _ = replay(m, {"ai": base["ai"]}, frozen="policies")
        best = base_ai
        for k in range(len(AI_STRATEGIES)):
            if k != base["ai"]:
                best = max(best, replay(m, {"ai": k}, frozen="policies")[1])
        gaps["AI company"] = (best - base_ai) / best if best > 0 else 0.0
    return gaps


def _gaps(job):
    params, regime, seed = job
    g = best_response_gaps(params, regime, seed)
    artists = {k: v for k, v in g.items() if k != "AI company"}
    return {"regime": regime, "seed": seed,
            "largest_artist_gap": max(artists.values()),
            "artists_over_5_percent": sum(v > 0.05 for v in artists.values()),
            "ai_gap": g.get("AI company", 0.0)}


def gap_grid(params, regimes, seeds, processes=None):
    """best_response_gaps for every regime and seed, in a fixed order."""
    return run_jobs([(params, r, s) for r in regimes for s in seeds], processes, _gaps)


def settle(params, regime, seed, tol=0.01, max_rounds=8):
    return settle_from(end_of_learning(params, regime, seed), tol, max_rounds)


def settle_from(m, tol=0.01, max_rounds=8):
    """Starting from what the agents learned, let each agent in turn switch to its
    best strategy given everyone else's, until no one gains more than `tol` (as a
    share of an artist's income before AI, or of the AI company's profit) or
    `max_rounds` rounds pass. The result is a profile in which no agent can do much
    better alone: an equilibrium near where learning ended, if one is reached."""
    profile = current_profile(m)
    rounds, converged = 0, False
    while rounds < max_rounds and not converged:
        rounds += 1
        converged = True
        if m.ai_present() and m.ai_policy == "learn":
            _, now, _ = replay(m, profile)
            best_k, best = profile["ai"], now
            for k in range(len(AI_STRATEGIES)):
                if k != profile["ai"]:
                    v = replay(m, dict(profile, ai=k))[1]
                    if v > best:
                        best_k, best = k, v
            if best_k != profile["ai"] and best - now > tol * max(abs(best), 1e-9):
                profile = dict(profile, ai=best_k)
                converged = False
        for a in m.artists:
            now = replay(m, profile)[0][a.idx]
            best_opt, best = profile["artists"][a.idx], now
            for opt in _options(m, a):
                if opt != profile["artists"][a.idx]:
                    prof = dict(profile, artists={**profile["artists"], a.idx: opt})
                    v = replay(m, prof)[0][a.idx]
                    if v > best:
                        best_opt, best = opt, v
            if best_opt != profile["artists"][a.idx] and best - now > tol * a.baseline_income:
                profile = dict(profile, artists={**profile["artists"], a.idx: best_opt})
                converged = False
    _, _, c = replay(m, profile)
    return summarize(c, c.records), rounds, converged


# ----- sensitivity --------------------------------------------------------------

SENSITIVITY_OUTCOMES = {
    "recognizability": ("fair_use", "recognizability"),
    "income_median": ("fair_use", "income_median"),
    "artists_left": ("fair_use", "artists_left"),
    "credit_cut_in_renewals": ("attribution", "renewals_per_artist"),
    "licence_gain_in_income": ("license_shapley", "income_median"),
}
SOBOL_REGIMES = ["fair_use", "attribution", "license_shapley"]


def _outcome(table, key, j, name):
    regime, field = SENSITIVITY_OUTCOMES[name]
    v = table[(key, j, regime)][field]
    if name == "credit_cut_in_renewals":
        v = table[(key, j, "fair_use")][field] - v
    elif name.endswith("_gain_in_income"):
        v -= table[(key, j, "fair_use")][field]
    return v


def _point(base, names, u, ranges=ALL_RANGES):
    changes = {}
    for name, x in zip(names, u):
        lo, hi = ranges[name]
        v = lo + x * (hi - lo)
        changes[name] = int(round(v)) if name in INTEGER else v
    return with_params(base, **changes)


def _mean_over_seeds(results):
    keys = results[0].keys()
    return {k: _nan_mean([r[k] for r in results]) for k in keys}


def _seeded_jobs(points, regimes, seeds):
    jobs, index = [], []
    for key, params in points:
        for r in regimes:
            for s in seeds:
                jobs.append((params, r, s, "learn", True, False))
                index.append((key, r))
    return jobs, index


def _collect(jobs, index, processes):
    """Settled outcomes, averaged over seeds."""
    results = run_jobs(jobs, processes)
    grouped = {}
    for (key, r), res in zip(index, results):
        grouped.setdefault((key, r), []).append(res["settled"])
    return {k: _mean_over_seeds(v) for k, v in grouped.items()}


def sobol(base, n_base, seeds=(1,), processes=None):
    """First-order and total Sobol indices for each outcome (Saltelli design, Jansen
    estimator for the total index), from settled outcomes, averaged over the seeds. Rows
    whose outcome is missing (every artist quit) are left out of that outcome's
    indices, so those indices describe markets where someone is still working."""
    names = list(RANGES)
    d = len(names)
    rng = Rng("style-genericide", "sobol", n_base)
    A = [[rng.random() for _ in range(d)] for _ in range(n_base)]
    B = [[rng.random() for _ in range(d)] for _ in range(n_base)]
    mats = {"A": A, "B": B}
    for i in range(d):
        mats[f"AB{i}"] = [a[:i] + [b[i]] + a[i + 1:] for a, b in zip(A, B)]
    points = [((key, j), _point(base, names, u)) for key, mat in mats.items() for j, u in enumerate(mat)]
    jobs, index = _seeded_jobs(points, SOBOL_REGIMES, seeds)
    means = _collect(jobs, index, processes)
    table = {(key, j, r): v for ((key, j), r), v in means.items()}

    rows, samples = [], []
    for name in SENSITIVITY_OUTCOMES:
        val = {(key, j): _outcome(table, key, j, name) for key in mats for j in range(n_base)}
        ok = [j for j in range(n_base) if all(not math.isnan(val[(key, j)]) for key in mats)]
        fA = [val[("A", j)] for j in ok]
        fB = [val[("B", j)] for j in ok]
        var = st.pvariance(fA + fB)
        for i, pname in enumerate(names):
            fAB = [val[(f"AB{i}", j)] for j in ok]
            s1, st_ = _indices(fA, fB, fAB, var)
            lo1, hi1, lot, hit = _boot(fA, fB, fAB, len(ok))
            rows.append({"outcome": name, "parameter": pname, "rows_used": len(ok),
                         "first_order": s1, "first_order_lo": lo1, "first_order_hi": hi1,
                         "total": st_, "total_lo": lot, "total_hi": hit})
    for key in ("A", "B"):
        for j, u in enumerate(mats[key]):
            p = _point(base, names, u)
            samples.append({"matrix": key, "row": j, **{n: getattr(p, n) for n in names},
                            **{o: _outcome(table, key, j, o) for o in SENSITIVITY_OUTCOMES}})
    return rows, samples


def _indices(fA, fB, fAB, var):
    n = len(fA)
    if var == 0 or n == 0:
        return 0.0, 0.0
    s1 = sum(b * (ab - a) for a, b, ab in zip(fA, fB, fAB)) / n / var
    st_ = sum((a - ab) ** 2 for a, ab in zip(fA, fAB)) / (2 * n) / var
    return s1, st_


def _boot(fA, fB, fAB, n, reps=200):
    rng = Rng("style-genericide", "bootstrap", n)
    s1s, sts = [], []
    for _ in range(reps):
        idx = [int(rng.random() * n) for _ in range(n)]
        a, b, ab = [fA[i] for i in idx], [fB[i] for i in idx], [fAB[i] for i in idx]
        s1, st_ = _indices(a, b, ab, st.pvariance(a + b))
        s1s.append(s1)
        sts.append(st_)
    s1s.sort()
    sts.sort()
    return (percentile(s1s, 0.025), percentile(s1s, 0.975), percentile(sts, 0.025), percentile(sts, 0.975))


def noise_share(base, n_points=32, seeds=tuple(range(1, 9)), processes=None):
    """How much of each outcome's variation comes from chance (the seed) rather than
    the settings: at n_points random settings, run several seeds each; the share is
    the average variance across seeds divided by the total variance."""
    names = list(RANGES)
    rng = Rng("style-genericide", "noise", n_points)
    points = [(("N", j), _point(base, names, [rng.random() for _ in names])) for j in range(n_points)]
    jobs, index = _seeded_jobs(points, SOBOL_REGIMES, seeds)
    results = run_jobs(jobs, processes)
    per = {}
    for (key, r), res in zip(index, results):
        per.setdefault((key, r), []).append(res["settled"])
    rows = []
    for name in SENSITIVITY_OUTCOMES:
        regime, field = SENSITIVITY_OUTCOMES[name]
        groups = []
        for j in range(n_points):
            vals = []
            for s in range(len(seeds)):
                table = {(("N", j), r): per[(("N", j), r)][s] for r in SOBOL_REGIMES}
                v = table[(("N", j), regime)][field]
                if name == "credit_cut_in_renewals":
                    v = table[(("N", j), "fair_use")][field] - v
                elif name.endswith("_gain_in_income"):
                    v -= table[(("N", j), "fair_use")][field]
                vals.append(v)
            vals = [v for v in vals if not math.isnan(v)]
            if len(vals) >= 2:
                groups.append(vals)
        allv = [v for g in groups for v in g]
        within = st.mean(st.pvariance(g) for g in groups)
        rows.append({"outcome": name, "points": len(groups), "seeds": len(seeds),
                     "noise_share": within / st.pvariance(allv) if st.pvariance(allv) else 0.0})
    return rows


# ----- screening and the robustness map -------------------------------------------

SCREEN_REGIMES = ["fair_use", "opt_out", "license_shapley", "attribution"]
SCREEN_OUTCOMES = {
    "recognizability": ("fair_use", "recognizability"),
    "income_median": ("fair_use", "income_median"),
    "artists_left": ("fair_use", "artists_left"),
    "opt_out_gain_in_income": ("opt_out", "income_median"),
    "licence_gain_in_income": ("license_shapley", "income_median"),
    "credit_cut_in_renewals": ("attribution", "renewals_per_artist"),
}


def _screen_value(t, name):
    regime, field = SCREEN_OUTCOMES[name]
    v = t[regime][field]
    if name == "credit_cut_in_renewals":
        v = t["fair_use"][field] - v
    elif name.endswith("_gain_in_income"):
        v -= t["fair_use"][field]
    return v


def morris(base, trajectories=16, levels=4, processes=None):
    """Elementary-effects screening (Morris, 1991; mu* of Campolongo, Cariboni and
    Saltelli, 2007) over every setting in ALL_RANGES. Each trajectory changes one
    setting at a time by two-thirds of its range. mu* is the mean absolute change
    in an outcome per such step, here divided by the outcome's standard deviation
    across all points so outcomes can be compared."""
    names = list(ALL_RANGES)
    k = len(names)
    delta = levels / (2 * (levels - 1))
    rng = Rng("style-genericide", "morris", trajectories)
    grid = [i / (levels - 1) for i in range(levels)]
    trajs = []
    for _ in range(trajectories):
        x = [rng.choice([g for g in grid if g + delta <= 1 + 1e-9]) for _ in names]
        order = rng.shuffle(list(range(k)))
        pts = [list(x)]
        for i in order:
            x = list(x)
            x[i] += delta
            pts.append(x)
        trajs.append((order, pts))
    points = [((t, j), _point(base, names, u)) for t, (_, pts) in enumerate(trajs) for j, u in enumerate(pts)]
    jobs, index = _seeded_jobs(points, SCREEN_REGIMES, (1,))
    means = _collect(jobs, index, processes)
    values = {name: {} for name in SCREEN_OUTCOMES}
    for (t, j), _ in points:
        t_regimes = {r: means[((t, j), r)] for r in SCREEN_REGIMES}
        for name in SCREEN_OUTCOMES:
            values[name][(t, j)] = _screen_value(t_regimes, name)
    rows = []
    for name in SCREEN_OUTCOMES:
        allv = [v for v in values[name].values() if not math.isnan(v)]
        sd = st.pstdev(allv) or 1.0
        effects = {p: [] for p in names}
        for t, (order, _) in enumerate(trajs):
            for step, i in enumerate(order):
                a, b = values[name][(t, step)], values[name][(t, step + 1)]
                if not (math.isnan(a) or math.isnan(b)):
                    effects[names[i]].append((b - a) / delta / sd)
        for p in names:
            e = effects[p]
            rows.append({"outcome": name, "parameter": p, "group": "behavior" if p in RANGES else "market, law or learning",
                         "mu_star": sum(abs(v) for v in e) / len(e) if e else float("nan"),
                         "mu": sum(e) / len(e) if e else float("nan"),
                         "sigma": st.pstdev(e) if len(e) > 1 else float("nan"), "effects": len(e)})
    return rows


ROBUSTNESS_REGIMES = [("fair_use", "learn"), ("fair_use", "keep"), ("opt_out", "learn"),
                      ("license_loo", "learn"), ("license_shapley", "learn"),
                      ("license_participation", "learn"), ("attribution", "learn")]

def _cmp(op, a, b):
    """A comparison that is undecided (None) when either side is missing."""
    if math.isnan(a) or math.isnan(b):
        return None
    return {"<": a < b, "<=": a <= b, ">=": a >= b, ">": a > b, "==": a == b}[op]


# Each claim is a yes or no at one setting of everything. Set before the second
# version of Run 1 was run.
CLAIMS = {
    "imitation erodes styles that never change (most popular artist below 0.9)":
        lambda t: _cmp("<", t[("fair_use", "keep")]["recognizability_top"], 0.9),
    "the most popular artist's style erodes most":
        lambda t: _cmp("<=", t[("fair_use", "keep")]["recognizability_top"],
                       t[("fair_use", "keep")]["recognizability_others"]),
    "artists who respond keep their styles recognizable (0.9 or more)":
        lambda t: _cmp(">=", t[("fair_use", "learn")]["recognizability"], 0.9),
    "artists lose income under fair use":
        lambda t: _cmp("<", t[("fair_use", "learn")]["income_median"], 1.0),
    "opt-out gives artists the highest median income of the regimes with AI":
        lambda t: _cmp(">=", t[("opt_out", "learn")]["income_median"], max(
            t[(r, "learn")]["income_median"] for r in ("fair_use", "license_loo", "license_shapley", "attribution"))),
    "a Shapley licence keeps at least as many artists working as fair use":
        lambda t: _cmp(">=", t[("license_shapley", "learn")]["artists_left"], t[("fair_use", "learn")]["artists_left"]),
    "a Shapley licence keeps at least as many artists working as leave-one-out":
        lambda t: _cmp(">=", t[("license_shapley", "learn")]["artists_left"], t[("license_loo", "learn")]["artists_left"]),
    "under the participation rule the AI company makes nothing":
        lambda t: _cmp("==", t[("license_participation", "learn")]["ai_volume"], 0),
    "crediting the artist means fewer new signatures":
        lambda t: _cmp("<", t[("attribution", "learn")]["renewals_per_artist"],
                       t[("fair_use", "learn")]["renewals_per_artist"]),
    "buyers gain under fair use":
        lambda t: _cmp(">", t[("fair_use", "learn")]["buyer_gain"], 0.0),
    "total welfare rises under fair use (buyers, artists and the AI company together)":
        lambda t: _cmp(">", t[("fair_use", "learn")]["welfare_change"], 0.0),
}


def robustness_map(base, n_points=200, processes=None):
    """At n_points settings drawn by Latin hypercube sampling over everything in
    ALL_RANGES, run every regime once (settled outcomes) and record whether each claim holds. The
    share of settings where a claim holds says how much it depends on the settings."""
    names = list(ALL_RANGES)
    rng = Rng("style-genericide", "robustness", n_points)
    cols = []
    for _ in names:
        perm = rng.shuffle(list(range(n_points)))
        cols.append([(perm[j] + rng.random()) / n_points for j in range(n_points)])
    points = [(j, _point(base, names, [c[j] for c in cols])) for j in range(n_points)]
    jobs = [(p, r, 1, pol, True, False) for _, p in points for r, pol in ROBUSTNESS_REGIMES]
    results = run_jobs(jobs, processes)
    per_point, rows = [], []
    for j, (_, p) in enumerate(points):
        t = {ROBUSTNESS_REGIMES[i]: results[j * len(ROBUSTNESS_REGIMES) + i]["settled"]
             for i in range(len(ROBUSTNESS_REGIMES))}
        line = {"point": j, **{n: getattr(p, n) for n in names}}
        for claim, test in CLAIMS.items():
            line[claim] = test(t)
        per_point.append(line)
    for claim in CLAIMS:
        vals = [r[claim] for r in per_point if r[claim] is not None]
        rows.append({"claim": claim, "points": len(vals), "share_holding": sum(vals) / len(vals) if vals else float("nan")})
    return rows, per_point


def robustness_by_setting(per_point):
    """For each claim and each setting: the share of points where the claim holds when
    the setting is in the lower half of its range, and in the upper half. A large
    difference means the claim turns on that setting."""
    rows = []
    for claim in CLAIMS:
        for name, (lo, hi) in ALL_RANGES.items():
            mid = (lo + hi) / 2
            low = [r[claim] for r in per_point if r[claim] is not None and r[name] < mid]
            high = [r[claim] for r in per_point if r[claim] is not None and r[name] >= mid]
            share_low = sum(low) / len(low) if low else float("nan")
            share_high = sum(high) / len(high) if high else float("nan")
            rows.append({"claim": claim, "setting": name, "share_low_half": share_low,
                         "share_high_half": share_high, "difference": share_high - share_low})
    return rows
