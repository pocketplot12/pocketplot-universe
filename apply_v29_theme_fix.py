"""
PocketPlot Universe - v29 theme fix.

The toggle button inline script ran BEFORE the window.pocketplot
definition script (because the button is in nav which is rendered before
the body's trailing script). This script:

  1. Removes the broken inline click handler from each toggle button
  2. Replaces it with one that re-attaches after window.pocketplot is
     defined (via DOMContentLoaded or just attaching in the body script)

Simpler approach: define window.pocketplot AT THE TOP of <head>, not
at the bottom. Then the toggle button script in nav can call it.

Run:
  cd /root/pocketplot
  python3 apply_v29_theme_fix.py
"""
import re
from pathlib import Path

PAGES = ['index.html', 'pricing.html', 'faq.html', 'terms.html',
         'how-it-works.html', '404.html', '500.html',
         'signup.html', 'signup-pro.html']

TOGGLE_BUTTON_HTML_REPLACEMENT = '''<script>
  // Bind toggle handler AFTER window.pocketplot is defined
  (function bindThemeToggle() {
    function tryBind() {
      var btn = document.getElementById('theme-toggle-btn');
      if (!btn) return;
      if (!window.pocketplot || typeof window.pocketplot.toggleTheme !== 'function') {
        setTimeout(tryBind, 10);
        return;
      }
      btn.addEventListener('click', function() {
        window.pocketplot.toggleTheme();
      });
    }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', tryBind);
    } else {
      tryBind();
    }
  })();
</script>'''


# Find the previous broken pattern and replace it
BROKEN_PATTERN = '''<script>
  document.getElementById('theme-toggle-btn').addEventListener('click', function() {
    window.pocketplot.toggleTheme();
  });
</script>'''


def fix_page(path: Path) -> bool:
    if not path.exists():
        return False
    src = path.read_text()
    if BROKEN_PATTERN not in src:
        return False
    new_src = src.replace(BROKEN_PATTERN, TOGGLE_BUTTON_HTML_REPLACEMENT)
    if new_src == src:
        return False
    path.write_text(new_src)
    print(f'  [{path.name}] fixed toggle handler')
    return True


def main():
    project = Path('/root/pocketplot')
    changed = 0
    for name in PAGES:
        if fix_page(project / name):
            changed += 1
    print(f'\nDone — {changed} page(s) updated.')


if __name__ == '__main__':
    main()
