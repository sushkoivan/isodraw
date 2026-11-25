"""Drawing constants (paper sizes, ISO 128 line types, lettering metrics) and small formatting helpers.

All lengths are paper millimetres unless stated otherwise.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple, Union

FONT = "Arial, Helvetica, sans-serif"
#: Arial cap height per em. ``font-size = h / CAP`` gives an ISO 3098 lettering (cap) height ``h``.
CAP = 0.716
#: ISO 3098 lettering heights used by the library [mm].
ISO_HEIGHTS = (2.5, 3.5, 5.0, 7.0)

#: ISO 216 A-series sheets in landscape orientation (width, height) [mm].
PAPER: Dict[str, Tuple[float, float]] = {
    "A4": (297.0, 210.0),
    "A3": (420.0, 297.0),
    "A2": (594.0, 420.0),
    "A1": (841.0, 594.0),
    "A0": (1189.0, 841.0),
}
#: ISO 5457 reference-zone grid (columns, rows) per sheet size.
ZONES: Dict[str, Tuple[int, int]] = {"A4": (6, 4), "A3": (8, 6), "A2": (12, 8), "A1": (16, 12), "A0": (24, 16)}
#: Zone row letters (I and O are skipped, as is customary).
ZONE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"
#: ISO 5457 frame margins (wide filing margin on the left).
MARGIN = dict(left=20.0, top=10.0, right=10.0, bottom=10.0)

TIER = 8.0                        # paper mm between stacked dimension tiers
ARROW_L, ARROW_W = 3.0, 0.55      # arrowhead length / half-width (closed, filled)
EXT_GAP, EXT_OVER = 1.0, 2.0      # extension-line gap from the object / overshoot past the dimension line
TAG_H = 2.5                       # lettering height of inline provenance tags

#: ISO 128-20 line types: stroke width [mm] and dash pattern (scaled for 0.25 mm narrow lines).
LINE_TYPES: Dict[str, Dict[str, Optional[Union[float, str]]]] = {
    "visible": dict(w=0.5, dash=None),
    "thin": dict(w=0.25, dash=None),
    "hidden": dict(w=0.25, dash="3 1"),
    "centre": dict(w=0.25, dash="8 1 1.5 1"),
    "phantom": dict(w=0.25, dash="8 1 1.5 1 1.5 1"),
    "frame": dict(w=0.7, dash=None),
    "hatch": dict(w=0.18, dash=None),
}

# character widths in em (Arial, approximate) for layout estimates
_CHAR_W = {**{c: 0.556 for c in "0123456789"}, " ": 0.278, ".": 0.278, ",": 0.278, ":": 0.278, ";": 0.278,
           "-": 0.333, "(": 0.333, ")": 0.333, "[": 0.278, "]": 0.278, "/": 0.278, "|": 0.26, "i": 0.222,
           "l": 0.222, "j": 0.222, "f": 0.278, "t": 0.278, "r": 0.333, "I": 0.278, "J": 0.5, "m": 0.833,
           "w": 0.722, "M": 0.833, "W": 0.944, "Ø": 0.778, "°": 0.4, "×": 0.584, "—": 1.0, "–": 0.556}


def text_width(s: str, h: float) -> float:
    """Estimated rendered width [mm] of string ``s`` at lettering (cap) height ``h`` [mm]."""
    fs = h / CAP
    w = 0.0
    for c in s:
        if c in _CHAR_W:
            w += _CHAR_W[c]
        elif c.isupper():
            w += 0.667
        else:
            w += 0.52
    return w * fs


def parse_scale(scale: Union[str, float, int]) -> Tuple[float, str]:
    """Parse an ISO 5455 scale. ``'1:2'`` -> ``(0.5, '1:2')``, ``2`` -> ``(2.0, '2:1')``."""
    if isinstance(scale, (int, float)):
        if scale <= 0:
            raise ValueError("scale must be positive")
        return float(scale), (f"1:{1 / scale:g}" if scale < 1 else f"{scale:g}:1")
    try:
        a, b = scale.split(":")
        s = float(a) / float(b)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"invalid scale {scale!r}, expected e.g. '1:2'") from exc
    if s <= 0:
        raise ValueError("scale must be positive")
    return s, scale


def fmt_value(v: float, dec: int = 1) -> str:
    """Format a dimension value with at most ``dec`` decimals and no trailing zeros (``12.50`` -> ``'12.5'``)."""
    s = f"{v:.{dec}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def _f(x: float) -> str:
    """Compact SVG number (3 decimals, trailing zeros stripped)."""
    s = f"{x:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _stroke(lt: str, color: str = "#000000", fill: str = "none") -> str:
    """SVG stroke attributes for line type ``lt``."""
    if lt not in LINE_TYPES:
        raise ValueError(f"unknown line type {lt!r}; choose one of {sorted(LINE_TYPES)}")
    d = LINE_TYPES[lt]
    s = f'stroke="{color}" stroke-width="{d["w"]}" fill="{fill}" stroke-linecap="round" stroke-linejoin="round"'
    if d["dash"]:
        s += f' stroke-dasharray="{d["dash"]}"'
    return s
