# Style genericide: Run 1

A simulation of how AI imitation can wear away the link between artists and their styles, and which legal rules keep that link.

**The idea.** Painter A always paints a small yellow bird, so seeing the bird tells you a painting is an A. An AI company then puts yellow birds in thousands of pictures A never painted. Now the bird tells you little, even though nobody copied any painting of A's. That is **style genericide**, named after the trademark term for a brand name that becomes the ordinary word for a thing ("escalator"). It is different from **dilution**, which is the artist losing sales. Either can happen without the other, so the simulation measures both.

Run 1 sets the human behaviors it needs across ranges taken as plausible, not measured, reports results at default settings, and then asks how much each result depends on the settings. Run 2 will use the numbers measured in Papers 2 and 3.

**This is the second version of Run 1** (5 November 2026). An independent review of the first version raised fifteen critiques; each was checked against the code and confirmed, and the model, the learning, the sensitivity analysis and the reporting were changed to answer them. The section "Critiques and answers" below takes them one at a time; `CHANGELOG.md` lists every change. Every result changed.

## How to run it from a fresh copy

You need Python 3.12, the three packages in `requirements.txt` (only the figures use them), and the painter world in the sibling folder `../painter_world` (or set `PAINTER_WORLD_DIR`).

```bash
python3 -m pip install -r requirements.txt
```

```bash
python3 run.py
```

```bash
python3 check.py
```

`run.py` takes about an hour on twelve processor cores and writes everything to `output/` (set `STYLE_GENERICIDE_OUT` to write elsewhere). It draws the figures from the saved tables, so `python3 run.py --figures` redraws them alone in seconds, with the same result. `check.py` takes a few minutes; `python3 check.py --rebuild` also rebuilds everything in a temporary folder and confirms the files are byte-identical. `../check_all.py` runs the checks of both folders and flags copies left by a file-sync program.

## The model, in plain words

**The world.** The painter world's twelve painters. Each has a signature found in 9 of their 10 paintings and in 2 of the other painters' 110. Painters differ in popularity: a few have many fans, most have few.

**Each period:**
1. Each working artist makes 10 works; other artists occasionally borrow a signature.
2. The AI company makes works at the closeness and volume its strategy sets. Some are made from conventions alone and imitate no one; the rest are made "in the style of" artists whose signatures it has learned, more for more popular artists.
3. Each signature's **recognizability** is computed: of all the works made in the last five periods that carry the artist's signature, the share the artist made, divided by that share before AI. It is the chance that a work showing the signature is really the artist's (the signature's *cue validity*). So 1 means as recognizable as before AI, and 0.1 means only a tenth as likely to be the artist's.
4. Buyers choose what to buy.
   - *Fans* of an artist choose among the artist's own work, AI works in that artist's style, AI works that imitate no one, and nothing, by a *nested logit model*: options in the same style are grouped, and one setting says how freely fans swap a real work for an AI work in its style. A fan values owning the artist's work more when the style is recognizable and when the fan knows the artist's current signature.
   - *Decorators* want any picture and choose among human-made, AI-made and nothing.
5. Money changes hands. Licence fees are paid where the regime requires them, to every rights holder, including artists who have quit.

**What the AI company chooses** each epoch: how closely to imitate (half or all of what its technology allows), how much to make (60, 240, 960 or 3,840 works per period), and whether 30 percent or none of its works are made from conventions alone; or to make nothing. It needs a few periods of an artist's work under a signature before it can learn it.

**What artists choose.**
- *Renew* their signature every 4, 8 or 16 periods, whenever AI imitations of the current one go on sale, or never. A new signature costs one period of the artist's pre-AI income, fans take a while to learn it, and the AI cannot imitate it until it has learned it.
- *Opt out* of training, under the opt-out regime. The AI then cannot learn their future signatures (unless opt-out leaks; see the settings); what it has learned stays learned.
- *Quit*, for an outside income equal to half the least popular artist's pre-AI income, and later *come back* with a fresh signature.

