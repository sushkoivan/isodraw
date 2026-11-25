"""Flanged shaft on A3: half section with hatching, diameters, chained lengths, an end view, notes and a mass
computed from the drawn profile.  Run:  python examples/flanged_shaft.py [out.svg]

The part is invented for this example; all numbers are round demo values.
"""

import math
import os
import sys

from isodraw import Sheet, arc_points, revolved_volume

# ---- part definition (model mm; x = axis, y = radius) -------------------------------------------------------------
L_FLANGE, R_FLANGE = 12.0, 40.0      # flange thickness / radius
L_SHAFT, R_SHAFT = 100.0, 15.0       # main journal
L_STEP, R_STEP = 48.0, 12.5          # stepped end
R_BORE = 6.0                         # through bore
R_FILLET, CHAMFER = 2.0, 1.0
PCD, D_HOLE, N_HOLES = 60.0, 9.0, 4
RHO = 7.85e-6                        # kg/mm^3, steel

x1 = L_FLANGE
x2 = x1 + L_SHAFT
x3 = x2 + L_STEP

# outer profile of the upper half, from the bore at the left face, clockwise around the material
fillet = arc_points(x1 + R_FILLET, R_SHAFT + R_FILLET, R_FILLET, 180, 270, 8)
profile = ([(0, R_BORE), (0, R_FLANGE), (x1, R_FLANGE)] + fillet
           + [(x2, R_SHAFT), (x2, R_STEP), (x3 - CHAMFER, R_STEP), (x3, R_STEP - CHAMFER), (x3, R_BORE)])

# mass from the drawn geometry (Pappus) minus the bolt holes
volume = revolved_volume(profile) - N_HOLES * math.pi * (D_HOLE / 2) ** 2 * L_FLANGE
mass = RHO * volume


def build() -> Sheet:
    sh = Sheet("A3", title="FLANGED SHAFT", number="DWG-1001", scale="1:1", material="Steel C45E",
               mass=f"{mass:.2f} kg", mass_src="calc:revolved_volume", status="CONCEPT", owner="isodraw examples")

    # ---- half section: upper half cut (hatched), lower half external view -----------------------------------------
    v = sh.view(60, 130, "1:1", label="HALF SECTION A-A", label_xy=(140, 195), name="A-A")
    r_in, r_out = PCD / 2 - D_HOLE / 2, PCD / 2 + D_HOLE / 2
    # the cutting plane passes through a bolt hole -> the flange section is split by the hole
    body = [(0, R_BORE), (0, r_in), (x1, r_in)] + profile[3:]
    v.polygon(body, hatch=(45, 2.0))
    v.rect(0, r_out, x1, R_FLANGE, hatch=(45, 2.0))
    v.centreline(-2, PCD / 2, x1 + 2, PCD / 2, ext=2)
    # lower half: outline only (hidden lines omitted, as usual in half sections)
    lower = [(x, -y) for x, y in profile[1:-1]]
    v.polyline([(0, 0)] + lower + [(x3, 0)])
    v.line(x3 - CHAMFER, -R_STEP, x3 - CHAMFER, 0)        # chamfer edge
    v.centreline(0, 0, x3, 0, ext=6)

    # chained lengths above the part, overall length one tier further out
    v.dim_linear((0, R_FLANGE), (x1, R_FLANGE), "part drawing", at=50, offset=1, text_pos="out_start")
    v.dim_linear((x1, R_FLANGE), (x2, R_SHAFT), "calc:bearing_span", at=50, offset=1)
    v.dim_linear((x2, R_SHAFT), (x3, R_STEP), "TBD", at=50, offset=1)
    v.dim_linear((0, R_FLANGE), (x3, R_STEP), "part drawing", at=50, offset=1, tier=1)

    # diameters: ISO 129-1 half dimensions from the external (lower) half across the axis
    v.dim_dia_half(x1 / 2, -R_FLANGE, "assume: Ø80 bar stock", over=4)
    v.dim_dia_half(60, -R_SHAFT, "calc:shaft_torsion", over=4)
    v.dim_dia_half(x2 + 24, -R_STEP, "bearing datasheet", over=4)
    v.dim_dia_half(30, R_BORE, "part drawing", over=12, text_at=0.75)

    v.leader(x3 - CHAMFER / 2, R_STEP - CHAMFER / 2, f"{CHAMFER:g}×45°", "ISO 2768-m", dx=8, dy=-14)
    v.leader(x1 + 0.6, R_SHAFT + 0.6, f"R{R_FILLET:g}", "calc:fillet_stress", dx=14, dy=-12)

    # ---- end view (first-angle: the view from the left is drawn on the right) -------------------------------------
    e = sh.view(330, 130, "1:1", label="VIEW B", label_xy=(330, 195), name="B")
    e.circle(0, 0, R_FLANGE)
    e.circle(0, 0, R_SHAFT, "hidden")
    e.circle(0, 0, R_BORE)
    e.circle(0, 0, PCD / 2, "centre")
    e.centre_mark(0, 0, 46)
    for k in range(N_HOLES):
        a = math.radians(90 * k)
        cx, cy = PCD / 2 * math.cos(a), PCD / 2 * math.sin(a)
        e.circle(cx, cy, D_HOLE / 2)
        e.centre_mark(cx, cy, 7)
    hx, hy = PCD / 2 * math.cos(math.radians(45)), PCD / 2 * math.sin(math.radians(45))
    e.leader(PCD / 2 + D_HOLE / 2 * math.cos(math.radians(45)), D_HOLE / 2 * math.sin(math.radians(45)),
             f"{N_HOLES}× Ø{D_HOLE:g} THRU", "calc:bolt_shear", dx=14, dy=-30)
    e.dim_diameter(0, 0, PCD / 2, "calc:bolt_shear", ang=-150, label="pitch circle")
    e.dim_angle(0, 0, 50, 0, 90, "part drawing", label="hole spacing")
    # cutting-plane indication A-A
    for y in (R_FLANGE + 8, -R_FLANGE - 8):
        e.line(0, y - 3, 0, y + 3, "visible")
    sh.text(*e.to_paper(3, R_FLANGE + 11), "A", h=5.0, weight="bold")
    sh.text(*e.to_paper(3, -R_FLANGE - 13), "A", h=5.0, weight="bold")

    # ---- notes and legend -----------------------------------------------------------------------------------------
    sh.notes(28, 205, 195, [
        "General tolerances ISO 2768-m. Break all sharp edges 0.3 × 45°.",
        f"Mass {mass:.2f} kg computed from the drawn profile (Pappus) minus {N_HOLES} bolt holes.",
        "Length of the stepped end is TBD until the bearing supplier is chosen.",
        "Colour of every dimension shows where the number came from (legend top right).",
    ])
    sh.prov_legend(305, 18)
    return sh


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "docs", "img", "flanged_shaft.svg")
    sheet = build()
    print(sheet.save(os.path.normpath(out)))
    for r in sheet.records:
        print(f'{r["n"]:>3}  {r["view"]:<4} {r["label"]:<16} {r["cls"]:<10} {r["prov"]}')
