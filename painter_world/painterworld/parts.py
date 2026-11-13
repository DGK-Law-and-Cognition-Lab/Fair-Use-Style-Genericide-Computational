"""The library of parts every painting is drawn from.

Each part is a function returning SVG elements in its own coordinates.
Ground parts stand on the point (0, 0) and extend upward (negative y).
Sky parts are centered on (0, 0). The renderer moves and scales them.

Every function takes `st`, the painting's stroke settings ({"sw": stroke
width, "ink": outline colour}), and `c`, a colour that only the props use.
"""

from math import cos, sin, radians

INK = "#2f2a26"
WOOD = "#8b6b3d"
DARK_WOOD = "#7a5230"


def shade(hex_colour, k):
    """Darken a #rrggbb colour by multiplying each channel by k."""
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return "#{:02x}{:02x}{:02x}".format(int(r * k), int(g * k), int(b * k))


def _s(fill, st, extra=""):
    """Fill plus the painting's outline."""
    return (f'fill="{fill}" stroke="{st["ink"]}" stroke-width="{st["sw"]:.2f}" '
            f'stroke-linejoin="round"{extra}')


def _bar(x1, y1, x2, y2, colour, width, st):
    """A thick coloured line with an outline: an ink line under a coloured one."""
    pts = f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"'
    return (f'<line {pts} stroke="{st["ink"]}" stroke-width="{width + 2 * min(st["sw"], 1.4):.2f}" '
            f'stroke-linecap="round"/>'
            f'<line {pts} stroke="{colour}" stroke-width="{width:.2f}" stroke-linecap="round"/>')


def _stroke(d, colour, width, st):
    """A coloured open path with an outline, drawn the same way as _bar."""
    return (f'<path d="{d}" fill="none" stroke="{st["ink"]}" '
            f'stroke-width="{width + 2 * min(st["sw"], 1.4):.2f}" stroke-linecap="round"/>'
            f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width:.2f}" '
            f'stroke-linecap="round"/>')


def _blob(circles, fill, st):
    """A shape made of overlapping circles, outlined only on its outer edge."""
    under = "".join(f'<circle cx="{x}" cy="{y}" r="{r + st["sw"]:.2f}" fill="{st["ink"]}"/>'
                    for x, y, r in circles)
    over = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>' for x, y, r in circles)
    return under + over


# ----- conventions ---------------------------------------------------------

def sun(st, c=None):
    rays = ""
    for k in range(8):
        a = radians(22.5 + 45 * k)
        rays += (f'<line x1="{20 * cos(a):.1f}" y1="{20 * sin(a):.1f}" '
                 f'x2="{27 * cos(a):.1f}" y2="{27 * sin(a):.1f}" stroke="#e0a526" '
                 f'stroke-width="3" stroke-linecap="round"/>')
    return rays + f'<circle r="15" {_s("#f5c542", st)}/>'


def cloud(st, c=None):
    return _blob([(-16, 2, 10), (0, -5, 13), (15, 1, 10), (6, 5, 9), (-6, 5, 9)], "#ffffff", st)


def tree(st, c=None):
    return (f'<rect x="-3.5" y="-30" width="7" height="30" {_s(DARK_WOOD, st)}/>'
            + _blob([(0, -44, 16), (-10, -36, 11), (10, -36, 11)], "#5b8f3a", st))


def house(st, c=None):
    return (f'<rect x="-20" y="-26" width="40" height="26" {_s("#efe0c0", st)}/>'
            f'<polygon points="-24,-26 0,-44 24,-26" {_s("#a65a3a", st)}/>'
            f'<rect x="-5" y="-14" width="10" height="14" {_s("#6b4a2f", st)}/>'
            f'<rect x="8" y="-21" width="8" height="7" {_s("#bfe0f0", st)}/>')


# ----- signature motifs ----------------------------------------------------

def yellow_bird(st, c=None):
    return (f'<polygon points="-9,-1 -16,-6 -15,2" {_s("#d9a800", st)}/>'
            f'<ellipse cx="0" cy="0" rx="9" ry="6" {_s("#f2c200", st)}/>'
            f'<circle cx="8" cy="-5" r="4.5" {_s("#f2c200", st)}/>'
            f'<polygon points="12,-6.5 17.5,-4.5 12,-3" {_s("#e07b00", st)}/>'
            f'<circle cx="9.3" cy="-6" r="1.1" fill="{st["ink"]}"/>'
            f'<ellipse cx="-2" cy="-1" rx="5" ry="3" transform="rotate(-20 -2 -1)" '
            f'{_s("#d9a800", st)}/>')


def hot_air_balloon(st, c=None):
    return (f'<line x1="-5" y1="6" x2="-4" y2="14" stroke="{st["ink"]}" stroke-width="1"/>'
            f'<line x1="5" y1="6" x2="4" y2="14" stroke="{st["ink"]}" stroke-width="1"/>'
            f'<path d="M0,-26 C18,-26 20,-4 6,6 L-6,6 C-20,-4 -18,-26 0,-26 Z" {_s("#d64545", st)}/>'
            f'<path d="M0,-26 C6,-26 7,-4 2,6 L-2,6 C-7,-4 -6,-26 0,-26 Z" {_s("#f4efe6", st)}/>'
            f'<rect x="-5" y="14" width="10" height="8" {_s("#9c6b3c", st)}/>')


def windmill(st, c=None):
    blades = "".join(f'<rect x="-3" y="-80" width="6" height="30" transform="rotate({a} 0 -50)" '
                     f'{_s("#f6f1e6", st)}/>' for a in (20, 110, 200, 290))
    return (f'<polygon points="-10,0 -5,-48 5,-48 10,0" {_s("#e9dfcf", st)}/>'
            f'<rect x="-3" y="-10" width="6" height="10" {_s("#6b4a2f", st)}/>'
            f'<polygon points="-7,-48 0,-57 7,-48" {_s("#8a4b3a", st)}/>'
            + blades + f'<circle cx="0" cy="-50" r="2.5" fill="{st["ink"]}"/>')


