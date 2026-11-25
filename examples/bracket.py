"""Angle bracket on A3 in *audit mode*: two views at 2:1, hidden lines, fillet, holes, and the full provenance
table printed on the sheet.  Run:  python examples/bracket.py [out.svg]

The part is invented for this example; all numbers are round demo values.
"""

import os
import sys

from isodraw import Sheet, arc_points

# ---- part definition (model mm) ----------------------------------------------------------------------------------
BASE_L, UPRIGHT_H, T, DEPTH = 60.0, 40.0, 6.0, 30.0
R_IN = 6.0                      # inner bend fillet
D_HOLE = 8.0                    # both holes
X_HOLE_BASE = 40.0              # hole in the base, from the back face
Y_HOLE_UPRIGHT = 25.0           # hole in the upright, from the bottom face


def build() -> Sheet:
    sh = Sheet("A3", title="ANGLE BRACKET", number="DWG-2001", scale="2:1", material="EN AW-6082-T6",
               mass="TBD", status="CONCEPT", owner="isodraw examples", show_tags=True)

    # ---- front view: L profile with the inner fillet ----------------------------------------------------------
    f = sh.view(50, 150, "2:1", label="FRONT VIEW", label_xy=(110, 178), name="FRONT")
    fillet = arc_points(T + R_IN, T + R_IN, R_IN, 270, 180, 12)
    outline = [(0, 0), (BASE_L, 0), (BASE_L, T)] + fillet + [(T, UPRIGHT_H), (0, UPRIGHT_H)]
    f.polyline(outline, closed=True)
    # holes seen edge-on -> hidden lines + centre lines
    for dx in (-D_HOLE / 2, D_HOLE / 2):
        f.line(X_HOLE_BASE + dx, 0, X_HOLE_BASE + dx, T, "hidden")
        f.line(0, Y_HOLE_UPRIGHT + dx, T, Y_HOLE_UPRIGHT + dx, "hidden")
    f.centreline(X_HOLE_BASE, -1, X_HOLE_BASE, T + 1)
    f.centreline(-1, Y_HOLE_UPRIGHT, T + 1, Y_HOLE_UPRIGHT)

    f.dim_linear((0, 0), (BASE_L, 0), "customer interface drawing", offset=-12)
    f.dim_linear((0, 0), (X_HOLE_BASE, 0), "calc:bolt_pattern", offset=-12, tier=1)
    f.dim_linear((BASE_L, 0), (BASE_L, T), "calc:bending_check", offset=8, orient="v")
    f.dim_linear((0, 0), (0, UPRIGHT_H), "customer interface drawing", offset=-22, orient="v")
    f.dim_linear((0, 0), (0, Y_HOLE_UPRIGHT), "TBD", offset=-10, orient="v")
    c = T + R_IN - R_IN * 0.7071              # point on the fillet at 225 deg
    f.leader(c, c, f"R{R_IN:g}", "assume: standard bend die", dx=16, dy=-16, value=R_IN, label="inner fillet")
    f.leader(T, UPRIGHT_H, "BREAK EDGES 0.5", "ISO 13715", dx=14, dy=-10)

    # ---- side view (first-angle: view from the left, drawn on the right) ---------------------------------------
    s = sh.view(240, 150, "2:1", label="VIEW FROM LEFT", label_xy=(270, 178), name="SIDE")
    s.rect(0, 0, DEPTH, UPRIGHT_H, lt="visible")
    s.line(0, T, DEPTH, T, "hidden")             # top of the base, behind the upright
    s.circle(DEPTH / 2, Y_HOLE_UPRIGHT, D_HOLE / 2)
    s.centre_mark(DEPTH / 2, Y_HOLE_UPRIGHT, 12)
    s.dim_linear((0, UPRIGHT_H), (DEPTH, UPRIGHT_H), "customer interface drawing", offset=10)
    s.leader(DEPTH / 2 + 2.83, Y_HOLE_UPRIGHT + 2.83, f"2× Ø{D_HOLE:g} THRU", "calc:bolt_pattern", dx=16, dy=-18)

    # ---- notes, legend and the on-sheet provenance table ------------------------------------------------------
    sh.notes(322, 18, 88, [
        "General tolerances ISO 2768-m.",
        "Audit mode: every value carries its [provenance tag].",
        "Mass TBD until the material is confirmed.",
    ])
    sh.prov_legend(322, 125)
    sh.prov_table(25, 190, 200, max_h=92)
    return sh


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "docs", "img", "bracket.svg")
    print(build().save(os.path.normpath(out)))