**How they learn.** Every 48 periods (an *epoch*), the AI company scores the strategy it just played by what it paid per period, leaving out the first 16 periods while the strategy settles in, and chooses the next one. Artists do the same, keeping separate scores for two situations: AI imitations of their current signature on sale, or not. Each strategy is tried once, then mostly the best so far, and sometimes another at random (an epsilon-greedy learner; Sutton and Barto, 2018, chapter 2). Two details matter:
- When an agent's usual strategy starts paying more or less, every other strategy's score moves with it, so an alternative keeps its gain or loss relative to the usual one. Only trying the alternative changes that.
- The first few tries of a strategy are averaged plainly, so one unlucky early try does not stick (Sutton and Barto, 2018, exercise 2.7).

After the early trying (about 25 epochs), an artist quits when even its best strategy pays less than quitting, and an artist who has quit tries coming back now and then. Many agents learning at once, each from their own payoffs, is what makes this multi-agent reinforcement learning. Learning lasts 4,800 periods.

**Two stages of results.** Where learning ends, the measured 100 periods are played twice:
- **Learned:** every agent keeps the strategy it learned.
- **Settled:** from that same point, agents in turn switch to their best response to everyone else's strategies (found by replaying the 100 periods with each alternative) until no agent can gain more than 1 percent by switching alone. This is an equilibrium (a *Nash equilibrium* in these strategies: no one can do better alone) near where learning ended.

The settled outcomes are the main results. Trial-and-error learning on this budget does not reliably reach best responses (see "How close learning gets"), and settling removes that source of error; learned outcomes are reported beside them.

**The regimes.**
- *No AI.*
- *Fair use:* training is free and nothing is paid.
- *Opt-out.*
- *Licensing:* the AI company pays 0.15 per sale (30 percent of its price). Every rule pays the imitated artist for sales in their style. The rules differ on sales of works made from conventions alone, which were learned from everyone at once: *leave-one-out* pays no one, since removing any one artist would change nothing; *Shapley* pays each artist an equal share (here the same as pivotality); *participation* pays every artist the full fee.
- *Credit the artist:* AI works in an artist's style name the artist. For the share of buyers who remember the credit, the signature still points to the artist. A credit can also change how appealing the AI work is.

**Null models.** The same markets with artists who never change anything, and with artists who pick strategies at random.

## Settings

How people behave, and how fast things happen (the Sobol analysis varies these):

| Setting | Default | Range | Measured in |
|---|---|---|---|
| How freely fans swap a real work for an AI work in its style (nest parameter; lower = more freely) | 0.5 | 0.2 to 1.0 | Paper 3, shop |
| Premium for human-made work | 0.8 | 0 to 2 | Paper 3, shop |
| Value of owning a work whose style points to its artist | 1.0 | 0 to 2 | Paper 3, shop |
| How a credit changes an AI work's appeal (negative sends fans to the original) | 0 | −1 to 1 | Paper 3, shop |
| Share of buyers who remember a credit | 0.5 | 0 to 1 | Paper 3, memory test |
| Share of buyers who are fans | 0.5 | 0.2 to 0.8 | Assumed |
| Periods before the AI can learn a new signature | 3 | 1 to 6 | Assumed |
| Speed fans learn a new signature, per period | 0.15 | 0.05 to 0.3 | Assumed |
| Cost of a new signature, in periods of pre-AI income | 1 | 0.25 to 4 | Assumed |

How the market, the law and the learning work (fixed at these defaults in the main runs; the screening and the robustness map vary them): the AI's technology (`max_closeness` 0.7, range 0.4 to 1), the licence fee (0.15; 0.05 to 0.4), the price of an AI work (0.5; 0.2 to 1.5), the AI's cost per work (0.05; 0.01 to 0.2), how much buyers value more AI works to choose from (`variety` 0.3; 0 to 0.6), the appeal of imitations of a dropped signature (0.5; 0 to 1), how strongly AI imitation follows popularity (`ai_concentration` 1; 0 = evenly, to 2), opt-out leakage (0; 0 to 0.5 per period), the outside income (`reservation_share` 0.5; 0.2 to 0.9), fans' familiarity with a new signature (0.3; 0.1 to 0.9), the recognizability window (5 periods; 3 to 10), how unequal popularity is (exponent 0.8; 0.3 to 1.5), and two learning settings (exploration floor 0.05, 0.02 to 0.1; step 0.2, 0.1 to 0.4). Every setting is in `output/params.json`.