def _taper(y, w_base, w_top, h):
    """Half-width of a tower at height y (negative), narrowing linearly."""
    return w_base + (w_top - w_base) * (-y) / h


def lighthouse(st, c=None):
    def band(y1, y2):
        a, b = _taper(y1, 8, 5, 50), _taper(y2, 8, 5, 50)
        return f'<polygon points="{-a:.1f},{y1} {a:.1f},{y1} {b:.1f},{y2} {-b:.1f},{y2}" {_s("#c8392b", st)}/>'
    return (f'<polygon points="-8,0 -5,-50 5,-50 8,0" {_s("#ffffff", st)}/>'
            + band(-12, -22) + band(-32, -42)
            + f'<rect x="-4" y="-62" width="8" height="8" {_s("#ffe27a", st)}/>'
            f'<rect x="-7" y="-54" width="14" height="4" {_s("#4a4a4a", st)}/>'
            f'<polygon points="-6,-62 0,-70 6,-62" {_s("#c8392b", st)}/>')


def scarecrow(st, c=None):
    return (f'<rect x="-1.5" y="-50" width="3" height="50" {_s(WOOD, st)}/>'
            f'<rect x="-20" y="-38" width="40" height="3" {_s(WOOD, st)}/>'
            f'<polygon points="-12,-38 12,-38 9,-18 -9,-18" {_s("#4d7cc0", st)}/>'
            f'<circle cx="0" cy="-45" r="7" {_s("#e8d29a", st)}/>'
            f'<rect x="-6" y="-60" width="12" height="8" {_s("#5a3e2b", st)}/>'
            f'<rect x="-11" y="-53" width="22" height="3" {_s("#5a3e2b", st)}/>'
            f'<path d="M-20,-36 l-4,4 M-20,-36 l-4,0 M20,-36 l4,4 M20,-36 l4,0" '
            f'stroke="#d8b25a" stroke-width="1.5"/>')


def crescent_moon(st, c=None):
    return f'<path d="M7,-14 A14,14 0 0,0 7,14 A20,20 0 0,1 7,-14 Z" {_s("#f3e9b5", st)}/>'


def sailboat_pond(st, c=None):
    return (f'<ellipse cx="0" cy="-9" rx="34" ry="9" {_s("#6fa8d6", st)}/>'
            f'<line x1="0" y1="-14" x2="0" y2="-38" stroke="{st["ink"]}" stroke-width="1.5"/>'
            f'<polygon points="1,-37 1,-15 14,-15" {_s("#ffffff", st)}/>'
            f'<polygon points="-1,-33 -1,-15 -10,-15" {_s("#f0e6d0", st)}/>'
            f'<path d="M-12,-14 L12,-14 L8,-8 L-8,-8 Z" {_s("#8b5a2b", st)}/>')


def three_crows(st, c=None):
    out = ""
    for dx, dy, k in ((-27, 4, 1.5), (0, -3, 1.7), (25, 6, 1.35)):
        out += (f'<path d="M{dx - 6 * k:.1f},{dy} Q{dx - 3 * k:.1f},{dy - 5 * k:.1f} {dx},{dy} '
                f'Q{dx + 3 * k:.1f},{dy - 5 * k:.1f} {dx + 6 * k:.1f},{dy}" fill="none" '
                f'stroke="#1c1c1c" stroke-width="2.8" stroke-linecap="round"/>')
    return out


def stone_well(st, c=None):
    thin = f'stroke="{st["ink"]}" stroke-width="0.8"'
    return (f'<rect x="-14" y="-42" width="3" height="24" {_s(DARK_WOOD, st)}/>'
            f'<rect x="11" y="-42" width="3" height="24" {_s(DARK_WOOD, st)}/>'
            f'<line x1="-12" y1="-36" x2="12" y2="-36" stroke="{DARK_WOOD}" stroke-width="2"/>'
            f'<line x1="0" y1="-36" x2="0" y2="-26" stroke="{st["ink"]}" stroke-width="1"/>'
            f'<rect x="-3" y="-26" width="6" height="5" {_s(WOOD, st)}/>'
            f'<polygon points="-19,-42 0,-54 19,-42" {_s("#8a4b3a", st)}/>'
            f'<rect x="-15" y="-18" width="30" height="18" {_s("#a8a29a", st)}/>'
            f'<line x1="-15" y1="-9" x2="15" y2="-9" {thin}/>'
            f'<line x1="-7" y1="-18" x2="-7" y2="-9" {thin}/><line x1="6" y1="-18" x2="6" y2="-9" {thin}/>'
            f'<line x1="-1" y1="-9" x2="-1" y2="0" {thin}/><line x1="10" y1="-9" x2="10" y2="0" {thin}/>'
            f'<ellipse cx="0" cy="-18" rx="15" ry="4" {_s("#5f5a54", st)}/>')


def kite(st, c=None):
    return ('<g transform="translate(0,-13)">'
            f'<path d="M0,18 Q6,26 0,32 Q-6,38 0,44" fill="none" stroke="{st["ink"]}" stroke-width="1.2"/>'
            f'<polygon points="-4,26 0,28 -4,30" {_s("#f2c200", st)}/>'
            f'<polygon points="4,38 0,40 4,42" {_s("#f2c200", st)}/>'
            f'<polygon points="0,-18 12,-2 0,18 -12,-2" {_s("#e05a3a", st)}/>'
            f'<path d="M0,-18 L0,18 M-12,-2 L12,-2" stroke="{st["ink"]}" stroke-width="0.8"/>'
            '</g>')


