"""Demo / self-test sheet that exercises every drawing primitive (``python -m isodraw demo out.svg``)."""

from .sheet import Sheet


def build_demo(show_tags: bool = False) -> Sheet:
    """Build an A3 sheet using every primitive, dimension type and all four provenance classes."""
    sh = Sheet("A3", title="ISODRAW DEMO SHEET", number="DWG-0000", scale="1:1", material="-", mass="-",
               status="DEMO", owner="isodraw example", show_tags=show_tags)
    sh.banner()
    v = sh.view(45, 120, "1:1", label="TEST VIEW", label_xy=(140, 190), name="TEST")
    v.rect(0, 0, 60, 30, hatch=(45, 2.0))
    v.rect(60, 0, 90, 30, hatch=(135, 2.0))
    v.circle(120, 15, 15)
    v.centre_mark(120, 15, 20)
    v.arc(160, 0, 20, 0, 90)
    v.line(0, -12, 90, -12, "hidden")
    v.line(0, -18, 90, -18, "phantom")
    v.centreline(-5, 15, 95, 15)
    v.dim_linear((0, 30), (60, 30), "part drawing", offset=8)
    v.dim_linear((60, 30), (90, 30), "calc:block_width", offset=8)
    v.dim_linear((0, 30), (90, 30), "assume: stock length", offset=8, tier=1)
    v.dim_linear((90, 0), (90, 30), "TBD", offset=10, orient="v")
    v.dim_linear((0, 0), (0, 3), "calc:block_width", offset=-6, orient="v")
    v.dim_diameter(120, 15, 15, "ISO 273")
    v.dim_radius(160, 0, 20, "calc:bend_radius", ang=15)
    v.dim_angle(160, 0, 40, 0, 90, "part drawing")
    v.dim_dia_half(40, 15, "part drawing", axis_y=15)
    v.leader(30, 0, "SOME CALLOUT", "assume: deburr all edges", dx=12, dy=32)
    v.balloon(75, 5, 1, "calc:block_width", dx=34, dy=34, label="test part")
    v.dim_linear((0, 0), (60, 30), "calc:diagonal", offset=-14, orient="aligned", label="aligned test")
    sh.notes(262, 18, 145, ["First note.", "Second note that is long enough to wrap onto a second line of the "
                                            "block so that wrapping is tested."])
    sh.prov_legend(262, 52)
    sh.prov_table(262, 85, 145, max_h=135)
    return sh
