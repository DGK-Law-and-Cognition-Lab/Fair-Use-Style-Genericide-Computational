"""Exact rates and diagnosticity for every feature: the generality map.

For a feature f and its home painter a (its owner, or else the painter who
uses it most):

  home rate        share of a's paintings with f
  others' rate     share of the other painters' paintings with f
  diagnosticity    ln(home rate / others' rate), each rate smoothed by adding
                   half a painting, so a feature no one else uses gets a large
                   finite value instead of infinity. This is the pointwise
                   mutual information between the feature and the painter.

The same three numbers are given one level up, for the home painter's genre:
the share of the genre's 40 paintings with f, the share of the other 80, and
the genre diagnosticity.

Features are listed at two grains. "oneoff:ladder:teal" is one painting's
teal ladder (the expression); "idea:ladder" is a ladder of any colour (the
idea), which every painter uses once.
"""

from math import log

from .world import PAINTERS, WORKS_PER_PAINTER, GENRES, GENRE_OF, idea_of, label, parse

CLASS = {"convention": "convention", "genre": "genre convention", "motif": "signature motif",
         "manner": "signature manner", "rare": "rare, no owner", "oneoff": "one-off",
         "idea": "idea behind one-offs"}


def features_with_ideas(features):
    return set(features) | {idea_of(f) for f in features if idea_of(f)}


def painter_counts(world):
    """{feature: {painter: number of that painter's paintings with it}}"""
    counts = {}
    for p in world["paintings"]:
        for f in features_with_ideas(p["features"]):
            counts.setdefault(f, {q: 0 for q in PAINTERS})[p["painter"]] += 1
    return dict(sorted(counts.items()))


def diagnosticity(n_home, n_others, n=WORKS_PER_PAINTER, n_other_works=None):
    n_other_works = n_other_works or n * (len(PAINTERS) - 1)
    return log(((n_home + 0.5) / (n + 1)) / ((n_others + 0.5) / (n_other_works + 1)))


def feature_table(world):
    rows = []
    n_works = len(world["paintings"])
    n_other_works = n_works - WORKS_PER_PAINTER
    for f, by_painter in painter_counts(world).items():
        meta = world["features"].get(f, {})
        home = meta.get("owner") or max(PAINTERS, key=lambda q: (by_painter[q], -PAINTERS.index(q)))
        total = sum(by_painter.values())
        n_home = by_painter[home]
        genre = GENRE_OF[home]
        n_genre = sum(by_painter[q] for q in GENRES[genre])
        n_genre_works = len(GENRES[genre]) * WORKS_PER_PAINTER
        rows.append({
            "feature": f, "class": CLASS[parse(f)[0]], "label": label(f),
            "owner": meta.get("owner") or "", "home_painter": home,
            "paintings": total, "painters_using": sum(1 for v in by_painter.values() if v),
            "world_rate": round(total / n_works, 4),
            "home_rate": round(n_home / WORKS_PER_PAINTER, 4),
            "others_rate": round((total - n_home) / n_other_works, 4),
            "diagnosticity": round(diagnosticity(n_home, total - n_home), 3),
            "genre": genre,
            "genre_rate": round(n_genre / n_genre_works, 4),
            "outside_genre_rate": round((total - n_genre) / (n_works - n_genre_works), 4),
            "genre_diagnosticity": round(diagnosticity(n_genre, total - n_genre, n=n_genre_works,
                                                       n_other_works=n_works - n_genre_works), 3),
        })
    return rows


def painter_rate_table(world):
    rows = []
    for f, by_painter in painter_counts(world).items():
        total = sum(by_painter.values())
        for q in PAINTERS:
            n = by_painter[q]
            rows.append({"feature": f, "painter": q, "count": n,
                         "rate": round(n / WORKS_PER_PAINTER, 4),
                         "others_rate": round((total - n) / (len(world["paintings"]) - WORKS_PER_PAINTER), 4),
                         "diagnosticity": round(diagnosticity(n, total - n), 3)})
    return rows


def class_summary(rows):
    """One line per class: how many features, and the range of each measure."""
    out = []
    for cls in CLASS.values():
        sub = [r for r in rows if r["class"] == cls]
        if not sub:
            continue
        rng = lambda key: (min(r[key] for r in sub), max(r[key] for r in sub))
        out.append({"class": cls, "features": len(sub),
                    "home_rate_min": rng("home_rate")[0], "home_rate_max": rng("home_rate")[1],
                    "others_rate_min": rng("others_rate")[0], "others_rate_max": rng("others_rate")[1],
                    "diagnosticity_min": rng("diagnosticity")[0],
                    "diagnosticity_max": rng("diagnosticity")[1],
                    "genre_diagnosticity_min": rng("genre_diagnosticity")[0],
                    "genre_diagnosticity_max": rng("genre_diagnosticity")[1]})
    return out
