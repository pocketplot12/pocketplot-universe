"""
PocketPlot — Minimal PDF generator (Phase 10).

Zero-dependency PDF writer. Supports:
  - Pages of any size (default US Letter)
  - Text (single font, 5 built-in sizes)
  - SVG embedding (as inline raster via the simplest possible approach:
    we DRAW the SVGs as PDF vector primitives — rectangles, paths, lines —
    by parsing a small subset of SVG attributes we know about)

This is NOT a general-purpose PDF library. It only handles the two
specific outputs PocketPlot needs: a 4-page coloring pack (vector
silhouettes) and a 1-page weekly planner (text + lines). Hand-coded for
those use cases because no PDF library is installed in the container.

PDF structure produced:
  - Header: %PDF-1.4
  - Body: catalog, page tree, font resource, content streams
  - Cross-reference table + trailer
"""
import io
import re
import zlib
from typing import List


# ---- Low-level PDF primitives ----

class PDFBuilder:
    """Build a minimal PDF. Tracks objects, generates xref table."""
    def __init__(self):
        self.objects: List[bytes] = []
        # Reserve slot 0 (always the free object)
        self.objects.append(b"")
        # Slot 1: Catalog (placeholder; we rewrite later)
        self.objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        # Slot 2: Page tree (placeholder)
        self.objects.append(b"<< /Type /Pages /Kids [] /Count 0 >>")
        self.pages_kids: List[int] = []
        self.font_resource_obj = 5  # Will fill in below

    def alloc(self, body: bytes) -> int:
        self.objects.append(body)
        return len(self.objects) - 1

    def add_page(self, width_pt: float, height_pt: float, content_obj: int) -> int:
        page_obj_idx = self.alloc(
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {width_pt:.0f} {height_pt:.0f}] "
            f"/Resources << /Font << /F1 {self.font_resource_obj} 0 R >> >> "
            f"/Contents {content_obj} 0 R >>".encode()
        )
        self.pages_kids.append(page_obj_idx)
        return page_obj_idx

    def set_page_count(self):
        # Patch slot 2 with the actual list of page objects
        kids = " ".join(f"{k} 0 R" for k in self.pages_kids)
        self.objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(self.pages_kids)} >>".encode()

    def render(self) -> bytes:
        self.set_page_count()
        out = io.BytesIO()
        out.write(b"%PDF-1.4\n")
        offsets = [0]
        for i in range(1, len(self.objects)):
            offsets.append(out.tell())
            out.write(f"{i} 0 obj\n".encode())
            body = self.objects[i]
            out.write(body)
            if not body.endswith(b"\n"):
                out.write(b"\n")
            out.write(b"endobj\n")
        xref_offset = out.tell()
        out.write(f"xref\n0 {len(self.objects)}\n".encode())
        out.write(b"0000000000 65535 f \n")
        for i in range(1, len(self.objects)):
            out.write(f"{offsets[i]:010d} 00000 n \n".encode())
        out.write(f"trailer\n<< /Size {len(self.objects)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode())
        return out.getvalue()


def _escape_pdf_string(s: str) -> str:
    """Escape characters that have special meaning inside a PDF string."""
    return (s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)"))


# ---- Text drawing ----

# A minimal PDF content stream with our text/font set up.
def _text_stream(width_pt: float, height_pt: float, ops: List[str]) -> bytes:
    """ops: list of strings like 'BT /F1 18 Tf 50 700 Td (Hello) Tj ET'"""
    body = "\n".join(ops)
    return body.encode("latin-1", errors="replace")


def _text_block(text: str, x: float, y: float, size: int = 12,
                font: str = "F1") -> str:
    """One line of text at (x, y) — uses Helvetica (built-in PDF font F1)."""
    return f"BT /{font} {size} Tf {x:.1f} {y:.1f} Td ({_escape_pdf_string(text)}) Tj ET"


def _line(x1: float, y1: float, x2: float, y2: float,
          width: float = 0.5, color: tuple = (0, 0, 0)) -> str:
    r, g, b = color
    return (f"{r:.2f} {g:.2f} {b:.2f} rg "
            f"{width} w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S")


def _rect(x: float, y: float, w: float, h: float,
          fill: tuple | None = None, stroke: tuple | None = (0, 0, 0),
          stroke_width: float = 0.5) -> str:
    parts = []
    if fill is not None:
        r, g, b = fill
        parts.append(f"{r:.2f} {g:.2f} {b:.2f} rg")
    else:
        parts.append("n")  # no fill
    if stroke is not None:
        r, g, b = stroke
        parts.append(f"{r:.2f} {g:.2f} {b:.2f} RG")
        parts.append(f"{stroke_width} w")
    parts.append(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re")
    if fill is not None:
        parts.append("f")
    if stroke is not None:
        parts.append("S")
    return " ".join(parts)


def _circle(cx: float, cy: float, r: float, fill: tuple | None = None,
            stroke: tuple | None = (0, 0, 0), stroke_width: float = 0.5) -> str:
    parts = []
    if fill is not None:
        r_, g_, b_ = fill
        parts.append(f"{r_:.2f} {g_:.2f} {b_:.2f} rg")
    if stroke is not None:
        r_, g_, b_ = stroke
        parts.append(f"{r_:.2f} {g_:.2f} {b_:.2f} RG")
        parts.append(f"{stroke_width} w")
    parts.append(f"{cx:.1f} {cy:.1f} {r:.1f} 0 360 arc")
    if fill is not None:
        parts.append("f")
    if stroke is not None:
        parts.append("S")
    return " ".join(parts)


# ---- SVG-to-PDF-vector primitive translator ----
# We support a small subset of SVG that covers the avatars + story
# characters + scenery shapes: <g transform="...">, <rect>, <circle>,
# <ellipse>, <line>, <path> with M/L/Z. Enough for the coloring pack.

_SVG_TAG_RE = re.compile(
    r'<(rect|circle|ellipse|line|path)\b([^/>]*)(/>|>(.*?)</\1>)',
    re.DOTALL,
)
_ATTR_RE = re.compile(r'(\w[\w:-]*)\s*=\s*"([^"]*)"')


def _parse_attrs(tag_attrs: str) -> dict:
    """Parse an attribute string into a dict, coercing numbers."""
    out = {}
    for m in _ATTR_RE.finditer(tag_attrs):
        k, v = m.group(1), m.group(2)
        # Try to coerce numeric attrs (everything else stays a string)
        try:
            if k in ("x", "y", "cx", "cy", "rx", "ry", "r", "x1", "y1", "x2", "y2",
                     "width", "height", "stroke-width", "fill-opacity"):
                out[k] = float(v)
                continue
        except Exception:
            pass
        out[k] = v
    return out


def _hex_to_rgb01(c: str) -> tuple:
    c = c.strip()
    if c.startswith("#"):
        c = c[1:]
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        if len(c) == 6:
            try:
                return (int(c[0:2], 16) / 255, int(c[2:4], 16) / 255, int(c[4:6], 16) / 255)
            except ValueError:
                return (0, 0, 0)
    if c == "white":
        return (1, 1, 1)
    if c == "black":
        return (0, 0, 0)
    return (0, 0, 0)


def _collect_translate(transform_str: str) -> tuple:
    """Crude transform parser — we only support translate(x,y) and scale(s).
    Returns (tx, ty, scale_x, scale_y)."""
    tx = ty = 0.0
    sx = sy = 1.0
    m = re.search(r"translate\(([^)]+)\)", transform_str)
    if m:
        parts = [float(x) for x in re.split(r"[\s,]+", m.group(1).strip()) if x]
        if len(parts) >= 1: tx = parts[0]
        if len(parts) >= 2: ty = parts[1]
    m = re.search(r"scale\(([^)]+)\)", transform_str)
    if m:
        parts = [float(x) for x in re.split(r"[\s,]+", m.group(1).strip()) if x]
        if len(parts) >= 1: sx = parts[0]
        if len(parts) >= 2: sy = parts[1]
    return tx, ty, sx, sy


def svg_fragment_to_pdf_ops(svg_fragment: str, tx: float = 0, ty: float = 0,
                             sx: float = 1, sy: float = 1,
                             outline_only: bool = False) -> List[str]:
    """Translate a small SVG fragment into PDF drawing operators.

    outline_only=True drops fills (used for the coloring pack — children
    fill them in themselves with crayons)."""
    ops = []
    for m in _SVG_TAG_RE.finditer(svg_fragment):
        tag = m.group(1)
        attrs = _parse_attrs(m.group(2))
        # Accumulate child transforms if present (we flatten for simplicity).
        # Each tag is drawn relative to the parent's origin; we don't
        # recurse into nested <g>'s here, but we DO honor the parent's
        # transform because the caller passes the cumulative tx/ty/sx/sy.
        if tag == "rect":
            x = (attrs.get("x", 0) or 0) * sx + tx
            y = (attrs.get("y", 0) or 0) * sy + ty
            w = (attrs.get("width", 0) or 0) * sx
            h = (attrs.get("height", 0) or 0) * sy
            fill = None if outline_only else _hex_to_rgb01(attrs.get("fill", "#1a241d"))
            stroke = _hex_to_rgb01(attrs.get("stroke", "#1a241d"))
            sw = attrs.get("stroke-width", 1.5)
            ops.append(_rect(x, y, w, h, fill=fill, stroke=stroke, stroke_width=sw))
        elif tag == "circle":
            cx = (attrs.get("cx", 0) or 0) * sx + tx
            cy = (attrs.get("cy", 0) or 0) * sy + ty
            r = (attrs.get("r", 0) or 0) * max(sx, sy)
            fill = None if outline_only else _hex_to_rgb01(attrs.get("fill", "#1a241d"))
            stroke = _hex_to_rgb01(attrs.get("stroke", "#1a241d"))
            sw = attrs.get("stroke-width", 1.5)
            ops.append(_circle(cx, cy, r, fill=fill, stroke=stroke, stroke_width=sw))
        elif tag == "ellipse":
            cx = (attrs.get("cx", 0) or 0) * sx + tx
            cy = (attrs.get("cy", 0) or 0) * sy + ty
            rx = (attrs.get("rx", 0) or 0) * sx
            ry = (attrs.get("ry", 0) or 0) * sy
            fill = None if outline_only else _hex_to_rgb01(attrs.get("fill", "#1a241d"))
            stroke = _hex_to_rgb01(attrs.get("stroke", "#1a241d"))
            sw = attrs.get("stroke-width", 1.5)
            ops.append(f"{fill[0]:.2f} {fill[1]:.2f} {fill[2]:.2f} rg "
                       if fill else "n")
            ops.append(f"{stroke[0]:.2f} {stroke[1]:.2f} {stroke[2]:.2f} RG")
            ops.append(f"{sw} w")
            ops.append(f"{cx:.1f} {cy:.1f} {rx:.1f} {ry:.1f} re")
            if fill:
                ops.append("f")
            ops.append("S")
        elif tag == "line":
            x1 = (attrs.get("x1", 0) or 0) * sx + tx
            y1 = (attrs.get("y1", 0) or 0) * sy + ty
            x2 = (attrs.get("x2", 0) or 0) * sx + tx
            y2 = (attrs.get("y2", 0) or 0) * sy + ty
            stroke = _hex_to_rgb01(attrs.get("stroke", "#1a241d"))
            sw = attrs.get("stroke-width", 1.5)
            ops.append(_line(x1, y1, x2, y2, sw, stroke))
        elif tag == "path":
            d = attrs.get("d", "")
            stroke = _hex_to_rgb01(attrs.get("stroke", "#1a241d"))
            sw = attrs.get("stroke-width", 1.5)
            ops.append(f"{stroke[0]:.2f} {stroke[1]:.2f} {stroke[2]:.2f} RG")
            ops.append(f"{sw} w")
            # Tiny d="..." parser: M x y / L x y / Z only.
            tokens = re.findall(r"[MLZ]|-?\d+\.?\d*", d)
            i = 0
            path_ops = []
            while i < len(tokens):
                t = tokens[i]
                if t == "M" or t == "L":
                    x = float(tokens[i+1]) * sx + tx
                    y = float(tokens[i+2]) * sy + ty
                    if t == "M":
                        path_ops.append(f"{x:.1f} {y:.1f} m")
                    else:
                        path_ops.append(f"{x:.1f} {y:.1f} l")
                    i += 3
                elif t == "Z" or t == "z":
                    path_ops.append("h")  # close path back to start
                    i += 1
                else:
                    i += 1
            if path_ops:
                ops.append(" ".join(path_ops))
                ops.append("S")
    return ops


def svg_to_pdf_page(svg_fragment: str, page_width: float = 612,
                     page_height: float = 792) -> bytes:
    """Build a one-page PDF that draws the given SVG fragment centered.

    Useful for "convert an SVG into a printable PDF" — used by the
    coloring pack (one PDF, one SVG character per page).
    """
    pdf = PDFBuilder()
    pdf.font_resource_obj = pdf.alloc(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    )

    # The SVG renders into a 400x400 viewBox; we scale it to fit the page.
    svg_size = 400
    target = min(page_width - 80, page_height - 80)
    scale = target / svg_size
    # Center it on the page
    offset_x = (page_width - svg_size * scale) / 2
    offset_y = (page_height - svg_size * scale) / 2

    ops = svg_fragment_to_pdf_ops(
        svg_fragment, tx=offset_x, ty=offset_y, sx=scale, sy=scale,
        outline_only=True,
    )
    body = _text_stream(page_width, page_height, ops)
    content_obj = pdf.alloc(
        f"<< /Length {len(body)} >>\nstream\n".encode() +
        body + b"\nendstream"
    )
    pdf.add_page(page_width, page_height, content_obj)
    return pdf.render()


# ---- Higher-level: the two PDFs PocketPlot ships ----

def build_coloring_pack(svg_fragments: list) -> bytes:
    """One PDF, one character per page. svg_fragments is a list of
    <g>-or-<svg> SVG fragments that draw the silhouette."""
    pdf = PDFBuilder()
    pdf.font_resource_obj = pdf.alloc(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    )
    page_w, page_h = 612, 792  # US Letter
    for idx, svg in enumerate(svg_fragments):
        # Page header
        header_ops = [
            "q",
            _text_block(f"PocketPlot Coloring Pack", 200, 740, 18),
            _text_block(f"Page {idx + 1} of {len(svg_fragments)}", 240, 720, 12,
                        font="F1"),
            "Q",
            "",
        ]
        svg_size = 400
        target = min(page_w - 80, page_h - 200)
        scale = target / svg_size
        ox = (page_w - svg_size * scale) / 2
        oy = 60  # leave room for the header
        svg_ops = svg_fragment_to_pdf_ops(
            svg, tx=ox, ty=oy, sx=scale, sy=scale, outline_only=True,
        )
        ops = header_ops + svg_ops
        body = _text_stream(page_w, page_h, ops)
        content_obj = pdf.alloc(
            f"<< /Length {len(body)} >>\nstream\n".encode() +
            body + b"\nendstream"
        )
        pdf.add_page(page_w, page_h, content_obj)
    return pdf.render()


def build_weekly_planner(child_name: str) -> bytes:
    """A printable one-week planner with the child's name at the top, and
    a daily tracker for word, story, and streak. One page."""
    pdf = PDFBuilder()
    pdf.font_resource_obj = pdf.alloc(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    )
    page_w, page_h = 612, 792

    ops = []
    # Header
    ops.append(_text_block(f"{child_name}'s PocketPlot Week", 180, 740, 22))
    ops.append(_text_block("Trace, color, or write each day.", 200, 715, 12))
    ops.append("")
    # 7 rows: Mon-Sun
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    row_top = 660
    row_height = 78
    for i, day in enumerate(days):
        y = row_top - i * row_height
        # Day label
        ops.append(_text_block(day, 50, y, 16))
        # Three columns: Word of the Day, Story read?, Streak day
        ops.append(_line(180, y - 18, 180, y + 8, 0.3))  # vertical separator
        ops.append(_line(350, y - 18, 350, y + 8, 0.3))
        ops.append(_text_block("Word:", 190, y, 11))
        ops.append(_text_block("Story read:", 360, y, 11))
        # Underline for the child to write on
        ops.append(_line(225, y - 5, 340, y - 5, 0.5))
        ops.append(_line(420, y - 5, 540, y - 5, 0.5))
        # Bottom row separator
        ops.append(_line(50, y - 22, 560, y - 22, 0.3))

    # Footer
    ops.append("")
    ops.append(_text_block("Each small night is a sentence in a longer story. — PocketPlot",
                           50, 60, 10))

    body = _text_stream(page_w, page_h, ops)
    content_obj = pdf.alloc(
        f"<< /Length {len(body)} >>\nstream\n".encode() +
        body + b"\nendstream"
    )
    pdf.add_page(page_w, page_h, content_obj)
    return pdf.render()
