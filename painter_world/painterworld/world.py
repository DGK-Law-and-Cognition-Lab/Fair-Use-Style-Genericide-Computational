"""The small world: twelve fictional painters and their 120 paintings.

The painters work in three genres of four: landscapes (A to D), harbors (E to H)
and streets (I to L). Every feature is placed by an exact quota, not a coin
flip, so its rate in each painter's work is known before anything is drawn:

  conventions        what every painter does, at nearly the same rate
  genre conventions  what every painter in one genre does, and no one outside it
  motifs             one signature object per painter, in 9 of the owner's 10
                     paintings and in 2 paintings by 2 other painters
  manners            one signature way of painting per painter, same quotas
  rare               rare features that point to no one: 6 paintings by 6
                     painters; every painter has 6, in different paintings
  one-offs           a prop in a colour, found in exactly one painting

The props behind the one-offs are balanced: every painter uses each of the
twenty props once, each in a different colour. So "a ladder" (the idea) is
equally common for everyone, while "a teal ladder" (this expression of it)
belongs to a single painting.
"""

from .parts import PARTS, WORLD_PROPS, COLOURS, FENCE_WIDTH
from .rng import Rng

SEED = "painter-world-2"
W, H = 400, 300
PAINTERS = list("ABCDEFGHIJKL")
WORKS_PER_PAINTER = 10
GENRES = {"landscape": PAINTERS[0:4], "harbor": PAINTERS[4:8], "street": PAINTERS[8:12]}
GENRE_OF = {p: g for g, ps in GENRES.items() for p in ps}

# Paintings out of each painter's ten, before a spread of -1, 0 or +1 that
# leaves the total across painters unchanged.
CONVENTIONS = {"horizon_low": 8, "sun": 7, "clouds": 6}
GENRE_CONVENTIONS = {
    "landscape": {"tree": 7, "hills": 6, "house": 5, "path": 4},
    "harbor": {"water": 8, "rowboat": 6, "pier": 5, "buoy": 4},
    "street": {"road": 8, "buildings": 6, "shopfront": 5, "bicycle": 4},
}
# Boats, piers and buoys go only in paintings that have water.
NEEDS = {"rowboat": "water", "pier": "water", "buoy": "water"}
# One signature object per painter, chosen to suit the painter's genre.
MOTIFS = ["windmill", "scarecrow", "stone_well", "sunflower",
          "lighthouse", "sailboat_pond", "crescent_moon", "yellow_bird",
          "hot_air_balloon", "kite", "picket_fence", "three_crows"]
MANNERS = ["banded_sky", "thick_outlines", "stippled_ground", "hatched_ground", "drop_shadows",
           "border_frame", "peach_sky", "vignette", "wavy_horizon", "violet_ground",
           "striped_ground", "horizon_glow"]
RARE = ["rainbow", "shooting_star", "butterfly", "mushrooms", "snail", "frog", "fox", "hedgehog",
        "owl", "paper_plane", "dragonfly", "puddle"]
OWNER_COUNT = 9
BORROW_COUNT = 2
RARE_COUNT = 6

LABELS = {
    "convention:horizon_low": "horizon in the lower third",
    "convention:sun": "a sun", "convention:clouds": "clouds",
    "genre:tree": "a round tree", "genre:hills": "rolling hills", "genre:house": "a small house",
    "genre:path": "a path to the horizon",
    "genre:water": "open water", "genre:rowboat": "a rowboat", "genre:pier": "a wooden pier",
    "genre:buoy": "a red buoy",
    "genre:road": "a road", "genre:buildings": "a row of town houses",
    "genre:shopfront": "a shop with an awning", "genre:bicycle": "a bicycle",
    "motif:yellow_bird": "a small yellow bird in a corner",
    "motif:hot_air_balloon": "a red hot-air balloon", "motif:windmill": "a windmill",
    "motif:lighthouse": "a striped lighthouse", "motif:scarecrow": "a scarecrow",
    "motif:crescent_moon": "a crescent moon by day", "motif:sailboat_pond": "a sailboat on a pond",
    "motif:three_crows": "three crows", "motif:stone_well": "a stone well",
    "motif:kite": "a kite with a tail", "motif:picket_fence": "a picket fence in front",
    "motif:sunflower": "a tall sunflower in front",
    "manner:banded_sky": "sky painted in bands", "manner:thick_outlines": "thick outlines",
    "manner:stippled_ground": "dotted ground", "manner:hatched_ground": "hatched ground",
    "manner:drop_shadows": "long cast shadows", "manner:border_frame": "a painted border",
    "manner:peach_sky": "a peach-tinted sky", "manner:vignette": "darkened corners",
    "manner:wavy_horizon": "a wavy horizon line", "manner:violet_ground": "violet-tinted ground",
    "manner:striped_ground": "ground in stripes", "manner:horizon_glow": "a glow along the horizon",
    "rare:rainbow": "a rainbow", "rare:shooting_star": "a shooting star",
    "rare:butterfly": "a butterfly", "rare:mushrooms": "red mushrooms", "rare:snail": "a snail",
    "rare:frog": "a frog", "rare:fox": "a fox", "rare:hedgehog": "a hedgehog",
    "rare:owl": "an owl on a stump", "rare:paper_plane": "a paper plane",
    "rare:dragonfly": "a dragonfly", "rare:puddle": "a puddle",
}


