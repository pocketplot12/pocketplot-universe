"""
PocketPlot Universe - v29 theme system.

CSS-only. Sets up two Kindle-e-ink-style themes (warm dark default, warm
light toggle) that override the v27 color tokens via [data-theme=...].

The system:

  1. Sets data-theme="warm-dark" on <html> immediately (before render)
     to avoid FOUC (flash of unstyled content)
  2. Reads localStorage for the user's choice (instant)
  3. Falls back to system preference (prefers-color-scheme: dark/light)
  4. Exposes window.pocketplot.setTheme() for any button to call
"""

# Inject at the START of <head> in index.html
# This script runs synchronously before <body> renders — sets data-theme
# on <html> so the right CSS variables apply at first paint.

THEME_BOOT = '''<script>
(function() {
  const STORAGE_KEY = 'pocketplot-theme';
  // Valid themes
  const THEMES = ['warm-dark', 'warm-light'];
  const DEFAULT_THEME = 'warm-dark';
  try {
    let theme = localStorage.getItem(STORAGE_KEY);
    if (!theme || !THEMES.includes(theme)) {
      // Detect system preference
      const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
      theme = prefersLight ? 'warm-light' : DEFAULT_THEME;
      localStorage.setItem(STORAGE_KEY, theme);
    }
    document.documentElement.setAttribute('data-theme', theme);
    // Also expose theme on a CSS class for legacy support (if anyone uses it)
    document.documentElement.classList.add('theme-' + theme);
  } catch (e) {
    // localStorage might fail (private mode, etc) — fallback to default
    document.documentElement.setAttribute('data-theme', DEFAULT_THEME);
  }
})();
</script>'''


# CSS for both themes. Use a CSS custom property cascade so existing
# tokens stay backwards compatible while adding semantic ones.

THEME_STYLES = '''
/* ============================================================
   THEME TOKENS - v29: Kindle-e-ink warm themes
   Each semantic variable gets values for BOTH themes.
   ============================================================ */
:root {
  /* Defaults = warm-dark (the "default" Apple-restrained look) */
  --bg:            #0a0f1c;        /* page background */
  --bg-elevated:   #15243f;        /* card background */
  --bg-overlay:    rgba(15, 26, 46, 0.78);  /* nav backdrop blur */
  --surface:       #1f3460;        /* hover states, secondary surfaces */
  --border:        rgba(201, 160, 78, 0.14);  /* hairline */
  --border-strong: rgba(201, 160, 78, 0.45);

  --ink:           #f5ecd6;        /* primary text — warm cream */
  --ink-soft:      #d8cba8;        /* body text — slight fade */
  --ink-muted:     #9eb6d4;        /* tertiary text */
  --ink-faint:     #6c7891;        /* footer, hints */

  --accent:        #c9a04e;        /* brass */
  --accent-light:  #e8c879;        /* lighter brass */
  --accent-deep:   #8a6a26;        /* deeper brass */
  --accent-warm:   #f0b54a;        /* amber — secondary accent */

  --button-text:   #1a1410;        /* dark text on brass buttons */

  --shadow:        0 4px 12px rgba(0, 0, 0, 0.45);
  --shadow-lg:     0 14px 32px rgba(0, 0, 0, 0.55);

  --hero-gradient:
    radial-gradient(ellipse 40% 50% at 25% 40%, rgba(93,222,240,0.05), transparent 60%),
    radial-gradient(ellipse 40% 50% at 75% 60%, rgba(240,181,74,0.05), transparent 60%),
    var(--bg);
}

/* WARM-LIGHT theme = Kindle paper / e-ink look
   Warm cream background (not white) + warm dark brown text (not black)
   Easier on the eyes for long reading than pure white */
html[data-theme="warm-light"] {
  --bg:            #f4ecd8;        /* warm cream — like a paperback page */
  --bg-elevated:   #faf3e0;        /* lighter cream for cards */
  --bg-overlay:    rgba(244, 236, 216, 0.85);
  --surface:       #ebe0c8;        /* hover state — slightly deeper cream */
  --border:        rgba(122, 98, 56, 0.18);  /* warm brown hairline */
  --border-strong: rgba(122, 98, 56, 0.55);

  --ink:           #3d2e1f;        /* warm dark brown — like book ink */
  --ink-soft:      #6b5840;        /* softer brown for body */
  --ink-muted:     #8b7558;        /* tertiary text — like aged paper */
  --ink-faint:     #a89579;        /* footer, hints */

  --accent:        #b8842a;        /* brass — slightly warmer/darker for cream */
  --accent-light:  #d4a04d;        /* lighter brass */
  --accent-deep:   #7a5518;
  --accent-warm:   #c89030;        /* amber */

  --button-text:   #fef9ec;        /* light text on brass buttons (inverted for cream bg) */
  /* Better: dark text on warm brass button for cream theme */

  --shadow:        0 1px 3px rgba(60, 40, 15, 0.10), 0 4px 10px rgba(60, 40, 15, 0.06);
  --shadow-lg:     0 4px 12px rgba(60, 40, 15, 0.18), 0 14px 28px rgba(60, 40, 15, 0.12);

  --hero-gradient:
    radial-gradient(ellipse 40% 50% at 25% 40%, rgba(184, 132, 42, 0.04), transparent 60%),
    radial-gradient(ellipse 40% 50% at 75% 60%, rgba(184, 132, 42, 0.04), transparent 60%),
    var(--bg);
}

/* Override button text for warm-light theme — keep dark text on brass */
html[data-theme="warm-light"] .cta-primary,
html[data-theme="warm-light"] button.btn-primary,
html[data-theme="warm-light"] .tier.featured .btn {
  color: #1a1410;  /* dark text on brass */
}
'''


# Toggle JS — place anywhere; idempotent. Returns the new theme name.
TOGGLE_JS = '''<script>
window.pocketplot = window.pocketplot || {};
window.pocketplot.setTheme = function(theme) {
  if (!['warm-dark', 'warm-light'].includes(theme)) {
    theme = 'warm-dark';
  }
  document.documentElement.setAttribute('data-theme', theme);
  try {
    localStorage.setItem('pocketplot-theme', theme);
  } catch (e) {}
  // Notify any iframe-style listeners (none yet, but future-proof)
  document.dispatchEvent(new CustomEvent('themechange', { detail: { theme: theme }}));
  // Sync to server if logged in (best-effort, fails silently if not)
  try {
    fetch('/api/theme', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theme: theme }),
      credentials: 'same-origin',
    }).catch(function() {});
  } catch (e) {}
  return theme;
};
window.pocketplot.toggleTheme = function() {
  const current = document.documentElement.getAttribute('data-theme') || 'warm-dark';
  const next = current === 'warm-dark' ? 'warm-light' : 'warm-dark';
  return window.pocketplot.setTheme(next);
};
window.pocketplot.getTheme = function() {
  return document.documentElement.getAttribute('data-theme') || 'warm-dark';
};
</script>'''


if __name__ == '__main__':
    print('Theme module - import functions in your page generator')
    print()
    print('THEME_BOOT = head-injected script (sets theme before first paint)')
    print('THEME_STYLES = CSS to append to <style>')
    print('TOGGLE_JS = button handler (window.pocketplot.setTheme / toggleTheme)')