def sunflower(st, c=None):
    petals = "".join(f'<ellipse cx="0" cy="-86" rx="3.5" ry="8" transform="rotate({30 * k} 0 -76)" '
                     f'{_s("#f4c430", st)}/>' for k in range(12))
    return (f'<rect x="-1.5" y="-72" width="3" height="72" {_s("#4c8a3b", st)}/>'
            f'<ellipse cx="-8" cy="-30" rx="8" ry="3.5" transform="rotate(-25 -8 -30)" {_s("#5a9c45", st)}/>'
            f'<ellipse cx="8" cy="-46" rx="8" ry="3.5" transform="rotate(25 8 -46)" {_s("#5a9c45", st)}/>'
            + petals + f'<circle cx="0" cy="-76" r="7" {_s("#6b4423", st)}/>')


# ----- rare features that belong to no one --------------------------------

def shooting_star(st, c=None):
    pts = []
    for k in range(10):
        r = 8 if k % 2 == 0 else 3.5
        a = radians(-90 + 36 * k)
        pts.append(f"{8 + r * cos(a):.1f},{r * sin(a):.1f}")
    trail = "".join(f'<line x1="2" y1="{y0}" x2="-20" y2="{y1}" stroke="#f5d76e" stroke-width="2" '
                    f'stroke-linecap="round"/>' for y0, y1 in ((2, 10), (0, 5), (-2, 0)))
    return trail + f'<polygon points="{" ".join(pts)}" {_s("#fff2a8", st)}/>'


def butterfly(st, c=None):
    return ('<g transform="translate(0,-24)">'
            f'<ellipse cx="-6" cy="-3" rx="6" ry="5" {_s("#9b59b6", st)}/>'
            f'<ellipse cx="6" cy="-3" rx="6" ry="5" {_s("#9b59b6", st)}/>'
            f'<ellipse cx="-5" cy="4" rx="4" ry="3.5" {_s("#c39bd3", st)}/>'
            f'<ellipse cx="5" cy="4" rx="4" ry="3.5" {_s("#c39bd3", st)}/>'
            f'<line x1="0" y1="-7" x2="0" y2="7" stroke="{st["ink"]}" stroke-width="1.8"/>'
            f'<path d="M0,-7 l-3,-4 M0,-7 l3,-4" stroke="{st["ink"]}" stroke-width="0.8"/>'
            '</g>')


def mushrooms(st, c=None):
    out = ""
    for dx, k in ((-9, 1.0), (3, 1.3), (12, 0.8)):
        out += (f'<rect x="{dx - 2 * k:.1f}" y="{-9 * k:.1f}" width="{4 * k:.1f}" height="{9 * k:.1f}" '
                f'{_s("#f3ead8", st)}/>'
                f'<path d="M{dx - 7 * k:.1f},{-8 * k:.1f} Q{dx},{-19 * k:.1f} {dx + 7 * k:.1f},{-8 * k:.1f} Z" '
                f'{_s("#c62828", st)}/>'
                f'<circle cx="{dx - 2 * k:.1f}" cy="{-11 * k:.1f}" r="{1.2 * k:.1f}" fill="#ffffff"/>'
                f'<circle cx="{dx + 2.5 * k:.1f}" cy="{-12.5 * k:.1f}" r="{1 * k:.1f}" fill="#ffffff"/>')
    return out


def snail(st, c=None):
    return (f'<path d="M-13,0 L12,0 Q15,0 15,-4 L12,-6 L-11,-4 Z" {_s("#cfc2a5", st)}/>'
            f'<line x1="12" y1="-5" x2="14" y2="-13" stroke="{st["ink"]}" stroke-width="1"/>'
            f'<line x1="9" y1="-5" x2="9" y2="-12" stroke="{st["ink"]}" stroke-width="1"/>'
            f'<circle cx="-2" cy="-9" r="8.5" {_s("#c98a4b", st)}/>'
            f'<path d="M-2,-9 m-5,0 a5,5 0 1,1 5,5 a3,3 0 1,1 -3,-3" fill="none" '
            f'stroke="{st["ink"]}" stroke-width="1"/>')


def frog(st, c=None):
    return (f'<ellipse cx="-9" cy="-2" rx="5" ry="2.5" {_s("#3f8f3a", st)}/>'
            f'<ellipse cx="9" cy="-2" rx="5" ry="2.5" {_s("#3f8f3a", st)}/>'
            f'<ellipse cx="0" cy="-7" rx="11" ry="7" {_s("#5aae4a", st)}/>'
            f'<circle cx="-5" cy="-14" r="3.5" {_s("#5aae4a", st)}/>'
            f'<circle cx="5" cy="-14" r="3.5" {_s("#5aae4a", st)}/>'
            f'<circle cx="-5" cy="-14.5" r="1.4" fill="{st["ink"]}"/>'
            f'<circle cx="5" cy="-14.5" r="1.4" fill="{st["ink"]}"/>'
            f'<path d="M-4,-6 Q0,-3 4,-6" fill="none" stroke="{st["ink"]}" stroke-width="0.9"/>')


def fox(st, c=None):
    return (f'<path d="M-14,-12 Q-30,-14 -26,-2 Q-22,4 -14,-6 Z" {_s("#e07b2a", st)}/>'
            f'<path d="M-27,-4 Q-25,2 -21,-1 Z" fill="#ffffff"/>'
            f'<rect x="-10" y="-8" width="3.5" height="8" {_s("#5a3e2b", st)}/>'
            f'<rect x="8" y="-8" width="3.5" height="8" {_s("#5a3e2b", st)}/>'
            f'<ellipse cx="0" cy="-12" rx="16" ry="7" {_s("#e07b2a", st)}/>'
            f'<polygon points="12,-14 24,-18 14,-24" {_s("#e07b2a", st)}/>'
            f'<polygon points="13,-23 14,-30 18,-21" {_s("#c4621c", st)}/>'
            f'<circle cx="17" cy="-19" r="1" fill="{st["ink"]}"/>')