## What Run 1 found, at the default settings

Averages over 30 seeds of the settled outcomes; learned outcomes in brackets where they differ much (`output/regimes.csv`, which also gives the 2.5th to 97.5th percentile of seeds). Money is per period, in the units of prices; artists' total income before AI is 4,017.

| Regime | Styles still point to their artists (working artists) | Median artist's income (1 = before AI) | Artists still working (of 12) | Change for buyers | Change for artists | AI company's profit | Change in total welfare |
|---|---|---|---|---|---|---|---|
| No AI | 1.00 | 1.00 | 12 | 0 | 0 | 0 | 0 |
| Fair use, artists never change | 0.17 | 0.12 | 12 | +2,184 | −3,595 | 795 | −617 |
| Fair use | 0.13 [0.40] | 0.30 | 2.4 [1.8] | +2,242 | −3,055 | 826 | +12 |
| Opt-out | 1.00 [0.97] | 0.52 [0.49] | 12 [6.8] | +2,058 | −1,963 | 518 | +614 |
| Licence, leave-one-out | 0.13 | 0.35 | 2.5 | +2,242 | −2,858 | 626 | +9 |
| Licence, Shapley | 0.15 | 0.37 | 2.4 | +2,222 | −2,791 | 562 | −7 |
| Licence, participation | 0.40 | 0.37 | 2.9 | +2,059 | −2,815 | 536 | −220 |
| Credit the artist | 0.25 | 0.30 | 3.0 | +2,247 | −3,062 | 820 | +5 |

Each finding below says why it was asked, what the simulation shows at the defaults, and how often it holds across the sampled settings (the robustness map, next section).

1. **Imitation erodes styles, the most popular most.** *Why ask:* this is genericide itself. *At the defaults:* if artists never change, only about a sixth of the works carrying a typical artist's signature are the artist's (0.17 of before), and for the most popular artist about a fourteenth (0.07), because the AI imitates in proportion to popularity. *Robustness:* both hold at every sampled setting. The second rests on one assumption: the AI makes more imitations where there is more demand. If it imitated every artist equally, everyone would erode alike.
2. **Under fair use, most artists stop working, and the rest cannot keep their styles.** *Why ask:* the first version found that artists stay recognizable by reinventing their signatures. *At the defaults:* about two of twelve keep working, and their signatures point to them a tenth as often as before (0.13). Renewing does not pay: the AI learns a new signature within three periods. Artists lose 3,055 of their 4,017; buyers gain 2,242; the AI earns 826; total welfare barely moves (+12). *Robustness:* artists lose income at every sampled setting and buyers gain at 93 percent. Total welfare rises at only 49 percent, a coin flip: it tends to rise when buyers value variety highly and to fall when they value human-made work highly. Reinvention keeps styles recognizable at only 13 percent of settings, mostly where a new signature is cheap and the AI is slow to learn one.
3. **Opt-out does best for artists, if it is enforced.** *At the defaults:* every artist opts out, makes one new signature the AI can never learn, and keeps it; all twelve keep working, styles are fully recognizable, the median artist keeps 52 percent of income, and total welfare rises most (+614). *Robustness:* opt-out gives artists the highest median income at only 10 percent of sampled settings. The main reason is leakage: with opt-out leaking at a rate of even a few percent per period, the AI learns most opted-out signatures within a few dozen periods. In the lower half of the leakage range it is best at 19 percent of settings; in the upper half, 1 percent.
4. **Licensing changes little.** *At the defaults:* licences raise the median artist's income from 0.30 to 0.35 to 0.37 but keep about the same number of artists working (2.4 to 2.9) and leave styles about as eroded. *Robustness:* a Shapley licence keeps at least as many working as fair use at 84 percent of settings and at least as many as leave-one-out at 92 percent; mostly these are ties. How the fee is split (Paper 2's question) matters less here than the fee level and the price of AI work (screening, below).
5. **The participation rule does not shut the AI down.** The first version's finding came from the AI being forced to make 30 percent of its works from conventions alone. Free to choose, it stops making them and pays fees only on imitations; total welfare falls (−220). *Robustness:* the AI makes nothing at 6 percent of settings.
6. **Crediting the artist helps recognizability a little, not income.** *At the defaults:* credits double how often a signature points to its artist (0.25 against 0.13) because buyers who remember the credit do not count the AI work against the artist, but income does not rise. *Robustness:* credits mean fewer new signatures at only 16 percent of settings, and this outcome is the noisiest of all (a third of its variation is chance).
7. **Learning matters.** Artists who pick strategies at random earn 0.10 of their income and leave total welfare 1,003 lower; artists who never change earn 0.12.

