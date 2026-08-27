"""
PocketPlot Universe - advertising-grade pitch deck (v23 Ad).

A polished, advertising-quality 14-page deck with:
  - A proper title sequence: cover, table of contents, section divider
  - Real typographic hierarchy (display serif headlines, sans body, mono labels)
  - Consistent brand mark header + page footer on every slide
  - Pull-quotes in italic amber
  - Clean grid layout (8-column mental model)
  - Section dividers with big section numbers
  - Brand mark on every slide

Fonts: uses fpdf2 core Helvetica family (no extra deps).
  - Headlines: Helvetica Bold (display weight via size)
  - Body: Helvetica Regular
  - Labels: Helvetica Italic small-caps style
  - Mono accents: Courier (for tech/code references)

Output: /root/pocketplot/pitch_deck_v23_ad.pdf
"""
from fpdf import FPDF
from PIL import Image
import os

BRAND_PATH = '/root/pocketplot/logo-halo-600.png'
if not os.path.exists(BRAND_PATH):
    BRAND_PATH = '/root/pocketplot/logo-600.png'

# ---- COLOR PALETTE (Tech-Victorian) ----
NAVY = (10, 15, 28)
NAVY_2 = (21, 36, 63)
NAVY_3 = (31, 52, 96)
NAVY_4 = (45, 70, 110)
BRASS = (201, 160, 78)
BRASS_D = (138, 106, 38)
BRASS_L = (232, 200, 121)
AMBER = (240, 181, 74)
AMBER_L = (255, 212, 122)
CREAM = (243, 233, 210)
CREAM_W = (232, 216, 184)
INK = (243, 233, 210)
INK_MUTED = (158, 182, 212)
INK_FAINT = (122, 138, 168)
INK_DIM = (90, 105, 130)
EMERALD = (29, 107, 80)
EMERALD_L = (61, 142, 112)

# ---- DIMENSIONS ----
# Slide: 17.78 x 10 inches (16:9 widescreen)
W, H = 17.78, 10
# Margins (in inches) - generous, professional
M_LEFT = 1.0
M_RIGHT = 1.0
M_TOP = 1.4    # leave space for header brand mark
M_BOTTOM = 0.8  # leave space for footer
CONTENT_W = W - M_LEFT - M_RIGHT
CONTENT_H = H - M_TOP - M_BOTTOM


