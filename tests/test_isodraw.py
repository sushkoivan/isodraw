import math
import re
import runpy
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import isodraw
from isodraw import PAPER, ProvenanceRules, Sheet, arc_points, classify, fmt_value, parse_scale, revolved_volume
from isodraw.__main__ import main
from isodraw import build_demo
from isodraw.provenance import DEFAULT_COLORS

NS = {"svg": "http://www.w3.org/2000/svg"}
ROOT = Path(__file__).resolve().parents[1]


def parse(sheet):
    return ET.fromstring(sheet.to_svg().split("\n", 1)[1])   # drop the XML declaration line


def texts(root):
    return ["".join(t.itertext()) for t in root.iter("{http://www.w3.org/2000/svg}text")]


@pytest.fixture
def sheet():
    return Sheet("A3", title="TEST PART", number="DWG-9", date="2000-01-01")


# ---- SVG structure ----------------------------------------------------------------------------------------------
def test_demo_is_well_formed_xml(tmp_path):
    out = tmp_path / "demo.svg"
    isodraw.demo(str(out))
    root = ET.parse(out).getroot()
    assert root.tag == "{http://www.w3.org/2000/svg}svg"


@pytest.mark.parametrize("size", list(PAPER))
def test_viewbox_matches_paper_size(size):
    root = parse(Sheet(size))
    w, h = PAPER[size]
    assert root.get("viewBox") == f"0 0 {w:g} {h:g}"
    assert root.get("width") == f"{w:g}mm" and root.get("height") == f"{h:g}mm"


def test_unknown_size_rejected():
    with pytest.raises(ValueError):
        Sheet("B5")


def test_title_block_contains_fields(sheet):
    t = texts(parse(sheet))
    assert "TEST PART" in t and "DWG-9" in t and "2000-01-01" in t and "isodraw" in t


def test_to_svg_is_idempotent(sheet):
    v = sheet.view(100, 100)
    v.rect(0, 0, 10, 10)
    assert sheet.to_svg() == sheet.to_svg()


def test_text_is_escaped(sheet):
    sheet.text(50, 50, "A < B & C")
    assert "A < B & C" in texts(parse(sheet))


# ---- coordinates ------------------------------------------------------------------------------------------------
def test_model_to_paper_flips_y(sheet):
    v = sheet.view(100, 150, "1:2")
    assert v.to_paper(0, 0) == (100, 150)
    assert v.to_paper(20, 10) == (110, 145)      # x right, model y up -> paper y down


def test_line_coordinates_in_svg(sheet):
    v = sheet.view(100, 150, "2:1")
    v.line(0, 0, 10, 5)
    line = [e for e in parse(sheet).iter("{http://www.w3.org/2000/svg}line") if e.get("x1") == "100"][0]
    assert (line.get("y1"), line.get("x2"), line.get("y2")) == ("150", "120", "140")


@pytest.mark.parametrize("scale,expected", [("1:2", (0.5, "1:2")), ("2:1", (2.0, "2:1")), (0.2, (0.2, "1:5")),
                                            (5, (5.0, "5:1"))])
def test_parse_scale(scale, expected):
    assert parse_scale(scale) == expected


def test_parse_scale_rejects_garbage():
    with pytest.raises(ValueError):
        parse_scale("half")


# ---- dimensions -------------------------------------------------------------------------------------------------
def test_dim_linear_measures_geometry(sheet):
    v = sheet.view(100, 150, "1:2")
    r = v.dim_linear((0, 0), (125.5, 40), "part drawing")
    assert r["value"] == pytest.approx(125.5) and r["text"] == "125.5"
    assert "125.5" in texts(parse(sheet))


def test_dim_linear_vertical_aligned_and_override(sheet):
    v = sheet.view(100, 150)
    assert v.dim_linear((0, 0), (5, 30), "x", orient="v")["text"] == "30"
    assert v.dim_linear((0, 0), (30, 40), "x", orient="aligned")["value"] == pytest.approx(50)
    assert v.dim_linear((0, 0), (10, 0), "x", value=12.25, prefix="Ø", suffix=" h6", dec=2)["text"] == "Ø12.25 h6"
    with pytest.raises(ValueError):
        v.dim_linear((0, 0), (1, 1), "x", orient="diagonal")


def test_diameter_radius_angle_values(sheet):
    v = sheet.view(100, 150)
    assert v.dim_diameter(0, 0, 15, "s")["text"] == "Ø30"
    assert v.dim_dia_half(10, 12.5, "s")["text"] == "Ø25"
    assert v.dim_radius(0, 0, 4, "s")["text"] == "R4"
    assert v.dim_angle(0, 0, 20, 0, 60, "s")["text"] == "60°"


def test_tbd_dimension_prints_tbd_and_records_none(sheet):
    v = sheet.view(100, 150)
    r = v.dim_linear((0, 0), (40, 0), "TBD")
    assert r["value"] is None and r["text"] == "TBD" and r["cls"] == "tbd"
    assert v.leader(0, 0, "FIX LATER", "tbd: supplier", value=3)["value"] is None


def test_records_populated_in_order():
    sh = build_demo()
    assert len(sh.records) == 12
    assert [r["n"] for r in sh.records] == list(range(1, 13))
    assert {r["cls"] for r in sh.records} == {"source", "calc", "assumption", "tbd"}
    assert set(sh.records[0]) == {"n", "view", "kind", "label", "value", "unit", "prov", "cls", "text"}
    assert {r["kind"] for r in sh.records} >= {"linear", "diameter", "radius", "angle", "callout", "balloon"}