The caveat for all of these: they hold at settings that were assumed, not measured, and the robustness map shows which ones survive across those assumptions.

## How robust each claim is

At 160 settings drawn across all 23 ranges (Latin hypercube sampling, which spreads points evenly across every range), every regime was run and settled, and each of eleven claims recorded as true or false (`output/robustness.csv`, Figure 4). The claims were written before this version was run.

| Claim | Share of settings where it holds |
|---|---|
| Imitation erodes styles that never change (most popular artist below 0.9) | 100% |
| The most popular artist's style erodes most | 100% |
| Artists lose income under fair use | 100% |
| Buyers gain under fair use | 93% |
| A Shapley licence keeps at least as many artists working as leave-one-out | 92% |
| A Shapley licence keeps at least as many artists working as fair use | 84% |
| Total welfare rises under fair use | 49% |
| Crediting the artist means fewer new signatures | 16% |
| Artists who respond keep their styles recognizable (0.9 or more) | 13% |
| Opt-out gives artists the highest median income of the regimes with AI | 10% |
| Under the participation rule the AI company makes nothing | 6% |

`output/robustness_by_setting.csv` shows, for each claim, how often it holds in the lower and the upper half of each setting's range, which says what each claim turns on.

## How close learning gets

The best-response test replays the measured periods from where learning ended, with one agent switched to each alternative, everyone else unchanged (for the AI company's alternatives, artists respond as they learned to). An artist's gap is what it would gain, as a share of its pre-AI income; the AI company's, as a share of its best profit (`output/best_response_gaps.csv`).
- In 89 of 180 runs no artist could gain more than 5 percent by switching alone; in 160 of 180, the AI company could not. The typical gap is 2 to 4 percent in every regime but opt-out.
- Under opt-out, learning leaves most artists far from their best choice (median gap 44 percent): opting out pays only after the AI stops copying the current signature, which trial and error rarely discovers on this budget. Settling finds it.
- A few artists who quit could have gained a lot by coming back (up to 2.4 times their pre-AI income, in one fair-use run); settling brings them back.
- Settling reached a profile in which no agent can gain more than 1 percent alone in all 210 runs, within four rounds.

The same learners in the published sharing game (below) end within 1.5 percent of their best choice with 1,500 rounds, but up to 10 percent from it with 100 rounds, about the market's budget. That is why the settled outcomes are the main results.

## Which settings matter

**Chance.** Settled outcomes depend little on the seed: at 24 settings with six seeds each, chance accounts for 0.1 percent of the variation in median income, 1 percent in artists working, 3 percent in licensing's gain, 5 percent in recognizability, and 32 percent in credit's effect on renewals (`output/noise.csv`). So the sensitivity results below are about the settings, not noise, except for credit's effect on renewals.

**The nine behavioral settings (Sobol analysis).** A Sobol analysis (Sobol, 2001; design and estimators from Saltelli et al., 2010) asks how much of the spread in an outcome each setting accounts for when every setting varies at once. It reports two numbers per setting. The *total index* is the share of the spread the setting is involved in, alone or together with others; the *first-order index* is the share it accounts for alone. It used 512 base samples of the nine settings in the table above (5,632 settings in all), each run in fair use, Shapley licensing and credit, and settled (`output/sensitivity.csv`, Figure 3; intervals are the middle 95 percent of 200 bootstrap resamples). Eight samples where every artist quit are left out of recognizability, and nine of credit's effect.
- *Recognizability under fair use* turns on the cost of a new signature (total 0.79, interval 0.68 to 0.93; alone 0.37, 0.19 to 0.58), then on how fast the AI learns a new one (total 0.43, 0.33 to 0.52). Each of the other settings is involved in a fifth or less.
- *Artists working under fair use* turns on the premium buyers pay for human-made work (total 0.90, 0.81 to 1.00; alone 0.63, 0.44 to 0.85). No other setting is involved in more than a fifth.
- *Median income under fair use* also turns on the human premium (total 0.74, 0.61 to 0.90), then on the share of buyers who are fans (0.33) and the cost of a new signature (0.25).
- *Licensing's gain in income* depends on several settings together: the share of fans, the human premium, the value of a recognizable style and how freely fans swap a real work for an AI one are each involved in 0.70 to 0.97 of the spread, and only the human premium matters clearly alone (0.45, 0.18 to 0.76).
- *Credit's effect on renewals* has no setting that matters alone (every first-order index is within 0.08 of zero), and with a third of its spread due to chance it has no reliable explanation in these settings.
- The two credit settings have indices of exactly zero for every outcome outside the credit regime, as they should, since they act only there.

Much of each outcome's spread comes from settings acting together: the first-order indices sum to between 0.08 (credit's effect) and 0.69 (artists working), well below 1. The first-order estimates are also imprecise: many intervals include zero, and a few estimates fall slightly below zero, which only sampling error can produce. The totals are the reliable numbers.