class AdPDF(FPDF):
    def __init__(self, total_pages=14):
        super().__init__(orientation='L', unit='in', format=(H, W))
        self.set_auto_page_break(auto=False)
        self.set_margins(0, 0, 0)
        self.current_slide = 0
        self.total = total_pages

    def add_slide(self):
        self.add_page()
        self.current_slide += 1
        # Navy fill
        self.set_fill_color(*NAVY)
        self.rect(0, 0, W, H, 'F')
        # Subtle top/bottom bands for depth
        self.set_fill_color(*NAVY_2)
        self.rect(0, 0, W, 0.4, 'F')
        self.rect(0, H - 0.4, W, 0.4, 'F')

    def draw_corner_brackets(self):
        """Brass corner ornaments in all four corners."""
        self.set_draw_color(*BRASS)
        self.set_line_width(0.012)
        inset = 0.4
        arm = 0.5
        # Top-left
        self.line(inset, inset, inset + arm, inset)
        self.line(inset, inset, inset, inset + arm)
        # Top-right
        self.line(W - inset, inset, W - inset - arm, inset)
        self.line(W - inset, inset, W - inset, inset + arm)
        # Bottom-left
        self.line(inset, H - inset, inset + arm, H - inset)
        self.line(inset, H - inset, inset, H - inset - arm)
        # Bottom-right
        self.line(W - inset, H - inset, W - inset - arm, H - inset)
        self.line(W - inset, H - inset, W - inset, H - inset - arm)

    def draw_brand_header(self):
        """Consistent brand mark + wordmark in the top-left of every content slide."""
        # Brand mark (small)
        if os.path.exists(BRAND_PATH):
            self.image(BRAND_PATH, 0.6, 0.55, w=0.45, h=0.42)
        # Wordmark
        self.set_text_color(*BRASS_L)
        self.set_font('Helvetica', 'B', 11)
        self.set_xy(1.15, 0.62)
        self.cell(w=4, h=0.25, txt='PocketPlot Universe')
        # Tagline right-aligned
        self.set_text_color(*INK_FAINT)
        self.set_font('Helvetica', 'I', 9)
        self.set_xy(W - 5, 0.62)
        self.cell(w=4.4, h=0.25, txt='Premium storytelling for adults', align='R')

    def draw_footer(self, page_num=None, section=None):
        """Page footer with divider, colophon, section name, page number."""
        if page_num is None:
            page_num = self.current_slide
        # Brass divider
        self.set_draw_color(*BRASS_D)
        self.set_line_width(0.004)
        self.line(M_LEFT, H - 0.55, W - M_RIGHT, H - 0.55)
        # Colophon (left)
        self.set_text_color(*INK_FAINT)
        self.set_font('Helvetica', '', 8)
        self.set_xy(M_LEFT, H - 0.48)
        col = 'PocketPlot Universe  -  Pitch deck v23'
        if section:
            col += f'  -  {section}'
        self.cell(w=W - M_LEFT - M_RIGHT, h=0.2, txt=col, align='L')
        # Page number (right)
        self.set_xy(W - M_RIGHT - 1.5, H - 0.48)
        self.cell(w=1.5, h=0.2, txt=f'{page_num}  /  {self.total}', align='R')

    # ---- TYPOGRAPHY ----

    def draw_eyebrow(self, text, y, color=None, align='C'):
        """Small-caps style label. Single line, tracked."""
        if color is None:
            color = BRASS_L
        self.set_text_color(*color)
        self.set_font('Helvetica', '', 10)
        x = M_LEFT if align == 'L' else 0
        w = CONTENT_W if align in ('L', 'C', 'R') else W
        self.set_xy(x, y)
        self.cell(w=w, h=0.22, txt=text.upper(), align=align)

    def draw_title(self, text, y, size=28, color=None, align='C'):
        if color is None:
            color = INK
        self.set_text_color(*color)
        self.set_font('Helvetica', 'B', size)
        lines = self._wrap(text, CONTENT_W, 'Helvetica', 'B', size)
        line_h = size / 72 * 1.25
        for i, line in enumerate(lines):
            x = M_LEFT if align == 'L' else 0
            w = CONTENT_W if align in ('L', 'C', 'R') else W
            self.set_xy(x, y + i * line_h)
            self.cell(w=w, h=line_h, txt=line, align=align)

    def draw_subtitle(self, text, y, size=14, color=None, italic=True, align='C'):
        if color is None:
            color = INK_MUTED
        self.set_text_color(*color)
        self.set_font('Helvetica', 'I' if italic else '', size)
        lines = self._wrap(text, CONTENT_W, 'Helvetica', 'I' if italic else '', size)
        line_h = size / 72 * 1.4
        for i, line in enumerate(lines):
            x = M_LEFT if align == 'L' else 0
            w = CONTENT_W if align in ('L', 'C', 'R') else W
            self.set_xy(x, y + i * line_h)
            self.cell(w=w, h=line_h, txt=line, align=align)

    def draw_divider(self, y, color=None, weight=0.012, width=2.0):
        """Centered horizontal divider."""
        if color is None:
            color = BRASS
        self.set_draw_color(*color)
        self.set_line_width(weight)
        cx = W / 2
        self.line(cx - width, y, cx + width, y)

    def draw_pull_quote(self, text, y, size=16, color=None):
        """Italic centered quote at the bottom of a slide."""
        if color is None:
            color = AMBER
        self.draw_subtitle(f'"{text}"', y, size=size, color=color, italic=True)

    def draw_label_value(self, label, value, y, label_w=2.2, value_color=None):
        """A label-value pair (used for the tech stack slide)."""
        # Label
        self.set_text_color(*AMBER)
        self.set_font('Helvetica', 'B', 12)
        self.set_xy(M_LEFT, y)
        self.cell(w=label_w, h=0.3, txt=label, align='L')
        # Value
        if value_color is None:
            value_color = INK
        self.set_text_color(*value_color)
        self.set_font('Helvetica', '', 12)
        self.set_xy(M_LEFT + label_w + 0.2, y)
        self.cell(w=W - M_LEFT - M_RIGHT - label_w - 0.2, h=0.3, txt=value, align='L')

    def draw_card(self, x, y, w, h, fill=None, accent_color=None, accent_pos='top'):
        if fill:
            self.set_fill_color(*fill)
            self.rect(x, y, w, h, 'F')
        if accent_color:
            self.set_draw_color(*accent_color)
            self.set_line_width(0.025)
            if accent_pos == 'top':
                self.line(x, y, x + w, y)
            elif accent_pos == 'left':
                self.line(x, y, x, y + h)

    def draw_centered_text_in_box(self, text, x, y, w, size, color=None, style='', line_h_mul=1.4):
        """Wrap text and center each line within the given box."""
        if color is None:
            color = INK
        self.set_text_color(*color)
        self.set_font('Helvetica', style, size)
        wrapped = self._wrap(text, w - 0.4, 'Helvetica', style, size)
        line_h = size / 72 * line_h_mul
        for i, line in enumerate(wrapped):
            tw = self.get_string_width(line)
            tx = x + (w - tw) / 2
            self.set_xy(tx, y + i * line_h)
            self.cell(w=tw, h=line_h, txt=line, align='L')

    def draw_left_bullets(self, bullets, x, y, w, size=11, color=None, gap=0.05):
        """Bullet list with proper indentation."""
        if color is None:
            color = CREAM_W
        self.set_text_color(*color)
        self.set_font('Helvetica', '', size)
        line_h = size / 72 * 1.35
        cur_y = y
        for b in bullets:
            text = f'-  {b}'
            wrapped = self._wrap(text, w - 0.3, 'Helvetica', '', size)
            for i, line in enumerate(wrapped):
                self.set_xy(x, cur_y + i * line_h)
                self.cell(w=w, h=line_h, txt=line, align='L')
            cur_y += line_h * len(wrapped) + gap
        return cur_y

    def draw_brand_image(self, x, y, w):
        if os.path.exists(BRAND_PATH):
            im = Image.open(BRAND_PATH)
            iw, ih = im.size
            h = w * ih / iw
            self.image(BRAND_PATH, x, y, w=w, h=h)
            return h
        return 0

    def _wrap(self, text, max_w, font, style, size):
        self.set_font(font, style, size)
        words = text.split()
        lines = []
        cur = []
        for wd in words:
            test = ' '.join(cur + [wd])
            if self.get_string_width(test) > max_w:
                if cur:
                    lines.append(' '.join(cur))
                    cur = [wd]
                else:
                    lines.append(wd)
            else:
                cur.append(wd)
        if cur:
            lines.append(' '.join(cur))
        return lines


