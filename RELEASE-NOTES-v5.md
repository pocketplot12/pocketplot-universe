# PocketPlot v5 — Khan Academy Kids Art Style

> Added 2026-08-22 to the existing v3 README.

The 7 illustrations used across the app were redesigned in the warm, rounded Khan Academy Kids aesthetic — friendly animal characters with dot eyes + cheek blush, soft peach/cream/sky-blue palette, simple uncluttered backgrounds.

**What changed:**

- **Hero illustration** — replaced the line-art parent-and-child scene with a cozy **bear parent + bunny child** under a starry window (rounded shapes, soft gradients, single floating heart).
- **3 how-it-works icons** — child's face (with rosy cheeks + glint eyes), an open book with a bright gold star above, a cozy house under a crescent moon with a tiny heart in the window.
- **Email header banner** — replaced the tree-branch + bird with a **sleeping cloud** (closed eyes, cheek blush, "Zzz" text), a crescent moon, and a few stars.
- **Moment-of-the-Day icon** *(new asset)* — a warm pink heart with a soft glow, appears next to the "Wren's Moment of the Day" eyebrow in the email.
- **Pro Tier badge** *(new asset)* — a puffy gold star with a soft glow, appears next to the POCKETPLOT wordmark in the Pro email header.

**How to verify visually:**

1. Run `python3 app.py`, sign up, check the `outbox/*.eml` for the new banner + moment heart + Pro star.
2. Open the saved `.eml` in any mail client (Apple Mail, Thunderbird) to see the rendered email.
3. Open `index.html` in a browser to see the new hero + 3 how-it-works icons in the marketing page.

**Implementation details:**

- All 5 line-art illustrations were inlined inside `INDEX_HTML` (now replaced).
- The email banner SVG (`EMAIL_BANNER_SVG`) was replaced wholesale.
- Two new module-level constants were added: `MOMENT_ICON_SVG` and `PRO_BADGE_SVG`.
- The constants are threaded through `render_email()` → `deliver_email()` → `_send_with_v4_enrichment()` so they're available on every outbound email.
- During the KAK redesign, an orphan duplicate `/audio/<sub>/<file>` Flask route (sitting after `app.run()`) was discovered and removed — it was preventing the app from importing.

— Gizmo / 小吉
