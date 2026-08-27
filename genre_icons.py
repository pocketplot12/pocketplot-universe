"""PocketPlot Universe — 16 genre card icons (v16).

Each genre gets a small SVG icon designed to fit a 64x64 viewBox.
The icons are intentionally stylized (gold on navy) to match the
homepage palette and the rest of the cinematic art direction.
"""


def _genre_icon(genre: str) -> str:
    """Return the SVG markup for a 64x64 genre card icon."""
    # Most icons use the gold gradient via the <defs> at the top of each
    # homepage card grid. We define it inline so the SVG is self-contained.
    g = genre.lower()
    return {
        "cyberpunk": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<rect x="8" y="20" width="22" height="36" stroke="#e6c879" stroke-width="1.6" fill="#15243f"/>'
            '<rect x="34" y="14" width="22" height="42" stroke="#e6c879" stroke-width="1.6" fill="#15243f"/>'
            '<rect x="12" y="26" width="14" height="3" fill="#ff3a8a"/>'
            '<rect x="12" y="32" width="14" height="3" fill="#44f0ff"/>'
            '<rect x="38" y="20" width="14" height="3" fill="#44f0ff"/>'
            '<rect x="38" y="26" width="14" height="3" fill="#ff3a8a"/>'
            '<circle cx="20" cy="48" r="1.6" fill="#e6c879"/>'
            '<circle cx="45" cy="48" r="1.6" fill="#e6c879"/>'
            '<line x1="20" y1="48" x2="45" y2="48" stroke="#e6c879" stroke-width="1.2"/>'
            '</svg>'
        ),
        "romance": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M 32 50 C 12 36 12 18 22 14 C 28 12 32 18 32 22 '
            'C 32 18 36 12 42 14 C 52 18 52 36 32 50 Z" '
            'stroke="#e6c879" stroke-width="1.8" fill="rgba(230,200,121,0.1)"/>'
            '<circle cx="22" cy="22" r="1.6" fill="#e6c879"/>'
            '<circle cx="42" cy="22" r="1.6" fill="#e6c879"/>'
            '</svg>'
        ),
        "action": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M 14 18 L 38 12 L 50 24 L 44 48 L 20 54 L 14 40 Z" '
            'stroke="#e6c879" stroke-width="1.8" fill="#15243f"/>'
            '<path d="M 38 12 L 50 24 L 56 12" stroke="#e6c879" stroke-width="1.4" fill="none"/>'
            '<line x1="14" y1="40" x2="20" y2="54" stroke="#e6c879" stroke-width="1.4"/>'
            '<line x1="44" y1="48" x2="50" y2="54" stroke="#e6c879" stroke-width="1.4"/>'
            '</svg>'
        ),
        "drama": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<circle cx="32" cy="32" r="20" stroke="#e6c879" stroke-width="1.6" fill="rgba(230,200,121,0.05)"/>'
            '<circle cx="32" cy="32" r="6" fill="#e6c879" fill-opacity="0.4"/>'
            '<circle cx="32" cy="32" r="2" fill="#e6c879"/>'
            '<line x1="32" y1="12" x2="32" y2="6" stroke="#e6c879" stroke-width="1.4" stroke-linecap="round"/>'
            '<line x1="32" y1="52" x2="32" y2="58" stroke="#e6c879" stroke-width="1.4" stroke-linecap="round"/>'
            '<line x1="12" y1="32" x2="6" y2="32" stroke="#e6c879" stroke-width="1.4" stroke-linecap="round"/>'
            '<line x1="52" y1="32" x2="58" y2="32" stroke="#e6c879" stroke-width="1.4" stroke-linecap="round"/>'
            '</svg>'
        ),
        "thriller": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M 16 48 L 24 18 L 32 32 L 40 12 L 48 48 Z" '
            'stroke="#e6c879" stroke-width="1.8" fill="#15243f"/>'
            '<circle cx="32" cy="28" r="2.4" fill="#e6c879"/>'
            '<path d="M 32 30 L 28 38" stroke="#e6c879" stroke-width="1.4"/>'
            '<path d="M 32 30 L 36 38" stroke="#e6c879" stroke-width="1.4"/>'
            '</svg>'
        ),
        "fantasy": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M 12 28 L 22 42 L 32 18 L 42 42 L 52 28 L 48 50 L 16 50 Z" '
            'stroke="#e6c879" stroke-width="1.8" fill="rgba(230,200,121,0.15)"/>'
            '<circle cx="12" cy="28" r="2" fill="#e6c879"/>'
            '<circle cx="32" cy="18" r="2.4" fill="#e6c879"/>'
            '<circle cx="52" cy="28" r="2" fill="#e6c879"/>'
            '<rect x="16" y="44" width="32" height="2" fill="#e6c879"/>'
            '</svg>'
        ),
        "comedy": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<circle cx="32" cy="32" r="20" stroke="#e6c879" stroke-width="1.8" fill="rgba(230,200,121,0.08)"/>'
            '<circle cx="25" cy="28" r="1.8" fill="#e6c879"/>'
            '<circle cx="39" cy="28" r="1.8" fill="#e6c879"/>'
            '<path d="M 22 36 Q 32 44 42 36" stroke="#e6c879" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
            '<path d="M 20 18 Q 24 14 28 18" stroke="#e6c879" stroke-width="1.2" fill="none"/>'
            '<path d="M 36 18 Q 40 14 44 18" stroke="#e6c879" stroke-width="1.2" fill="none"/>'
            '</svg>'
        ),
        "scifi": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<circle cx="32" cy="32" r="6" stroke="#e6c879" stroke-width="1.6" fill="rgba(230,200,121,0.15)"/>'
            '<circle cx="32" cy="32" r="14" stroke="#e6c879" stroke-width="1.4" fill="none" stroke-dasharray="2 2"/>'
            '<circle cx="32" cy="32" r="22" stroke="#e6c879" stroke-width="1.2" fill="none" stroke-dasharray="1 3"/>'
            '<circle cx="32" cy="32" r="2" fill="#e6c879"/>'
            '<circle cx="46" cy="32" r="1.6" fill="#44f0ff"/>'
            '<circle cx="18" cy="32" r="1.6" fill="#44f0ff"/>'
            '</svg>'
        ),
        "horror": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<rect x="22" y="14" width="20" height="36" stroke="#e6c879" stroke-width="1.8" fill="#1a0a14" rx="3"/>'
            '<line x1="22" y1="24" x2="42" y2="24" stroke="#e6c879" stroke-width="1.4"/>'
            '<line x1="22" y1="36" x2="42" y2="36" stroke="#e6c879" stroke-width="1.4"/>'
            '<line x1="22" y1="48" x2="42" y2="48" stroke="#e6c879" stroke-width="1.4"/>'
            '<path d="M 30 18 L 30 10 M 34 18 L 34 10" stroke="#e6c879" stroke-width="1.4"/>'
            '<circle cx="27" cy="28" r="1.6" fill="#e6c879"/>'
            '<circle cx="37" cy="28" r="1.6" fill="#e6c879"/>'
            '</svg>'
        ),
        "detective": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<ellipse cx="32" cy="42" rx="22" ry="4" fill="#15243f" stroke="#e6c879" stroke-width="1.4"/>'
            '<circle cx="24" cy="22" r="5" stroke="#e6c879" stroke-width="1.6" fill="none"/>'
            '<line x1="28" y1="26" x2="38" y2="36" stroke="#e6c879" stroke-width="2" stroke-linecap="round"/>'
            '<path d="M 14 42 L 50 42" stroke="#e6c879" stroke-width="1.4"/>'
            '<path d="M 16 38 Q 22 36 26 38 Q 30 40 34 38 Q 38 36 42 38 Q 46 40 50 38" '
            'stroke="#e6c879" stroke-width="1" fill="none" opacity="0.7"/>'
            '</svg>'
        ),
        "fairytales": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M 14 32 L 14 50 L 50 50 L 50 32 L 32 14 Z" '
            'stroke="#e6c879" stroke-width="1.8" fill="rgba(230,200,121,0.15)"/>'
            '<rect x="22" y="38" width="8" height="12" fill="#fff3c4"/>'
            '<rect x="34" y="38" width="8" height="12" fill="#fff3c4"/>'
            '<rect x="30" y="46" width="6" height="4" fill="#1a0a14"/>'
            '<path d="M 18 30 L 22 22 L 26 30" stroke="#e6c879" stroke-width="1.2" fill="none"/>'
            '<path d="M 46 30 L 42 22 L 38 30" stroke="#e6c879" stroke-width="1.2" fill="none"/>'
            '</svg>'
        ),
        "superhero": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M 32 8 L 44 32 L 32 56 L 20 32 Z" '
            'stroke="#e6c879" stroke-width="1.8" fill="rgba(230,200,121,0.2)"/>'
            '<path d="M 32 8 L 32 56" stroke="#e6c879" stroke-width="1.4"/>'
            '<path d="M 20 32 L 44 32" stroke="#e6c879" stroke-width="1.4"/>'
            '<circle cx="32" cy="8" r="2" fill="#e6c879"/>'
            '<circle cx="32" cy="56" r="2" fill="#e6c879"/>'
            '<circle cx="20" cy="32" r="2" fill="#e6c879"/>'
            '<circle cx="44" cy="32" r="2" fill="#e6c879"/>'
            '</svg>'
        ),
        "chicklit": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns://www.w3.org/2000/svg">'
            '<rect x="14" y="14" width="36" height="36" stroke="#e6c879" stroke-width="1.6" fill="rgba(230,200,121,0.1)"/>'
            '<path d="M 14 14 L 50 50 M 50 14 L 14 50" stroke="#e6c879" stroke-width="1.2" opacity="0.6"/>'
            '<circle cx="32" cy="32" r="10" stroke="#e6c879" stroke-width="1.6" fill="none"/>'
            '<text x="32" y="36" font-family="Fraunces, Georgia, serif" font-style="italic" '
            'font-size="14" font-weight="700" fill="#e6c879" text-anchor="middle">&#9829;</text>'
            '</svg>'
        ),
        "adventure": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M 14 50 L 28 18 L 36 26 L 44 14 L 50 50 Z" '
            'stroke="#e6c879" stroke-width="1.8" fill="rgba(230,200,121,0.15)"/>'
            '<line x1="28" y1="18" x2="44" y2="14" stroke="#e6c879" stroke-width="1.2"/>'
            '<path d="M 18 50 L 22 36 L 30 32" stroke="#e6c879" stroke-width="1.2" fill="none"/>'
            '<circle cx="44" cy="14" r="2.4" fill="#e6c879"/>'
            '</svg>'
        ),
        "roleplaying": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<polygon points="32,8 56,22 56,42 32,56 8,42 8,22" '
            'stroke="#e6c879" stroke-width="1.8" fill="rgba(230,200,121,0.1)"/>'
            '<text x="32" y="38" font-family="monospace" font-size="16" font-weight="700" '
            'fill="#e6c879" text-anchor="middle">20</text>'
            '<circle cx="32" cy="8" r="1.6" fill="#e6c879"/>'
            '<circle cx="56" cy="22" r="1.6" fill="#e6c879"/>'
            '<circle cx="56" cy="42" r="1.6" fill="#e6c879"/>'
            '<circle cx="32" cy="56" r="1.6" fill="#e6c879"/>'
            '<circle cx="8" cy="42" r="1.6" fill="#e6c879"/>'
            '<circle cx="8" cy="22" r="1.6" fill="#e6c879"/>'
            '</svg>'
        ),
        "historical": (
            '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<rect x="20" y="20" width="24" height="32" stroke="#e6c879" stroke-width="1.6" fill="#1a0a14"/>'
            '<rect x="24" y="24" width="3" height="3" fill="#e6c879"/>'
            '<rect x="29" y="24" width="3" height="3" fill="#e6c879"/>'
            '<rect x="34" y="24" width="3" height="3" fill="#e6c879"/>'
            '<rect x="39" y="24" width="3" height="3" fill="#e6c879"/>'
            '<rect x="24" y="30" width="3" height="3" fill="#e6c879"/>'
            '<rect x="29" y="30" width="3" height="3" fill="#e6c879"/>'
            '<rect x="34" y="30" width="3" height="3" fill="#e6c879"/>'
            '<rect x="39" y="30" width="3" height="3" fill="#e6c879"/>'
            '<rect x="24" y="36" width="3" height="3" fill="#e6c879"/>'
            '<rect x="29" y="36" width="3" height="3" fill="#e6c879"/>'
            '<rect x="34" y="36" width="3" height="3" fill="#e6c879"/>'
            '<rect x="39" y="36" width="3" height="3" fill="#e6c879"/>'
            '<rect x="14" y="52" width="36" height="4" fill="#e6c879"/>'
            '<rect x="14" y="14" width="36" height="4" fill="#e6c879"/>'
            '</svg>'
        ),
    }.get(g, (
        '<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<circle cx="32" cy="32" r="20" stroke="#e6c879" stroke-width="1.6" fill="none"/>'
        '</svg>'
    ))


def render_genre_card(genre: str, label: str) -> str:
    """Return the full HTML for one genre card (icon + label)."""
    icon = _genre_icon(genre)
    return (
        '<a class="genre-card" href="/signup?genre=' + genre + '">'
        + icon
        + '<div class="genre-label">' + label + '</div>'
        + '</a>'
    )


def render_genre_grid() -> str:
    """Return the full HTML for the 16-card genre grid."""
    from story_image_composer import GENRES_V16, GENRE_LABELS
    return (
        '<div class="genre-grid">'
        + "".join(render_genre_card(g, GENRE_LABELS[g]) for g in GENRES_V16)
        + '</div>'
    )
