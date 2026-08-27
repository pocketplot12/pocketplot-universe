"""
PocketPlot Universe - QR code generator (v23).

Pure-Python QR code generator using the 'qrcode' library.

We use qrcode + qrcode.image.svg.SvgPathImage for SVG output
because SVG QR codes are crisp at any size, don't require a
raster library, and embed cleanly in HTML / SVG documents.

The QR code for a story links to /play/<share_token> - the
game-format player. Scanning the QR on mobile opens the story
in the same format, no app required.
"""

try:
    import qrcode
    from qrcode.image.svg import SvgPathImage
except ImportError:
    qrcode = None
    SvgPathImage = None


def qr_svg(url: str, box_size: int = 8, border: int = 2) -> str:
    """Generate an SVG QR code that encodes `url`.

    Returns the full <svg>...</svg> string, suitable for embedding
    in HTML pages or saving as a standalone .svg file.
    """
    if qrcode is None:
        # Library not installed - return a placeholder so the page still renders.
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            f'<rect width="100" height="100" fill="#f3e9d2"/>'
            f'<text x="50" y="50" text-anchor="middle" font-family="sans-serif" '
            f'font-size="8" fill="#5a2010">QR library missing</text>'
            f'</svg>'
        )
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(image_factory=SvgPathImage)
    # img is a PIL-like Image; .to_string() returns bytes for SVG
    if hasattr(img, 'to_string'):
        return img.to_string().decode('utf-8')
    # Fallback for older versions
    import io
    buf = io.BytesIO()
    img.save(buf, format='SVG')
    return buf.getvalue().decode('utf-8')


def qr_png_data_url(url: str, box_size: int = 8, border: int = 2) -> str:
    """Generate a PNG QR code as a base64 data URL.

    Useful when you need to embed the QR in an <img> tag or email body.
    """
    if qrcode is None:
        # 1x1 transparent gif as fallback
        return (
            'data:image/png;base64,'
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
        )
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    import base64, io
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return f'data:image/png;base64,{b64}'


# ---- Share token data model ----
# A share token is a short, URL-safe identifier that maps to a world.
# When someone hits /play/<token>, we look up the world and show the
# player UI. Tokens are public (no auth required to play) but the
# creator can revoke them. Tokens also have a 'kind' so we can
# differentiate 'game' (playable) vs 'preview' (read-only).

import secrets
import string

_TOKEN_ALPHABET = string.ascii_lowercase + string.digits  # base36, URL-safe


def make_share_token(length: int = 10) -> str:
    """Generate a URL-safe share token."""
    return ''.join(secrets.choice(_TOKEN_ALPHABET) for _ in range(length))


# ---- Player-session cookie (for the no-account play experience) ----
# When someone plays a story without an account, we set a cookie
# that tracks their choices within that game session. The cookie
# is keyed by share_token + a random session id.

def make_player_session_id() -> str:
    """Generate a session id for an anonymous player."""
    return secrets.token_urlsafe(16)