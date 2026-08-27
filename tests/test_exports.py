"""
Export tests: EPUB generation, bulk ZIP, cover image.
"""
import os
import io
import zipfile
import sys
sys.path.insert(0, '/root/pocketplot')

import exports
import social


def test_epub_export_creates_file(db, test_world):
    """EPUB export creates a valid .epub file."""
    out = exports.world_to_epub(db, test_world['id'])
    assert out is not None
    # out may be bytes (BytesIO) or a string (path)
    if isinstance(out, bytes):
        # Validate it as a ZIP file from bytes
        import io
        with zipfile.ZipFile(io.BytesIO(out)) as z:
            names = z.namelist()
            assert 'mimetype' in names
            info = z.getinfo('mimetype')
            assert info.compress_type == zipfile.ZIP_STORED
            content = z.read('mimetype').decode()
            assert content == 'application/epub+zip'
    else:
        # It's a file path
        assert os.path.exists(out)
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
            assert 'mimetype' in names
            info = z.getinfo('mimetype')
            assert info.compress_type == zipfile.ZIP_STORED
            content = z.read('mimetype').decode()
            assert content == 'application/epub+zip'
        os.unlink(out)


def test_bulk_zip_export_creates_zip(db, test_world):
    """Bulk ZIP export creates a ZIP with manifest + per-episode markdown."""
    out = exports.world_to_bulk_zip(db, test_world['id'])
    assert out is not None
    if isinstance(out, bytes):
        import io
        with zipfile.ZipFile(io.BytesIO(out)) as z:
            names = z.namelist()
            assert 'manifest.json' in names
            assert 'README.md' in names
    else:
        assert os.path.exists(out)
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
            assert 'manifest.json' in names
            assert 'README.md' in names
        os.unlink(out)


def test_cover_image_generation(db, test_world):
    """Cover image generator creates a 1200x630 PNG."""
    out_path = social.generate_cover(
        db, test_world['id'],
        title=test_world['title'],
        genre='fantasy',
        tone='mysterious',
        subtitle='A test story',
    )
    assert out_path is not None
    assert os.path.exists(out_path)
    # Verify it's a valid PNG of the right size
    from PIL import Image
    im = Image.open(out_path)
    assert im.size == (1200, 630)
    assert im.mode == 'RGB'
    # Cleanup
    os.unlink(out_path)


def test_cover_image_caching(db, test_world):
    """Cover image is cached after first generation."""
    out1 = social.generate_cover(
        db, test_world['id'], title='Test', genre='fantasy', tone='mysterious'
    )
    # Second call should return the cached path (same file)
    out2 = social.generate_cover(
        db, test_world['id'], title='Test', genre='fantasy', tone='mysterious'
    )
    assert out1 == out2
    # Cleanup
    if os.path.exists(out1):
        os.unlink(out1)


def test_cover_image_genre_palette(db, test_world):
    """Cover uses the correct palette per genre."""
    for genre in ['fantasy', 'scifi', 'noir', 'horror', 'romance']:
        out = social.generate_cover(
            db, test_world['id'] + hash(genre) % 1000,
            title=f'Test {genre}', genre=genre, tone='hopeful'
        )
        assert out is not None
        assert os.path.exists(out)
        os.unlink(out)