def build_deck():
    pdf = AdPDF(total_pages=14)

    # =========================================================
    # SLIDE 1: COVER
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    # Brand mark, centered
    brand_h = pdf.draw_brand_image(W/2 - 1.6, 1.2, 3.2)
    # Eyebrow + title block
    pdf.draw_eyebrow('PocketPlot Universe', 5.4)
    pdf.draw_title('Create. Roleplay. Explore.', 5.85, size=42, color=BRASS_L)
    pdf.draw_subtitle('A premium storytelling platform for adults', 6.85, size=15)
    # Brass divider
    pdf.draw_divider(7.5, weight=0.015, width=2.5)
    # Footer
    pdf.draw_eyebrow('Pitch deck  /  v23  /  Q4 2026', 7.8, color=BRASS, align='C')
    # Colophon at the bottom (cover-specific)
    pdf.set_text_color(*INK_FAINT)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_xy(M_LEFT, H - 0.48)
    pdf.cell(w=CONTENT_W, h=0.2, txt='PocketPlot Universe  -  Pitch deck v23  -  Page 1 / 14', align='C')

    # =========================================================
    # SLIDE 2: TABLE OF CONTENTS
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    pdf.draw_brand_header()
    pdf.draw_eyebrow('Contents', 1.6, align='L')
    pdf.draw_title('What is in this deck', 1.95, size=30, color=INK, align='L')
    pdf.draw_divider(2.75, weight=0.008, width=3.0)
    toc = [
        ('01', 'Cover', '1'),
        ('02', 'Table of contents', '2'),
        ('03', 'Section divider', '3'),
        ('04', 'What is PocketPlot?', '4'),
        ('05', 'Who is it for?', '5'),
        ('06', 'Three core differentiators', '6'),
        ('07', 'Every story, two surfaces', '7'),
        ('08', 'The world map', '8'),
        ('09', 'Engagement & community', '9'),
        ('10', 'Exports: PDF, EPUB, Bulk ZIP', '10'),
        ('11', 'Roadmap: v24, v25', '11'),
        ('12', 'Tech stack', '12'),
        ('13', 'Get involved', '13'),
        ('14', 'Colophon', '14'),
    ]
    y = 3.1
    for num, title, page in toc:
        # Number (amber)
        pdf.set_text_color(*AMBER)
        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_xy(2.5, y)
        pdf.cell(w=0.7, h=0.3, txt=num, align='L')
        # Title
        pdf.set_text_color(*INK)
        pdf.set_font('Helvetica', '', 13)
        pdf.set_xy(3.4, y)
        pdf.cell(w=8, h=0.3, txt=title, align='L')
        # Page number
        pdf.set_text_color(*INK_FAINT)
        pdf.set_font('Helvetica', '', 12)
        pdf.set_xy(W - 1.5, y)
        pdf.cell(w=0.5, h=0.3, txt=page, align='R')
        # Subtle separator
        pdf.set_draw_color(*NAVY_3)
        pdf.set_line_width(0.002)
        pdf.line(M_LEFT, y + 0.4, W - M_RIGHT, y + 0.4)
        y += 0.45
    pdf.draw_footer(section='Table of contents')

    # =========================================================
    # SLIDE 3: SECTION DIVIDER (Section 1)
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    # Big section number on the left
    pdf.set_text_color(*BRASS)
    pdf.set_font('Helvetica', 'B', 140)
    pdf.set_xy(M_LEFT, 2.8)
    pdf.cell(w=4, h=2.5, txt='01', align='L')
    # Section title
    pdf.draw_eyebrow('Section one', 4.4, color=BRASS_L, align='L')
    pdf.draw_title('Overview', 4.8, size=44, color=BRASS_L, align='L')
    pdf.draw_divider(6.0, weight=0.012, width=4.0)
    # Pull quote
    pdf.draw_subtitle(
        '"A world the user can actually play in - not a button-click visual novel."',
        7.0, size=14, color=AMBER, italic=True, align='L'
    )
    # Footer
    pdf.draw_footer(section='Overview')

    # =========================================================
    # SLIDE 4: WHAT IS POCKETPLOT?
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    pdf.draw_brand_header()
    pdf.draw_eyebrow('Section 1  /  Overview', 1.6, align='L')
    pdf.draw_title('What is PocketPlot?', 1.95, size=30, color=INK, align='L')
    pdf.draw_divider(2.75, weight=0.008, width=3.0)
    pdf.draw_subtitle(
        'A premium storytelling platform where adults create, share, and explore branching interactive worlds.',
        3.15, size=14, color=INK_MUTED, italic=True, align='L'
    )
    # Two cards
    card_w = (CONTENT_W - 0.4) / 2
    card_h = 4.0
    card_y = 3.9
    # Card 1
    pdf.draw_card(M_LEFT, card_y, card_w, card_h, fill=NAVY_2, accent_color=BRASS)
    pdf.draw_centered_text_in_box('A creative writing studio', M_LEFT + 0.2, card_y + 0.3, card_w - 0.4, 17, color=BRASS_L, style='B')
    pdf.draw_centered_text_in_box(
        'Generate original branching stories with consistent scene art. Every story is procedurally assembled from in-house word pools - no two stories are alike.',
        M_LEFT + 0.3, card_y + 1.1, card_w - 0.6, 11, color=CREAM_W, line_h_mul=1.5
    )
    pdf.draw_centered_text_in_box(
        'Choose from 16 genres, set the tone, describe your character - the engine composes a full branching world with scene-by-scene illustrations.',
        M_LEFT + 0.3, card_y + 2.3, card_w - 0.6, 11, color=CREAM_W, line_h_mul=1.5
    )
    # Card 2
    x2 = M_LEFT + card_w + 0.4
    pdf.draw_card(x2, card_y, card_w, card_h, fill=NAVY_2, accent_color=AMBER)
    pdf.draw_centered_text_in_box('A social storytelling network', x2 + 0.2, card_y + 0.3, card_w - 0.4, 17, color=BRASS_L, style='B')
    pdf.draw_centered_text_in_box(
        'Share stories via QR code or short link. Readers can play through (game mode) or read through (manga mode) - no account required.',
        x2 + 0.3, card_y + 1.1, card_w - 0.6, 11, color=CREAM_W, line_h_mul=1.5
    )
    pdf.draw_centered_text_in_box(
        'Public profiles, likes, follow graph, leaderboards. Creators see views, plays, completions, and words written for every story.',
        x2 + 0.3, card_y + 2.3, card_w - 0.6, 11, color=CREAM_W, line_h_mul=1.5
    )
    # Pull quote at bottom
    pdf.draw_pull_quote('A world the user can actually play in - not a button-click visual novel.', 8.2, size=14)
    pdf.draw_footer(section='What is PocketPlot?')

    # =========================================================
    # SLIDE 5: WHO IS IT FOR?
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    pdf.draw_brand_header()
    pdf.draw_eyebrow('Section 1  /  Overview', 1.6, align='L')
    pdf.draw_title('Who is it for?', 1.95, size=30, color=INK, align='L')
    pdf.draw_divider(2.75, weight=0.008, width=3.0)
    pdf.draw_subtitle('Three audiences, one platform.', 3.15, size=14, italic=True, align='L')
    # Three cards
    audiences = [
        ('01', 'Writers & worldbuilders',
         'Outline a world, pick a tone, and the engine generates a full branching narrative. Scene art generated to match. Export to EPUB, PDF, or share a playable link.',
         BRASS),
        ('02', 'Roleplayers & GMs',
         'Bring your own AI engine (BYOB). Run campaigns, share worlds as game links. Players play through with their own choices - no sign-up needed.',
         AMBER),
        ('03', 'Readers & players',
         'Discover public stories. Play them as visual novels or read them as manga-style pages. Like, follow, and track your reading stats.',
         BRASS_L),
    ]
    card_w = (CONTENT_W - 0.4) / 3
    card_h = 4.6
    card_y = 3.7
    for i, (num, title, body, accent) in enumerate(audiences):
        x = M_LEFT + i * (card_w + 0.2)
        pdf.draw_card(x, card_y, card_w, card_h, fill=NAVY_2, accent_color=accent)
        # Number
        pdf.set_text_color(*accent)
        pdf.set_font('Helvetica', 'B', 44)
        pdf.set_xy(x, card_y + 0.4)
        pdf.cell(w=card_w, h=0.7, txt=num, align='C')
        # Title
        pdf.draw_centered_text_in_box(title, x + 0.1, card_y + 1.5, card_w - 0.2, 16, color=BRASS_L, style='B')
        # Body
        pdf.draw_centered_text_in_box(body, x + 0.15, card_y + 2.2, card_w - 0.3, 11, color=CREAM_W, line_h_mul=1.5)
    pdf.draw_footer(section='Audience')

    # =========================================================
    # SLIDE 6: THREE DIFFERENTIATORS
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    pdf.draw_brand_header()
    pdf.draw_eyebrow('Section 2  /  Differentiators', 1.6, align='L')
    pdf.draw_title('Three things that make PocketPlot different', 1.95, size=28, color=INK, align='L')
    pdf.draw_divider(2.75, weight=0.008, width=3.0)
    features = [
        ('01', 'Branching-first',
         'Every world is a graph, not a list. Each scene has 2-3 choices that branch the story. The same world can be played hundreds of times with different paths.',
         BRASS),
        ('02', 'BYOB - Bring Your Own Brain',
         'Connect your own OpenAI-compatible LLM (OpenAI, Anthropic via proxy, OpenRouter, Ollama). The platform handles content moderation on the response side.',
         AMBER),
        ('03', 'Consistent scene art',
         'Every scene gets a procedurally-composed SVG illustration matched to genre, tone, and story state. Visual continuity without paying per image.',
         BRASS_L),
    ]
    card_w = (CONTENT_W - 0.4) / 3
    card_h = 4.8
    card_y = 3.4
    for i, (num, title, body, accent) in enumerate(features):
        x = M_LEFT + i * (card_w + 0.2)
        pdf.draw_card(x, card_y, card_w, card_h, fill=NAVY_2, accent_color=accent)
        # Number
        pdf.set_text_color(*accent)
        pdf.set_font('Helvetica', 'B', 56)
        pdf.set_xy(x, card_y + 0.5)
        pdf.cell(w=card_w, h=0.9, txt=num, align='C')
        # Title
        pdf.draw_centered_text_in_box(title, x + 0.1, card_y + 1.9, card_w - 0.2, 16, color=BRASS_L, style='B')
        # Body
        pdf.draw_centered_text_in_box(body, x + 0.15, card_y + 2.7, card_w - 0.3, 11, color=CREAM_W, line_h_mul=1.5)
    pdf.draw_footer(section='Differentiators')

    # =========================================================
    # SLIDE 7: TWO WAYS TO PLAY
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    pdf.draw_brand_header()
    pdf.draw_eyebrow('Section 3  /  Game modes', 1.6, align='L')
    pdf.draw_title('Every story, two surfaces', 1.95, size=30, color=INK, align='L')
    pdf.draw_divider(2.75, weight=0.008, width=3.0)
    pdf.draw_subtitle('One world. Two ways to experience it. The creator publishes both.', 3.15, size=14, italic=True, align='L')
    card_w = (CONTENT_W - 0.4) / 2
    card_h = 5.0
    card_y = 3.9
    # PLAY
    pdf.draw_card(M_LEFT, card_y, card_w, card_h, fill=NAVY_2, accent_color=AMBER)
    pdf.draw_centered_text_in_box('PLAY MODE', M_LEFT + 0.2, card_y + 0.3, card_w - 0.4, 22, color=AMBER, style='B')
    pdf.draw_centered_text_in_box('Visual novel. Choices. Branching.', M_LEFT + 0.2, card_y + 0.95, card_w - 0.4, 13, color=INK, style='I')
    pdf.draw_left_bullets([
        'Numbered choice buttons advance the player session',
        'Progress bar shows chapter X of Y',
        'Completion banner when the story is finished',
        'See-world-map link for visual navigation',
        'Session stored as cookie plus database row',
        'Player path tracked as visited episode list',
    ], M_LEFT + 0.4, card_y + 1.7, card_w - 0.8, size=11)
    # READ
    x2 = M_LEFT + card_w + 0.4
    pdf.draw_card(x2, card_y, card_w, card_h, fill=NAVY_2, accent_color=BRASS)
    pdf.draw_centered_text_in_box('READ MODE', x2 + 0.2, card_y + 0.3, card_w - 0.4, 22, color=BRASS, style='B')
    pdf.draw_centered_text_in_box('Manga / storybook. Read-only.', x2 + 0.2, card_y + 0.95, card_w - 0.4, 13, color=INK, style='I')
    pdf.draw_left_bullets([
        'One page per episode in manga-style panels',
        'Art panel plus italic narration blockquote',
        'One to two speech bubbles per page',
        'Page-flip CSS animation between pages',
        'Keyboard navigation with left and right arrows',
        'Cream parchment background with brass borders',
    ], x2 + 0.4, card_y + 1.7, card_w - 0.8, size=11)
    pdf.draw_footer(section='Game modes')

    # =========================================================
    # SLIDE 8: WORLD MAP
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    pdf.draw_brand_header()
    pdf.draw_eyebrow('Section 4  /  World map', 1.6, align='L')
    pdf.draw_title('Scenes as nodes. Choices as edges.', 1.95, size=30, color=INK, align='L')
    pdf.draw_divider(2.75, weight=0.008, width=3.0)
    # Text on the left
    text_w = W / 2 - M_LEFT - 1.0
    pdf.draw_eyebrow('A Minecraft-style foundation', 3.4, color=BRASS_L, align='L')
    pdf.draw_left_bullets([
        'Each scene is one node on a 2D map',
        'Visited scenes pulse with amber light',
        'Click a node to enter that scene',
        'Linear graph synthesis when no author data exists',
        'Custom placement in v24 (scene_nodes_json)',
        'Foundation for full Minecraft-style exploration',
    ], M_LEFT, 3.9, w=text_w, size=12)
    # Brand image on the right
    pdf.draw_brand_image(W - 4.4, 2.8, 3.4)
    pdf.draw_footer(section='World map')

    # =========================================================
    # SLIDE 9: ENGAGEMENT & COMMUNITY
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    pdf.draw_brand_header()
    pdf.draw_eyebrow('Section 5  /  Engagement & community', 1.6, align='L')
    pdf.draw_title('Built for sharing. Built for retention.', 1.95, size=28, color=INK, align='L')
    pdf.draw_divider(2.75, weight=0.008, width=3.0)
    col_w = (CONTENT_W - 0.4) / 2
    card_h = 5.0
    card_y = 3.4
    # Engagement
    pdf.draw_card(M_LEFT, card_y, col_w, card_h, fill=NAVY_2, accent_color=BRASS)
    pdf.draw_centered_text_in_box('Engagement loop', M_LEFT + 0.2, card_y + 0.3, col_w - 0.4, 17, color=BRASS_L, style='B')
    pdf.draw_left_bullets([
        'One-tap like on any story, persisted',
        'Per-world stats: views, plays, completions, likes, words',
        'Continue-the-story prompt on every episode',
        'Chapter progress bar on every screen',
        'Milestone emails: first story, 10 words, 100, 1k, 10k',
        'Weekly summary email for Pro and Creator tiers',
    ], M_LEFT + 0.4, card_y + 1.2, col_w - 0.8, size=11)
    # Community
    x2 = M_LEFT + col_w + 0.4
    pdf.draw_card(x2, card_y, col_w, card_h, fill=NAVY_2, accent_color=AMBER)
    pdf.draw_centered_text_in_box('Community', x2 + 0.2, card_y + 0.3, col_w - 0.4, 17, color=BRASS_L, style='B')
    pdf.draw_left_bullets([
        'Public profile at /u/<username>',
        'Up to 3 featured stories per profile',
        'Follow graph: followers and following',
        'Notifications for new follower or story share',
        'Share token system: one world, many links',
        'QR code generation for every share link',
    ], x2 + 0.4, card_y + 1.2, col_w - 0.8, size=11)
    pdf.draw_footer(section='Engagement & community')

    # =========================================================
    # SLIDE 10: EXPORTS
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    pdf.draw_brand_header()
    pdf.draw_eyebrow('Section 6  /  Exports', 1.6, align='L')
    pdf.draw_title('Take it with you. In any format.', 1.95, size=30, color=INK, align='L')
    pdf.draw_divider(2.75, weight=0.008, width=3.0)
    formats = [
        ('PDF', 'Cover page plus all chapters in one document. Uses the existing pdf_gen.py pipeline.', BRASS),
        ('EPUB', 'Standard e-reader format. Cover, TOC, per-chapter XHTML. Hand-rolled, no library dependency.', AMBER),
        ('Bulk ZIP', 'manifest.json plus README plus one .md per episode. Drop into any static site.', BRASS_L),
        ('Share link', 'A short URL plus QR code. Recipient plays or reads in browser, no sign-up.', EMERALD_L),
    ]
    card_w = (CONTENT_W - 0.6) / 4
    card_h = 5.0
    card_y = 3.4
    for i, (name, body, accent) in enumerate(formats):
        x = M_LEFT + i * (card_w + 0.2)
        pdf.draw_card(x, card_y, card_w, card_h, fill=NAVY_2, accent_color=accent)
        # Number
        pdf.set_text_color(*accent)
        pdf.set_font('Helvetica', 'B', 44)
        pdf.set_xy(x, card_y + 0.5)
        pdf.cell(w=card_w, h=0.7, txt=f'0{i+1}', align='C')
        # Name
        pdf.draw_centered_text_in_box(name, x + 0.1, card_y + 1.8, card_w - 0.2, 17, color=BRASS_L, style='B')
        # Body
        pdf.draw_centered_text_in_box(body, x + 0.15, card_y + 2.6, card_w - 0.3, 11, color=CREAM_W, line_h_mul=1.5)
    pdf.draw_footer(section='Exports')

    # =========================================================
    # SLIDE 11: ROADMAP
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    pdf.draw_brand_header()
    pdf.draw_eyebrow('Section 7  /  Roadmap', 1.6, align='L')
    pdf.draw_title('The path to a Minecraft-style world', 1.95, size=30, color=INK, align='L')
    pdf.draw_divider(2.75, weight=0.008, width=3.0)
    versions = [
        ('v22', 'DONE',   'Tech-Victorian visual identity + brand mark', CREAM_W),
        ('v23', 'DONE',   'Engagement, community, exports, PWA, READ mode', BRASS_L),
        ('v24', 'NEXT',   'Inventory, build mode, real node-graph editor, VAPID push delivery, custom world-map coordinates', AMBER),
        ('v25', 'FUTURE', 'Real-time multiplayer, native iOS/Android shells, AI-generated manga art', BRASS),
    ]
    y = 3.4
    for v, status, desc, color in versions:
        # Badge box
        pdf.set_fill_color(*NAVY_2)
        pdf.rect(M_LEFT, y, 1.8, 0.8, 'F')
        pdf.set_draw_color(*color)
        pdf.set_line_width(0.025)
        pdf.rect(M_LEFT, y, 1.8, 0.8)
        # Version
        pdf.set_text_color(*color)
        pdf.set_font('Helvetica', 'B', 18)
        pdf.set_xy(M_LEFT, y + 0.1)
        pdf.cell(w=1.0, h=0.35, txt=v, align='C')
        pdf.set_font('Helvetica', '', 8)
        pdf.set_xy(M_LEFT, y + 0.45)
        pdf.cell(w=1.0, h=0.25, txt=status, align='C')
        # Description
        pdf.set_text_color(*INK)
        pdf.set_font('Helvetica', '', 13)
        wrapped = pdf._wrap(desc, CONTENT_W - 2.2, 'Helvetica', '', 13)
        line_h = 13 / 72 * 1.4
        for i, line in enumerate(wrapped):
            pdf.set_xy(M_LEFT + 2.0, y + i * line_h)
            pdf.cell(w=CONTENT_W - 2.0, h=line_h, txt=line, align='L')
        y += max(0.9, 0.4 * len(wrapped) + 0.3)
    pdf.draw_footer(section='Roadmap')

    # =========================================================
    # SLIDE 12: TECH STACK
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    pdf.draw_brand_header()
    pdf.draw_eyebrow('Section 8  /  Tech stack', 1.6, align='L')
    pdf.draw_title('Single-file Flask. No vendor lock-in.', 1.95, size=30, color=INK, align='L')
    pdf.draw_divider(2.75, weight=0.008, width=3.0)
    stack = [
        ('Backend',  'Python 3.13 + Flask (single app.py, ~9000 lines) + APScheduler + sqlite3'),
        ('Frontend', 'Server-rendered HTML + inline CSS + Jinja2 templates (no SPA, no build step)'),
        ('Storage',  'SQLite (single file) + outbox-folder email + JSON column metadata'),
        ('AI',       'Procedural generator (default) + OpenAI-compatible BYOB (Creator tier)'),
        ('Mobile',   'PWA (manifest + service worker) -> installable on iOS/Android home screens'),
    ]
    y = 3.4
    for label, value in stack:
        pdf.draw_label_value(label, value, y, label_w=2.0)
        # Subtle separator
        pdf.set_draw_color(*NAVY_3)
        pdf.set_line_width(0.003)
        pdf.line(M_LEFT, y + 0.45, W - M_RIGHT, y + 0.45)
        y += 0.65
    pdf.draw_pull_quote('A world the user can actually play in - not a button-click visual novel.', 7.8, size=14)
    pdf.draw_footer(section='Tech stack')

    # =========================================================
    # SLIDE 13: GET INVOLVED
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    # Brand mark centered
    brand_h = pdf.draw_brand_image(W/2 - 1.4, 1.5, 2.8)
    pdf.draw_eyebrow('Thank you', 4.7, color=BRASS_L, align='C')
    pdf.draw_title('Get involved', 5.1, size=42, color=BRASS_L, align='C')
    pdf.draw_divider(6.0, weight=0.015, width=2.5)
    pdf.draw_subtitle('pocketplot.app', 6.4, size=20, color=AMBER, italic=False, align='C')
    pdf.draw_subtitle('Try the public /seed prompt generator  -  Read the open HANDOFF.md', 7.0, size=13, italic=True, align='C')
    pdf.draw_subtitle('Reach out: hello@pocketplot.app', 7.6, size=11, color=INK_MUTED, italic=True, align='C')
    # Footer
    pdf.set_text_color(*INK_FAINT)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_xy(M_LEFT, H - 0.48)
    pdf.cell(w=CONTENT_W, h=0.2, txt='PocketPlot Universe  -  Pitch deck v23  -  Page 13 / 14', align='C')

    # =========================================================
    # SLIDE 14: COLOPHON
    # =========================================================
    pdf.add_slide()
    pdf.draw_corner_brackets()
    pdf.draw_brand_header()
    pdf.draw_eyebrow('Colophon', 1.6, align='L')
    pdf.draw_title('About this deck', 1.95, size=30, color=INK, align='L')
    pdf.draw_divider(2.75, weight=0.008, width=3.0)
    # Body
    body_lines = [
        'This deck was generated programmatically from a single Python script.',
        '',
        'Typography: Helvetica family (fpdf2 core fonts).',
        'Brand mark: an illustration you provided (split-book character).',
        'Palette: Tech-Victorian - deep navy, brass, amber, cream, emerald.',
        'Format: 1280 x 720 pts (16:9 widescreen).',
        '',
        'The script lives in the project root as build_pitch_deck_ad.py.',
        'Regenerate with: python3 build_pitch_deck_ad.py',
        '',
        'The full platform source is at /root/pocketplot/v23-final.zip.',
    ]
    y = 3.4
    for line in body_lines:
        if line == '':
            y += 0.15
            continue
        # Italic lines
        is_quote = line.startswith('"') or line.startswith('Regenerate') or line.startswith('The full')
        pdf.set_text_color(*INK_MUTED if is_quote else INK)
        pdf.set_font('Helvetica', 'I' if is_quote else '', 12)
        wrapped = pdf._wrap(line, CONTENT_W, 'Helvetica', 'I' if is_quote else '', 12)
        line_h = 12 / 72 * 1.5
        for w_line in wrapped:
            pdf.set_xy(M_LEFT, y)
            pdf.cell(w=CONTENT_W, h=line_h, txt=w_line, align='L')
            y += line_h
    # Footer
    pdf.draw_footer(section='Colophon')

    out = '/root/pocketplot/pitch_deck_v23_ad.pdf'
    pdf.output(out)
    return out


if __name__ == '__main__':
    out = build_deck()
    import os
    print(f'Written: {out} - {os.path.getsize(out)} bytes ({os.path.getsize(out)/1024:.0f} KB)')