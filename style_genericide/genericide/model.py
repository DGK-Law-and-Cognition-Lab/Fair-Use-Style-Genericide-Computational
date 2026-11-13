"""The style-genericide market: artists, an AI company, buyers and a legal regime.

Each period:
  1. artists act on their current strategy: keep their signature, renew it on
     a schedule, or renew it whenever the AI is selling imitations of it; opt
     out of training where the regime allows it
  2. artists make works; other artists occasionally borrow a signature
  3. the AI company makes works at the closeness and volume its strategy sets:
     some made only from conventions, the rest "in the style of" artists whose
     current or earlier signature it has learned, more for artists with more fans
  4. every signature's recognizability is computed over the last few periods
  5. buyers choose what to buy, and money changes hands

Recognizability. Of all the works made in the last few periods that carry an
artist's signature, the share the artist made (the signature's cue validity:
the chance that a work showing it is the artist's). It is divided by its value
before AI, so 1 means as recognizable as before AI. It is not capped.

Learning. Every epoch (48 periods) the AI company scores the strategy it just
played by what it paid per period, leaving out the first periods while a new
strategy settles in, and picks the next one. Artists then see whether AI
imitations of their current signature are on sale, and do the same, keeping
separate scores for the two situations. Each strategy is tried
once, then mostly the best so far, sometimes another at random (see Learner).
Once the early trying is over, an artist quits when even its best strategy
pays less than quitting; while learning goes on, an artist who has quit tries
coming back now and then. Nothing is tried at random in the last periods,
which are the ones measured.
"""

import math
from dataclasses import dataclass, replace

from .world import PAINTERS, OWNER_RATE, BORROW_RATE, Rng, diagnosticity

REGIMES = ["no_ai", "fair_use", "opt_out", "license_loo", "license_shapley",
           "license_participation", "attribution"]

# An artist's strategy: renew the signature every k periods (0 = never) or
# whenever the AI is selling imitations of the current one, and whether to opt out.
IMITATED = -1
RENEW_EVERY = [0, 4, 8, 16, IMITATED]
# The AI company's strategy: closeness of imitation (half or all of the closeness
# its technology allows, max_closeness), works per period, and the share of its
# works made only from conventions (imitating no one). The last makes nothing.
AI_STRATEGIES = ([(c, vol, g) for c in (0.5, 1.0) for vol in (60, 240, 960, 3840)
                  for g in (0.0, 0.3)] + [(0.0, 0, 0.0)])


@dataclass(frozen=True)
class Params:
    # How people behave. Run 1 sets these across ranges; Papers 2 and 3 measure them.
    nest: float = 0.5               # 1 = fans treat a real work and an AI work in its style as unrelated; near 0 = interchangeable
    human_premium: float = 0.8      # extra value of a human-made work
    identity_value: float = 1.0     # extra value of owning a work whose style points to its artist, for a fan who knows the style
    credit_effect: float = 0.0      # change in an AI work's appeal when it credits the artist (negative sends fans to the original)
    credit_memory: float = 0.5      # share of credits buyers remember, so the style still points to the artist
    fan_share: float = 0.5          # share of buyers who are fans of a particular artist
    learn_lag: int = 3              # periods a signature must exist before the AI can learn it
    familiarity_growth: float = 0.15  # how fast fans learn a new signature, per period
    renewal_cost: float = 1.0       # one-off cost of a new signature, in periods of the artist's income before AI
    # How the market and the law work. Fixed at these values in the main runs; the
    # screening analysis varies them.
    n_buyers: int = 2000
    price_human: float = 3.0
    price_ai: float = 0.5
    fan_quality: float = 3.5
    decor_quality: float = 2.0
    generic_quality: float = 0.5
    variety: float = 0.3            # appeal added by more AI works to choose from (log scale)
    outdated_factor: float = 0.5    # appeal of an AI imitation of a signature the artist has dropped
    ai_cost: float = 0.05           # AI company's cost per work
    max_closeness: float = 0.7      # how closely the AI's technology can imitate a style (1 = as appealing to fans as the artist's own work)
    ai_concentration: float = 1.0   # AI imitations go to learned artists in proportion to popularity to this power (0 = evenly)
    work_cost: float = 0.5          # artist's cost per work
    royalty: float = 0.15           # licence fee per AI sale
    opt_out_leak: float = 0.0       # chance per period that the AI learns an opted-out signature anyway
    switch_familiarity: float = 0.3  # fans' familiarity with a brand-new signature
    reservation_share: float = 0.5  # income from quitting, as a share of the least popular artist's income before AI
    window: int = 5                 # periods of works used to compute recognizability
    popularity_exponent: float = 0.8
    # Time.
    ai_arrives: int = 20
    learn_periods: int = 4800
    measure_periods: int = 100
    epoch: int = 48                 # periods a strategy is played before it is scored
    settle: int = 16                # periods at the start of each epoch left out of the score
    # Learning.
    step: float = 0.2               # weight of the newest epoch in a strategy's score
    explore_start: float = 0.3      # chance of trying a random strategy, per epoch, at first
    explore_floor: float = 0.05     # and at least this, until learning ends
    explore_decay: float = 0.93     # per epoch

    @property
    def periods(self):
        return self.ai_arrives + self.learn_periods + self.measure_periods


