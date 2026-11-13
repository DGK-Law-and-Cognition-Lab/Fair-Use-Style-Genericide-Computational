"""Reduced cases: the simulation's learning agents inside two published models.

Neither published model is a special case of the style-genericide market. Neither
has signatures, fans or imitation of one artist. So each check puts the agents
the market uses (model.Learner, with the market's learning settings) into the
published model's own game. It then asks two things. Do the agents end where the
paper's equilibrium says they should? Do they reproduce the paper's policy results?

Keinan and Ben-Porat (2026), "Strategic content creation with GenAI: To share or
not to share?", Proceedings of the ACM Web Conference 2026, 169-180
(arXiv:2505.16358v4). Creators choose how much to invest in quality and whether
to let a platform's AI train on their work. The platform pays sharers a fraction
rho of its AI revenue, split in proportion to the quality each shared.

Yang and Zhang (2024, revised 2025), "Generative AI and copyright: A dynamic
perspective" (arXiv:2402.17801v2). Over two periods, creators of different skill
choose to make nothing, make by hand or make with AI. Between the periods the AI
company trains on human work, paying f for each unit it uses.

Equation and proposition numbers below are the papers'.
"""

import math
from bisect import bisect_right
from dataclasses import dataclass, replace

from .model import Params, Learner
from .world import Rng


def learn(n_players, n_strategies, payoffs, seed_parts, rounds, measure, params=Params()):
    """Repeated play by the market's learners (model.Learner), with the market's
    exploration schedule and step size. Each round is one epoch. Nothing is
    explored in the measured rounds. Returns the strategy profiles of the measured rounds."""
    rng = Rng("published", *seed_parts)
    learners = [Learner(n_strategies, rng.shuffle(list(range(n_strategies)))) for _ in range(n_players)]
    allowed = list(range(n_strategies))
    measured = []
    for r in range(rounds + measure):
        explore = 0.0 if r >= rounds else max(params.explore_floor,
                                              params.explore_start * params.explore_decay ** r)
        for lr in learners:
            lr.close_epoch(params.step)
            lr.choose(rng, explore, allowed)
        profile = [lr.current for lr in learners]
        for lr, v in zip(learners, payoffs(profile)):
            lr.record(v)
        if r >= rounds:
            measured.append(profile)
    return measured


# ---------------------------------------------------------------------------
# Keinan and Ben-Porat (2026)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KBP:
    """The paper's simulation defaults (Section 5), with 12 creators for the 12 painters."""
    n: int = 12
    alpha: float = 0.5      # AI quality added per unit of shared quality
    mu: float = 100.0       # traffic scale
    gamma: float = 0.8      # how traffic grows with total quality
    theta: float = 1.5      # cost exponent: creator i pays a_i x^theta for quality x


def kbp_costs(game, lo=1.0, hi=10.0):
    """Cost coefficients drawn uniformly from [1, 10], as in the paper."""
    rng = Rng("published", "kbp-costs")
    return [rng.uniform(lo, hi) for _ in range(game.n)]


def kbp_utilities(game, a, x, s, rho):
    """Creators' utilities and the platform's revenue (Section 2).
    Creator i's share of attention is x_i / (total + Q_AI); the AI's is Q_AI / (total + Q_AI),
    of which i receives rho x_i s_i / shared. Q_AI times that share is alpha rho x_i s_i."""
    total = sum(x)
    shared = sum(xi * si for xi, si in zip(x, s))
    q_ai = game.alpha * shared
    denom = total + q_ai
    costs = [ai * xi ** game.theta for ai, xi in zip(a, x)]
    if denom <= 0:
        return [-c for c in costs], 0.0
    traffic = game.mu * total ** game.gamma
    u = [traffic * (xi + game.alpha * rho * xi * si) / denom - c for xi, si, c in zip(x, s, costs)]
    platform = traffic * q_ai * (1 - rho) / denom if shared > 0 else 0.0
    return u, platform


