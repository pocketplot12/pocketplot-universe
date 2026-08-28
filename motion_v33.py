"""
PocketPlot Universe - v33 motion system.

Phase 1 (scroll reveals) + Phase 2 (micro-animations).

Design tokens + JS observer pattern + a11y (prefers-reduced-motion respect).
"""

ANIMATION_TOKENS = """
/* === Motion tokens === */
:root {
  --ease-out:    cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-strong: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --dur-instant: 80ms;
  --dur-fast:    180ms;
  --dur:         320ms;
  --dur-slow:    600ms;
  --dur-slower:  900ms;
  --reveal-distance: 28px;
}

/* === Reveal initial state (before JS observer adds .visible) === */
.reveal {
  opacity: 0;
  transform: translateY(var(--reveal-distance));
  transition: opacity var(--dur) var(--ease-out),
              transform var(--dur) var(--ease-out);
  will-change: opacity, transform;
}
.reveal.visible {
  opacity: 1;
  transform: translateY(0);
}

/* Stagger children */
.reveal-stagger > .reveal {
  transition-delay: 0ms;
}
.reveal-stagger > .reveal:nth-child(1) { transition-delay: 0ms; }
.reveal-stagger > .reveal:nth-child(2) { transition-delay: 80ms; }
.reveal-stagger > .reveal:nth-child(3) { transition-delay: 160ms; }
.reveal-stagger > .reveal:nth-child(4) { transition-delay: 240ms; }
.reveal-stagger > .reveal:nth-child(5) { transition-delay: 320ms; }

/* === Micro-animations === */

/* Buttons: subtle press + lift */
.btn-primary, .btn, button, a.cta-primary {
  transition: transform var(--dur-fast) var(--ease-out),
              box-shadow var(--dur-fast) var(--ease-out),
              background var(--dur-fast) var(--ease-out),
              border-color var(--dur-fast) var(--ease-out);
}
.btn-primary:not(:disabled):hover,
.btn:not(:disabled):hover,
button:not(:disabled):hover,
a.cta-primary:hover {
  transform: translateY(-1px);
}
.btn-primary:not(:disabled):active,
.btn:not(:disabled):active,
button:not(:disabled):active,
a.cta-primary:active {
  transform: translateY(0) scale(0.98);
  transition-duration: var(--dur-instant);
}

/* Cards: lift on hover */
.card, .tier, .panel {
  transition: transform var(--dur) var(--ease-out),
              border-color var(--dur) var(--ease-out),
              background var(--dur) var(--ease-out),
              box-shadow var(--dur) var(--ease-out);
}
.card:not(.static):hover,
.tier:not(.static):hover,
.panel:not(.static):hover {
  transform: translateY(-4px);
}

/* Toggle button icon: rotate on click */
.theme-toggle svg {
  transition: transform var(--dur) var(--ease-in-out),
              opacity var(--dur-fast) var(--ease-out);
}
.theme-toggle.spinning svg {
  transform: rotate(360deg);
}

/* Stat numbers: scale-in on reveal */
.stat .n {
  display: inline-block;
  opacity: 0;
  transform: translateY(12px) scale(0.9);
  transition: opacity var(--dur-slow) var(--ease-out),
              transform var(--dur-slow) var(--ease-out-strong);
}
.stat .n.visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

/* Hero text: subtle entrance */
.hero h1 {
  animation: heroIn var(--dur-slower) var(--ease-out) 0s both;
}
.hero .eyebrow, .hero .lede, .hero .cta-wrap {
  animation: heroIn var(--dur-slower) var(--ease-out) 100ms both;
}

@keyframes heroIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Subtle ambient breath on brass accents */
.pulse-soft {
  animation: pulseSoft 4s var(--ease-in-out) infinite;
}
@keyframes pulseSoft {
  0%, 100% { opacity: 0.85; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.04); }
}

/* === Reduced motion: respect user preference === */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  .reveal, .stat .n {
    opacity: 1 !important;
    transform: none !important;
  }
}
"""

# JS: scroll observer + count-up animation + reduced-motion check
OBSERVER_JS = '''<script>
// v33 motion: scroll-triggered reveals + count-up animations
(function() {
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // If reduced motion, reveal everything immediately and bail
  if (prefersReducedMotion) {
    document.querySelectorAll('.reveal').forEach(function(el) {
      el.classList.add('visible');
    });
    document.querySelectorAll('.stat .n').forEach(function(el) {
      el.classList.add('visible');
    });
    return;
  }

  // IntersectionObserver: add .visible when 15% in view
  if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.15,
      rootMargin: '0px 0px -60px 0px'  // trigger slightly before fully visible
    });

    // Observe all .reveal elements
    document.querySelectorAll('.reveal').forEach(function(el) {
      observer.observe(el);
    });

    // Observe stat numbers (have their own .n class)
    document.querySelectorAll('.stat .n').forEach(function(el) {
      observer.observe(el);
    });
  } else {
    // Fallback: just show everything
    document.querySelectorAll('.reveal, .stat .n').forEach(function(el) {
      el.classList.add('visible');
    });
  }

  // Toggle button: add spinning class momentarily on click
  var toggleBtn = document.getElementById('theme-toggle-btn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', function() {
      toggleBtn.classList.add('spinning');
      setTimeout(function() {
        toggleBtn.classList.remove('spinning');
      }, 400);
    });
  }

  // Count-up animation for .stat .n when it gets .visible
  document.querySelectorAll('.stat .n').forEach(function(el) {
    var targetText = (el.textContent || '').trim();
    var targetNum = parseFloat(targetText.replace(/[^0-9.]/g, ''));
    if (isNaN(targetNum)) return;
    var duration = 1200;
    var start = performance.now();
    var origText = targetText;
    var suffix = targetText.replace(/[0-9.]/g, '').trim();

    function tick() {
      var elapsed = performance.now() - start;
      if (elapsed >= duration) {
        el.textContent = targetNum + suffix;
        return;
      }
      var progress = elapsed / duration;
      // ease-out-cubic
      var eased = 1 - Math.pow(1 - progress, 3);
      var current = Math.floor(targetNum * eased);
      el.textContent = current + suffix;
      requestAnimationFrame(tick);
    }

    // Start count-up when .visible class is added
    var mo = new MutationObserver(function(muts) {
      muts.forEach(function(m) {
        if (m.attributeName === 'class' && el.classList.contains('visible')) {
          mo.disconnect();
          el.textContent = '0' + suffix;
          requestAnimationFrame(tick);
        }
      });
    });
    mo.observe(el, { attributes: true });
  });
})();
</script>'''


def main():
    print('=' * 60)
    print('PocketPlot Universe - v33 motion system')
    print('=' * 60)


if __name__ == '__main__':
    main()