def parse(fid):
    """Split a feature id into (kind, name, colour or None)."""
    bits = fid.split(":")
    return bits[0], bits[1], bits[2] if len(bits) > 2 else None


def label(fid):
    kind, name, colour = parse(fid)
    if kind == "oneoff":
        return f"a {colour} {name.replace('_', ' ')}"
    if kind == "idea":
        return f"a {name.replace('_', ' ')} of any colour"
    return LABELS[fid]


def oneoff_id(prop, colour):
    return f"oneoff:{prop}:{colour}"


def idea_of(fid):
    """The idea-level feature behind a one-off ("a ladder" for "a teal ladder")."""
    kind, name, _ = parse(fid)
    return f"idea:{name}" if kind == "oneoff" else None


def genre_of_feature(fid):
    """The genre a genre convention belongs to, or None."""
    kind, name, _ = parse(fid)
    if kind != "genre":
        return None
    return next(g for g, convs in GENRE_CONVENTIONS.items() if name in convs)


# ----- feature quotas ------------------------------------------------------

def _work_ids(painter):
    return [f"{painter}{k + 1:02d}" for k in range(WORKS_PER_PAINTER)]


def assign_features():
    """Return {painting id: set of feature ids} and {feature id: owner painter}."""
    feats = {w: set() for p in PAINTERS for w in _work_ids(p)}
    owner = {}

    for name, base in CONVENTIONS.items():
        fid = f"convention:{name}"
        spread = Rng(SEED, "spread", fid).shuffle([-1] * 4 + [0] * 4 + [1] * 4)
        for p, d in zip(PAINTERS, spread):
            for w in Rng(SEED, "convention", fid, p).sample(_work_ids(p), base + d):
                feats[w].add(fid)

    for genre, convs in GENRE_CONVENTIONS.items():
        for name, base in convs.items():
            fid = f"genre:{name}"
            spread = Rng(SEED, "spread", fid).shuffle([-1, 0, 0, 1])
            for p, d in zip(GENRES[genre], spread):
                pool = _work_ids(p)
                if name in NEEDS:
                    pool = [w for w in pool if f"genre:{NEEDS[name]}" in feats[w]]
                for w in Rng(SEED, "genre", fid, p).sample(pool, base + d):
                    feats[w].add(fid)

    borrowed = {w: False for w in feats}
    for i, p in enumerate(PAINTERS):
        for fid in (f"motif:{MOTIFS[i]}", f"manner:{MANNERS[i]}"):
            owner[fid] = p
            for w in Rng(SEED, "owner", fid).sample(_work_ids(p), OWNER_COUNT):
                feats[w].add(fid)
            others = Rng(SEED, "borrow", fid).shuffle([q for q in PAINTERS if q != p])
            placed = 0
            for q in others:
                free = [w for w in _work_ids(q) if not borrowed[w]]
                if free:
                    w = Rng(SEED, "borrow", fid, q).choice(free)
                    feats[w].add(fid)
                    borrowed[w] = True
                    placed += 1
                if placed == BORROW_COUNT:
                    break

    # A balanced design: painter j gets rares j, j+1, ..., j+5 (mod 12) after both
    # lists are shuffled, so each rare goes to 6 painters and each painter has 6 rares.
    rares = Rng(SEED, "rare-order").shuffle(list(RARE))
    painters = Rng(SEED, "rare-painters").shuffle(list(PAINTERS))
    for j, p in enumerate(painters):
        works = Rng(SEED, "rare-works", p).sample(_work_ids(p), RARE_COUNT)
        for k, w in enumerate(works):
            feats[w].add(f"rare:{rares[(j + k) % len(rares)]}")

    colour_names = list(COLOURS)
    for i, p in enumerate(PAINTERS):
        order = Rng(SEED, "oneoffs", p).shuffle(list(range(len(WORLD_PROPS))))
        for k, w in enumerate(_work_ids(p)):
            for j in order[2 * k:2 * k + 2]:
                fid = oneoff_id(WORLD_PROPS[j], colour_names[(i + j) % len(colour_names)])
                feats[w].add(fid)
                owner[fid] = p
    return feats, owner