def hedgehog(st, c=None):
    spikes = " ".join(f"{-14 + 3.5 * k:.1f},{-6 - 9 * (1 - ((k - 4) / 4.5) ** 2) - (2 if k % 2 else 0):.1f}"
                      for k in range(9))
    return (f'<polygon points="-15,0 {spikes} 14,-4 14,0" {_s("#7a5a3a", st)}/>'
            f'<path d="M12,-7 Q20,-5 19,-1 L12,0 Z" {_s("#d9b48a", st)}/>'
            f'<circle cx="19" cy="-2" r="1.3" fill="{st["ink"]}"/>'
            f'<circle cx="15" cy="-5" r="0.9" fill="{st["ink"]}"/>')


def owl(st, c=None):
    return (f'<rect x="-9" y="-14" width="18" height="14" {_s(DARK_WOOD, st)}/>'
            f'<ellipse cx="0" cy="-14" rx="9" ry="2.5" {_s("#b48a52", st)}/>'
            f'<ellipse cx="0" cy="-27" rx="9" ry="12" {_s("#8d6e52", st)}/>'
            f'<polygon points="-8,-36 -6,-42 -3,-37" {_s("#8d6e52", st)}/>'
            f'<polygon points="8,-36 6,-42 3,-37" {_s("#8d6e52", st)}/>'
            f'<circle cx="-3.5" cy="-31" r="3.5" {_s("#fff3c4", st)}/>'
            f'<circle cx="3.5" cy="-31" r="3.5" {_s("#fff3c4", st)}/>'
            f'<circle cx="-3.5" cy="-31" r="1.4" fill="{st["ink"]}"/>'
            f'<circle cx="3.5" cy="-31" r="1.4" fill="{st["ink"]}"/>'
            f'<polygon points="-1.5,-27 1.5,-27 0,-24" fill="#e0a526"/>')


def paper_plane(st, c=None):
    return (f'<polygon points="-17,-2 17,-7 -9,7" {_s("#ffffff", st)}/>'
            f'<polygon points="-9,7 17,-7 -4,1" {_s("#d9dde3", st)}/>'
            f'<path d="M-20,8 Q-30,12 -38,8" fill="none" stroke="#ffffff" stroke-width="1.4" '
            f'stroke-dasharray="3 3"/>')


def dragonfly(st, c=None):
    return (f'<ellipse cx="-6" cy="-5" rx="8" ry="3" transform="rotate(-20 -6 -5)" {_s("#d6eef5", st)}/>'
            f'<ellipse cx="6" cy="-5" rx="8" ry="3" transform="rotate(20 6 -5)" {_s("#d6eef5", st)}/>'
            f'<ellipse cx="-6" cy="1" rx="7" ry="2.5" transform="rotate(15 -6 1)" {_s("#d6eef5", st)}/>'
            f'<ellipse cx="6" cy="1" rx="7" ry="2.5" transform="rotate(-15 6 1)" {_s("#d6eef5", st)}/>'
            + _bar(0, -6, 0, 13, "#1e88a8", 2.4, st)
            + f'<circle cx="0" cy="-8" r="2.6" {_s("#1e88a8", st)}/>')


def puddle(st, c=None):
    return (f'<ellipse cx="0" cy="-4" rx="25" ry="5" {_s("#8fc3e3", st)}/>'
            f'<ellipse cx="-6" cy="-5" rx="9" ry="1.6" fill="#ffffff" opacity="0.7"/>')


# ----- genre conventions: what one genre's painters do ---------------------

def rowboat(st, c=None):
    return (_bar(-6, -9, -26, 3, "#c9a46b", 2, st) + _bar(6, -9, 26, 3, "#c9a46b", 2, st)
            + f'<path d="M-24,-11 L24,-11 Q20,-1 12,0 L-12,0 Q-20,-1 -24,-11 Z" {_s("#a0522d", st)}/>'
            f'<rect x="-24" y="-13" width="48" height="3" {_s("#f0e6d0", st)}/>')


def buoy(st, c=None):
    return (f'<rect x="-1.5" y="-26" width="3" height="10" {_s("#555555", st)}/>'
            f'<circle cx="0" cy="-27" r="3" {_s("#ffe27a", st)}/>'
            f'<polygon points="-8,0 8,0 5,-16 -5,-16" {_s("#d84a3a", st)}/>'
            f'<rect x="-6.3" y="-11" width="12.6" height="4" fill="#ffffff"/>')


def pier(st, c=None):
    posts = "".join(f'<rect x="{x - 2}" y="-14" width="4" height="14" {_s(DARK_WOOD, st)}/>'
                    for x in (-44, -22, 0, 22, 44))
    lines = "".join(f'<line x1="{x}" y1="-21" x2="{x}" y2="-14" stroke="{st["ink"]}" stroke-width="0.7"/>'
                    for x in range(-40, 50, 10))
    return posts + f'<rect x="-50" y="-21" width="100" height="7" {_s("#b48a52", st)}/>' + lines


def buildings(st, c=None):
    out = ""
    for x0, w, h, col in ((-65, 40, 58, "#d9b38c"), (-25, 46, 72, "#b7c4cf"), (21, 44, 50, "#e3c5c5")):
        out += f'<rect x="{x0}" y="{-h}" width="{w}" height="{h}" {_s(col, st)}/>'
        for wy in range(-h + 8, -16, 14):
            for wx in (x0 + 7, x0 + w - 15):
                out += f'<rect x="{wx}" y="{wy}" width="8" height="8" {_s("#f7f1d0", st)}/>'
        out += f'<rect x="{x0 + w / 2 - 5:.1f}" y="-12" width="10" height="12" {_s("#6b4a2f", st)}/>'
    return out


