"""The :class:`Sheet`: paper space, ISO 5457 frame, ISO 7200 title block, notes, legends and SVG output.

Paper space is the SVG viewBox in millimetres (1 user unit = 1 mm on paper, y pointing DOWN).
"""

from __future__ import annotations

import datetime
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from xml.sax.saxutils import escape

from .provenance import CLASSES, ProvenanceRules
from .styles import (CAP, FONT, LINE_TYPES, MARGIN, PAPER, TAG_H, ZONE_LETTERS, ZONES, _f, _stroke, fmt_value,
                     text_width)
from .view import View

DRAWN_BY = "isodraw"
STANDARDS_NOTE = "ISO 128 / 129-1 / 5457 / 7200, dims in mm"

Record = Dict[str, Any]


class Sheet:
    """One drawing sheet.

    Args:
        size: ``"A4"`` ... ``"A0"`` (landscape).
        title, number, rev, scale, sheet, material, mass, mass_src, drawn_by, date, status, owner:
            ISO 7200 title-block fields (strings). ``date`` defaults to today.
        provenance: :class:`~isodraw.ProvenanceRules` that classify and colour provenance tags.
        show_tags: ``True`` = "audit mode": every value is followed by a small raised ``[tag]``.
            ``False`` (default) = values are only colour-coded; tags still go to :attr:`records`.

    Attributes:
        records: one dict per dimension / callout with keys ``n, view, kind, label, value, unit, prov, cls,
            text`` -- the machine-readable register of every number on the sheet.
    """

    def __init__(self, size: str = "A3", *, title: str = "", number: str = "DWG-0001", rev: str = "A",
                 scale: str = "1:1", sheet: str = "1/1", material: str = "", mass: str = "", mass_src: str = "",
                 drawn_by: str = DRAWN_BY, date: Optional[str] = None, status: str = "CONCEPT", owner: str = "",
                 provenance: Optional[ProvenanceRules] = None, show_tags: bool = False) -> None:
        if size not in PAPER:
            raise ValueError(f"size must be one of {list(PAPER)}")
        self.size = size
        self.W, self.H = PAPER[size]
        self.title_block: Dict[str, str] = dict(
            title=title, number=number, rev=rev, scale=scale, sheet=sheet, material=material, mass=mass,
            mass_src=mass_src, drawn_by=drawn_by, date=date or datetime.date.today().isoformat(), status=status,
            owner=owner)
        self.rules = provenance or ProvenanceRules()
        self.show_tags = show_tags
        self.defs: List[str] = []
        self.back: List[str] = []       # drawn first, under everything (banner)
        self.views: List[View] = []
        self.paper: List[str] = []      # paper-space annotation (notes, tables, legends)
        self.records: List[Record] = []
        self._n = 0
        self.fx0, self.fy0 = MARGIN["left"], MARGIN["top"]
        self.fx1, self.fy1 = self.W - MARGIN["right"], self.H - MARGIN["bottom"]

    # ---- ids / records / provenance ------------------------------------------------------------------------------
    def uid(self, prefix: str = "id") -> str:
        """Unique SVG id."""
        self._n += 1
        return f"{prefix}{self._n}"

    def prov_class(self, prov: object) -> str:
        """Provenance class of ``prov`` under this sheet's rules."""
        return self.rules.classify(prov)

    def prov_color(self, prov: object) -> str:
        """Colour of ``prov`` under this sheet's rules."""
        return self.rules.color(prov)

    def tag_width(self, prov: object) -> float:
        """Paper width taken by the inline ``[tag]`` (0 unless ``show_tags``)."""
        return text_width(f"[{prov}]", TAG_H) + 0.5 if self.show_tags else 0.0

    def record(self, view: Optional[str], kind: str, label: str, value: Optional[float], unit: str, prov: object,
               text: str) -> Record:
        """Append one entry to :attr:`records` and return it."""
        r = dict(n=len(self.records) + 1, view=view, kind=kind, label=label, value=value, unit=unit, prov=str(prov),
                 cls=self.prov_class(prov), text=text)
        self.records.append(r)
        return r

    # ---- paper-space primitives ----------------------------------------------------------------------------------
    def line(self, x1: float, y1: float, x2: float, y2: float, lt: str = "thin", color: str = "#000000",
             out: Optional[List[str]] = None) -> None:
        """Straight line in paper coordinates."""
        (self.paper if out is None else out).append(
            f'<line x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}" {_stroke(lt, color)}/>')

    def rect(self, x: float, y: float, w: float, h: float, lt: str = "thin", color: str = "#000000",
             fill: str = "none", out: Optional[List[str]] = None) -> None:
        """Rectangle in paper coordinates (top-left corner ``x, y``)."""
        d = LINE_TYPES[lt]
        (self.paper if out is None else out).append(
            f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}" stroke="{color}" '
            f'stroke-width="{d["w"]}" fill="{fill}"/>')

    def text(self, x: float, y: float, s: str, h: float = 3.5, anchor: str = "start", color: str = "#000000",
             rotate: float = 0.0, weight: str = "normal", fit: Optional[float] = None,
             opacity: Optional[float] = None, out: Optional[List[str]] = None, prov: Optional[object] = None
             ) -> float:
        """Text with its baseline at paper point ``(x, y)``; returns the estimated width [mm].

        Args:
            h: lettering (cap) height [mm] -- use ISO 3098 sizes 2.5 / 3.5 / 5 / 7.
            anchor: ``"start"``, ``"middle"`` or ``"end"``.
            rotate: degrees, clockwise on paper (SVG convention).
            fit: maximum width [mm]; longer text is squeezed with ``textLength``.
            prov: provenance tag, appended as a small raised ``[tag]`` when ``show_tags`` is on.
        """
        fs = h / CAP
        attrs = f'x="{_f(x)}" y="{_f(y)}" font-family="{FONT}" font-size="{_f(fs)}" fill="{color}"'
        attrs += f' text-anchor="{anchor}"'
        if weight != "normal":
            attrs += f' font-weight="{weight}"'
        if opacity is not None:
            attrs += f' fill-opacity="{opacity}"'
        if rotate:
            attrs += f' transform="rotate({_f(rotate)} {_f(x)} {_f(y)})"'
        full_w = text_width(s, h) + (self.tag_width(prov) if prov is not None else 0.0)
        if fit is not None and full_w > fit:
            attrs += f' textLength="{_f(fit)}" lengthAdjust="spacingAndGlyphs"'
        body = escape(s)
        if prov is not None and self.show_tags:
            pc = self.prov_color(prov)
            body += (f'<tspan font-size="{_f(TAG_H / CAP)}" dy="{_f(-0.35 * h)}" dx="0.5" fill="{pc}" '
                     f'class="prov-tag">[{escape(str(prov))}]</tspan>')
        (self.paper if out is None else out).append(f"<text {attrs}>{body}</text>")
        return full_w

    def wrap(self, s: str, width: float, h: float) -> List[str]:
        """Greedy word wrap of ``s`` into lines no wider than ``width`` [mm] (7 % reserve for the estimate)."""
        words, lines, cur = s.split(" "), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if text_width(t, h) <= 0.93 * width or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    # ---- views ---------------------------------------------------------------------------------------------------
    def view(self, ox: float, oy: float, scale: Union[str, float] = "1:1", label: Optional[str] = None,
             clip: Optional[Tuple[float, float, float, float]] = None,
             label_xy: Optional[Tuple[float, float]] = None, name: Optional[str] = None) -> View:
        """Add a view whose model origin sits at paper point ``(ox, oy)``.

        Args:
            scale: ISO 5455 scale, e.g. ``"1:2"``, ``"2:1"`` or a float.
            label: view caption, e.g. ``"SECTION A-A"`` (the scale is appended).
            clip: model rectangle ``(x1, y1, x2, y2)``; geometry outside it is clipped and a rounded border is
                drawn (detail views).
            label_xy: paper position of the caption (default: 10 mm below the origin).
            name: short view name used in :attr:`records` (default: last word of ``label``).
        """
        v = View(self, ox, oy, scale, label, clip, label_xy, name)
        self.views.append(v)
        return v

    # ---- blocks --------------------------------------------------------------------------------------------------
    def banner(self, s: str = "CONCEPT — NOT FOR MANUFACTURE", h: Optional[float] = None) -> None:
        """Large, very light diagonal watermark drawn under all geometry."""
        h = h or self.H / 20
        cx, cy = (self.fx0 + self.fx1) / 2, (self.fy0 + self.fy1) / 2
        ang = -math.degrees(math.atan2(self.fy1 - self.fy0, self.fx1 - self.fx0)) * 0.5
        self.text(cx, cy + h / 2, s, h=h, anchor="middle", color="#000000", rotate=ang, weight="bold",
                  opacity=0.07, out=self.back)

    def notes(self, x: float, y: float, width: float, items: Sequence[str], title: str = "GENERAL NOTES",
              h: float = 2.5, numbered: bool = True) -> float:
        """Notes block with top-left corner at ``(x, y)``; long items are wrapped. Returns its height [mm]."""
        self.text(x, y + 5.0, title, h=3.5, weight="bold")
        yy = y + 5.0 + 2.0
        for i, it in enumerate(items, 1):
            lab = f"{i}." if numbered else ""
            ind = 7.0 if numbered else 0.0
            for j, ln in enumerate(self.wrap(it, width - ind, h)):
                yy += h * 1.6
                if j == 0 and lab:
                    self.text(x, yy, lab, h=h)
                self.text(x + ind, yy, ln, h=h)
            yy += 0.6
        return yy - y

    def prov_legend(self, x: float, y: float, h: float = 2.5, title: Optional[str] = None) -> float:
        """Colour legend of the four provenance classes; returns its height [mm]."""
        if title is None:
            title = "PROVENANCE  [tag] after every value" if self.show_tags else "DIMENSION COLOURS = PROVENANCE"
        self.text(x, y + 3.5, title, h=h, weight="bold")
        yy = y + 3.5
        for k in CLASSES:
            yy += h * 1.7
            col = self.rules.colors[k]
            self.rect(x, yy - h, 5.0, h, lt="thin", color=col, fill=col)
            self.text(x + 7.0, yy, self.rules.descriptions[k], h=h, color=col)
        return yy - y + 1.5

    def prov_table(self, x: float, y: float, width: float, max_h: Optional[float] = None, h: float = 2.5,
                   title: str = "PROVENANCE OF EVERY DIMENSION / CALLOUT") -> Tuple[float, float]:
        """Table ``# | view | feature | value | source`` of all :attr:`records` so far.

        Splits into side-by-side columns if it would be taller than ``max_h``. Returns ``(width, height)`` used.
        Call it after all views are dimensioned.
        """
        row = h * 1.55
        self.text(x, y + 3.5, title, h=3.5, weight="bold")
        y0 = y + 6.0
        recs = self.records
        n_rows_max = max(1, len(recs)) if max_h is None else max(1, int((max_h - 6.0 - row) / row))
        cols = [recs[i:i + n_rows_max] for i in range(0, len(recs), n_rows_max)] or [[]]
        cw = width / len(cols)
        fr = [0.0, 0.05, 0.16, 0.64, 0.79]     # column fractions: n, view, feature, value, prov
        for ci, chunk in enumerate(cols):
            x0 = x + ci * cw
            yy = y0 + row
            for j, hd in enumerate(("#", "view", "feature", "value", "source")):
                self.text(x0 + fr[j] * cw + 0.5, yy - 0.8, hd, h=h, weight="bold")
            self.line(x0, yy + 0.4, x0 + cw - 2.0, yy + 0.4, lt="thin")
            for r in chunk:
                yy += row
                col = self.rules.colors[r["cls"]]
                if r["value"] is None:
                    val = "TBD" if r["cls"] == "tbd" else "-"
                else:
                    val = fmt_value(r["value"], 2) + (" " + r["unit"] if r["unit"] else "")
                cells = (str(r["n"]), r["view"] or "", r["label"], val, r["prov"])
                for j, c in enumerate(cells):
                    wmax = ((fr[j + 1] if j + 1 < len(fr) else 1.0) - fr[j]) * cw - 1.5
                    self.text(x0 + fr[j] * cw + 0.5, yy - 0.8, c, h=h, color=col if j >= 3 else "#000000",
                              fit=wmax)
        return width, 6.0 + row * (min(len(recs), n_rows_max) + 1) + 1.0

    # ---- frame and title block -----------------------------------------------------------------------------------
    def _frame(self, out: List[str]) -> None:
        """ISO 5457 border with reference zones (numbers left->right, letters top->bottom) in the margins."""
        self.rect(self.fx0, self.fy0, self.fx1 - self.fx0, self.fy1 - self.fy0, lt="frame", out=out)
        ncol, nrow = ZONES[self.size]
        dx, dy = (self.fx1 - self.fx0) / ncol, (self.fy1 - self.fy0) / nrow
        for i in range(ncol + 1):
            xx = self.fx0 + i * dx
            if 0 < i < ncol:
                self.line(xx, self.fy0, xx, self.fy0 - 5, lt="thin", out=out)
                self.line(xx, self.fy1, xx, self.fy1 + 5, lt="thin", out=out)
            if i < ncol:
                for yy in (self.fy0 - 3.0, self.fy1 + 6.5):
                    self.text(xx + dx / 2, yy, str(i + 1), h=3.5, anchor="middle", out=out)
        for j in range(nrow + 1):
            yy = self.fy0 + j * dy
            if 0 < j < nrow:
                self.line(self.fx0, yy, self.fx0 - 5, yy, lt="thin", out=out)
                self.line(self.fx1, yy, self.fx1 + 5, yy, lt="thin", out=out)
            if j < nrow:
                for xx in (self.fx0 - 4.0, self.fx1 + 5.0):
                    self.text(xx, yy + dy / 2 + 1.75, ZONE_LETTERS[j], h=3.5, anchor="middle", out=out)

    def _projection_symbol(self, cx: float, cy: float, out: List[str], h: float = 3.5) -> None:
        """ISO 5456-2 first-angle symbol: truncated cone (narrow end left), end view (2 circles) to the right."""
        d_big, d_small, length = 2 * h, h, 2 * h
        x0 = cx - length - 1.0
        pts = [(x0, cy - d_small / 2), (x0 + length, cy - d_big / 2), (x0 + length, cy + d_big / 2),
               (x0, cy + d_small / 2)]
        out.append('<polygon points="' + " ".join(f"{_f(a)},{_f(b)}" for a, b in pts) + f'" {_stroke("thin")}/>')
        cxe = cx + d_big / 2 + 1.5
        out.append(f'<circle cx="{_f(cxe)}" cy="{_f(cy)}" r="{_f(d_big / 2)}" {_stroke("thin")}/>')
        out.append(f'<circle cx="{_f(cxe)}" cy="{_f(cy)}" r="{_f(d_small / 2)}" {_stroke("thin")}/>')
        self.line(x0 - 1.5, cy, x0 + length + 1.5, cy, lt="centre", out=out)
        self.line(cxe - d_big / 2 - 1.5, cy, cxe + d_big / 2 + 1.5, cy, lt="centre", out=out)
        self.line(cxe, cy - d_big / 2 - 1.5, cxe, cy + d_big / 2 + 1.5, lt="centre", out=out)

    def _title_block(self, out: List[str]) -> None:
        """ISO 7200-style title block, 180 x 58 mm, bottom right inside the frame."""
        w_tb, h_tb = 180.0, 58.0
        x0, y0 = self.fx1 - w_tb, self.fy1 - h_tb
        t = self.title_block
        mass = f'{t["mass"]}  ({t["mass_src"]})' if t["mass_src"] else t["mass"]
        rows = [  # (row height, [(cell width, label, value, value lettering height)])
            (10.0, [(120, "MATERIAL", t["material"], 3.5), (60, "MASS (source)", mass, 3.5)]),
            (10.0, [(100, "DRAWN BY", t["drawn_by"], 3.5), (40, "DATE", t["date"], 3.5),
                    (40, "STATUS", t["status"], 3.5)]),
            (11.0, [(30, "SCALE", t["scale"], 3.5), (30, "PROJECTION", "", 3.5), (25, "SHEET", t["sheet"], 3.5),
                    (25, "REVISION", t["rev"], 3.5), (70, "STANDARDS", STANDARDS_NOTE, 2.5)]),
            (13.0, [(180, "TITLE", t["title"], 5.0)]),
            (14.0, [(110, "DRAWING NUMBER", t["number"], 7.0), (70, "OWNER", t["owner"], 2.5)]),
        ]
        self.rect(x0, y0, w_tb, h_tb, lt="frame", fill="#ffffff", out=out)
        yy = y0
        for hrow, cells in rows:
            xx = x0
            for w, lab, val, vh in cells:
                self.rect(xx, yy, w, hrow, lt="thin", out=out)
                self.text(xx + 1.0, yy + 3.0, lab, h=2.0 if len(lab) > 12 else 2.5, color="#444444", out=out)
                if lab == "PROJECTION":
                    self._projection_symbol(xx + w / 2, yy + hrow / 2 + 1.5, out)
                elif val:
                    lines = [val] if text_width(val, vh) <= w - 3 or vh <= 3.5 else self.wrap(val, w - 3, vh)
                    if len(lines) > 1:
                        vh = 3.5
                        lines = self.wrap(val, w - 3, vh)[:2]
                    for k, ln in enumerate(lines):
                        by = yy + hrow - 1.6 - (len(lines) - 1 - k) * vh * 1.35
                        self.text(xx + 1.5, by, ln, h=vh, fit=w - 3,
                                  weight="bold" if lab in ("DRAWING NUMBER", "TITLE") else "normal",
                                  color="#c00000" if lab == "STATUS" else "#000000", out=out)
                xx += w
            yy += hrow

    # ---- output --------------------------------------------------------------------------------------------------
    def to_svg(self) -> str:
        """Render the sheet to an SVG string (can be called repeatedly)."""
        chrome: List[str] = []
        self._frame(chrome)
        self._title_block(chrome)
        tb = self.title_block
        parts = ['<?xml version="1.0" encoding="UTF-8"?>',
                 f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(self.W)}mm" height="{_f(self.H)}mm" '
                 f'viewBox="0 0 {_f(self.W)} {_f(self.H)}">',
                 f'<title>{escape((tb["number"] + " " + tb["title"]).strip())}</title>',
                 f'<rect x="0" y="0" width="{_f(self.W)}" height="{_f(self.H)}" fill="#ffffff"/>',
                 "<defs>", *self.defs,
                 f'<clipPath id="frameclip"><rect x="{_f(self.fx0)}" y="{_f(self.fy0)}" '
                 f'width="{_f(self.fx1 - self.fx0)}" height="{_f(self.fy1 - self.fy0)}"/></clipPath>',
                 "</defs>", '<g id="banner" clip-path="url(#frameclip)">', *self.back, "</g>"]
        for v in self.views:
            clip = f' clip-path="url(#{v.clip_id})"' if v.clip_id else ""
            parts += [f'<g id="{v.gid}-geom"{clip}>', *v.geom, "</g>", f'<g id="{v.gid}-anno">', *v.anno, "</g>"]
        parts += ['<g id="paper">', *self.paper, "</g>", '<g id="frame">', *chrome, "</g>", "</svg>"]
        return "\n".join(parts) + "\n"

    def save(self, path: str) -> str:
        """Write the SVG to ``path`` (UTF-8) and return the path."""
        s = self.to_svg()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(s)
        return path
