"""Provenance classification: every number on a drawing says where it came from.

Each dimension and callout carries a free-form *provenance tag* (``prov``), e.g. ``"datasheet rev B"``,
``"calc:shaft_torsion"``, ``"assume: 2 mm clearance"`` or ``"TBD"``. A :class:`ProvenanceRules` object sorts the tag
into one of four classes, and the class picks the colour of the dimension:

==============  =============================================  ============
class           default rule (case-insensitive)                colour
==============  =============================================  ============
``tbd``         contains the word ``TBD``                      red
``assumption``  starts with ``assume:`` or ``A:``              orange
``calc``        starts with ``calc:`` or ``C:``                dark blue
``source``      anything else (drawing, standard, datasheet)   black
==============  =============================================  ============

The rules are checked in that order. Prefixes, markers, colours and legend texts are all configurable, or you can
pass any ``callable(tag) -> class`` as ``classifier``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple

#: The four provenance classes, in legend order.
CLASSES: Tuple[str, ...] = ("source", "calc", "assumption", "tbd")

DEFAULT_COLORS: Dict[str, str] = {"source": "#000000", "calc": "#0b3d91", "assumption": "#d96c00", "tbd": "#d00000"}
DEFAULT_DESCRIPTIONS: Dict[str, str] = {
    "source": "sourced (drawing, standard, datasheet)",
    "calc": "calculated (calc:<script>)",
    "assumption": "assumption (assume:<reason>)",
    "tbd": "TBD -- not yet defined",
}


@dataclass
class ProvenanceRules:
    """User-configurable mapping from provenance tag to class and colour.

    Example::

        rules = ProvenanceRules(calc_prefixes=("calc:", "FEA:"), colors={**DEFAULT_COLORS, "calc": "#006400"})
        sheet = Sheet("A3", provenance=rules)
    """

    tbd_markers: Tuple[str, ...] = ("TBD",)
    assumption_prefixes: Tuple[str, ...] = ("assume:", "A:")
    calc_prefixes: Tuple[str, ...] = ("calc:", "C:")
    case_sensitive: bool = False
    colors: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_COLORS))
    descriptions: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_DESCRIPTIONS))
    classifier: Optional[Callable[[str], str]] = None

    def classify(self, tag: object) -> str:
        """Return the class (``'source'``, ``'calc'``, ``'assumption'`` or ``'tbd'``) of a provenance tag."""
        p = str(tag).strip()
        if self.classifier is not None:
            cls = self.classifier(p)
            if cls not in CLASSES:
                raise ValueError(f"classifier returned {cls!r}; expected one of {CLASSES}")
            return cls
        flags = 0 if self.case_sensitive else re.IGNORECASE
        for m in self.tbd_markers:
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(m) + r"(?![A-Za-z0-9])", p, flags):
                return "tbd"
        cmp = p if self.case_sensitive else p.lower()

        def starts(prefixes: Tuple[str, ...]) -> bool:
            return any(cmp.startswith(x if self.case_sensitive else x.lower()) for x in prefixes)

        if starts(self.assumption_prefixes):
            return "assumption"
        if starts(self.calc_prefixes):
            return "calc"
        return "source"

    def color(self, tag: object) -> str:
        """Colour of the class that ``tag`` belongs to."""
        return self.colors[self.classify(tag)]


#: Rules used when a :class:`~isodraw.Sheet` is created without ``provenance=``.
DEFAULT_RULES = ProvenanceRules()


def classify(tag: object, rules: Optional[ProvenanceRules] = None) -> str:
    """Classify ``tag`` with ``rules`` (default: :data:`DEFAULT_RULES`)."""
    return (rules or DEFAULT_RULES).classify(tag)