def shopfront(st, c=None):
    stripes = "".join(f'<rect x="{-26 + 52 / 6 * k:.2f}" y="-38" width="{52 / 6:.2f}" height="10" '
                      f'fill="{"#d64545" if k % 2 == 0 else "#ffffff"}"/>' for k in range(6))
    return (f'<rect x="-24" y="-52" width="48" height="52" {_s("#efe0c0", st)}/>'
            f'<rect x="-20" y="-50" width="40" height="9" {_s("#4a6b8a", st)}/>'
            + stripes + f'<rect x="-26" y="-38" width="52" height="10" fill="none" '
            f'stroke="{st["ink"]}" stroke-width="{st["sw"]:.2f}"/>'
            f'<rect x="-19" y="-24" width="20" height="16" {_s("#bfe0f0", st)}/>'
            f'<rect x="6" y="-24" width="12" height="24" {_s("#6b4a2f", st)}/>')


def bicycle(st, c=None):
    def wheel(x):
        return (f'<circle cx="{x}" cy="-10" r="10" fill="none" stroke="{st["ink"]}" stroke-width="2.6"/>'
                f'<circle cx="{x}" cy="-10" r="1.6" fill="{st["ink"]}"/>')
    return (wheel(-14) + wheel(14)
            + _stroke("M-14,-10 L-4,-26 L10,-26 L14,-10 M-4,-26 L1,-10 L-14,-10 M1,-10 L10,-26",
                      "#2e7d9a", 2, st)
            + _bar(-6, -30, -1, -30, "#3b2f2a", 2.5, st)
            + _bar(10, -26, 8, -32, "#555555", 1.6, st) + _bar(5, -32, 11, -32, "#555555", 1.6, st))


# ----- props: the objects one-off features are made from -------------------

def ladder(st, c):
    out = _bar(-9, 0, -3, -52, c, 3, st) + _bar(5, 0, 11, -52, c, 3, st)
    for t in (0.14, 0.32, 0.5, 0.68, 0.86):
        out += _bar(-9 + 6 * t, -52 * t, 5 + 6 * t, -52 * t, c, 2.4, st)
    return out


def umbrella(st, c):
    return (f'<line x1="0" y1="-2" x2="0" y2="-60" stroke="#5b4a3a" stroke-width="2"/>'
            f'<path d="M0,-2 Q0,3 -5,1" fill="none" stroke="#5b4a3a" stroke-width="2"/>'
            f'<path d="M-24,-38 Q-24,-60 0,-60 Q24,-60 24,-38 Q18,-42 12,-38 Q6,-42 0,-38 '
            f'Q-6,-42 -12,-38 Q-18,-42 -24,-38 Z" {_s(c, st)}/>')


def chair(st, c):
    return (_bar(-9, 0, -9, -40, c, 3.5, st) + _bar(9, 0, 9, -40, c, 3.5, st)
            + f'<rect x="-12" y="-44" width="24" height="9" {_s(c, st)}/>'
            f'<rect x="-12" y="-31" width="24" height="5" {_s(c, st)}/>'
            f'<rect x="-13" y="-21" width="26" height="6" {_s(c, st)}/>')


def bucket(st, c):
    return (f'<path d="M-10,-20 Q0,-34 10,-20" fill="none" stroke="{st["ink"]}" stroke-width="1.4"/>'
            f'<polygon points="-10,-20 10,-20 7,0 -7,0" {_s(c, st)}/>'
            f'<ellipse cx="0" cy="-20" rx="10" ry="2.5" {_s(shade(c, 0.7), st)}/>')


def flag(st, c):
    return (f'<line x1="0" y1="0" x2="0" y2="-56" stroke="#6d6d6d" stroke-width="2.5"/>'
            f'<path d="M1.5,-56 Q12,-60 25,-54 L25,-40 Q12,-46 1.5,-42 Z" {_s(c, st)}/>'
            f'<circle cx="0" cy="-57" r="2" {_s("#d4af37", st)}/>')


def wheel(st, c):
    spokes = "".join(_bar(0, -18, 15 * cos(radians(30 * k)), -18 + 15 * sin(radians(30 * k)), c, 2, st)
                     for k in range(0, 12, 2))
    return (spokes
            + f'<circle cx="0" cy="-18" r="17" fill="none" stroke="{st["ink"]}" '
            f'stroke-width="{4.5 + 2 * st["sw"]:.2f}"/>'
            f'<circle cx="0" cy="-18" r="17" fill="none" stroke="{c}" stroke-width="4.5"/>'
            f'<circle cx="0" cy="-18" r="3.5" {_s(shade(c, 0.7), st)}/>')


def barrel(st, c):
    hoop = f'fill="none" stroke="{st["ink"]}" stroke-width="1.6"'
    return (f'<path d="M-11,-30 Q-15,-15 -11,0 L11,0 Q15,-15 11,-30 Z" {_s(c, st)}/>'
            f'<path d="M-12.5,-23 Q0,-20 12.5,-23" {hoop}/>'
            f'<path d="M-12.5,-7 Q0,-4 12.5,-7" {hoop}/>'
            f'<ellipse cx="0" cy="-30" rx="11" ry="3" {_s(shade(c, 0.75), st)}/>')


def lamp_post(st, c):
    return (f'<rect x="-5" y="-6" width="10" height="6" {_s(c, st)}/>'
            + _bar(0, -6, 0, -56, c, 3, st)
            + f'<polygon points="-6,-58 6,-58 4,-70 -4,-70" {_s("#fff1a8", st)}/>'
            f'<rect x="-6" y="-59" width="12" height="2" {_s(c, st)}/>'
            f'<polygon points="-7,-70 0,-77 7,-70" {_s(c, st)}/>')


