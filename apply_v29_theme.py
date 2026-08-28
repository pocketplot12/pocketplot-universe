"""
PocketPlot Universe - v29 theme applier.

Idempotent. Injects the Kindle-e-ink theme system into HTML pages:

  1. THEME_BOOT script at top of <head> (sets data-theme before paint)
  2. THEME_STYLES appended to existing <style> blocks
  3. TOGGLE_JS appended before </body>
  4. Theme toggle button added to the existing nav (sun/moon icon)

Run:
  cd /root/pocketplot
  python3 apply_v29_theme.py
"""
import re
import sys
from pathlib import Path

# Import the theme module so we can read its constants
sys.path.insert(0, str(Path(__file__).parent))
import theme_v29 as t


PAGES = ['index.html', 'pricing.html', 'faq.html', 'terms.html',
         'how-it-works.html', '404.html', '500.html',
         'signup.html', 'signup-pro.html']


# Toggle button (sun/moon SVG icons + click handler)
TOGGLE_BUTTON_HTML = '''<button type="button" class="theme-toggle" id="theme-toggle-btn" aria-label="Toggle reading theme" title="Toggle theme (Kindle light / warm dark)">
  <svg class="icon-sun" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.6"/>
    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  </svg>
  <svg class="icon-moon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</button>
<script>
  document.getElementById('theme-toggle-btn').addEventListener('click', function() {
    window.pocketplot.toggleTheme();
  });
</script>'''


# Toggle button CSS — uses CSS vars + shows the right icon per theme
TOGGLE_BUTTON_CSS = '''
/* Theme toggle button — visible on both themes */
.theme-toggle {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--ink-soft);
  transition: color 200ms, border-color 200ms, background 200ms;
  padding: 0;
  flex-shrink: 0;
}
.theme-toggle:hover {
  border-color: var(--border-strong);
  color: var(--accent-light);
  background: rgba(201, 160, 78, 0.06);
}
.theme-toggle svg {
  width: 18px;
  height: 18px;
  transition: opacity 200ms, transform 200ms;
}
/* Show sun when in dark mode (click to go to light) */
.theme-toggle .icon-moon { display: none; }
.theme-toggle .icon-sun { display: inline-block; }
html[data-theme="warm-light"] .theme-toggle .icon-sun { display: none; }
html[data-theme="warm-light"] .theme-toggle .icon-moon { display: inline-block; }
'''


def apply_to_page(path: Path) -> bool:
    """Apply v29 theme to one HTML file. Returns True if changes made."""
    if not path.exists():
        return False
    src = path.read_text()

    # Skip if already applied
    if 'pocketplot.setTheme' in src or 'data-theme="warm-light"' in src:
        return False

    changes = []

    # 1. Inject boot script in <head> (just after <head>)
    if '<head>' in src and t.THEME_BOOT not in src:
        src = src.replace('<head>', '<head>\n' + t.THEME_BOOT, 1)
        changes.append('boot-script')

    # 2. Inject theme CSS at end of <style>
    if '</style>' in src:
        # Find the LAST </style> so we add once
        last_style_end = src.rfind('</style>')
        inject = '\n\n/* v29 theme system (Kindle-e-ink warm themes) */\n' + t.THEME_STYLES
        # Add toggle button CSS at the start of the themes block
        src = src[:last_style_end] + TOGGLE_BUTTON_CSS + inject + src[last_style_end:]
        changes.append('styles')

    # 3. Inject toggle button + handler before </body>, AFTER existing nav-links
    #    Find the nav-links </nav> close — insert toggle button just before </nav>
    if '</nav>' in src and 'theme-toggle-btn' not in src:
        # Find last </nav> close
        last_nav_close = src.rfind('</nav>')
        if last_nav_close > 0:
            # Insert toggle button right before </nav>
            src = src[:last_nav_close] + '  ' + TOGGLE_BUTTON_HTML + '\n  ' + src[last_nav_close:]
            changes.append('toggle-button')

    # 4. Inject toggle JS at end of body (after existing scripts, before </body>)
    # Combine the existing <script> if any with our toggle JS
    if '</body>' in src and 'toggleTheme' not in src:
        # Insert before </body>
        src = src.replace('</body>', t.TOGGLE_JS + '\n</body>')
        changes.append('toggle-js')

    if changes:
        path.write_text(src)
        print(f'  [{path.name}] applied: {", ".join(changes)}')
        return True
    return False


def main():
    print('=' * 60)
    print('PocketPlot Universe - v29 theme applier')
    print('=' * 60)
    print()
    print('Injects:')
    print('  - Theme boot script (sets data-theme before first paint)')
    print('  - Kindle-e-ink warm-dark + warm-light CSS variables')
    print('  - Sun/moon toggle button in nav')
    print('  - Toggle JS (localStorage persist + cross-device sync)')
    print()

    project = Path('/root/pocketplot')
    changed_count = 0
    for name in PAGES:
        path = project / name
        if apply_to_page(path):
            changed_count += 1

    print()
    if changed_count == 0:
        print('No changes needed — v29 theme already applied to all pages.')
    else:
        print(f'Done — {changed_count} page(s) updated.')
    print()
    print('Next steps:')
    print('  1. Verify in browser at https://pocketplot.app')
    print('  2. Click sun/moon icon in nav to test toggle')
    print('  3. Reload — choice should persist via localStorage')


if __name__ == '__main__':
    main()