# ---- provenance -------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("tag,cls", [
    ("TBD", "tbd"), ("length TBD by supplier", "tbd"), ("assume: 2 mm gap", "assumption"),
    ("A: stock size", "assumption"), ("calc:shaft_torsion", "calc"), ("C: fea run 3", "calc"),
    ("CALC:upper", "calc"), ("ISO 2768-m", "source"), ("datasheet", "source"), ("outbdx", "source"),
])
def test_default_classification(tag, cls):
    assert classify(tag) == cls


def test_dimension_colour_follows_provenance(sheet):
    v = sheet.view(100, 150)
    v.dim_linear((0, 0), (40, 0), "calc:x")
    v.dim_linear((0, 0), (40, 0), "assume: y", tier=1)
    fills = {t.get("fill") for t in parse(sheet).iter("{http://www.w3.org/2000/svg}text")
             if "".join(t.itertext()) == "40"}
    assert fills == {DEFAULT_COLORS["calc"], DEFAULT_COLORS["assumption"]}


def test_custom_rules_and_classifier():
    rules = ProvenanceRules(calc_prefixes=("FEA:",), colors={**DEFAULT_COLORS, "calc": "#00ff00"})
    sh = Sheet("A4", provenance=rules)
    r = sh.view(50, 50).dim_linear((0, 0), (10, 0), "FEA: model 2")
    assert r["cls"] == "calc" and sh.prov_color("FEA: x") == "#00ff00"
    assert sh.prov_class("calc:x") == "source"          # default prefix no longer active
    upper = ProvenanceRules(classifier=lambda t: "tbd" if t.startswith("?") else "source")
    assert upper.classify("?gap") == "tbd" and upper.classify("gap") == "source"
    with pytest.raises(ValueError):
        ProvenanceRules(classifier=lambda t: "maybe").classify("x")


def test_tags_hidden_by_default_and_shown_in_audit_mode():
    clean, audit = build_demo(show_tags=False), build_demo(show_tags=True)
    assert "prov-tag" not in clean.to_svg()
    tagged = [r for r in audit.records if r["kind"] != "balloon"]     # a balloon without text has no tag
    assert audit.to_svg().count('class="prov-tag"') >= len(tagged)
    assert "[calc:block_width]" in audit.to_svg()


# ---- line types, hatching, clipping -----------------------------------------------------------------------------
def test_line_types_emitted(sheet):
    v = sheet.view(100, 150)
    for i, lt in enumerate(("visible", "hidden", "centre", "phantom")):
        v.line(0, i, 10, i, lt)
    svg = sheet.to_svg()
    for dash in ('stroke-dasharray="3 1"', 'stroke-dasharray="8 1 1.5 1"', 'stroke-dasharray="8 1 1.5 1 1.5 1"'):
        assert dash in svg
    assert 'stroke-width="0.5"' in svg
    with pytest.raises(ValueError):
        v.line(0, 0, 1, 1, "wavy")


def test_hatch_is_clipped_to_polygon(sheet):
    v = sheet.view(100, 150)
    v.rect(0, 0, 20, 10, hatch=(45, 2.0))
    root = parse(sheet)
    clip = root.find(".//svg:clipPath/svg:polygon", NS)
    assert clip is not None
    hatch = [p for p in root.iter("{http://www.w3.org/2000/svg}path") if p.get("clip-path")]
    assert len(hatch) == 1 and hatch[0].get("stroke-width") == "0.18"
    assert hatch[0].get("d").count("M") >= 10    # 10 x 20 mm at 2 mm spacing -> many lines


def test_view_clip(sheet):
    v = sheet.view(100, 150, "2:1", clip=(-5, -5, 5, 10))
    v.circle(0, 0, 50)
    root = parse(sheet)
    rect = root.find(f".//svg:clipPath[@id='{v.clip_id}']/svg:rect", NS)
    assert [float(rect.get(k)) for k in ("x", "y", "width", "height")] == [90, 130, 20, 30]
    g = root.find(f".//svg:g[@id='{v.gid}-geom']", NS)
    assert g.get("clip-path") == f"url(#{v.clip_id})"


def test_all_text_inside_paper():
    for sh in (build_demo(), build_demo(show_tags=True)):
        for t in parse(sh).iter("{http://www.w3.org/2000/svg}text"):
            x, y = float(t.get("x")), float(t.get("y"))
            assert 0 <= x <= sh.W and 0 <= y <= sh.H


# ---- helpers / CLI / examples -----------------------------------------------------------------------------------
def test_helpers():
    assert fmt_value(12.50) == "12.5" and fmt_value(3.0) == "3" and fmt_value(1.256, 2) == "1.26"
    pts = arc_points(0, 0, 10, 0, 90, 4)
    assert pts[0] == pytest.approx((10, 0)) and pts[-1] == pytest.approx((0, 10)) and len(pts) == 5
    # cylinder r = 10, length 20 as a revolved rectangle
    assert revolved_volume([(0, 0), (20, 0), (20, 10), (0, 10)]) == pytest.approx(math.pi * 100 * 20)


def test_cli_demo(tmp_path, capsys):
    out = tmp_path / "d.svg"
    assert main(["demo", str(out)]) == 0 and out.exists()
    assert main([]) == 2
    assert main(["--version"]) == 0 and isodraw.__version__ in capsys.readouterr().out


@pytest.mark.parametrize("name", ["flanged_shaft", "bracket"])
def test_examples_run(name, tmp_path):
    out = tmp_path / f"{name}.svg"
    mod = runpy.run_path(str(ROOT / "examples" / f"{name}.py"))
    sh = mod["build"]()
    sh.save(str(out))
    ET.parse(out)
    assert sh.records and re.match(r"DWG-\d+", sh.title_block["number"])