def mailbox(st, c):
    return (f'<rect x="-2" y="-22" width="4" height="22" {_s(WOOD, st)}/>'
            f'<path d="M-11,-22 L-11,-32 A11,7 0 0,1 11,-32 L11,-22 Z" {_s(c, st)}/>'
            f'<rect x="11" y="-34" width="2" height="9" fill="{st["ink"]}"/>'
            f'<rect x="11" y="-34" width="6" height="3.5" fill="{st["ink"]}"/>')


def bench(st, c):
    d = shade(c, 0.7)
    return (f'<rect x="-17" y="-26" width="3" height="26" {_s(d, st)}/>'
            f'<rect x="14" y="-26" width="3" height="26" {_s(d, st)}/>'
            f'<rect x="-21" y="-26" width="42" height="3.5" {_s(c, st)}/>'
            f'<rect x="-21" y="-20" width="42" height="3.5" {_s(c, st)}/>'
            f'<rect x="-21" y="-14" width="42" height="4" {_s(c, st)}/>')


def signpost(st, c):
    return (f'<rect x="-2" y="-50" width="4" height="50" {_s(WOOD, st)}/>'
            f'<polygon points="-1,-47 18,-47 24,-42 18,-37 -1,-37" {_s(c, st)}/>'
            f'<polygon points="1,-33 -18,-33 -24,-28 -18,-23 1,-23" {_s(c, st)}/>')


def tent(st, c):
    return (f'<line x1="0" y1="-36" x2="0" y2="-42" stroke="{st["ink"]}" stroke-width="1.5"/>'
            f'<polygon points="-24,0 0,-36 24,0" {_s(c, st)}/>'
            f'<polygon points="-7,0 0,-20 7,0" {_s(shade(c, 0.55), st)}/>')


def wheelbarrow(st, c):
    return (_bar(-14, -16, -30, -8, WOOD, 2.5, st)
            + f'<line x1="-12" y1="-12" x2="-14" y2="0" stroke="#555555" stroke-width="2"/>'
            f'<polygon points="-20,-20 12,-20 6,-7 -14,-7" {_s(c, st)}/>'
            f'<circle cx="8" cy="-6" r="6" {_s("#555555", st)}/>'
            f'<circle cx="8" cy="-6" r="1.5" fill="#cccccc"/>')


def bell(st, c):
    return (f'<rect x="-14" y="-44" width="3" height="44" {_s(DARK_WOOD, st)}/>'
            f'<rect x="11" y="-44" width="3" height="44" {_s(DARK_WOOD, st)}/>'
            f'<rect x="-17" y="-47" width="34" height="4" {_s(DARK_WOOD, st)}/>'
            f'<line x1="0" y1="-43" x2="0" y2="-40" stroke="{st["ink"]}" stroke-width="1.5"/>'
            f'<path d="M-8,-22 Q-8,-40 0,-40 Q8,-40 8,-22 L11,-19 L-11,-19 Z" {_s(c, st)}/>'
            f'<circle cx="0" cy="-17" r="2.5" fill="{st["ink"]}"/>')


def anchor(st, c):
    return (_bar(0, -38, 0, -4, c, 3.5, st) + _bar(-10, -32, 10, -32, c, 3.5, st)
            + _stroke("M-17,-15 Q-15,0 0,-3 Q15,0 17,-15", c, 3.5, st)
            + f'<circle cx="0" cy="-43" r="4.5" fill="none" stroke="{st["ink"]}" '
            f'stroke-width="{3 + 2 * st["sw"]:.2f}"/>'
            f'<circle cx="0" cy="-43" r="4.5" fill="none" stroke="{c}" stroke-width="3"/>'
            f'<polygon points="-17,-15 -21,-10 -13,-11" {_s(c, st)}/>'
            f'<polygon points="17,-15 21,-10 13,-11" {_s(c, st)}/>')


def teapot(st, c):
    d = shade(c, 0.75)
    return (_stroke("M-12,-18 Q-24,-14 -12,-6", c, 3, st)
            + f'<polygon points="10,-12 22,-24 25,-22 12,-5" {_s(c, st)}/>'
            f'<ellipse cx="0" cy="-12" rx="14" ry="12" {_s(c, st)}/>'
            f'<ellipse cx="0" cy="-23" rx="7" ry="2.5" {_s(d, st)}/>'
            f'<circle cx="0" cy="-27" r="2.2" {_s(d, st)}/>')


def crate(st, c):
    thin = f'stroke="{st["ink"]}" stroke-width="0.9"'
    return (f'<rect x="-14" y="-28" width="28" height="28" {_s(c, st)}/>'
            f'<rect x="-11" y="-25" width="22" height="22" fill="none" {thin}/>'
            f'<line x1="-11" y1="-3" x2="11" y2="-25" {thin}/>')


def birdhouse(st, c):
    return (f'<rect x="-2" y="-36" width="4" height="36" {_s(WOOD, st)}/>'
            f'<rect x="-11" y="-52" width="22" height="17" {_s(c, st)}/>'
            f'<polygon points="-14,-51 0,-62 14,-51" {_s(shade(c, 0.65), st)}/>'
            f'<circle cx="0" cy="-45" r="3.5" fill="{st["ink"]}"/>')


def swing(st, c):
    rope = f'stroke="{st["ink"]}" stroke-width="1"'
    return (_bar(-22, 0, -15, -48, c, 3, st) + _bar(22, 0, 15, -48, c, 3, st)
            + _bar(-17, -48, 17, -48, c, 3, st)
            + f'<line x1="-6" y1="-48" x2="-6" y2="-15" {rope}/>'
            f'<line x1="6" y1="-48" x2="6" y2="-15" {rope}/>'
            f'<rect x="-9" y="-16" width="18" height="3.5" {_s(shade(c, 0.7), st)}/>')


