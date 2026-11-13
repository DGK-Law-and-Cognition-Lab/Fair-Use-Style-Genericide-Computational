# Changelog

## 2026-11-12: the package that writes the figure files pinned

A rebuild in a newly made Python environment gave four figure files that differed from the saved ones, though every pixel was the same. `requirements.txt` fixed the versions of matplotlib and numpy but not of Pillow, the package matplotlib uses to write image files, and a newer Pillow compresses them differently. `requirements.txt` now also pins Pillow 10.3.0, the version the saved figures were written with. No output changed; the checksum list was refreshed with `run.py --figures`.

## 2026-11-11: a reference's title corrected

Keinan and Ben-Porat's paper was cited under its first preprint's title, "Strategic content creation in the age of GenAI". The published title, on the record for its DOI (10.1145/3774904.3792308), is "Strategic content creation with GenAI: To share or not to share?" The README's reference list and the opening note in `genericide/published.py` now give the published title and pages. Only that note changed in the code, so no output changed; the checksum list was refreshed with `run.py --figures`.

## 2026-11-09: the rebuild check names any file that differs

`check.py --rebuild` used to report only pass or fail, and the rebuilt copy was deleted with its temporary folder. It now compares the two checksum lists file by file and names each file that differs. No output changed; a full rebuild gave byte-identical files.

## 2026-11-05: second version of Run 1, answering a review

An independent review of the first version (read cold, with no access to our reasoning) raised fifteen critiques and nine inconsistencies. Every one that could be checked was checked against the code and outputs, and each was confirmed. The changes, by critique:

**What the model measures and assumes**
- *Recognizability hid genericide.* It was the painter world's diagnosticity, whose comparison group grew with AI output and which was capped at 1, so a flooded signature could still score near 1. It is now the signature's cue validity: of the works in the last few periods that carry the signature, the share the artist made, relative to before AI, with no cap. The old measure is kept as `diagnostic_ratio`.
- *Renewing was nearly free.* It cost half of one period's income, and fans' familiarity with a new signature only moved fans between artists. Now a new signature costs one period's income by default (varied from a quarter to four periods), each artist's fans are a fixed share of all fans, and the value a fan places on an artist's style is multiplied by how well the fan knows it.
- *The AI company's choices sat at the edge of its menu.* It now also chooses whether to make works from conventions alone (30 percent or none), and volume runs to 3,840 works per period. Closeness is half or all of what its technology allows (`max_closeness`, default 0.7), because closer imitation costs it nothing and it will always use the best it has; how good the technology is becomes a setting the analyses vary (0.4 to 1.0).
- *"Participation shuts the AI down" came from the fixed 30 percent of convention-only works.* With the AI free to make none, the rule no longer stops it.
- *"The most popular lose most" was assumed.* AI imitations go to artists in proportion to popularity raised to `ai_concentration` (default 1, as before), which the analyses vary from 0 (evenly) to 2.
- *Licence fees went only to artists still working.* They now go to every rights holder, including those who quit, and the Shapley share is split among all twelve.
- *Opt-out was perfectly enforced by assumption.* `opt_out_leak` is the chance per period that the AI learns an opted-out signature anyway (default 0, varied to 0.5).
- *Quitting was permanent and happened during the early trying.* Artists now quit only after the trying phase, and while learning goes on an artist who has quit tries coming back now and then. The outside income (`reservation_share`) is varied.
- Who is popular now depends on the seed only, so regimes with the same seed are paired.

**Learning and equilibrium**
- *Runs that never settled were averaged into the results.* Every run now has two stages: the learned strategies held fixed for the measured periods (as before), and a settling step from that point, in which agents in turn switch to their best response until none gains more than 1 percent. The settled outcomes are the main results; the learned ones are reported beside them.
- Artists keep separate scores for two situations only: whether AI imitations of their current signature are on sale. Separate scores for each of the AI company's strategies split artists' experience thirty ways once the AI's menu grew, and their choices became nearly random.
- A situation first met in the measured periods now uses what the artist learned for the situation it met most often, not "never renew."
- In the best-response test, the AI company's alternatives are tested with artists responding as they learned to respond; artists who quit are tested for coming back.
- `check.py` no longer requires the median learned run in each regime to be within 5 percent of best responses: under opt-out the median gap is 44 percent, because trial and error rarely discovers that opting out pays only once the AI stops copying the current signature. It now requires that settling reach a stable profile in every run, and that the best-response table match a fresh replay; the learned gaps are reported in the README.

**Sensitivity**
- *The Sobol analysis was mostly noise and an all-quit artifact* (first-order indices summing to −1.14). It now uses settled outcomes, in which chance accounts for 0.1 to 5 percent of the variation in every outcome but credit's effect on renewals (32 percent; `noise.csv`), leaves out samples where every artist quit for outcomes about working artists, and uses 512 base samples.
- *Only behavioral settings were varied.* A Morris screening (`screening.csv`) varies 23 settings: the nine behavioral ones and fourteen about the market, the law and the learning.
- A robustness map (`robustness.csv`) records, at 160 settings drawn across all 23 ranges, whether each of eleven claims holds. The claims were written before the second version was run.