def logsumexp(xs):
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


class Learner:
    """Scores a fixed list of strategies by what each has paid, and picks among them.

    Each strategy is tried once, in an order of the agent's own. After that the
    agent mostly plays the strategy with the highest score, and sometimes, at a
    rate that falls over time, a strategy picked at random (epsilon-greedy; Sutton
    and Barto, 2018, chapter 2). With no exploring, it plays the highest score.

    Scores are on the scale of pay. The score of the strategy the agent plays as
    its choice tracks what it pays now; when that score moves, every other score
    moves with it, so each alternative keeps its gain or loss relative to the
    agent's choice, and only trying the alternative changes that. Step sizes start
    as plain averages over the first few tries and settle at `step` (Sutton and
    Barto, 2018, exercise 2.7)."""

    def __init__(self, n, order=None):
        self.values = [0.0] * n
        self.tries = [0] * n
        self.trace = [0.0] * n
        self.order = list(order) if order is not None else list(range(n))
        self.current = self.order[0]
        self.explored = True            # whether the current strategy was a try rather than the agent's choice
        self.earned = 0.0
        self.periods = 0

    def record(self, payoff):
        self.earned += payoff
        self.periods += 1

    def close_epoch(self, step, fresh=False):
        """Score the epoch just played. fresh: the agent has just come back after time
        away, so the strategy's score becomes what it just paid."""
        if self.periods:
            k = self.current
            self.tries[k] += 1
            self.trace[k] += step * (1 - self.trace[k])
            weight = 1.0 if fresh else step / self.trace[k]
            mean = self.earned / self.periods
            if self.explored or fresh or self.tries[k] == 1:
                self.values[k] += weight * (mean - self.values[k])
            else:
                shift = weight * (mean - self.values[k])
                self.values = [v + shift for v in self.values]
        self.earned, self.periods = 0.0, 0

    def greedy(self, allowed):
        return max(allowed, key=lambda k: (self.values[k], -k))

    def choose(self, rng, explore, allowed):
        untried = [k for k in self.order if k in allowed and self.tries[k] == 0]
        best = self.greedy(allowed)
        if untried and explore > 0:
            self.current = untried[0]
        elif explore > 0 and rng.random() < explore:
            self.current = rng.choice(allowed)
        else:
            self.current = best
        self.explored = self.current != best
        return self.current

    def best_value(self, allowed):
        tried = [self.values[k] for k in allowed if self.tries[k]]
        return max(tried) if tried else None

    def experience(self):
        return sum(self.tries)


class Artist:
    def __init__(self, idx, popularity, n_strategies, order):
        self.idx = idx
        self.name = PAINTERS[idx]
        self.popularity = popularity    # share of all fans who are this artist's fans
        self.active = True
        self.opted_out = False
        self.signature = idx            # 0-11 are the painters' own signatures; new ones count up from 100
        self.signature_age = 10
        self.familiarity = 1.0          # how well the artist's fans know the current signature
        self.history = []               # per period: (works, signature, works carrying it)
        self.recognizability = 1.0
        self.diagnostic_ratio = 1.0     # the painter world's diagnosticity, relative to before AI (a second measure)
        self.income = 0.0
        self.human_sales = 0.0
        self.ai_sales_in_style = 0.0
        self.royalties = 0.0
        self.baseline_income = None
        # Artists can see whether AI imitations of their current signature are on sale,
        # and keep separate scores for the two situations: what pays depends on it (for
        # example, opting out and keeping a signature pays only once the AI is not copying it).
        self.n_strategies, self.order = n_strategies, order
        self.learners = {}
        self.context = None
        self.strategy = 0               # the strategy the artist is playing
        self.renewals = 0
        self.renewed_now = False
        self.exited_at = None
        self.returning = False          # came back from quitting at the start of this epoch
        self.comebacks = 0

    @property
    def learner(self):
        if self.context not in self.learners:
            self.learners[self.context] = Learner(self.n_strategies, self.order)
        return self.learners[self.context]

    def most_practiced(self):
        """The learner for the situation the artist has the most experience of."""
        return max(self.learners.values(), key=lambda lr: lr.experience(), default=None)