def watering_can(st, c):
    return (_stroke("M-10,-18 Q-2,-34 8,-18", c, 3, st)
            + f'<polygon points="8,-9 24,-23 26,-20 9,-3" {_s(c, st)}/>'
            f'<ellipse cx="25" cy="-22" rx="3" ry="2" {_s(shade(c, 0.7), st)}/>'
            f'<rect x="-12" y="-20" width="21" height="20" rx="2.5" {_s(c, st)}/>')


# Props kept back from the world, so a learner's inventions are new ideas.

def traffic_cone(st, c):
    def band(y1, y2):
        a, b = _taper(y1 + 3, 10, 3, 31), _taper(y2 + 3, 10, 3, 31)
        return f'<polygon points="{-a:.1f},{y1} {a:.1f},{y1} {b:.1f},{y2} {-b:.1f},{y2}" fill="#ffffff"/>'
    return (f'<polygon points="-10,-3 -3,-34 3,-34 10,-3" {_s(c, st)}/>'
            + band(-14, -19) + band(-24, -28)
            + f'<rect x="-13" y="-3" width="26" height="3" {_s(c, st)}/>')


def easel(st, c):
    return (_bar(0, 0, 0, -44, "#6d5330", 2, st)
            + _bar(-12, 0, -3, -50, WOOD, 2.5, st) + _bar(12, 0, 3, -50, WOOD, 2.5, st)
            + f'<rect x="-14" y="-44" width="28" height="20" {_s(c, st)}/>'
            f'<path d="M-10,-30 Q-3,-40 4,-32 T12,-36" fill="none" stroke="#ffffff" stroke-width="1.5"/>'
            + _bar(-16, -23, 16, -23, WOOD, 2.5, st))


def lantern(st, c):
    return (f'<path d="M-5,-30 Q0,-38 5,-30" fill="none" stroke="{st["ink"]}" stroke-width="1.4"/>'
            f'<rect x="-7" y="-26" width="14" height="20" {_s("#fff1a8", st)}/>'
            f'<rect x="-8" y="-26" width="2.5" height="20" {_s(c, st)}/>'
            f'<rect x="5.5" y="-26" width="2.5" height="20" {_s(c, st)}/>'
            f'<polygon points="-9,-26 9,-26 5,-31 -5,-31" {_s(c, st)}/>'
            f'<rect x="-9" y="-6" width="18" height="6" {_s(c, st)}/>')


def drum(st, c):
    return (_bar(-4, -26, -14, -34, WOOD, 1.8, st) + _bar(4, -26, 14, -34, WOOD, 1.8, st)
            + f'<rect x="-14" y="-20" width="28" height="20" {_s(c, st)}/>'
            f'<polyline points="-14,-17 -9,-4 -4,-17 1,-4 6,-17 11,-4 14,-12" fill="none" '
            f'stroke="#f0e6d0" stroke-width="1.4"/>'
            f'<ellipse cx="0" cy="-20" rx="14" ry="4" {_s("#f0e6d0", st)}/>')


def hourglass(st, c):
    return (_bar(-9, -32, -9, -2, c, 2, st) + _bar(9, -32, 9, -2, c, 2, st)
            + f'<path d="M-7,-30 L7,-30 L1.5,-17 L7,-4 L-7,-4 L-1.5,-17 Z" {_s("#e8f1f5", st)}/>'
            f'<polygon points="-5,-26 5,-26 1,-19 -1,-19" fill="#e3b04b"/>'
            f'<polygon points="-6,-4 6,-4 0,-10" fill="#e3b04b"/>'
            f'<rect x="-11" y="-34" width="22" height="4" {_s(c, st)}/>'
            f'<rect x="-11" y="-4" width="22" height="4" {_s(c, st)}/>')


def trophy(st, c):
    return (_stroke("M-11,-30 Q-21,-29 -10,-19", c, 2.5, st)
            + _stroke("M11,-30 Q21,-29 10,-19", c, 2.5, st)
            + f'<rect x="-10" y="-6" width="20" height="6" {_s(shade(c, 0.7), st)}/>'
            f'<rect x="-2.5" y="-14" width="5" height="8" {_s(c, st)}/>'
            f'<path d="M-12,-34 L12,-34 Q12,-14 0,-14 Q-12,-14 -12,-34 Z" {_s(c, st)}/>')


def birdcage(st, c):
    bars = "".join(_bar(x, -4, x, -24, c, 1.8, st) for x in (-11, -5.5, 0, 5.5, 11))
    return (bars + _stroke("M-12,-24 Q-12,-38 0,-38 Q12,-38 12,-24", c, 2.2, st)
            + _bar(-12, -24, 12, -24, c, 2, st)
            + f'<path d="M0,-38 L0,-42 Q3,-45 0,-47" fill="none" stroke="{st["ink"]}" stroke-width="1.2"/>'
            f'<rect x="-13" y="-4" width="26" height="4" {_s(c, st)}/>')


def rocket(st, c):
    fin = shade(c, 0.65)
    return (f'<polygon points="-4,-8 0,0 4,-8" fill="#f39c12"/>'
            f'<polygon points="-7,-18 -14,-6 -7,-10" {_s(fin, st)}/>'
            f'<polygon points="7,-18 14,-6 7,-10" {_s(fin, st)}/>'
            f'<path d="M0,-56 Q10,-44 8,-8 L-8,-8 Q-10,-44 0,-56 Z" {_s(c, st)}/>'
            f'<circle cx="0" cy="-36" r="4.5" {_s("#dff3ff", st)}/>')


