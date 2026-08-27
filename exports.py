"""
PocketPlot Universe - export module (v23).

Three export formats for a single world:
  1. PDF - book-like layout with cover page + chapters (existing pdf_gen.py
     already does this for one episode; we extend to a full world)
  2. EPUB - standard ebook format, generated from scratch (no library dep)
  3. Bulk ZIP - markdown + SVG per episode + manifest.json

We deliberately avoid third-party EPUB libraries (ebooklib has heavy
deps + license constraints). The EPUB format is well-specified enough
to generate directly.
"""

import io
import json
import zipfile
import datetime as dt
import html
import re
import uuid


def _esc(text: str) -> str:
    """HTML-escape text."""
    return html.escape(text or "")


def _slug(text: str, max_len: int = 60) -> str:
    """Make a URL-safe slug from text."""
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", (text or "").lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s[:max_len] or "world"


# ============== EPUB ==============

def world_to_epub(db, world_id: int, subscriber_email: str = "") -> bytes:
    """Generate a complete .epub file for the world.

    EPUB structure:
      mimetype                  (uncompressed, must be first)
      META-INF/container.xml     (uncompressed, must be second)
      OEBPS/content.opf         (the package manifest)
      OEBPS/toc.ncx              (legacy nav)
      OEBPS/nav.xhtml            (EPUB3 nav)
      OEBPS/title.xhtml          (the cover/title page)
      OEBPS/chapter_NN.xhtml     (one per episode)
      OEBPS/style.css            (styling)
    """
    world = db.execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not world:
        raise ValueError(f"world {world_id} not found")

    title = world['title'] or "Untitled"
    author = subscriber_email or "Anonymous"
    now = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    uuid_str = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_DNS, f'pocketplot-{world_id}-{now}')}"
    episodes = db.execute(
        "SELECT * FROM world_episodes WHERE world_id=? ORDER BY episode_number",
        (world_id,),
    ).fetchall()

    # --- content.opf ---
    manifest_items = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>',
    ]
    spine_items = ['<itemref idref="title"/>', '<itemref idref="nav"/>']
    for i, ep in enumerate(episodes, start=1):
        manifest_items.append(
            f'<item id="ch{i:02d}" href="ch{i:02d}.xhtml" media-type="application/xhtml+xml"/>'
        )
        spine_items.append(f'<itemref idref="ch{i:02d}"/>')
    manifest_items.append('<item id="style" href="style.css" media-type="text/css"/>')

    content_opf = f"""<?xml version='1.0' encoding='utf-8'?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId" xml:lang="en">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="BookId">{uuid_str}</dc:identifier>
    <dc:title>{_esc(title)}</dc:title>
    <dc:creator>{_esc(author)}</dc:creator>
    <dc:language>en</dc:language>
    <dc:date>{now[:10]}</dc:date>
    <meta property="dcterms:modified">{now}</meta>
    <meta name="generator" content="PocketPlot Universe v23"/>
  </metadata>
  <manifest>
    {chr(10).join(manifest_items)}
  </manifest>
  <spine>
    {chr(10).join(spine_items)}
  </spine>
</package>"""

    # --- toc.ncx (legacy) ---
    nav_points = []
    for i, ep in enumerate(episodes, start=1):
        nav_points.append(
            f'<navPoint id="np{i:02d}" playOrder="{i}">'
            f'<navLabel><text>{_esc(ep["title"] or f"Chapter {i}")}</text></navLabel>'
            f'<content src="ch{i:02d}.xhtml"/>'
            '</navPoint>'
        )
    toc_ncx = f"""<?xml version='1.0' encoding='utf-8'?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{uuid_str}"/>
    <meta name="dtb:depth" content="1"/>
  </head>
  <docTitle><text>{_esc(title)}</text></docTitle>
  <navMap>
    {chr(10).join(nav_points)}
  </navMap>
</ncx>"""

    # --- nav.xhtml (EPUB3) ---
    nav_items = []
    for i, ep in enumerate(episodes, start=1):
        nav_items.append(
            f'<li><a href="ch{i:02d}.xhtml">{_esc(ep["title"] or f"Chapter {i}")}</a></li>'
        )
    nav_xhtml = f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head><title>{_esc(title)}</title></head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Contents</h1>
    <ol>{chr(10).join(nav_items)}</ol>
  </nav>
</body>
</html>"""

    # --- title.xhtml ---
    title_xhtml = f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head><title>{_esc(title)}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body class="cover">
  <div class="cover-inner">
    <h1 class="title">{_esc(title)}</h1>
    <p class="meta">by {_esc(author)}</p>
    <p class="meta">PocketPlot Universe · {now[:10]}</p>
  </div>
</body>
</html>"""

    # --- per-chapter xhtml ---
    chapter_files = {}
    for i, ep in enumerate(episodes, start=1):
        body = (ep['body'] or "").replace("\n\n", "</p><p>")
        body = re.sub(r"<", "&lt;", body)
        body = re.sub(r">", "&gt;", body)
        ch_xhtml = f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head><title>{_esc(ep['title'] or f'Chapter {i}')}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body class="chapter">
  <h1 class="chapter-title">{_esc(ep['title'] or f'Chapter {i}')}</h1>
  <p>{body}</p>
