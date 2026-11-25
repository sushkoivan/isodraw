"""The :class:`View`: model-space geometry and ISO 129-1 dimensions.

A view maps model millimetres (x right, y UP) to paper millimetres (y DOWN)::

    X = ox + s * x
    Y = oy - s * y          (s = scale factor, (ox, oy) = paper position of the model origin)

All coordinates are converted in Python -- no SVG transforms are applied to text, so text is never mirrored.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union

from .geometry import Point, arc_points
from .styles import ARROW_L, ARROW_W, EXT_GAP, EXT_OVER, TIER, _f, _stroke, fmt_value, parse_scale, text_width

if TYPE_CHECKING:  # pragma: no cover
    from .sheet import Sheet

Record = Dict[str, Any]


class View:
    """A drawing view placed on a :class:`~isodraw.Sheet`. Create it with :meth:`Sheet.view`.

    Geometry methods take MODEL coordinates (mm, y up). Every dimension / callout method takes a mandatory
    provenance tag ``prov`` (see :mod:`isodraw.provenance`), is coloured by it and returns its record.
    """

    def __init__(self, sheet: "Sheet", ox: float, oy: float, scale: Union[str, float] = "1:1",
                 label: Optional[str] = None, clip: Optional[Tuple[float, float, float, float]] = None,
                 label_xy: Optional[Tuple[float, float]] = None, name: Optional[str] = None) -> None:
        self.sheet = sheet
        self.ox, self.oy = ox, oy
        self.s, self.scale_str = parse_scale(scale)
        self.label = label
        self.name = name or (label or "view").split()[-1]
        self.gid = sheet.uid("view")
        self.geom: List[str] = []
        self.anno: List[str] = []
        self.clip_id: Optional[str] = None
        if clip is not None:
            x1, y1, x2, y2 = clip
            (X1, Y1), (X2, Y2) = self.to_paper(x1, y1), self.to_paper(x2, y2)
            self.clip_id = sheet.uid("clipv")
            box = (f'x="{_f(min(X1, X2))}" y="{_f(min(Y1, Y2))}" width="{_f(abs(X2 - X1))}" '
                   f'height="{_f(abs(Y2 - Y1))}"')
            sheet.defs.append(f'<clipPath id="{self.clip_id}"><rect {box}/></clipPath>')
            self.anno.append(f'<rect {box} rx="4" {_stroke("thin")}/>')
        if label:
            if label_xy is None:
                label_xy = (ox, oy + 10)
            sheet.text(label_xy[0], label_xy[1], f"{label}  {self.scale_str}", h=5.0, anchor="middle",
                       weight="bold", out=self.anno)

    # ---- coordinates ---------------------------------------------------------------------------------------------
    def to_paper(self, x: float, y: float) -> Tuple[float, float]:
        """Model point (mm, y up) -> paper point (mm, y down)."""
        return self.ox + self.s * x, self.oy - self.s * y

    def _pts(self, pts: Sequence[Point]) -> str:
        return " ".join(f"{_f(X)},{_f(Y)}" for X, Y in (self.to_paper(x, y) for x, y in pts))

    # ---- geometry primitives (model coordinates) -----------------------------------------------------------------
    def line(self, x1: float, y1: float, x2: float, y2: float, lt: str = "visible", color: str = "#000000") -> None:
        """Straight line. ``lt``: ``visible``, ``thin``, ``hidden``, ``centre``, ``phantom`` (ISO 128-20)."""
        (X1, Y1), (X2, Y2) = self.to_paper(x1, y1), self.to_paper(x2, y2)
        self.geom.append(f'<line x1="{_f(X1)}" y1="{_f(Y1)}" x2="{_f(X2)}" y2="{_f(Y2)}" {_stroke(lt, color)}/>')

    def polyline(self, pts: Sequence[Point], lt: str = "visible", closed: bool = False,
                 color: str = "#000000") -> None:
        """Open (or ``closed``) polyline through model points."""
        tag = "polygon" if closed else "polyline"
        self.geom.append(f'<{tag} points="{self._pts(pts)}" {_stroke(lt, color)}/>')

    def polygon(self, pts: Sequence[Point], lt: str = "visible",
                hatch: Optional[Tuple[float, ...]] = None, color: str = "#000000") -> None:
        """Closed outline; ``hatch=(angle_deg, spacing_paper_mm[, phase])`` adds ISO 128-50 section hatching."""
        if hatch:
            self.hatch(pts, *hatch)
        self.polyline(pts, lt, closed=True, color=color)

    def rect(self, x1: float, y1: float, x2: float, y2: float, lt: str = "visible",
             hatch: Optional[Tuple[float, ...]] = None) -> None:
        """Axis-aligned rectangle between model corners, optionally hatched."""
        self.polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], lt, hatch)

    def circle(self, cx: float, cy: float, r: float, lt: str = "visible") -> None:
        """Circle of model radius ``r``."""
        X, Y = self.to_paper(cx, cy)
        self.geom.append(f'<circle cx="{_f(X)}" cy="{_f(Y)}" r="{_f(r * self.s)}" {_stroke(lt)}/>')

    def arc(self, cx: float, cy: float, r: float, a0: float, a1: float, lt: str = "visible",
            color: str = "#000000") -> None:
        """Circular arc, counter-clockwise (model) from ``a0`` to ``a1`` [deg]."""
        if a1 < a0:
            a0, a1 = a1, a0
        x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
        x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
        (X0, Y0), (X1, Y1) = self.to_paper(x0, y0), self.to_paper(x1, y1)
        large = 1 if (a1 - a0) % 360 > 180 else 0
        R = r * self.s
        # model y-up -> paper y-down, so a CCW model arc is drawn with SVG sweep-flag = 0
        self.geom.append(f'<path d="M{_f(X0)},{_f(Y0)} A{_f(R)},{_f(R)} 0 {large} 0 {_f(X1)},{_f(Y1)}" '
                         f'{_stroke(lt, color)}/>')

    def hatch(self, pts: Sequence[Point], angle: float = 45.0, spacing: float = 2.0, phase: float = 0.0,
              color: str = "#000000") -> None:
        """Parallel thin lines at ``angle`` (deg, CCW on paper) every ``spacing`` paper mm, clipped to the polygon.

        Use a different angle or ``phase`` for adjacent parts (ISO 128-50).
        """
        P = [self.to_paper(x, y) for x, y in pts]
        cid = self.sheet.uid("hat")
        self.sheet.defs.append(f'<clipPath id="{cid}"><polygon points="'
                               + " ".join(f"{_f(a)},{_f(b)}" for a, b in P) + '"/></clipPath>')
        th = math.radians(angle)
        d = (math.cos(th), -math.sin(th))        # direction on paper (y down)
        n = (math.sin(th), math.cos(th))         # normal
        ds = [X * n[0] + Y * n[1] for X, Y in P]
        ts = [X * d[0] + Y * d[1] for X, Y in P]
        k0 = math.floor((min(ds) - phase) / spacing)
        k1 = math.ceil((max(ds) - phase) / spacing)
        segs = []
        for k in range(k0, k1 + 1):
            dd = phase + k * spacing
            ax, ay = n[0] * dd + d[0] * (min(ts) - 1), n[1] * dd + d[1] * (min(ts) - 1)
            bx, by = n[0] * dd + d[0] * (max(ts) + 1), n[1] * dd + d[1] * (max(ts) + 1)
            segs.append(f"M{_f(ax)},{_f(ay)}L{_f(bx)},{_f(by)}")
        self.geom.append(f'<path clip-path="url(#{cid})" d="{"".join(segs)}" {_stroke("hatch", color)}/>')

    def centreline(self, x1: float, y1: float, x2: float, y2: float, ext: float = 3.0) -> None:
        """Chain line (ISO 128 type 04.1), extended ``ext`` paper mm beyond both points."""
        (X1, Y1), (X2, Y2) = self.to_paper(x1, y1), self.to_paper(x2, y2)
        L = math.hypot(X2 - X1, Y2 - Y1) or 1.0
        ux, uy = (X2 - X1) / L, (Y2 - Y1) / L
        self.geom.append(f'<line x1="{_f(X1 - ux * ext)}" y1="{_f(Y1 - uy * ext)}" x2="{_f(X2 + ux * ext)}" '
                         f'y2="{_f(Y2 + uy * ext)}" {_stroke("centre")}/>')

    def centre_mark(self, cx: float, cy: float, size: Optional[float] = None) -> None:
        """Cross of chain lines at a hole centre; ``size`` = half-length in paper mm (default 6)."""
        size = size or 6.0
        X, Y = self.to_paper(cx, cy)
        for a, b, c, d in ((X - size, Y, X + size, Y), (X, Y - size, X, Y + size)):
            self.geom.append(f'<line x1="{_f(a)}" y1="{_f(b)}" x2="{_f(c)}" y2="{_f(d)}" {_stroke("centre")}/>')

    # ---- annotation helpers (paper coordinates) ------------------------------------------------------------------
    def _pl(self, X1: float, Y1: float, X2: float, Y2: float, color: str, lt: str = "thin") -> None:
        self.anno.append(f'<line x1="{_f(X1)}" y1="{_f(Y1)}" x2="{_f(X2)}" y2="{_f(Y2)}" {_stroke(lt, color)}/>')

    def _arrow(self, X: float, Y: float, ux: float, uy: float, color: str) -> None:
        """Filled arrowhead with its tip at (X, Y) pointing along (ux, uy)."""
        bx, by = X - ux * ARROW_L, Y - uy * ARROW_L
        px, py = -uy * ARROW_W, ux * ARROW_W
        self.anno.append(f'<polygon points="{_f(X)},{_f(Y)} {_f(bx + px)},{_f(by + py)} {_f(bx - px)},'
                         f'{_f(by - py)}" fill="{color}" stroke="none"/>')

    def _dim_text(self, X: float, Y: float, s: str, prov: str, h: float, rot: float, anchor: str,
                  color: str) -> float:
        return self.sheet.text(X, Y, s, h=h, anchor=anchor, color=color, rotate=rot, prov=prov, out=self.anno)

    def _value(self, value: Optional[float], measured: float, prov: str, prefix: str, suffix: str,
               dec: int) -> Tuple[Optional[float], str]:
        """Value shown on the drawing: ``value`` if given, else the measured geometry; 'TBD' for TBD tags."""
        tbd = self.sheet.prov_class(prov) == "tbd"
        v = None if tbd else (measured if value is None else value)
        txt = prefix + ("TBD" if tbd else fmt_value(v, dec)) + suffix
        return v, txt

    # ---- dimensions ----------------------------------------------------------------------------------------------
    def dim_linear(self, p1: Point, p2: Point, prov: object, offset: float = 10.0, orient: str = "h",
                   tier: int = 0, value: Optional[float] = None, prefix: str = "", suffix: str = "",
                   label: Optional[str] = None, dec: int = 1, text_pos: str = "auto", text_dx: float = 0.0,
                   h: float = 3.5, unit: str = "mm", at: Optional[float] = None) -> Record:
        """ISO 129-1 linear dimension between model points ``p1`` and ``p2``.

        Args:
            prov: provenance tag (mandatory).
            offset: paper mm from ``p1`` to the dimension line. ``orient="h"`` measures ``|dx|`` with the line
                ABOVE ``p1`` for ``offset > 0``; ``"v"`` measures ``|dy|`` with the line RIGHT of ``p1``;
                ``"aligned"`` measures the true distance with the line to the left of ``p1 -> p2``.
            tier: stacks the dimension ``tier * 8`` mm further out (chain / baseline dimensioning).
            value: value to print instead of the measured length (e.g. a nominal size on a schematic view).
            prefix, suffix: e.g. ``prefix="Ø"``, ``suffix=" H7"``.
            label: feature name in the records (default: the printed text).
            dec: maximum decimals.
            text_pos: ``"auto"`` (outside if too short), ``"inside"``, ``"out_end"``, ``"out_start"``.
            text_dx: shift of the text along the dimension line [paper mm].
            at: absolute MODEL coordinate of the dimension line (y for ``"h"``, x for ``"v"``); overrides
                ``offset`` (the sign of ``offset`` still gives the tier direction).
        """
        prov = str(prov)
        color = self.sheet.prov_color(prov)
        (A1x, A1y), (A2x, A2y) = self.to_paper(*p1), self.to_paper(*p2)
        off = offset + math.copysign(tier * TIER, offset if offset else 1.0)
        if orient == "h":
            meas = abs(p2[0] - p1[0])
            yd = A1y - off if at is None else self.to_paper(0, at)[1] - math.copysign(tier * TIER, offset or 1.0)
            D1, D2 = (A1x, yd), (A2x, yd)
        elif orient == "v":
            meas = abs(p2[1] - p1[1])
            xd = A1x + off if at is None else self.to_paper(at, 0)[0] + math.copysign(tier * TIER, offset or 1.0)
            D1, D2 = (xd, A1y), (xd, A2y)
        elif orient == "aligned":
            meas = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            L = math.hypot(A2x - A1x, A2y - A1y) or 1.0
            nx, ny = (A2y - A1y) / L, -(A2x - A1x) / L    # left normal on paper
            D1, D2 = (A1x + nx * off, A1y + ny * off), (A2x + nx * off, A2y + ny * off)
        else:
            raise ValueError("orient must be 'h', 'v' or 'aligned'")
        e1, e2 = (A1x, A1y), (A2x, A2y)
        v, txt = self._value(value, meas, prov, prefix, suffix, dec)
        # extension lines: small gap at the object, overshoot past the dimension line
        for (ex, ey), (dx_, dy_) in ((e1, D1), (e2, D2)):
            L = math.hypot(dx_ - ex, dy_ - ey)
            if L > EXT_GAP:
                ux, uy = (dx_ - ex) / L, (dy_ - ey) / L
                self._pl(ex + ux * EXT_GAP, ey + uy * EXT_GAP, dx_ + ux * EXT_OVER, dy_ + uy * EXT_OVER, color)
        # dimension line + arrows
        Ld = math.hypot(D2[0] - D1[0], D2[1] - D1[1]) or 1e-9
        ux, uy = (D2[0] - D1[0]) / Ld, (D2[1] - D1[1]) / Ld
        if ux < -1e-9 or (abs(ux) < 1e-9 and uy > 0):   # run left->right / bottom->top so text reads correctly
            D1, D2, ux, uy = D2, D1, -ux, -uy
        pw = self.sheet.tag_width(prov)
        tw = text_width(txt, h) + pw
        inside = Ld >= tw + 2 * ARROW_L + 2.0
        if text_pos == "inside":
            inside = True
        elif text_pos in ("out_end", "out_start"):
            inside = False
        rot = math.degrees(math.atan2(uy, ux))
        nX, nY = uy, -ux                       # 'above' the line on paper
        if inside:
            self._pl(*D1, *D2, color)
            self._arrow(*D1, -ux, -uy, color)
            self._arrow(*D2, ux, uy, color)
            mx, my = (D1[0] + D2[0]) / 2 + ux * text_dx, (D1[1] + D2[1]) / 2 + uy * text_dx
            tx, ty = mx + nX * 1.0, my + nY * 1.0
            anchor = "middle"
            tx -= ux * pw / 2                  # centre the value + tag group
            ty -= uy * pw / 2
        else:
            ext = ARROW_L + 3.0
            self._pl(D1[0] - ux * ext, D1[1] - uy * ext, D2[0] + ux * ext, D2[1] + uy * ext, color)
            self._arrow(*D1, ux, uy, color)
            self._arrow(*D2, -ux, -uy, color)
            if text_pos == "out_start":
                sx, sy = D1[0] - ux * (ext + 1.0 + tw), D1[1] - uy * (ext + 1.0 + tw)
                self._pl(sx, sy, D1[0] - ux * ext, D1[1] - uy * ext, color)
            else:
                sx, sy = D2[0] + ux * (ext + 1.0), D2[1] + uy * (ext + 1.0)
                self._pl(D2[0] + ux * ext, D2[1] + uy * ext, sx + ux * tw, sy + uy * tw, color)
            sx += ux * text_dx
            sy += uy * text_dx
            tx, ty = sx + nX * 1.0, sy + nY * 1.0
            anchor = "start"
        self._dim_text(tx, ty, txt, prov, h, rot if abs(rot) > 1e-6 else 0.0, anchor, color)
        return self.sheet.record(self.name, "linear", label or txt, v, unit, prov, txt)

    def dim_dia_half(self, x: float, r: float, prov: object, axis_y: float = 0.0, over: float = 6.0,
                     value: Optional[float] = None, label: Optional[str] = None, dec: int = 1, h: float = 3.5,
                     text_at: float = 0.5) -> Record:
        """ISO 129-1 diameter dimension in a half section (horizontal axis at ``axis_y``).

        The dimension line runs at model ``x`` from the feature (``y = axis_y + r``) across the axis by ``over``
        paper mm, with ONE arrowhead at the feature. Value = ``2 r``. ``text_at`` = text position along the line
        (0 = feature, 1 = end past the axis).
        """
        prov = str(prov)
        color = self.sheet.prov_color(prov)
        X, Yf = self.to_paper(x, axis_y + r)
        _, Ya = self.to_paper(x, axis_y)
        sgn = 1.0 if Ya > Yf else -1.0
        Ye = Ya + sgn * over
        self._pl(X, Yf, X, Ye, color)
        self._arrow(X, Yf, 0.0, -sgn, color)
        v, txt = self._value(value, 2 * abs(r), prov, "Ø", "", dec)
        ty = Yf + (Ye - Yf) * text_at
        tw = text_width(txt, h) + self.sheet.tag_width(prov)
        # vertical text reading from the right (rotate -90), placed left of the line
        self._dim_text(X - 1.0, ty + tw / 2, txt, prov, h, -90.0, "start", color)
        return self.sheet.record(self.name, "diameter", label or txt, v, "mm", prov, txt)

    def dim_diameter(self, cx: float, cy: float, r: float, prov: object, ang: float = 30.0,
                     value: Optional[float] = None, label: Optional[str] = None, dec: int = 1,
                     h: float = 3.5) -> Record:
        """Full diameter across a circle at angle ``ang`` [deg]; arrows at both ends, text beyond the upper end."""
        prov = str(prov)
        color = self.sheet.prov_color(prov)
        c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        A = self.to_paper(cx - r * c, cy - r * s_)
        B = self.to_paper(cx + r * c, cy + r * s_)
        L = math.hypot(B[0] - A[0], B[1] - A[1]) or 1e-9
        ux, uy = (B[0] - A[0]) / L, (B[1] - A[1]) / L
        v, txt = self._value(value, 2 * r, prov, "Ø", "", dec)
        tw = text_width(txt, h) + self.sheet.tag_width(prov)
        side = 1 if ux >= 0 else -1
        self._pl(*A, B[0] + ux * 3, B[1] + uy * 3, color)
        self._pl(B[0] + ux * 3, B[1] + uy * 3, B[0] + ux * 3 + (tw + 2) * side, B[1] + uy * 3, color)
        self._arrow(*A, -ux, -uy, color)
        self._arrow(*B, ux, uy, color)
        tx = B[0] + ux * 3 + (1 if side > 0 else -(tw + 1))
        self._dim_text(tx, B[1] + uy * 3 - 1.0, txt, prov, h, 0.0, "start", color)
        return self.sheet.record(self.name, "diameter", label or txt, v, "mm", prov, txt)

    def dim_radius(self, cx: float, cy: float, r: float, prov: object, ang: float = 45.0, prefix: str = "R",
                   value: Optional[float] = None, label: Optional[str] = None, dec: int = 1, h: float = 3.5,
                   shoulder: Optional[float] = None) -> Record:
        """Radius: line from the centre through the arc at ``ang``, arrow on the arc, horizontal shoulder + text.

        ``shoulder`` = shoulder length in paper mm (default: text width + 2).
        """
        prov = str(prov)
        color = self.sheet.prov_color(prov)
        C = self.to_paper(cx, cy)
        A = self.to_paper(cx + r * math.cos(math.radians(ang)), cy + r * math.sin(math.radians(ang)))
        L = math.hypot(A[0] - C[0], A[1] - C[1]) or 1e-9
        ux, uy = (A[0] - C[0]) / L, (A[1] - C[1]) / L
        v, txt = self._value(value, r, prov, prefix, "", dec)
        tw = text_width(txt, h) + self.sheet.tag_width(prov) + 1.0
        sh = shoulder if shoulder is not None else tw + 2.0
        E = (A[0] + ux * 6, A[1] + uy * 6)
        sgn = 1 if ux >= 0 else -1
        self._pl(*C, *E, color)
        self._pl(*E, E[0] + sgn * sh, E[1], color)
        self._arrow(*A, ux, uy, color)
        tx = E[0] + 1.0 if sgn > 0 else E[0] - sh + 1.0
        self._dim_text(tx, E[1] - 1.0, txt, prov, h, 0.0, "start", color)
        return self.sheet.record(self.name, "radius", label or txt, v, "mm", prov, txt)

    def dim_angle(self, cx: float, cy: float, r: float, a0: float, a1: float, prov: object,
                  value: Optional[float] = None, label: Optional[str] = None, dec: int = 0,
                  h: float = 3.5) -> Record:
        """Angular dimension: arc of model radius ``r`` from ``a0`` to ``a1`` [deg], text at mid-angle."""
        prov = str(prov)
        color = self.sheet.prov_color(prov)
        P = [self.to_paper(*p) for p in arc_points(cx, cy, r, a0, a1, 40)]
        self.anno.append('<polyline points="' + " ".join(f"{_f(a)},{_f(b)}" for a, b in P) + '" '
                         + _stroke("thin", color) + "/>")
        for (X, Y), (Xn, Yn) in ((P[0], P[1]), (P[-1], P[-2])):
            L = math.hypot(X - Xn, Y - Yn) or 1.0
            self._arrow(X, Y, (X - Xn) / L, (Y - Yn) / L, color)
        v, txt = self._value(value, abs(a1 - a0), prov, "", "°", dec)
        am = math.radians((a0 + a1) / 2)
        X, Y = self.to_paper(cx + r * math.cos(am), cy + r * math.sin(am))
        X += 2.0 * math.cos(am)
        Y -= 2.0 * math.sin(am)
        self._dim_text(X, Y, txt, prov, h, 0.0, "start" if math.cos(am) >= 0 else "end", color)
        return self.sheet.record(self.name, "angle", label or txt, v, "deg", prov, txt)

    def leader(self, x: float, y: float, text: str, prov: object, dx: float = 10.0, dy: float = -10.0,
               value: Optional[float] = None, label: Optional[str] = None, balloon: Optional[Union[int, str]] = None,
               h: float = 3.5, unit: str = "mm", dot: bool = False,
               to: Optional[Tuple[float, float]] = None) -> Record:
        """Leader (callout) from model point ``(x, y)`` to a paper offset ``(dx, dy)`` -- or to the absolute
        PAPER point ``to`` -- with a horizontal shoulder and text.

        Text runs right if the end is right of the point, else left. ``value`` is only recorded (the text is
        printed as given). ``balloon=n`` draws a numbered balloon instead; ``dot=True`` ends the leader on a dot
        (for surfaces) instead of an arrow.
        """
        prov = str(prov)
        color = self.sheet.prov_color(prov)
        X, Y = self.to_paper(x, y)
        if to is not None:
            dx, dy = to[0] - X, to[1] - Y
        E = (X + dx, Y + dy)
        L = math.hypot(dx, dy) or 1.0
        if dot:
            self.anno.append(f'<circle cx="{_f(X)}" cy="{_f(Y)}" r="0.6" fill="{color}"/>')
        else:
            self._arrow(X, Y, -dx / L, -dy / L, color)
        if balloon is not None:
            R = 4.0
            cxb, cyb = E[0] + R * dx / L, E[1] + R * dy / L
            self._pl(X, Y, *E, color)
            ring = _stroke("thin", color, "#ffffff")
            self.anno.append(f'<circle cx="{_f(cxb)}" cy="{_f(cyb)}" r="{R}" {ring}/>')
            self.sheet.text(cxb, cyb + 1.75, str(balloon), h=3.5, anchor="middle", color=color, out=self.anno)
            if text:
                self.sheet.text(cxb + (R + 1.5) * (1 if dx >= 0 else -1), cyb + 1.2, text, h=2.5, color=color,
                                anchor="start" if dx >= 0 else "end", prov=prov, out=self.anno)
            return self.sheet.record(self.name, "balloon", label or f"({balloon}) {text}".strip(), value, unit,
                                     prov, f"({balloon}) {text}".strip())
        sgn = 1 if dx >= 0 else -1
        tw = text_width(text, h) + self.sheet.tag_width(prov) + 1.0
        self._pl(X, Y, *E, color)
        self._pl(*E, E[0] + sgn * (tw + 1.0), E[1], color)
        tx = E[0] + 0.5 if sgn > 0 else E[0] - tw - 0.5
        self._dim_text(tx, E[1] - 1.0, text, prov, h, 0.0, "start", color)
        if self.sheet.prov_class(prov) == "tbd":
            value = None
        return self.sheet.record(self.name, "callout", label or text, value, unit if value is not None else "",
                                 prov, text)

    def balloon(self, x: float, y: float, n: Union[int, str], prov: object, dx: float = 10.0, dy: float = -10.0,
                text: str = "", to: Optional[Tuple[float, float]] = None, label: Optional[str] = None) -> Record:
        """Numbered item balloon (part reference) with a dot on the part; ``prov`` is mandatory as always."""
        return self.leader(x, y, text, prov, dx, dy, balloon=n, dot=True, to=to,
                           label=f"({n}) {label}" if label else None)