class Market:
    """One simulated art market under one regime.

    artist_policy: "learn"; "keep" (never change, never quit); or "random"
    (a random strategy each epoch, never quit). ai_policy: "learn", or a fixed
    (closeness, volume, share made only from conventions) triple.

    frozen: None while learning; "actions" holds every agent's current strategy;
    "policies" lets artists keep choosing, without learning, by what they have
    learned for each situation (used to test the AI company's alternatives).
    """

    def __init__(self, params, regime, seed, artist_policy="learn", ai_policy="learn"):
        assert regime in REGIMES
        self.p, self.regime, self.seed = params, regime, seed
        self.artist_policy, self.ai_policy = artist_policy, ai_policy
        self.rng = Rng("style-genericide", regime, seed)
        self.strategies = [(k, out) for k in RENEW_EVERY for out in ((False, True) if regime == "opt_out" else (False,))]
        # Who is popular depends on the seed only, so every regime with the same seed
        # has the same artists in the same positions (comparisons across regimes are paired).
        ranks = Rng("style-genericide", "popularity", seed).shuffle(list(range(1, len(PAINTERS) + 1)))
        raw = [r ** -params.popularity_exponent for r in ranks]
        total = sum(raw)
        n = len(self.strategies)
        # Each agent tries the strategies first in an order of its own, so they do not all try the same one at once.
        self.artists = [Artist(i, raw[i] / total, n, [0] + self.rng.shuffle(list(range(1, n))))
                        for i in range(len(PAINTERS))]
        self.ai = Learner(len(AI_STRATEGIES), self.rng.shuffle(list(range(len(AI_STRATEGIES)))))
        self.learned = {}               # artist index -> newest signature the AI has learned for that artist
        self.learned_ids = set()
        self.next_signature = 100
        self.other_counts = []          # per period: ({signature: works by others carrying it}, human works, AI works)
        self.t = 0
        self.epochs = 0
        self.records = []
        self.frozen = None
        # The market starts with a full window of pre-AI works already made.
        n_others = 10 * (len(self.artists) - 1)
        for a in self.artists:
            a.history = [(10, a.signature, 10 * OWNER_RATE)] * self.p.window
        self.other_counts = [({a.signature: BORROW_RATE * n_others for a in self.artists},
                              10 * len(self.artists), 0.0)] * self.p.window
        own0 = self.p.window * 10 * OWNER_RATE
        others0 = self.p.window * n_others
        self.cue0 = own0 / (own0 + BORROW_RATE * others0)
        self.d0 = diagnosticity(own0, BORROW_RATE * others0, n=self.p.window * 10, n_other_works=others0)
        demand = self._demand(None)
        for a in self.artists:
            a.baseline_income = self.p.price_human * demand["human"][a.idx] - self.p.work_cost * 10
        self.reservation = self.p.reservation_share * min(a.baseline_income for a in self.artists)
        self.baseline_surplus = demand["surplus"]

    # ----- strategies --------------------------------------------------------

    def ai_present(self):
        return self.regime != "no_ai" and self.t >= self.p.ai_arrives

    def measuring(self):
        return self.t >= self.p.ai_arrives + self.p.learn_periods

    def scoring(self):
        """Whether this period counts toward the current strategy's score: the first
        periods of each epoch are left out, while a new strategy settles in."""
        return (self.t - self.p.ai_arrives) % self.p.epoch >= self.p.settle

    def explore_rate(self):
        if self.measuring():
            return 0.0
        return max(self.p.explore_floor, self.p.explore_start * self.p.explore_decay ** self.epochs)

    def ai_strategy(self):
        """(closeness, works per period, share made only from conventions), or None."""
        if not self.ai_present():
            return None
        if isinstance(self.ai_policy, tuple):
            return self.ai_policy
        c, vol, g = AI_STRATEGIES[self.ai.current]
        return (c * self.p.max_closeness, vol, g)

    def selling_imitations(self, a):
        """Whether AI imitations of the artist's current signature are on sale."""
        choice = self.ai_strategy()
        return bool(choice and choice[1] > 0 and choice[2] < 1
                    and self.learned.get(a.idx) == a.signature)

    def new_epoch(self):
        """Score the strategies just played, then choose the next ones. The AI company
        chooses first; artists then see its choice and choose."""
        if self.frozen == "actions":
            return
        learning = self.frozen is None
        explore = self.explore_rate() if learning else 0.0
        if isinstance(self.ai_policy, tuple):
            settled = True
        else:
            if learning:
                self.ai.close_epoch(self.p.step)
                self.ai.choose(self.rng, explore, list(range(len(AI_STRATEGIES))))
            # Artists quit only in response to the AI company's own choice, not to one of its tries.
            settled = not self.ai.explored
        allowed = list(range(len(self.strategies)))
        trying_over = explore <= self.p.explore_floor
        for a in self.artists:
            if not a.active:
                # While learning, an artist who has quit tries coming back now and then (at
                # the exploring rate), with a fresh signature and its best strategy for one.
                if not (learning and self.artist_policy == "learn" and self.rng.random() < explore):
                    continue
                self.come_back(a)
            elif learning:
                a.learner.close_epoch(self.p.step, fresh=a.returning)
                a.returning = False
            a.context = self.selling_imitations(a)
            lr = a.learner
            if self.artist_policy == "keep":
                lr.current = 0
            elif self.artist_policy == "random":
                lr.current = self.rng.choice(allowed)
            elif learning and a.returning:
                lr.current, lr.explored = lr.greedy(allowed), False
            elif learning:
                lr.choose(self.rng, explore, allowed)
                best = lr.best_value(allowed)
                # Quitting pays the outside income; licence fees, if any, are paid either way.
                if (settled and trying_over and best is not None and best < self.reservation + a.royalties
                        and all(lr.tries[k] for k in allowed)):
                    a.active = False
                    a.exited_at = self.t
            if self.artist_policy == "learn" and (explore == 0 or not learning):
                # No exploring: play the best known strategy. In a situation never met while
                # learning, use what was learned for the situation met most often.
                source = lr if lr.experience() else a.most_practiced()
                lr.current = source.greedy(allowed) if source else 0
                lr.explored = False
            a.strategy = lr.current
            a.opted_out = self.strategies[a.strategy][1]
        self.epochs += 1

    def come_back(self, a):
        a.active, a.exited_at, a.returning = True, None, True
        a.signature, self.next_signature = self.next_signature, self.next_signature + 1
        a.signature_age, a.familiarity = 0, self.p.switch_familiarity
        a.comebacks += 1

    # ----- one period ----------------------------------------------------------

    def renew_signatures(self):
        costs = {}
        for a in self.artists:
            a.renewed_now = False
            if not a.active or not self.ai_present():
                continue
            every = self.strategies[a.strategy][0]
            if every == IMITATED:
                due = self.selling_imitations(a)
            else:
                due = every and a.signature_age >= every
            if due:
                a.signature = self.next_signature
                self.next_signature += 1
                a.signature_age = 0
                a.familiarity = self.p.switch_familiarity
                a.renewals += 1
                a.renewed_now = True
                costs[a.idx] = self.p.renewal_cost * a.baseline_income
        return costs

    def ai_learns(self):
        """The AI learns each signature that has existed long enough, unless its artist
        opted out (an opted-out signature can still leak, at rate opt_out_leak)."""
        if not self.ai_present():
            return
        for a in self.artists:
            if a.signature_age < self.p.learn_lag or a.signature in self.learned_ids:
                continue
            if a.opted_out and not (self.p.opt_out_leak > 0 and self.rng.random() < self.p.opt_out_leak):
                continue
            self.learned[a.idx] = a.signature
            self.learned_ids.add(a.signature)

    def styled_volumes(self, volume, generic):
        """AI works per period in each learned artist's style, by popularity."""
        styled = (1 - generic) * volume
        weights = {i: self.artists[i].popularity ** self.p.ai_concentration for i in self.learned}
        total = sum(weights.values())
        return {i: styled * w / total for i, w in weights.items()} if total else {}

    def produce(self, choice):
        """Record this period's works: who made them and which signatures they carry."""
        others = {}
        human_total = 0
        for a in self.artists:
            if a.active:
                a.history.append((10, a.signature, 10 * OWNER_RATE))
                human_total += 10
            else:
                a.history.append((0, a.signature, 0.0))
            a.history = a.history[-self.p.window:]
        for a in self.artists:
            if a.active:
                others[a.signature] = others.get(a.signature, 0.0) + BORROW_RATE * (human_total - 10)
        ai_total = 0.0
        if choice and choice[1] > 0:
            phi, volume, generic = choice
            ai_total = volume
            # Under attribution, a credited AI work still points to the artist for the
            # share of buyers who remember the credit.
            weight = 1.0 - (self.p.credit_memory if self.regime == "attribution" else 0.0)
            for i, v in self.styled_volumes(volume, generic).items():
                sig = self.learned[i]
                others[sig] = others.get(sig, 0.0) + v * phi * OWNER_RATE * weight
        self.other_counts.append((others, human_total, ai_total))
        self.other_counts = self.other_counts[-self.p.window:]

    def update_recognizability(self):
        for a in self.artists:
            own_with = sum(c for _, s, c in a.history if s == a.signature)
            others_with = sum(o.get(a.signature, 0.0) for o, _, _ in self.other_counts)
            a.recognizability = (own_with / (own_with + others_with) / self.cue0) if own_with + others_with else 0.0
            own_total = sum(w for w, _, _ in a.history)
            if own_total:
                others_total = sum(h + ai for _, h, ai in self.other_counts) - own_total
                a.diagnostic_ratio = diagnosticity(own_with, others_with, n=own_total,
                                                   n_other_works=others_total) / self.d0

    # ----- buyers ----------------------------------------------------------

    def _demand(self, choice):
        """Expected purchases by fans (nested logit) and by decorators (logit).
        Each artist's fans are a fixed share of all fans; how much they value the
        artist's style depends on how recognizable it is and how well they know it."""
        p = self.p
        ai_on = bool(choice and choice[1] > 0)
        phi, volume, generic = choice if ai_on else (0.0, 0, 0.0)
        fans_total = p.n_buyers * p.fan_share
        decor_total = p.n_buyers - fans_total
        styled = self.styled_volumes(volume, generic) if ai_on else {}
        generic_volume = generic * volume
        human = [0.0] * len(self.artists)
        ai_style = [0.0] * len(self.artists)
        generic_sales = 0.0
        surplus = 0.0
        credit = 1.0 if self.regime == "attribution" else 0.0
        offer_generic = ai_on and generic_volume > 0
        v_generic = p.generic_quality + p.variety * math.log(1 + generic_volume / 10) - p.price_ai
        for a in self.artists:
            fans = fans_total * a.popularity
            nest = []
            if a.active:
                nest.append(("h", p.fan_quality + p.identity_value * a.recognizability * a.familiarity
                             + p.human_premium - p.price_human))
            if ai_on and styled.get(a.idx, 0) > 0:
                current = self.learned[a.idx] == a.signature or not a.active
                fit = phi * (1.0 if current else p.outdated_factor)
                nest.append(("a", p.fan_quality * fit + p.variety * math.log(1 + styled[a.idx] / 10)
                             + p.credit_effect * credit - p.price_ai))
            terms = [0.0] + ([v_generic] if offer_generic else [])
            if nest:
                within = logsumexp([v / p.nest for _, v in nest])
                terms.append(p.nest * within)
            denom = logsumexp(terms)
            surplus += fans * denom
            if nest:
                p_nest = math.exp(p.nest * within - denom)
                for kind, v in nest:
                    share = p_nest * math.exp(v / p.nest - within)
                    if kind == "h":
                        human[a.idx] += fans * share
                    else:
                        ai_style[a.idx] += fans * share
            if offer_generic:
                generic_sales += fans * math.exp(v_generic - denom)
        active = [a for a in self.artists if a.active]
        pop = sum(a.popularity for a in active)
        v_h = p.decor_quality + p.human_premium - p.price_human
        terms = [0.0] + ([v_h] if active else [])
        if ai_on:
            v_a = p.decor_quality + p.variety * math.log(1 + volume / 100) - p.price_ai
            terms.append(v_a)
        denom = logsumexp(terms)
        surplus += decor_total * denom
        if active:
            dh = decor_total * math.exp(v_h - denom)
            for a in active:
                human[a.idx] += dh * a.popularity / pop
        if ai_on:
            da = decor_total * math.exp(v_a - denom)
            for i, v in styled.items():
                ai_style[i] += da * v / volume
            generic_sales += da * generic_volume / volume
        return {"human": human, "ai_style": ai_style, "generic": generic_sales, "surplus": surplus}

    def settle(self, choice, costs):
        """Sales, fees and income for one period. Licence fees go to every rights
        holder, including artists who have quit, since the AI was trained on their work."""
        p = self.p
        ai_on = bool(choice and choice[1] > 0)
        d = self._demand(choice)
        royalties = [0.0] * len(self.artists)
        n = len(self.artists)
        if self.regime.startswith("license") and ai_on:
            # Sales in an artist's style: that artist alone is pivotal, so every rule pays them.
            for a in self.artists:
                royalties[a.idx] += p.royalty * d["ai_style"][a.idx]
            # Sales made only from conventions: no one artist is pivotal. Leave-one-out pays
            # no one; Shapley (and pivotality, here) pays each an equal share; participation
            # pays each the full fee.
            if self.regime == "license_shapley":
                for a in self.artists:
                    royalties[a.idx] += p.royalty * d["generic"] / n
            elif self.regime == "license_participation":
                for a in self.artists:
                    royalties[a.idx] += p.royalty * d["generic"]
        for a in self.artists:
            a.human_sales = d["human"][a.idx]
            a.ai_sales_in_style = d["ai_style"][a.idx]
            a.royalties = royalties[a.idx]
            if a.active:
                a.income = (p.price_human * a.human_sales - p.work_cost * 10 + royalties[a.idx]
                            - costs.get(a.idx, 0.0))
            else:
                a.income = self.reservation + royalties[a.idx]
        ai_sales = sum(d["ai_style"]) + d["generic"]
        ai_profit = (p.price_ai * ai_sales - p.ai_cost * choice[1] - sum(royalties)) if ai_on else 0.0
        return d, ai_sales, ai_profit

    def step(self):
        if self.ai_present() and (self.t - self.p.ai_arrives) % self.p.epoch == 0:
            self.new_epoch()
        costs = self.renew_signatures()
        choice = self.ai_strategy()
        self.ai_learns()
        self.produce(choice)
        self.update_recognizability()
        d, ai_sales, ai_profit = self.settle(choice, costs)
        for a in self.artists:
            if a.active:
                if self.ai_present() and self.scoring() and self.frozen is None:
                    a.learner.record(a.income)
                a.signature_age += 1
                a.familiarity += self.p.familiarity_growth * (1 - a.familiarity)
        if self.ai_present() and self.scoring() and self.frozen is None:
            self.ai.record(ai_profit)
        self.records.append(self._record(choice, d, ai_sales, ai_profit))
        self.t += 1

    def _record(self, choice, d, ai_sales, ai_profit):
        phi, volume, generic = choice if choice else (None, 0, 0.0)
        return {
            "t": self.t, "measuring": self.measuring(),
            "phi": phi, "volume": volume, "generic": generic,
            "ai_sales": ai_sales, "ai_profit": ai_profit, "surplus": d["surplus"],
            "artists": [{
                "name": a.name, "popularity": a.popularity, "active": a.active,
                "recognizability": a.recognizability, "diagnostic_ratio": a.diagnostic_ratio,
                "income": a.income, "baseline": a.baseline_income, "human_sales": a.human_sales,
                "ai_sales_in_style": a.ai_sales_in_style, "royalties": a.royalties,
                "renewed": a.renewed_now,
                "renew_every": self.strategies[a.strategy][0] if a.active else None,
                "opted_out": a.opted_out,
            } for a in self.artists],
        }

    def run(self):
        for _ in range(self.p.periods):
            self.step()
        return self.records


def run_market(params, regime, seed, artist_policy="learn", ai_policy="learn"):
    return Market(params, regime, seed, artist_policy, ai_policy).run()


def with_params(params, **changes):
    return replace(params, **changes)
