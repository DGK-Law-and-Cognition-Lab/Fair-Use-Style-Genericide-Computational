"""What the simulation takes from the painter world: the painters, their quotas,
the diagnosticity measure and the seeded random numbers.

The painter world is the sibling folder ../painter_world, or the folder named
by PAINTER_WORLD_DIR.
"""

import os
import sys
from pathlib import Path

PAINTER_WORLD = Path(os.environ.get("PAINTER_WORLD_DIR",
                                    Path(__file__).resolve().parents[2] / "painter_world"))
sys.path.insert(0, str(PAINTER_WORLD))

from painterworld.world import PAINTERS, MOTIFS, OWNER_COUNT, BORROW_COUNT, WORKS_PER_PAINTER  # noqa: E402
from painterworld.measures import diagnosticity  # noqa: E402
from painterworld.rng import Rng  # noqa: E402

# A signature is in 9 of its owner's 10 paintings and in 2 of the other 110.
OWNER_RATE = OWNER_COUNT / WORKS_PER_PAINTER
BORROW_RATE = BORROW_COUNT / (WORKS_PER_PAINTER * (len(PAINTERS) - 1))

__all__ = ["PAINTERS", "MOTIFS", "OWNER_RATE", "BORROW_RATE", "diagnosticity", "Rng"]