**Every setting, screened.** A Morris screening (Morris, 1991; measure from Campolongo, Cariboni and Saltelli, 2007) varies all 23 settings one at a time along twelve random paths and measures how much each moves each outcome (`output/screening.csv`). Settings that are not human behavior matter as much as those that are:
- recognizability: the cost of a new signature, how much buyers value more AI choices (`variety`), and fans' familiarity with a new signature;
- income and the number working: the human premium, `variety`, the outside income, how unequal popularity is, and how strongly imitation follows popularity;
- opt-out's advantage: leakage, above all;
- licensing's gain: the fee level and the price of an AI work, far above how the fee is split.

So Paper 3's shop measures several of the numbers that matter most (the human premium, the value of a recognizable style), but not all: the outside income, the value buyers put on AI variety, the price of AI work and opt-out enforcement need their own sources.

## Critiques and answers

The fifteen critiques of the independent review, each with what was done and what it showed.

| Critique | What was done | What it showed |
|---|---|---|
| 1. "Participation shuts the AI down" follows from the AI being forced to make 30% convention-only works | The AI chooses that share | The AI keeps making imitations; the finding was an artifact |
| 2. Recognizability hid genericide (a capped ratio inflated by AI volume) | Cue validity, uncapped; old measure kept as `diagnostic_ratio` | Erosion is far deeper than the first version showed (0.17, not 0.78, for artists who never change) |
| 3. Renewing was nearly free | One period's income by default, varied 0.25 to 4; familiarity lowers the value of a new style; fans no longer move between artists | Renewal rarely pays; reinvention keeps styles recognizable at 13% of settings |
| 4. The AI's choices sat at the edge of its menu | Larger volume menu; closeness tied to a technology setting the analyses vary | Volume is now an interior choice (960 of up to 3,840); the AI always uses its best closeness, since closeness costs it nothing |
| 5. "The most popular lose most" was assumed | How strongly imitation follows popularity is a setting (0 to 2) | Holds whenever imitation leans toward popular artists at all; would vanish if the AI imitated evenly |
| 6. Runs that never settled were averaged in | Settling step; settled outcomes are the main results | All 210 runs settle; opt-out's learned and settled outcomes differ most |
| 7. Quitting was permanent and early | Quitting only after the trying; coming back; outside income varied | Fewer artists are stranded; the outside income is among the most influential settings |
| 8. The sensitivity analysis was mostly noise and an all-quit artifact | Settled outcomes; all-quit samples left out; noise measured | Noise is small except for credit's effect on renewals |
| 9. Only behavioral settings were varied | Morris screening of 23 settings; robustness map | Several market and legal settings matter as much as behavior |
| 10. Opt-out was perfectly enforced | Leakage setting | Opt-out's advantage needs near-perfect enforcement |
| 11. "Buyers gain 65–73%" was not meaningful | Money per period for buyers, artists, the AI company and their total | Buyers' gain and artists' loss are similar in size; total welfare changes little under fair use |
| 12. The market is static (fixed prices, one AI company, no entry) | The price of AI work is screened | Not yet modeled: AI pricing, several AI companies, new artists entering (see below) |
| 13. Learning design flaws (own renewal phase in the context; untried situations defaulting to "never renew"; artists frozen in the AI's test) | Two situations only; fallback to the most practiced situation; artists respond in the AI's test | Learned outcomes still differ from settled ones (under fair use, recognizability 0.40 learned against 0.13 settled), most under opt-out; settled outcomes are the main results |
| 14. The published-model checks did not test the market's budget | The sharing game at 100 rounds | Up to 10% from best choices at that budget; hence settling |
| 15. The Pixiv check could not fail and its pass mark was set to the result | The check now tests only that sales of human work fall | In settled outcomes artists do not move away from imitated styles at the defaults (renewing does not pay); in learned outcomes they renew about every 14 periods |

## Checks

`check.py` confirms:
- the code is the code the saved outputs were made with (each code file's checksum is in `output/MANIFEST.sha256`);
- with no AI, recognizability stays exactly 1, incomes stay at their pre-AI level, and no one renews or quits;
- with fixed strategies, every artist's recognizability equals the formula worked out by hand;
- purchases before AI equal the logit formula;
- the same seed gives the same run, and one processor and many give the same results;
- the saved results match a fresh run;
- settling reached a stable profile in every run;
- sales of human work fall under fair use in every seed (the direction Kim, Jin and Lee, 2026, measured on Pixiv);
- the best-response table matches a fresh replay;
- the learning agents, placed inside two published models, end where those papers' equilibria say (next section).

## Checks against published models

Two published models study creators and AI with equations, not simulation. Neither has styles or signatures, so neither is a simple case of this market. Instead, the checks put this simulation's learning agents, with the same learning rule and settings, into each published model's own game (`output/published_models.csv`).

**Keinan and Ben-Porat (2026).** Twelve creators choose how much to invest in quality and whether to let a platform's AI train on their work, for a share of the platform's AI revenue (the *revenue share*).
- The payoffs as written here obey the paper's sharing rule exactly (Lemma 2), in all 4,096 sharing patterns.
- When everyone must share, the agents' quality lands within half a quality step of the paper's equilibrium formula and rises with the revenue share (Proposition 7); no creator could gain more than 1 percent by changing quality alone.
- Choosing whether to share: nobody shares when sharers get nothing and everybody when they get everything (Proposition 4). From a revenue share of 0.1 up the agents reach the paper's equilibrium exactly; at 0.05, five creators share instead of eight, none more than 1.5 percent from their best choice.
- Choosing both: sharing matches the paper's condition for full sharing.

**Yang and Zhang (2025).** Creators of different skill choose to make nothing, make by hand or make with AI, over two periods; between them the AI company trains on human work and pays a fee per unit.
- The agents' choices follow the paper's rule (Proposition 4.1) to within one skill step.
- With plenty of old training data, free training gives the best AI and the highest creator income, consumer benefit and welfare (Proposition 5.1).
- With no old data, a moderate fee gives better AI than free training; a very high fee stops training, and free training then beats it for creators and welfare (Propositions 5.5 and 5.6).
- Every outcome is within 0.005 of the paper's equilibrium.

What the checks show: the learning agents find the equilibria that published theory derives, in two different games. What they do not show: that this market's own results are right.

## Not yet in Run 1

- Liability for outputs, which would give the AI a reason not to imitate as closely as it can.
- The AI company setting its own price; more than one AI company.
- New artists entering.
- Buyers who learn.

## Files

| File | What it does |
|---|---|
| `genericide/world.py` | Takes the painters, signature quotas, diagnosticity and seeded random numbers from the painter world |
| `genericide/model.py` | The market, the agents, the buyers and the regimes |
| `genericide/experiments.py` | Runs, null models, the best-response test, settling, Sobol, noise, screening and the robustness map |
| `genericide/published.py` | The learning agents inside the two published models, and each paper's equilibrium |
| `run.py` | Writes every output |
| `check.py` | The checks above |

## Output

| File | Contents |
|---|---|
| `params.json` | Every setting and range |
| `runs.csv` | One row per regime, artist behavior, stage (learned or settled) and seed |
| `regimes.csv` | Averages over seeds, with the 2.5th to 97.5th percentile of seeds |
| `timeseries.csv` | Recognizability, income, artists working and renewals, period by period, while agents learn |
| `best_response_gaps.csv` | For each regime and seed, the most any artist, and the AI company, could gain by switching alone where learning ended |
| `sensitivity.csv`, `sensitivity_samples.csv` | Sobol indices with intervals, and the samples behind them |
| `noise.csv` | The share of each outcome's variation that is chance |
| `screening.csv` | Morris screening of all 23 settings |
| `robustness.csv`, `robustness_points.csv`, `robustness_by_setting.csv` | The share of settings where each claim holds; the points; and how each claim depends on each setting |
| `published_models.csv` | Each published result: its value in the paper's equilibrium and where the learning agents ended |
| `fig1_recognizability.png` | Whether styles still point to their artists while agents learn, by regime (averaged over each 48-period epoch) |
| `fig2_regimes.png` | Recognizability, income, artists working and total welfare by regime, settled (filled) and learned (open) |
| `fig3_sensitivity.png` | Which behavioral settings each outcome depends on |
| `fig4_robustness.png` | The share of settings at which each claim holds |
| `MANIFEST.sha256` | Checksums for every file above and for the code |

## References

Campolongo, F., Cariboni, J., and Saltelli, A. (2007). An effective screening design for sensitivity analysis of large models. *Environmental Modelling and Software, 22*(10), 1509–1518.

Keinan, G., and Ben-Porat, O. (2026). Strategic content creation with GenAI: To share or not to share? *Proceedings of the ACM Web Conference 2026*, 169–180. https://doi.org/10.1145/3774904.3792308. Preprint: arXiv:2505.16358.

Kim, S., Jin, G. Z., and Lee, E. (2026). Does generative AI crowd out human creators? Evidence from Pixiv. NBER Working Paper 34733.

McKay, M. D., Beckman, R. J., and Conover, W. J. (1979). A comparison of three methods for selecting values of input variables in the analysis of output from a computer code. *Technometrics, 21*(2), 239–245.

Morris, M. D. (1991). Factorial sampling plans for preliminary computational experiments. *Technometrics, 33*(2), 161–174.

Saltelli, A., Annoni, P., Azzini, I., Campolongo, F., Ratto, M., and Tarantola, S. (2010). Variance based sensitivity analysis of model output. Design and estimator for the total sensitivity index. *Computer Physics Communications, 181*(2), 259–270.

Sobol, I. M. (2001). Global sensitivity indices for nonlinear mathematical models and their Monte Carlo estimates. *Mathematics and Computers in Simulation, 55*(1–3), 271–280.

Sutton, R. S., and Barto, A. G. (2018). *Reinforcement learning: An introduction* (2nd ed.). MIT Press.

Train, K. E. (2009). *Discrete choice methods with simulation* (2nd ed.). Cambridge University Press.

Yang, S. A., and Zhang, A. H. (2025). Generative AI and copyright: A dynamic perspective. arXiv:2402.17801, version 2 (first version 2024).
