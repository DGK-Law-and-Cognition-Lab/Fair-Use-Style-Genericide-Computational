# Style genericide: simulation code and outputs

This repository holds the computer simulation behind the Article "Style Genericide" by David G. Kamper, with every table and figure the simulation produced and the checks that confirm them.

**The idea.** A painter always paints a small yellow bird, so seeing the bird tells you whose painting it is. An AI company then puts yellow birds in thousands of pictures the painter never made. Now the bird tells you little, even though no painting was copied. That is *style genericide*, named after the trademark term for a brand name that becomes the ordinary word for a thing ("escalator"). The simulation is a small art market of twelve artists, one AI company and buyers. It is run under seven legal regimes: no AI, fair use, opt-out, three ways of dividing a licence fee, and crediting the artist. It asks which regimes keep styles pointing to their artists, and what each costs artists, buyers and the AI company.

**Which run this is.** Run 1, second version, of 5 November 2026. Every setting in Run 1 is assumed, not measured. A later run will replace some settings with measured values and will be released here as a new version.

## What is here

| Folder or file | Contents |
|---|---|
| `style_genericide/` | The simulation. `run.py` and `genericide/` are the code. `check.py` is the checks. `output/` holds every saved table and figure, and a list of checksums (`MANIFEST.sha256`). `README.md` describes the model, the results and each output file. `CHANGELOG.md` records every change. |
| `painter_world/painterworld/` | Five code files from the "painter world", a small built world of twelve fictional painters: the painters and how often each one's signature appears, a measure of how strongly a feature points to a painter, and the random-number generator. The simulation uses these five files and nothing else from the painter world. |
| `CITATION.cff` | How to cite this repository |
| `LICENSE` | The MIT licence |

A *checksum* is a short fingerprint of a file: change one character of the file and the fingerprint changes. The checks use checksums to confirm that the code and the saved outputs belong together.

## How to run it

You need Python 3.12. The simulation uses only what comes with Python. The figures need three packages, listed with their exact versions in `style_genericide/requirements.txt`.

```bash
cd style_genericide
```

```bash
python3 -m pip install -r requirements.txt
```

Run the checks. This takes a few minutes, and each of the 23 checks prints PASS or FAIL.

```bash
python3 check.py
```

Run the checks and also rebuild everything in a temporary folder. This confirms that every rebuilt file is the same as the saved one, byte for byte. It takes about an hour on twelve processor cores.

```bash
python3 check.py --rebuild
```

Rerun the simulation and rewrite everything in `output/`. This also takes about an hour.

```bash
python3 run.py
```

The simulation is *seeded*: its random numbers start from fixed values, so every run gives the same files.

## What the checks confirm

- The code is the code the saved outputs were made with.
- With no AI in the market, nothing changes: styles stay fully recognizable and incomes stay where they were.
- Recognizability and purchases equal formulas worked out by hand.
- The same seed gives the same run, on one processor or many, and the saved results match a fresh run.
- The simulation's learning agents, placed inside two published economic models (Keinan and Ben-Porat, 2026; Yang and Zhang, 2025), end where those papers' equations say they should.
- With `--rebuild`, a fresh run of everything gives byte-identical files.

The full list is in `style_genericide/README.md`, under "Checks".

## Two notes

- `style_genericide/README.md` mentions `../check_all.py`. That script belongs to the lab's larger project folder, where it runs these checks together with the checks of other folders. It is not in this repository. `check.py` is the complete check of the simulation.
- The five painter-world files are unchanged copies. Their comments mention other painter-world files (its own checks, its drawing code, its pixel measurements) that are not in this repository. Nothing here needs them.

## The paper

David G. Kamper, *Style Genericide* (in preparation). University of Chicago Law School; Department of Psychology, University of California, Los Angeles.

## How to cite

Each release of this repository is archived at Zenodo, which gives it a permanent identifier (a DOI). Cite the release you used. `CITATION.cff` has the details, and GitHub's "Cite this repository" button reads it.

## Licence

MIT. See `LICENSE`.