# ----- the catalogue -------------------------------------------------------
# w and h are the part's width and height at scale 1, used to keep parts
# from overlapping. region says where on the canvas the part goes. size
# multiplies the part's drawn size wherever it is placed.

def _p(fn, w, h, region, size=1.0):
    return {"draw": fn, "w": w, "h": h, "region": region, "size": size}


# Size factors set from the pixel measurements in salience.py (3 November 2026),
# so every signature object and rare feature covers roughly 0.5 to 3 percent
# of the canvas. Without them the smallest covered under 0.3 percent.
SIZES = {"crescent_moon": 2.0, "paper_plane": 1.6, "three_crows": 1.5, "snail": 1.2,
         "mushrooms": 1.15, "buoy": 1.3, "stone_well": 0.8}
FENCE_WIDTH = 110
RAINBOW_RADIUS = 54


PARTS = {
    "sun": _p(sun, 56, 56, "sky"),
    "cloud": _p(cloud, 58, 32, "sky"),
    "tree": _p(tree, 44, 62, "ground"),
    "house": _p(house, 50, 46, "far"),
    "yellow_bird": _p(yellow_bird, 36, 20, "corner"),
    "hot_air_balloon": _p(hot_air_balloon, 42, 50, "sky"),
    "windmill": _p(windmill, 64, 82, "far"),
    "lighthouse": _p(lighthouse, 22, 72, "far"),
    "scarecrow": _p(scarecrow, 50, 62, "ground"),
    "crescent_moon": _p(crescent_moon, 18, 30, "sky"),
    "sailboat_pond": _p(sailboat_pond, 70, 40, "ground"),
    "three_crows": _p(three_crows, 76, 24, "sky"),
    "stone_well": _p(stone_well, 40, 56, "ground"),
    "kite": _p(kite, 26, 64, "sky"),
    "sunflower": _p(sunflower, 36, 96, "front"),
    "shooting_star": _p(shooting_star, 44, 24, "sky"),
    "butterfly": _p(butterfly, 26, 34, "ground"),
    "mushrooms": _p(mushrooms, 36, 26, "ground"),
    "snail": _p(snail, 30, 20, "ground"),
    "frog": _p(frog, 30, 20, "ground"),
    "fox": _p(fox, 54, 32, "ground"),
    "hedgehog": _p(hedgehog, 36, 18, "ground"),
    "owl": _p(owl, 22, 44, "ground"),
    "paper_plane": _p(paper_plane, 56, 20, "sky"),
    "dragonfly": _p(dragonfly, 32, 26, "sky"),
    "puddle": _p(puddle, 52, 12, "ground"),
    "rowboat": _p(rowboat, 56, 18, "water"),
    "buoy": _p(buoy, 18, 32, "water"),
    "pier": _p(pier, 100, 22, "pier"),
    "buildings": _p(buildings, 130, 72, "far"),
    "shopfront": _p(shopfront, 54, 52, "far"),
    "bicycle": _p(bicycle, 50, 34, "ground"),
    "ladder": _p(ladder, 26, 54, "ground"),
    "umbrella": _p(umbrella, 50, 62, "ground"),
    "chair": _p(chair, 26, 44, "ground"),
    "bucket": _p(bucket, 24, 32, "ground"),
    "flag": _p(flag, 30, 60, "ground"),
    "wheel": _p(wheel, 42, 38, "ground"),
    "barrel": _p(barrel, 30, 34, "ground"),
    "lamp_post": _p(lamp_post, 16, 78, "ground"),
    "mailbox": _p(mailbox, 32, 42, "ground"),
    "bench": _p(bench, 46, 28, "ground"),
    "signpost": _p(signpost, 50, 52, "ground"),
    "tent": _p(tent, 50, 42, "ground"),
    "wheelbarrow": _p(wheelbarrow, 58, 24, "ground"),
    "bell": _p(bell, 36, 50, "ground"),
    "anchor": _p(anchor, 44, 50, "ground"),
    "teapot": _p(teapot, 50, 30, "ground"),
    "crate": _p(crate, 30, 30, "ground"),
    "birdhouse": _p(birdhouse, 30, 64, "ground"),
    "swing": _p(swing, 48, 52, "ground"),
    "watering_can": _p(watering_can, 40, 34, "ground"),
    "traffic_cone": _p(traffic_cone, 28, 36, "ground"),
    "easel": _p(easel, 34, 52, "ground"),
    "lantern": _p(lantern, 20, 40, "ground"),
    "drum": _p(drum, 34, 36, "ground"),
    "hourglass": _p(hourglass, 26, 36, "ground"),
    "trophy": _p(trophy, 44, 36, "ground"),
    "birdcage": _p(birdcage, 30, 50, "ground"),
    "rocket": _p(rocket, 30, 58, "ground"),
}

for _name, _k in SIZES.items():
    PARTS[_name]["size"] = _k

# Twenty props make the world's one-off features; eight are kept back for
# learners to invent with.
WORLD_PROPS = ["ladder", "umbrella", "chair", "bucket", "flag", "wheel", "barrel", "lamp_post",
               "mailbox", "bench", "signpost", "tent", "wheelbarrow", "bell", "anchor", "teapot",
               "crate", "birdhouse", "swing", "watering_can"]
RESERVED_PROPS = ["traffic_cone", "easel", "lantern", "drum", "hourglass", "trophy", "birdcage",
                  "rocket"]

# Twelve prop colours, one per painter in the rotation world.py uses.
COLOURS = {
    "crimson": "#c62828", "orange": "#ef6c00", "gold": "#f9a825", "lime": "#9ccc65",
    "green": "#2e7d32", "teal": "#00897b", "azure": "#29b6f6", "cobalt": "#283593",
    "violet": "#7b1fa2", "pink": "#ec407a", "brown": "#6d4c41", "charcoal": "#455a64",
}