def kbp_threshold(game, x, s, i):
    """Lemma 2: creator i gains from sharing exactly when rho exceeds tau_i."""
    others = sum(x) - x[i]
    others_shared = sum(xj * sj for j, (xj, sj) in enumerate(zip(x, s)) if j != i)
    return x[i] / (x[i] + others + game.alpha * others_shared)


def _bisect(fn, lo, hi, iters=100):
    """Root of a function that is positive at lo and negative at hi."""
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if fn(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def kbp_best_quality(game, a_i, others, rho):
    """Best quality for a creator when everyone shares, given the others' total quality.
    Utility mu k z (z + R)^(gamma - 1) - a z^theta is strictly concave in z, k = (1 + alpha rho)/(1 + alpha)."""
    k = (1 + game.alpha * rho) / (1 + game.alpha)
    g, th = game.gamma, game.theta

    def slope(z):
        return game.mu * k * (z + others) ** (g - 2) * (others + g * z) - a_i * th * z ** (th - 1)

    hi = (game.mu * k / (a_i * th)) ** (1 / (th - g)) + 1.0
    return _bisect(slope, 1e-12, hi)


def kbp_ese(game, a, rho, tol=1e-12):
    """The unique equilibrium of the game in which everyone must share (Lemma 3),
    by damped best responses."""
    x = [1.0] * game.n
    for _ in range(10000):
        total = sum(x)
        new = [kbp_best_quality(game, a[i], total - x[i], rho) for i in range(game.n)]
        change = max(abs(u - v) for u, v in zip(new, x))
        x = [0.5 * u + 0.5 * v for u, v in zip(new, x)]
        if change < tol:
            break
    return x


def kbp_symmetric_ese(game, a, rho):
    """Closed form when every creator has the same cost coefficient a, from the
    first-order condition: x^(theta - gamma) = mu k n^(gamma - 1) (1 + (gamma - 1)/n) / (a theta)."""
    n, g, th = game.n, game.gamma, game.theta
    k = (1 + game.alpha * rho) / (1 + game.alpha)
    return (game.mu * k * n ** (g - 1) * (1 + (g - 1) / n) / (a * th)) ** (1 / (th - g))


def kbp_full_sharing_holds(game, a, rho):
    """Definition 1: everyone sharing at the enforced-sharing qualities is an
    equilibrium if no creator gains by withholding at any quality."""
    x = kbp_ese(game, a, rho)
    s = [1] * game.n
    u, _ = kbp_utilities(game, a, x, s, rho)
    for i in range(game.n):
        others = sum(x) - x[i]

        def withhold(z):
            return (game.mu * (z + others) ** game.gamma * z / (z + others + game.alpha * others)
                    - a[i] * z ** game.theta)

        hi = 4 * (game.mu / a[i]) ** (1 / (game.theta - game.gamma))
        zs = [hi * j / 2000 for j in range(2001)]
        j = max(range(len(zs)), key=lambda m: withhold(zs[m]))
        lo_z, hi_z = zs[max(j - 1, 0)], zs[min(j + 1, 2000)]
        for _ in range(200):           # golden-section refinement
            m1 = hi_z - 0.618034 * (hi_z - lo_z)
            m2 = lo_z + 0.618034 * (hi_z - lo_z)
            if withhold(m1) < withhold(m2):
                lo_z = m1
            else:
                hi_z = m2
        if withhold(0.5 * (lo_z + hi_z)) > u[i] + 1e-9:
            return False
    return True


def kbp_theorem5_bound(game, a, rho):
    """Theorem 5: full sharing is the unique equilibrium if rho exceeds this bound,
    where x_i^max solves a_i z^theta = mu z^gamma."""
    x = kbp_ese(game, a, rho)
    total = sum(x)
    bound = 0.0
    for i in range(game.n):
        xmax = (game.mu / a[i]) ** (1 / (game.theta - game.gamma))
        bound = max(bound, xmax / (xmax + (1 + game.alpha) * (total - x[i])))
    return bound


def kbp_sharing_equilibria(game, a, x, rho):
    """Every sharing profile, with qualities fixed at x, from which no creator gains
    by switching alone. Found by checking all 2^n profiles."""
    n = game.n
    found = []
    for bits in range(2 ** n):
        s = [(bits >> i) & 1 for i in range(n)]
        u, _ = kbp_utilities(game, a, x, s, rho)
        stable = True
        for i in range(n):
            t = list(s)
            t[i] = 1 - t[i]
            if kbp_utilities(game, a, x, t, rho)[0][i] > u[i] + 1e-9:
                stable = False
                break
        if stable:
            found.append(tuple(s))
    return found


def kbp_lemma2_violations(game, a, x, rho):
    """Count the profiles and creators where sharing pays more but rho <= tau_i, or the reverse."""
    n = game.n
    bad = 0
    for bits in range(2 ** n):
        s = [(bits >> i) & 1 for i in range(n)]
        for i in range(n):
            on, off = list(s), list(s)
            on[i], off[i] = 1, 0
            gain = kbp_utilities(game, a, x, on, rho)[0][i] - kbp_utilities(game, a, x, off, rho)[0][i]
            tau = kbp_threshold(game, x, s, i)
            if abs(rho - tau) > 1e-9 and (gain > 0) != (rho > tau):
                bad += 1
    return bad


def kbp_regret(game, a, x, s, rho, grid=None, can_withhold=True):
    """The most any creator could gain, as a share of its pay, by changing alone:
    its quality (given a grid) and, where it may, whether it shares."""
    u, _ = kbp_utilities(game, a, x, s, rho)
    worst = 0.0
    for i in range(game.n):
        for q in (grid if grid else [x[i]]):
            for share in ((0, 1) if can_withhold else (s[i],)):
                t, v = list(x), list(s)
                t[i], v[i] = q, share
                worst = max(worst, (kbp_utilities(game, a, t, v, rho)[0][i] - u[i]) / abs(u[i]))
    return worst


def kbp_learn_sharing(game, a, x, rho, rounds=1500, measure=20):
    """Creators with fixed qualities learn only whether to share (0 = withhold, 1 = share).
    Returns the last measured profile."""
    def payoffs(profile):
        return kbp_utilities(game, a, x, profile, rho)[0]
    return list(learn(game.n, 2, payoffs, ("kbp-share", rho), rounds, measure)[-1])


QUALITY_GRID = [0.5 * j for j in range(61)]


def kbp_learn_quality(game, a, rho, grid, share_choice, rounds=6000, measure=50):
    """Creators learn their quality from a grid. If share_choice is False everyone
    must share; if True each strategy is a (quality, share) pair.
    Returns the last measured qualities and sharing choices."""
    pairs = [(q, 1) for q in grid] + ([(q, 0) for q in grid] if share_choice else [])

    def payoffs(profile):
        return kbp_utilities(game, a, [pairs[k][0] for k in profile], [pairs[k][1] for k in profile], rho)[0]

    last = learn(game.n, len(pairs), payoffs, ("kbp-quality", rho, share_choice), rounds, measure)[-1]
    return [pairs[k][0] for k in last], [pairs[k][1] for k in last]


# ---------------------------------------------------------------------------
# Yang and Zhang (2024, revised 2025)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class YZ:
    """The paper's numerical parameters (Section 5)."""
    c_h: float = 0.3        # cost of making a work by hand
    c_a: float = 0.05       # creator's own cost of making a work with AI
    lam: float = 0.6        # how much of an AI work's quality comes from the AI
    beta: float = 0.6       # share of a high-quality work's value its creator earns
    phi: float = 0.6        # protection for AI works, relative to human works
    M: float = 2.0          # creators in period 2 (period 1 has 1)
    k: float = 5.0          # training efficiency
    x1: float = 0.4         # AI quality in period 1
    q0: float = math.inf    # unused training data already available: inf = abundant, 0 = scarce
    f: float = 0.0          # fee per unit of training data (0 = generous fair use)


def yz_q(m, x2):
    """Eq. 4: data needed to raise AI quality from x1 to x2."""
    return 0.0 if x2 <= m.x1 else math.log((1 - m.x1) / (1 - x2)) / m.k


def yz_q_inv(m, data):
    return 1.0 if data == math.inf else 1 - (1 - m.x1) * math.exp(-m.k * data)


def yz_thresholds(m, X, p):
    """Table 1: creators below the lower threshold make nothing, those between use AI,
    those above make by hand (Proposition 4.1)."""
    lpb = m.lam * m.phi * m.beta
    xa = (m.c_a + p - (1 - m.lam) * m.phi * m.c_h) / lpb
    xh = (m.c_a + p + (1 - (1 - m.lam) * m.phi) * m.beta - m.c_h) / lpb
    xn = (m.c_a + p) / lpb
    x_ho = m.c_h / m.beta
    x_ha = (lpb * X + m.c_h - m.c_a - p) / ((1 - (1 - m.lam) * m.phi) * m.beta)
    x_ao = (m.c_a + p - lpb * X) / ((1 - m.lam) * m.phi * m.beta)
    if m.phi <= (m.beta - m.c_h) / (m.beta * (1 - m.lam)):     # Case I
        if X <= xa:
            return x_ho, x_ho
        if X <= xn:
            return x_ao, x_ha
        if X <= xh:
            return 0.0, x_ha
        return 0.0, 1.0
    if X <= xa:                                                 # Case II
        return x_ho, x_ho
    if X <= xh:
        return x_ao, x_ha
    if X <= xn:
        return x_ao, 1.0
    return 0.0, 1.0


def yz_outcomes(m, X, p, lo, hi, mass):
    """Corollary 4.2: high-quality human and AI works, AI revenue, creator income
    (before training income), consumer surplus and welfare, for thresholds lo and hi."""
    qh = mass * (1 - hi ** 2) / 2
    qa = mass * m.lam * X * (hi - lo) + mass * (1 - m.lam) * (hi ** 2 - lo ** 2) / 2
    return {
        "human": qh, "ai": qa,
        "revenue": mass * p * (hi - lo),
        "income": m.beta * (qh + m.phi * qa) - mass * (m.c_h * (1 - hi) + (m.c_a + p) * (hi - lo)),
        "consumers": (1 - m.beta) * qh + (1 - m.phi * m.beta) * qa,
        "welfare": qh + qa - mass * (m.c_h * (1 - hi) + m.c_a * (hi - lo)),
    }


def _break_even_price(m, X, cost):
    """The lowest price at which period-2 revenue covers the training cost, or None."""
    def revenue(p):
        lo, hi = yz_thresholds(m, X, p)
        return m.M * p * max(hi - lo, 0.0)
    if cost <= 0:
        return 0.0
    top = m.lam * m.phi * m.beta * X + (1 - m.lam) * m.phi * m.c_h - m.c_a + 1.0
    lo_p, hi_p = 0.0, max(top, 1e-9)
    for _ in range(100):               # revenue is concave in price: find its peak
        m1 = hi_p - 0.618034 * (hi_p - lo_p)
        m2 = lo_p + 0.618034 * (hi_p - lo_p)
        if revenue(m1) < revenue(m2):
            lo_p = m1
        else:
            hi_p = m2
    peak = 0.5 * (lo_p + hi_p)
    if revenue(peak) < cost:
        return None
    return _bisect(lambda p: cost - revenue(p), 0.0, peak)


class YZFirm:
    """The AI company's period-2 choice (Proposition 4.3 and Lemma 4.4): the AI quality
    that gives AI users the most value, phi beta lam X2 - p2, at a price that just
    covers the training fees, among qualities the available data allow."""

    def __init__(self, m, points=1000):
        self.m = m
        top = 1 - 1e-9
        self.grid = [m.x1 + (top - m.x1) * j / points for j in range(points + 1)]
        self.price = []
        best, best_j = -math.inf, 0
        self.best_upto = []             # best feasible grid point at or below each grid point
        for j, X in enumerate(self.grid):
            p = 0.0 if m.f == 0 else _break_even_price(m, X, m.f * yz_q(m, X))
            self.price.append(p)
            if p is not None:
                v = m.phi * m.beta * m.lam * X - p
                if v > best + 1e-15:
                    best, best_j = v, j
            self.best_upto.append(best_j)

    def choose(self, data):
        """Returns (period-2 AI quality, price, data bought) given the data available."""
        m = self.m
        x_data = yz_q_inv(m, data)
        if m.f == 0:
            if data == math.inf:
                return 1.0, 0.0, math.inf
            return x_data, 0.0, data
        j = bisect_right(self.grid, x_data) - 1
        if j < 0:
            return m.x1, 0.0, 0.0
        X = self.grid[self.best_upto[j]]
        return X, self.price[self.best_upto[j]], yz_q(m, X)


def yz_period1_thresholds(m, firm):
    """Period-1 thresholds in equilibrium: Proposition 4.7 when there is no training
    income, otherwise Proposition 4.8 with Appendix A's definitions."""
    if m.f == 0 or m.q0 == math.inf:
        return yz_thresholds(m, m.x1, 0.0)
    lpb = m.lam * m.phi * m.beta
    b_ai = (1 - (1 - m.lam) * m.phi) * m.beta
    x_ao = (m.c_a - lpb * m.x1) / ((1 - m.lam) * m.phi * m.beta)
    x_ho_f = m.c_h / (m.beta + m.f)                                           # Eq. 25
    x_ha_f = min(1.0, (m.c_h - m.c_a + lpb * m.x1) / (b_ai + m.f))
    xa_f = (m.c_a - (1 - m.lam) * m.phi * m.beta / (m.beta + m.f) * m.c_h) / lpb  # Eq. 26
    x_f = yz_q_inv(m, m.q0 + (1 - max(x_ho_f, x_ha_f) ** 2) / 2)               # Eq. 27
    x_c, _, q_c = firm.choose(yz_q(m, x_f))                                    # Eqs. 28-29
    if x_c <= m.x1:
        return yz_thresholds(m, m.x1, 0.0)
    if x_c >= x_f - 1e-6:                                                      # full compensation
        return (x_ho_f, x_ho_f) if m.x1 <= xa_f else (max(0.0, x_ao), x_ha_f)

    def per_unit(x):                                                           # partial compensation
        return 2 * q_c / (2 * m.q0 + 1 - x ** 2) * m.f
    x_ho_p = _bisect(lambda x: -((m.beta + per_unit(x)) * x - m.c_h), 1e-12, 1 - 1e-12)      # Eq. 30
    xa_p = (m.c_a - (1 - m.lam) * m.phi * m.beta * x_ho_p) / lpb                              # Eq. 33
    if m.x1 <= xa_p:
        return x_ho_p, x_ho_p
    x_ha_p = _bisect(lambda x: -((b_ai + per_unit(x)) * x - lpb * m.x1 - (m.c_h - m.c_a)),
                     1e-12, 1 - 1e-12)                                                        # Eq. 32
    return max(0.0, x_ao), x_ha_p


def yz_equilibrium(m, firm=None):
    """The paper's equilibrium: period-1 thresholds, the firm's choice, period-2 outcomes."""
    firm = firm or YZFirm(m)
    lo1, hi1 = yz_period1_thresholds(m, firm)
    human1 = (1 - hi1 ** 2) / 2
    x2, p2, _ = firm.choose(m.q0 + human1)
    lo2, hi2 = yz_thresholds(m, x2, p2)
    return {"lo1": lo1, "hi1": hi1, "x2": x2, "p2": p2,
            "period2": yz_outcomes(m, x2, p2, lo2, hi2, m.M)}


def yz_learn(m, n_creators=200, rounds=1500, measure=50, firm=None):
    """Creators at evenly spaced skills learn, each round, whether to make nothing (0),
    make with AI (1) or make by hand (2) in period 1; the firm then trains on what was
    made and pays fees; creators in period 2 then learn their own choices.
    Returns averages over the measured rounds."""
    firm = firm or YZFirm(m)
    skills = [(j + 0.5) / n_creators for j in range(n_creators)]
    state = {}

    def period1(profile):
        human = sum(x for x, c in zip(skills, profile) if c == 2) / n_creators
        x2, p2, bought = firm.choose(m.q0 + human)
        if m.f > 0 and human > 0 and m.q0 != math.inf:
            per_unit = m.f * min(1.0, bought / (m.q0 + human))
        else:
            per_unit = 0.0                 # no fee, or a negligible share of an endless pool
        state.update(human=human, x2=x2, p2=p2)
        out = []
        for x, c in zip(skills, profile):
            if c == 2:
                out.append(m.beta * x - m.c_h + per_unit * x)
            elif c == 1:
                out.append(m.phi * m.beta * (m.lam * m.x1 + (1 - m.lam) * x) - m.c_a)
            else:
                out.append(0.0)
        return out

    first = learn(n_creators, 3, period1, ("yz", m.x1, m.q0, m.f), rounds, measure)
    x2, p2 = state["x2"], state["p2"]

    def period2(profile):
        return [m.beta * x - m.c_h if c == 2 else
                m.phi * m.beta * (m.lam * x2 + (1 - m.lam) * x) - m.c_a - p2 if c == 1 else 0.0
                for x, c in zip(skills, profile)]

    second = learn(n_creators, 3, period2, ("yz-2", m.x1, m.q0, m.f), rounds, measure)
    final1, final2 = first[-1], second[-1]
    mass = m.M / n_creators
    qh = sum(x for x, c in zip(skills, final2) if c == 2) * mass
    qa = sum(m.lam * x2 + (1 - m.lam) * x for x, c in zip(skills, final2) if c == 1) * mass
    n_h = sum(c == 2 for c in final2) * mass
    n_a = sum(c == 1 for c in final2) * mass
    return {
        "choices1": final1, "choices2": final2, "skills": skills,
        "stable": all(p == final1 for p in first) and all(p == final2 for p in second),
        "human1": sum(x for x, c in zip(skills, final1) if c == 2) / n_creators,
        "x2": x2, "p2": p2,
        "period2": {
            "human": qh, "ai": qa, "revenue": p2 * n_a,
            "income": m.beta * (qh + m.phi * qa) - m.c_h * n_h - (m.c_a + p2) * n_a,
            "consumers": (1 - m.beta) * qh + (1 - m.phi * m.beta) * qa,
            "welfare": qh + qa - m.c_h * n_h - m.c_a * n_a,
        },
    }


def learned_thresholds(skills, choices):
    """Lower and upper thresholds read off learned choices (0 nothing, 1 AI, 2 by hand)."""
    makers = [x for x, c in zip(skills, choices) if c > 0]
    human = [x for x, c in zip(skills, choices) if c == 2]
    lo = min(makers) if makers else 1.0
    hi = min(human) if human else 1.0
    return lo, hi


def with_changes(m, **changes):
    return replace(m, **changes)


# ---------------------------------------------------------------------------
# The table of published results against what the learners did
# ---------------------------------------------------------------------------

def report():
    """Each row: a published result, its value in the paper's equilibrium, and the
    value the learning agents reached. Written to output/published_models.csv."""
    rows = []

    def add(paper, result, case, quantity, published, simulated):
        rows.append({"paper": paper, "result": result, "case": case, "quantity": quantity,
                     "published": published, "simulated": simulated})

    kbp = "Keinan and Ben-Porat (2026)"
    g = KBP()
    a = kbp_costs(g)
    same = [5.5] * g.n
    for rho in (0.05, 0.1, 0.2):
        x = kbp_ese(g, a, rho)
        add(kbp, "Lemma 2", f"rho = {rho}", "profiles where sharing pays but rho <= tau, or the reverse",
            0, kbp_lemma2_violations(g, a, x, rho))
    for rho in (0.0, 0.25, 0.5, 0.75, 1.0):
        q, s = kbp_learn_quality(g, same, rho, QUALITY_GRID, share_choice=False, rounds=15000)
        add(kbp, "Lemma 3, Proposition 7", f"rho = {rho}, all must share", "mean quality",
            kbp_symmetric_ese(g, 5.5, rho), sum(q) / g.n)
        add(kbp, "Lemma 3", f"rho = {rho}, all must share", "largest gain from changing quality alone (share of pay)",
            0, kbp_regret(g, same, q, s, rho, QUALITY_GRID, can_withhold=False))
    for rho in (0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 1.0):
        x = kbp_ese(g, a, rho)
        eqs = kbp_sharing_equilibria(g, a, x, rho)
        s = kbp_learn_sharing(g, a, x, rho)
        add(kbp, "Lemma 2, Proposition 4", f"rho = {rho}, qualities fixed", "creators sharing",
            sum(eqs[0]) if len(eqs) == 1 else float("nan"), sum(s))
        add(kbp, "Lemma 2", f"rho = {rho}, qualities fixed", "largest gain from switching alone (share of pay)",
            0, kbp_regret(g, a, x, s, rho))
    # The market gives its agents about 100 epochs. The same sharing game with only
    # 100 rounds shows how close learners get on that budget (reported, not checked).
    for rho in (0.05, 0.1, 0.2, 0.3):
        x = kbp_ese(g, a, rho)
        s = list(learn(g.n, 2, lambda prof: kbp_utilities(g, a, x, prof, rho)[0], ("kbp-share-100", rho), 100, 20)[-1])
        add(kbp, "Lemma 2, 100 rounds", f"rho = {rho}, qualities fixed, 100 rounds",
            "largest gain from switching alone (share of pay)", 0, kbp_regret(g, a, x, s, rho))
    for rho in (0.0, 0.25, 0.5, 1.0):
        q, s = kbp_learn_quality(g, same, rho, QUALITY_GRID, share_choice=True)
        add(kbp, "Definition 1, Theorem 5", f"rho = {rho}, quality and sharing", "creators sharing",
            g.n if kbp_full_sharing_holds(g, same, rho) else 0, sum(s))

    yz = "Yang and Zhang (2025)"
    m = YZ()
    for x1 in (0.05, 0.15, 0.4):
        mm = replace(m, x1=x1)
        out = yz_learn(mm)
        lo, hi = learned_thresholds(out["skills"], out["choices1"])
        plo, phi_ = yz_thresholds(mm, x1, 0.0)
        add(yz, "Proposition 4.1", f"AI quality {x1}", "lowest skill that makes anything", plo, lo)
        add(yz, "Proposition 4.1", f"AI quality {x1}", "lowest skill that makes by hand", phi_, hi)
    for label, q0, fees in (("plenty of old data", math.inf, (0.0, 0.1, 0.2)), ("no old data", 0.0, (0.0, 0.2, 1.0))):
        for f in fees:
            mm = replace(m, q0=q0, f=f)
            firm = YZFirm(mm)
            e = yz_equilibrium(mm, firm)
            out = yz_learn(mm, firm=firm)
            case = f"{label}, fee {f}"
            result = "Proposition 5.1" if q0 == math.inf else "Propositions 5.5 and 5.6, Figure 7"
            add(yz, result, case, "lowest skill that makes by hand, period 1", e["hi1"],
                learned_thresholds(out["skills"], out["choices1"])[1])
            add(yz, result, case, "AI quality, period 2", e["x2"], out["x2"])
            for key, name in (("ai", "high-quality AI works, period 2"), ("income", "creator income, period 2"),
                              ("welfare", "welfare, period 2"), ("consumers", "consumer surplus, period 2")):
                add(yz, result, case, name, e["period2"][key], out["period2"][key])
    return rows
