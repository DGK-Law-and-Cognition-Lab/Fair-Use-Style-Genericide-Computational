"""Seeded random numbers, identical to the Mondrian study's rng.js.

mulberry32 and xmur3 are ported bit for bit, so the same seed string gives
the same sequence here and in a browser. check.py holds test values taken
from rng.js.
"""

MASK = 0xFFFFFFFF


def _imul(a, b):
    return (a * b) & MASK


def mulberry32(seed):
    """Return a function giving floats in [0, 1) from a 32-bit seed."""
    s = seed & MASK

    def next_float():
        nonlocal s
        s = (s + 0x6D2B79F5) & MASK
        t = s
        t = _imul(t ^ (t >> 15), t | 1)
        t ^= (t + _imul(t ^ (t >> 7), t | 61)) & MASK
        return ((t ^ (t >> 14)) & MASK) / 4294967296

    return next_float


def xmur3(text):
    """Hash an ASCII string into a function giving 32-bit seeds."""
    h = (1779033703 ^ len(text)) & MASK
    for ch in text:
        h = _imul(h ^ ord(ch), 3432918353)
        h = ((h << 13) | (h >> 19)) & MASK

    def next_seed():
        nonlocal h
        h = _imul(h ^ (h >> 16), 2246822507)
        h = _imul(h ^ (h >> 13), 3266489909)
        h ^= h >> 16
        return h & MASK

    return next_seed


class Rng:
    """A seeded generator with the helpers rng.js provides."""

    def __init__(self, *parts):
        key = ":".join(str(p) for p in parts)
        self.random = mulberry32(xmur3(key)())

    def uniform(self, lo, hi):
        return lo + self.random() * (hi - lo)

    def integer(self, lo, hi):
        """Inclusive lo, exclusive hi, as rngInt in rng.js."""
        return int(lo + self.random() * (hi - lo))

    def choice(self, items):
        return items[int(self.random() * len(items))]

    def shuffle(self, items):
        """Fisher-Yates in place, as rngShuffle in rng.js. Returns the list."""
        for i in range(len(items) - 1, 0, -1):
            j = int(self.random() * (i + 1))
            items[i], items[j] = items[j], items[i]
        return items

    def sample(self, items, k):
        return self.shuffle(list(items))[:k]

    def bernoulli(self, p):
        return self.random() < p