</body>
</html>"""
        chapter_files[f"OEBPS/ch{i:02d}.xhtml"] = ch_xhtml.encode('utf-8')

    # --- style.css ---
    style_css = b"""\
@namespace { html
body { font-family: Georgia, serif; line-height: 1.5; margin: 5%; }
h1 { font-family: Georgia, serif; font-size: 1.5em; margin-bottom: 0.5em; }
.cover { text-align: center; padding-top: 30%; }
.cover-inner { max-width: 80%; margin: 0 auto; }
.cover .title { font-size: 2.4em; margin-bottom: 0.3em; }
.cover .meta { font-style: italic; color: #555; }
.chapter-title { text-align: center; font-style: italic; margin-bottom: 1em; }
"""

    # --- container.xml ---
    container_xml = b"""<?xml version='1.0' encoding='utf-8'?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

    # --- assemble the zip ---
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        # mimetype MUST be the first entry and MUST be stored (not deflated)
        z.writestr(zipfile.ZipInfo('mimetype'), b'application/epub+zip',
                   compress_type=zipfile.ZIP_STORED)
        # container.xml MUST be the second entry, also stored
        z.writestr(zipfile.ZipInfo('META-INF/container.xml'), container_xml,
                   compress_type=zipfile.ZIP_STORED)
        # everything else is deflated
        z.writestr('OEBPS/content.opf', content_opf.encode('utf-8'))
        z.writestr('OEBPS/toc.ncx', toc_ncx.encode('utf-8'))
        z.writestr('OEBPS/nav.xhtml', nav_xhtml.encode('utf-8'))
        z.writestr('OEBPS/title.xhtml', title_xhtml.encode('utf-8'))
        z.writestr('OEBPS/style.css', style_css)
        for path, data in chapter_files.items():
            z.writestr(path, data)
    return buf.getvalue()


# ============== Bulk ZIP ==============

def world_to_bulk_zip(db, world_id: int) -> bytes:
    """Generate a bulk ZIP for a world: one markdown file per episode + manifest.json."""
    world = db.execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not world:
        raise ValueError(f"world {world_id} not found")

    episodes = db.execute(
        "SELECT * FROM world_episodes WHERE world_id=? ORDER BY episode_number",
        (world_id,),
    ).fetchall()

    safe = _slug(dict(world).get('title'))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        # Manifest
        wd = dict(world)
        manifest = {
            'world_id': wd.get('id'),
            'title': wd.get('title'),
            'genre': wd.get('genre'),
            'tone': wd.get('tone'),
            'setting': wd.get('setting'),
            'episode_count': len(episodes),
            'exported_at': dt.datetime.utcnow().isoformat() + 'Z',
            'format_version': 'pocketplot-bulk-1.0',
        }
        z.writestr('manifest.json', json.dumps(manifest, indent=2).encode('utf-8'))

        # README
        readme = (
            f"# {wd.get('title') or 'Untitled'}\n\n"
            f"Genre: {wd.get('genre') or 'unknown'}\n"
            f"Tone: {wd.get('tone') or 'unknown'}\n"
            f"Setting: {wd.get('setting') or 'unknown'}\n\n"
            f"Exported from PocketPlot Universe on {dt.datetime.utcnow().strftime('%Y-%m-%d')}.\n\n"
            f"Each chapter is a separate .md file. Import them back into the platform,\n"
            f"or read them with your favorite Markdown editor.\n"
        )
        z.writestr('README.md', readme.encode('utf-8'))

        # One .md per episode
        for i, ep in enumerate(episodes, start=1):
            md = f"# {ep['title'] or f'Chapter {i}'}\n\n"
            md += (ep['body'] or '').replace('\n\n', '\n\n---\n\n')
            md += '\n\n---\n\n*End of Chapter {0}*\n'.format(i)
            fname = '{0:02d}-chapter-{1}.md'.format(i, _slug(ep['title'] or str(i)))
            z.writestr('chapters/' + fname, md.encode('utf-8'))

    return buf.getvalue()


# ============== Per-world PDF (single file) ==============

def world_to_pdf(db, world_id: int) -> bytes:
    """Generate a single PDF for the world: cover page + all episodes as one document."""
    # We reuse pdf_gen.py's primitives if available
    try:
        from pdf_gen import build_pdf  # existing module
    except ImportError:
        raise ImportError("pdf_gen module not available")
    world = db.execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not world:
        raise ValueError(f"world {world_id} not found")
    episodes = db.execute(
        "SELECT * FROM world_episodes WHERE world_id=? ORDER BY episode_number",
        (world_id,),
    ).fetchall()
    # Compose a single story object for the existing build_pdf signature
    story = {
        'title': world['title'] or 'Untitled',
        'genre': world.get('genre') or '',
        'tone': world.get('tone') or '',
        'setting': world.get('setting') or '',
        'character_description': world.get('character_description') or '',
        'primary_objective': world.get('primary_objective') or '',
        'episodes': [
            {'title': ep['title'] or f'Chapter {i}',
             'body': ep['body'] or '',
             'episode_number': i}
            for i, ep in enumerate(episodes, start=1)
        ],
    }
    return build_pdf(story)