# ----- layout --------------------------------------------------------------

def horizon_y(features):
    return 200 if "convention:horizon_low" in features else 150


def depth_scale(y, yh):
    """Parts lower on the canvas are nearer, so drawn larger."""
    return 0.8 + 0.55 * (y - yh) / (H - yh)


def part_of(fid):
    kind, name, _ = parse(fid)
    if kind == "convention" and name == "sun":
        return name
    if kind in ("genre", "motif", "rare", "oneoff") and name in PARTS:
        return name
    return None


def band(features):
    """Water (harbors) or a road (streets) runs across the ground below the horizon:
    the band's top and bottom, measured down from the horizon, or None."""
    if "genre:water" in features:
        return (0, 32)
    if "genre:road" in features:
        return (20, 46)
    return None


def _box(part, x, y, s):
    p = PARTS[part]
    w, h = p["w"] * s * p["size"], p["h"] * s * p["size"]
    if p["region"] in ("sky", "corner"):
        return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
    return (x - w / 2, y - h, x + w / 2, y)


def _clear(box, boxes, margin):
    x0, y0, x1, y1 = box
    if x0 < 4 or x1 > W - 4 or y0 < 4:
        return False
    return all(x1 + margin <= b[0] or b[2] + margin <= x0 or y1 + margin <= b[1] or b[3] + margin <= y0
               for b in boxes)


def _place(part, rng, yh, boxes, low=24):
    """Find a spot for a part that overlaps nothing already placed. Ground parts
    stand at least `low` below the horizon (more when a band of water or road is there)."""
    region = PARTS[part]["region"]
    for attempt in range(600):
        margin = 3 if attempt < 400 else 0
        if region == "sky":
            x, y, s = rng.uniform(26, W - 26), rng.uniform(20, yh - 30), 1.0
        elif region == "far":
            y = rng.uniform(yh + 6, yh + 18)
            x, s = rng.uniform(30, W - 30), 0.85
        elif region == "front":
            x = rng.choice([rng.uniform(24, 70), rng.uniform(W - 70, W - 24)])
            y, s = rng.uniform(H - 12, H - 4), 0.95
        elif region == "water":
            x, y, s = rng.uniform(34, W - 34), rng.uniform(yh + 14, yh + 28), 0.85
        elif region == "pier":
            x, y, s = rng.choice([54.0, W - 54.0]), yh + 30.0, 1.0
        else:
            y = rng.uniform(yh + low, H - 8)
            x, s = rng.uniform(26, W - 26), depth_scale(y, yh)
        box = _box(part, x, y, s)
        if _clear(box, boxes, margin):
            boxes.append(box)
            return {"x": round(x, 1), "y": round(y, 1), "s": round(s, 3)}
    raise RuntimeError(f"no room for {part}")


# Sky and far parts are placed first, big ground parts before small ones.
_ORDER = {"corner": 0, "sky": 1, "far": 2, "pier": 3, "water": 4, "front": 5, "ground": 6}


