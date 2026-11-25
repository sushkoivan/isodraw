"""isodraw -- ISO-style engineering drawings as SVG, straight from Python. Standard library only.

Quick start::

    from isodraw import Sheet

    sh = Sheet("A3", title="SPACER", number="DWG-0001", scale="1:1", material="EN AW-6082-T6")
    v = sh.view(120, 150, "1:1", label="FRONT VIEW")
    v.rect(0, 0, 80, 20, hatch=(45, 2.0))
    v.dim_linear((0, 20), (80, 20), "calc:spacer_length", offset=10)
    v.dim_linear((80, 0), (80, 20), "assume: stock bar", offset=10, orient="v")
    sh.save("spacer.svg")

Every dimension carries a provenance tag and is coloured by it -- see :mod:`isodraw.provenance`.
"""

from ._demo import build_demo
from .geometry import arc_points, polygon_area_centroid, revolved_volume
from .provenance import CLASSES, DEFAULT_COLORS, DEFAULT_DESCRIPTIONS, DEFAULT_RULES, ProvenanceRules, classify
from .sheet import DRAWN_BY, Sheet
from .styles import ISO_HEIGHTS, LINE_TYPES, PAPER, fmt_value, parse_scale, text_width
from .view import View

__version__ = "0.1.0"

__all__ = [
    "Sheet", "View", "ProvenanceRules", "classify", "CLASSES", "DEFAULT_RULES", "DEFAULT_COLORS",
    "DEFAULT_DESCRIPTIONS", "DRAWN_BY", "LINE_TYPES", "PAPER", "ISO_HEIGHTS", "arc_points",
    "polygon_area_centroid", "revolved_volume", "fmt_value", "parse_scale", "text_width", "demo", "build_demo", "__version__",
]


def demo(path: str = "isodraw_demo.svg") -> str:
    """Write a demo sheet that exercises every primitive; returns the path."""
    return build_demo().save(path)
