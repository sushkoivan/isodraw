"""Small model-space geometry helpers (all angles in degrees, counter-clockwise, model y up)."""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

Point = Tuple[float, float]


def arc_points(cx: float, cy: float, r: float, a0: float, a1: float, n: Optional[int] = None) -> List[Point]:
    """Polyline approximation of an arc from ``a0`` to ``a1`` (end points included).

    ``a1 < a0`` runs clockwise. ``n`` = number of segments (default: one per 2 degrees, at least 4).
    """
    if n is None:
        n = max(4, int(abs(a1 - a0) / 2) + 1)
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def polygon_area_centroid(pts: Sequence[Point]) -> Tuple[float, float, float]:
    """Signed area and centroid ``(A, x_c, y_c)`` of a closed polygon (shoelace formula)."""
    pts = list(pts)
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        c = x1 * y2 - x2 * y1
        a += c
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    a *= 0.5
    if abs(a) < 1e-15:
        return 0.0, 0.0, 0.0
    return a, cx / (6 * a), cy / (6 * a)


def revolved_volume(pts: Sequence[Point]) -> float:
    """Volume of a polygon (x = axial, y = radius >= 0) revolved about the x axis (Pappus: V = 2 pi |A| y_c)."""
    a, _, yc = polygon_area_centroid(pts)
    return 2 * math.pi * abs(a) * yc