def make_layout(features, rng, keep=None):
    """Positions for every drawn feature. `keep` holds positions to reuse."""
    keep = dict(keep or {})
    yh = horizon_y(features)
    layout, boxes = {"horizon": yh}, []
    low = 24 if band(features) is None else band(features)[1] + 10

    for fid, pl in keep.items():
        if fid in features and part_of(fid):
            layout[fid] = pl
            boxes.append(_box(part_of(fid), pl["x"], pl["y"], pl["s"]))
        elif fid in features and fid == "convention:clouds":
            layout[fid] = pl
            boxes.extend(_box("cloud", c["x"], c["y"], c["s"]) for c in pl)
        elif fid in features:
            layout[fid] = pl

    if "genre:hills" in features and "genre:hills" not in layout:
        xs, bumps = -20.0, []
        while xs < W:
            w = rng.uniform(110, 190)
            bumps.append([round(xs, 1), round(w, 1), round(rng.uniform(18, 38), 1)])
            xs += w * rng.uniform(0.6, 0.85)
        layout["genre:hills"] = bumps
    if "genre:path" in features and "genre:path" not in layout:
        layout["genre:path"] = {"bottom": round(rng.uniform(150, 250), 1),
                                     "top": round(rng.uniform(175, 225), 1)}
    if "rare:rainbow" in features and "rare:rainbow" not in layout:
        layout["rare:rainbow"] = {"cx": round(rng.uniform(120, 280), 1)}
    if "motif:picket_fence" in features:
        if "motif:picket_fence" not in layout:
            layout["motif:picket_fence"] = {"x0": round(rng.uniform(10, W - 10 - FENCE_WIDTH), 1)}
        x0 = layout["motif:picket_fence"]["x0"]
        boxes.append((x0, H - 34, x0 + FENCE_WIDTH, H))
    if "motif:yellow_bird" in features and "motif:yellow_bird" not in layout:
        right = rng.bernoulli(0.5)
        layout["motif:yellow_bird"] = {"x": W - 32 if right else 32, "y": 26, "s": 1.25,
                                       "flip": right}
        boxes.append(_box("yellow_bird", layout["motif:yellow_bird"]["x"], 26, 1.25))

    todo = sorted((f for f in features if part_of(f) and f not in layout),
                  key=lambda f: (_ORDER[PARTS[part_of(f)]["region"]],
                                 -PARTS[part_of(f)]["w"] * PARTS[part_of(f)]["h"], f))
    for fid in todo:
        layout[fid] = _place(part_of(fid), rng, yh, boxes, low)
    if "convention:clouds" in features and "convention:clouds" not in layout:
        n = 2 + int(rng.random() * 2)
        layout["convention:clouds"] = [_place("cloud", rng, yh, boxes) for _ in range(n)]
    return layout


def remap_layout(layout, yh_new):
    """Move a kept layout onto a canvas whose horizon sits at a different height."""
    yh_old = layout["horizon"]
    if yh_old == yh_new:
        return dict(layout)
    out = {"horizon": yh_new}
    for fid, pl in layout.items():
        if fid == "horizon":
            continue
        if fid == "convention:clouds":
            out[fid] = [dict(c, y=round(c["y"] * yh_new / yh_old, 1)) for c in pl]
        elif isinstance(pl, dict) and "y" in pl:
            region = PARTS[part_of(fid)]["region"]
            if region in ("sky", "corner"):
                out[fid] = dict(pl, y=round(pl["y"] * yh_new / yh_old, 1))
            elif region == "front":
                out[fid] = dict(pl)
            elif region in ("water", "pier"):
                out[fid] = dict(pl, y=round(pl["y"] + yh_new - yh_old, 1))
            else:
                y = yh_new + (pl["y"] - yh_old) * (H - yh_new) / (H - yh_old)
                s = depth_scale(y, yh_new) if region == "ground" else pl["s"]
                out[fid] = dict(pl, y=round(y, 1), s=round(s, 3))
        else:
            out[fid] = pl
    return out


# ----- the world -----------------------------------------------------------

def build_world():
    feats, owner = assign_features()
    paintings = []
    for p in PAINTERS:
        for w in _work_ids(p):
            fs = sorted(feats[w])
            paintings.append({"id": w, "painter": p, "genre": GENRE_OF[p], "features": fs,
                              "layout": make_layout(fs, Rng(SEED, "layout", w))})
    features = {}
    for pt in paintings:
        for fid in pt["features"]:
            kind, _, _ = parse(fid)
            features.setdefault(fid, {"id": fid, "kind": kind, "owner": owner.get(fid),
                                      "label": label(fid)})
    for fid, meta in features.items():
        meta["genre"] = genre_of_feature(fid)
    return {"seed": SEED, "painters": PAINTERS, "genres": GENRES, "works_per_painter": WORKS_PER_PAINTER,
            "features": dict(sorted(features.items())), "paintings": paintings}