**Reporting**
- *"Buyers gain 69 to 76 percent" was not meaningful,* since a percentage of the choice model's welfare measure depends on where zero is set. Gains and losses are now in money per period, for buyers, artists and the AI company, and their total.
- The "middle 95 percent of seeds" was the minimum to the second-largest value; it is now the 2.5th to 97.5th percentile.
- The Pixiv check now tests only that sales of human work fall, which it can fail; whether artists move away from imitated styles is reported, not checked, since it depends on the stage and settings.
- The published-model checks now also report the sharing game at the market's learning budget (100 rounds), where creators end up to 10 percent below their best choice. The 3 percent test applies only at the full budget (1,500 rounds); it had at first also caught the 100-round rows.
- The figures are drawn from the saved tables, so `run.py --figures` redraws them alone. Figure 3 now says its numbers are total Sobol indices, and Figure 4 rounds halves up, as the README does (148 of 160 settings is 93 percent; it had shown 92).
- README errors corrected: six artists, not five, quit in some seeds; the Shapley share did not keep the least popular working; renewal cost was one period's income, not "pre-AI income"; Figure 1's averaging; per-regime best-response counts.

**Sync protection.** `MANIFEST.sha256` now also lists every code file, and `check.py` first confirms the code is the code the outputs were made with. On 4 to 5 November a computer update left the painter world's code rolled back to its first version while other files kept the second; this check would have caught that. `../check_all.py` runs both folders' checks and flags sync-conflict copies.

Every result in the README changed.

## 2026-11-03, later: published-model checks, and the fixes they led to

Added:
- `genericide/published.py`: the simulation's learning agents placed inside two published models, Keinan and Ben-Porat (2026) and Yang and Zhang (2024, revised 2025), with each paper's equilibrium computed from its own equations.
- `best_response_gaps` in `genericide/experiments.py`: after learning, replays the measured periods with every strategy held fixed and one agent switched to each alternative, to see what that agent would gain by switching alone.
- Outputs `best_response_gaps.csv` and `published_models.csv`, and checks on both in `check.py`.

What the checks found in the first build's learning rule, and the changes:
- In Keinan and Ben-Porat's sharing game, learners often stopped short of the equilibrium: some creators could gain up to 20 percent by switching. Cause: when conditions changed so that every strategy paid more, only the strategy being played had its score updated, so the agent stayed on it. Now the other scores move with it, keeping their gain or loss relative to the agent's choice, and only trying an alternative changes that.
- In the market under opt-out, artists could gain 12 to 28 percent of their pre-AI income by switching strategy alone. Causes: with 8 strategies and 60 short epochs, most alternatives were tried once, early, while the AI company was still trying its own options; a single early score was never revised; and a fixed renewal schedule cannot express "renew once to escape imitation, then stop," which is what opt-out rewards. Changes:
  - a new artist strategy: renew whenever the AI is making works in the current signature (the response Kim, Jin and Lee observed on Pixiv);
  - artists see the AI company's choice, and whether AI works in their current signature are on the market, and keep separate scores for each thing they might see. The first means the AI company's tries no longer scramble artists' scores. The second was needed because "opt out and stop renewing" pays well only once the AI is no longer copying the current signature; with one score for both situations, artists under opt-out kept renewing every 16 periods for nothing in 13 of 30 runs;
  - epochs of 48 periods, scored after the first 16, so a strategy is judged on how it pays once it has settled in; 4,800 learning periods instead of 480;
  - step sizes that start as plain averages over the first few tries (Sutton and Barto, 2018, exercise 2.7), so one early score does not stick;
  - each agent tries the strategies first in its own order, so agents do not all try the same one at once.
- An exploration rule based on upper confidence bounds was tried along the way and dropped: in the sharing game, creators explored in step with each other and disturbed each other's scores.
- A first version of the best-response replay held the strategies of the last learning epoch, which were often random tries, rather than the agents' final choices. Fixed before any result was kept.
- The standard set for the best-response check before the final runs was that in at least 90 percent of runs in every regime, no agent could gain more than 5 percent by switching alone. The final version does not meet it everywhere (README, "How close agents get to their best choices"). More learning time and more exploring were tried and did not close the gap. The check now asserts the median run and the README reports the tails.

Every Run 1 result changed with these fixes; the README reports the new ones.

## 2026-11-03

Run 1, first build.

- `genericide/world.py`: takes the painters, the signature quotas (9 of an owner's 10 paintings, 2 of the other 110), the diagnosticity measure and the seeded random numbers from `../painter_world`.
- `genericide/model.py`: the market. Artists, an AI company, fans (nested logit) and decorators (logit); seven regimes (no AI, fair use, opt-out, licensing under leave-one-out, Shapley and participation, credit the artist).
- `genericide/experiments.py`: runs over seeds, null models (artists who never change; artists who pick strategies at random), and Sobol sensitivity over nine settings.
- `run.py`, `check.py`, `README.md`.

Changes made while building, before any result was kept:
- Artists first learned period by period (Q-learning). Two problems: random tries of "quit" ended careers by accident, and the learning rule counted an action the regime did not allow, which kept every estimate too high. Replaced with learning over strategies scored by epoch, with quitting never tried at random.
- The AI company's learning started every option at zero and stuck on the first one it tried. It now tries each option once before comparing them.
- The market now starts with a full window of pre-AI works, so recognizability is exactly 1 before AI arrives.
- Figure 1 averages over each 8-period epoch and spaces its labels.
