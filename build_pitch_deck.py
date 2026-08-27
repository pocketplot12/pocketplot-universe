"""
PocketPlot Universe - pitch deck (v23).

Generates a 10-slide PDF pitch deck that explains:
  1. Cover slide (with the brand mark)
  2. What is PocketPlot?
  3. Who is it for?
  4. Core features (the big three)
  5. The two game modes (PLAY + READ)
  6. Engagement & community
  7. Exports (PDF, EPUB, Bulk ZIP)
  8. The visual identity
  9. Roadmap (v24 + v25)
 10. Tech stack + call to action

Output: /tmp/pp_pitch_deck.pdf
"""
from fpdf import FPDF
from PIL import Image
import os

# Load the brand mark
BRAND_PATH = '/root/pocketplot/logo-halo-600.png'
if not os.path.exists(BRAND_PATH):
    BRAND_PATH = '/root/pocketplot/logo-600.png'

# Colors (RGB)
NAVY = (10, 15, 28)
NAVY_2 = (21, 36, 63)
BRASS = (201, 160, 78)
BRASS_L = (232, 200, 121)
AMBER = (240, 181, 74)
AMBER_L = (255, 212, 122)
CREAM = (243, 233, 210)
CREAM_W = (232, 216, 184)
INK = (243, 233, 210)
INK_MUTED = (158, 182, 212)
INK_FAINT = (122, 138, 168)
EMERALD = (29, 107, 80)

# Slide size: 16:9 widescreen (17.78 x 10 inches at 72dpi)
# But fpdf2 wants (height, width), so this is (W, H) for our coordinate system
# even though format=(H, W) is passed
W, H = 17.78, 10


class SlidePDF(FPDF):
    """Custom FPDF subclass that draws Tech-Victorian styled slides."""
    def __init__(self):
        # fpdf2 format tuple is (HEIGHT, WIDTH) - opposite to what I assumed!
        # For landscape 17.78x10 inches, we pass (10, 17.78) and orientation='L'
        super().__init__(orientation='L', unit='in', format=(10, 17.78))
        self.set_auto_page_break(auto=False)
        self.set_margins(0.4, 0.4, 0.4)
        self.current_slide = 0

    def header(self):
        pass  # no auto header

    def add_slide(self):
        self.add_page()
        self.current_slide += 1
        # Background: deep navy with subtle radial gradient (we use a base fill)
        self.set_fill_color(*NAVY)
        self.rect(0, 0, W, H, 'F')

    def draw_gold_line(self, x1, y1, x2, y2, weight=0.01):
        self.set_draw_color(*BRASS)
        self.set_line_width(weight)
        self.line(x1, y1, x2, y2)

    def draw_brand_mark(self, x, y, size=1.5):
        """Embed the brand image at (x, y) with the given size in inches."""
        if os.path.exists(BRAND_PATH):
            self.image(BRAND_PATH, x, y, w=size, h=size * 0.93)
        else:
            # Fallback: just a circle
            self.set_fill_color(*BRASS)
            self.ellipse(x, y, size, size, 'F')

    def draw_text_hero(self, text, y, color=None, font='Helvetica', style='B', size=42):
        if color is None:
            color = INK
        self.set_text_color(*color)
        self.set_font(font, style, size)
        # Split text if it overflows
        words = text.split()
        lines = []
        cur = []
        max_w = W - 1.2
        for w in words:
            test = ' '.join(cur + [w])
            if self.get_string_width(test) > max_w:
                if cur:
                    lines.append(' '.join(cur))
                    cur = [w]
                else:
                    lines.append(w)
            else:
                cur.append(w)
        if cur:
            lines.append(' '.join(cur))
        # Center as a block
        line_h = 0.6
        total_h = len(lines) * line_h
        start_y = y
        for i, line in enumerate(lines):
            self.set_xy(0.6, start_y + i * line_h)
            self.cell(w=W - 1.2, h=line_h, txt=line, align='C')

    def draw_text_subhead(self, text, y, color=None, size=22):
        if color is None:
            color = INK_MUTED
        self.set_text_color(*color)
        self.set_font('Helvetica', '', size)
        words = text.split()
        lines = []
        cur = []
        max_w = W - 1.2
        for w in words:
            test = ' '.join(cur + [w])
            if self.get_string_width(test) > max_w:
                if cur:
                    lines.append(' '.join(cur))
                    cur = [w]
                else:
                    lines.append(w)
            else:
                cur.append(w)
        if cur:
            lines.append(' '.join(cur))
        line_h = 0.4
        for i, line in enumerate(lines):
            self.set_xy(0.6, y + i * line_h)
            self.cell(w=W - 1.2, h=line_h, txt=line, align='C')

    def draw_text_left(self, text, x, y, color=None, font='Helvetica', style='', size=14, w=None):
        if color is None:
            color = INK
        if w is None:
            w = W - 1.2
        self.set_text_color(*color)
        self.set_font(font, style, size)
        self.set_xy(x, y)
        self.cell(w=w, h=0.3, txt=text, align='L')

    def draw_text_title(self, text, y, size=32, color=None):
        if color is None:
            color = INK
        self.set_text_color(*color)
        self.set_font('Helvetica', 'B', size)
        words = text.split()
        lines = []
        cur = []
        max_w = W - 1.2
        for w in words:
            test = ' '.join(cur + [w])
            if self.get_string_width(test) > max_w:
                if cur:
                    lines.append(' '.join(cur))
                    cur = [w]
                else:
                    lines.append(w)
            else:
                cur.append(w)
        if cur:
            lines.append(' '.join(cur))
        line_h = 0.5
        for i, line in enumerate(lines):
            self.set_xy(0.6, y + i * line_h)
            self.cell(w=W - 1.2, h=line_h, txt=line, align='C')

    def draw_eyebrow(self, text, y, color=None):
        if color is None:
            color = BRASS_L
        self.set_text_color(*color)
        self.set_font('Helvetica', '', 9)
        self.set_xy(0.6, y)
        self.cell(w=W - 1.2, h=0.2, txt=text.upper(), align='C')

    def draw_centered_multi(self, text, x, y, w, color, font, style, size, line_h=0.3, align='L'):
        """Render multi_cell text but center the resulting block horizontally."""
        self.set_text_color(*color)
        self.set_font(font, style, size)
        # Wrap lines manually to fit width
        words = text.split()
        lines = []
        cur = []
        for wd in words:
            test = ' '.join(cur + [wd])
            if self.get_string_width(test) > w:
                if cur:
                    lines.append(' '.join(cur))
                    cur = [wd]
                else:
                    lines.append(wd)
            else:
                cur.append(wd)
        if cur:
            lines.append(' '.join(cur))
        for i, line in enumerate(lines):
            line_w = self.get_string_width(line)
            line_x = x + (w - line_w) / 2
            self.set_xy(line_x, y + i * line_h)
            self.cell(w=line_w, h=line_h, txt=line, align='L')

    def draw_decorative_bracket(self):
        """Brass corner ornaments."""
        self.set_draw_color(*BRASS)
        self.set_line_width(0.012)
        # Top-left
        self.line(0.3, 0.3, 0.7, 0.3)
        self.line(0.3, 0.3, 0.3, 0.7)
        BRASS_D = (138, 106, 38)
        self.set_draw_color(*BRASS_D)
        self.line(0.36, 0.36, 0.7, 0.36)
        self.line(0.36, 0.36, 0.36, 0.7)
        # Top-right
        self.line(W - 0.3, 0.3, W - 0.7, 0.3)
        self.line(W - 0.3, 0.3, W - 0.3, 0.7)
        # Bottom-left
        self.line(0.3, H - 0.3, 0.7, H - 0.3)
        self.line(0.3, H - 0.3, 0.3, H - 0.7)
        # Bottom-right
        self.line(W - 0.3, H - 0.3, W - 0.7, H - 0.3)
        self.line(W - 0.3, H - 0.3, W - 0.3, H - 0.7)

    def draw_footer(self, slide_num, total):
        """Subtle page number + colophon."""
        self.set_text_color(*INK_FAINT)
        self.set_font('Helvetica', '', 8)
        self.set_xy(0.4, H - 0.35)
        self.cell(w=3, h=0.2, txt='PocketPlot Universe - PocketPitch v23', align='L')
        self.set_xy(W - 1.5, H - 0.35)
        self.cell(w=1.1, h=0.2, txt=f'{slide_num} / {total}', align='R')


def build_deck():
    pdf = SlidePDF()
    TOTAL = 10

    # ============================================
    # SLIDE 1: COVER
    # ============================================
    pdf.add_slide()
    pdf.draw_decorative_bracket()
    # Brand mark big in the center
    pdf.draw_brand_mark(W/2 - 1.6, 1.4, 3.2)
    pdf.draw_eyebrow('PocketPlot Universe', 5.2)
    pdf.draw_text_hero('Create. Roleplay. Explore.', 5.7, color=BRASS_L, size=42)
    pdf.draw_text_subhead('Premium storytelling for adults - 18+', 6.6, color=INK_MUTED, size=18)
    # Brass divider
    pdf.draw_gold_line(W/2 - 2.5, 7.5, W/2 + 2.5, 7.5, weight=0.015)
    pdf.draw_text_subhead('Pitch deck - v23', 7.7, color=BRASS, size=14)
    pdf.draw_footer(1, TOTAL)

    # ============================================
    # SLIDE 2: WHAT IS POCKETPLOT?
    # ============================================
    pdf.add_slide()
    pdf.draw_decorative_bracket()
    pdf.draw_eyebrow('What is PocketPlot?', 0.7)
    pdf.draw_text_title('A premium storytelling platform for adults.', 1.1)
    pdf.draw_gold_line(W/2 - 1.5, 1.9, W/2 + 1.5, 1.9, weight=0.01)
    # Two columns
    col1_x, col2_x = 0.8, W/2 + 0.3
    col_w = (W - 1.6) / 2 - 0.2
    # Column 1
    pdf.set_text_color(*BRASS_L)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_xy(col1_x, 2.4)
    pdf.cell(w=col_w, h=0.3, txt='A creative writing studio')
    pdf.set_text_color(*INK)
    pdf.set_font('Helvetica', '', 12)
    pdf.set_xy(col1_x, 2.8)
    pdf.multi_cell(w=col_w, h=0.3, txt="Generate original branching stories with consistent scene art. Every story is procedurally assembled from in-house word pools -- no two stories are alike.")
    pdf.set_xy(col1_x, 4.0)
    pdf.multi_cell(w=col_w, h=0.3, txt="Choose from 16 genres, set the tone, describe your character and objective -- the engine composes a full branching world with scene-by-scene illustrations.")
    # Column 2
    pdf.set_text_color(*BRASS_L)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_xy(col2_x, 2.4)
    pdf.cell(w=col_w, h=0.3, txt='A social storytelling network')
    pdf.set_text_color(*INK)
    pdf.set_font('Helvetica', '', 12)
    pdf.set_xy(col2_x, 2.8)
    pdf.multi_cell(w=col_w, h=0.3, txt="Share stories via QR code or short link. Readers can play through (game mode) or read through (manga mode) -- no account required.")
    pdf.set_xy(col2_x, 4.0)
    pdf.multi_cell(w=col_w, h=0.3, txt="Public profiles, likes, follow graph, leaderboards. Creators see views, plays, completions, and words written for every story.")
    # Tagline
    pdf.set_text_color(*AMBER)
    pdf.set_font('Helvetica', 'I', 16)
    pdf.set_xy(0.6, 7.4)
    pdf.cell(w=W - 1.2, h=0.4, txt='"A world the user can actually play in -- not a button-click visual novel."', align='C')
    pdf.draw_footer(2, TOTAL)

    # ============================================
    # SLIDE 3: WHO IS IT FOR?
    # ============================================
    pdf.add_slide()
    pdf.draw_decorative_bracket()
    pdf.draw_eyebrow('Who is it for?', 0.7)
    pdf.draw_text_title('Three audiences, one platform.', 1.1)
    pdf.draw_gold_line(W/2 - 1.5, 1.9, W/2 + 1.5, 1.9, weight=0.01)
    # Three columns
    col_w = (W - 1.6) / 3 - 0.2
    for i, (icon, title, body) in enumerate([
        ('Writing', 'Writers & worldbuilders',
         'Outline a world, pick a tone, and the engine generates a full branching narrative. Scene art generated to match. Export to EPUB, PDF, or share a playable link.'),
        ('Tabletop', 'Roleplayers & GMs',
         'Bring your own AI engine (BYOB). Run campaigns, share worlds as game links. Players can play through with their own choices -- no sign-up needed.'),
        ('Reader', 'Readers & players',
         'Discover public stories. Play them as visual novels or read them as manga-style pages. Like, follow, and track your reading stats.'),
    ]):
        x = 0.6 + i * (col_w + 0.3)
        pdf.set_text_color(*AMBER)
        pdf.set_font('Helvetica', 'B', 36)
        pdf.set_xy(x, 2.4)
        pdf.cell(w=col_w, h=0.7, txt=icon, align='C')
        pdf.set_text_color(*BRASS_L)
        pdf.set_font('Helvetica', 'B', 15)
        pdf.set_xy(x, 3.4)
        pdf.cell(w=col_w, h=0.4, txt=title, align='C')
        pdf.set_text_color(*INK)
        pdf.set_font('Helvetica', '', 11)
        pdf.set_xy(x, 4.0)
        pdf.multi_cell(w=col_w, h=0.3, txt=body, align='L')
    pdf.draw_footer(3, TOTAL)

    # ============================================
    # SLIDE 4: CORE FEATURES (THE BIG THREE)
    # ============================================
    pdf.add_slide()
    pdf.draw_decorative_bracket()
    pdf.draw_eyebrow('Core features', 0.7)
    pdf.draw_text_title('Three things that make PocketPlot different.', 1.1)
    pdf.draw_gold_line(W/2 - 2, 1.9, W/2 + 2, 1.9, weight=0.01)
    # Three big features as cards
    features = [
        ('01', 'Branching-first',
         'Every world is a graph, not a list. Each scene has 2-3 choices that branch the story. The same world can be played hundreds of times with different paths.', BRASS),
        ('02', 'BYOB',
         'Bring Your Own Brain. Connect your own OpenAI-compatible LLM (OpenAI, Anthropic via proxy, OpenRouter, Ollama). The platform handles content moderation on the response side.', AMBER),
        ('03', 'Consistent scene art',
         'Every scene gets a procedurally-composed SVG illustration matched to the genre, tone, and story state. Visual continuity without paying per image.', BRASS_L),
    ]
    card_w = (W - 1.6) / 3 - 0.2
    for i, (num, title, body, accent) in enumerate(features):
        x = 0.6 + i * (card_w + 0.3)
        # Card background
        pdf.set_fill_color(*NAVY_2)
        pdf.rect(x, 2.4, card_w, 4.2, 'F')
        # Top accent line
        pdf.set_draw_color(*accent)
        pdf.set_line_width(0.025)
        pdf.line(x, 2.4, x + card_w, 2.4)
        # Number
        pdf.set_text_color(*accent)
        pdf.set_font('Helvetica', 'B', 42)
        pdf.set_xy(x + 0.1, 2.6)
        pdf.cell(w=card_w - 0.2, h=0.7, txt=num, align='C')
        # Title
        pdf.set_text_color(*INK)
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_xy(x + 0.1, 3.4)
        pdf.cell(w=card_w - 0.2, h=0.4, txt=title, align='C')
        # Body
        pdf.set_text_color(*CREAM_W)
        pdf.set_font('Helvetica', '', 11)
        pdf.set_xy(x + 0.15, 4.0)
        pdf.multi_cell(w=card_w - 0.3, h=0.3, txt=body, align='L')
    pdf.draw_footer(4, TOTAL)

    # ============================================
    # SLIDE 5: TWO GAME MODES
    # ============================================
    pdf.add_slide()
    pdf.draw_decorative_bracket()
    pdf.draw_eyebrow('Two ways to play', 0.7)
    pdf.draw_text_title('Every story, two surfaces.', 1.1)
    pdf.draw_gold_line(W/2 - 2, 1.9, W/2 + 2, 1.9, weight=0.01)
    # Two side-by-side cards
    card_w = (W - 1.6) / 2 - 0.2
    card_h = 5.5
    # PLAY mode
    x = 0.6
    pdf.set_fill_color(*NAVY_2)
    pdf.rect(x, 2.4, card_w, card_h, 'F')
    pdf.set_draw_color(*AMBER)
    pdf.set_line_width(0.03)
    pdf.line(x, 2.4, x + card_w, 2.4)
    pdf.set_text_color(*AMBER)
    pdf.set_font('Helvetica', 'B', 22)
    pdf.set_xy(x, 2.6)
    pdf.cell(w=card_w, h=0.4, txt='PLAY MODE', align='C')
    pdf.set_text_color(*INK)
    pdf.set_font('Helvetica', 'I', 13)
    pdf.set_xy(x, 3.1)
    pdf.cell(w=card_w, h=0.3, txt='Visual novel. Choices. Branching.', align='C')
    pdf.set_text_color(*CREAM_W)
    pdf.set_font('Helvetica', '', 11)
    play_bullets = (
        "- Numbered choice buttons\n"
        "- Each choice advances the player session\n"
        "- Progress bar (chapter X of Y)\n"
        "- Completion banner when finished\n"
        "- 'See world map' link\n"
        "- Stored as a session cookie + DB row\n"
        "- Player path tracked: [ep1, ep3, ep5, ...]"
    )
    pdf.draw_centered_multi(play_bullets, x + 0.2, 3.6, card_w - 0.4, CREAM_W, 'Helvetica', '', 11, line_h=0.3)
    # READ mode
    x = W/2 + 0.4
    pdf.set_fill_color(*NAVY_2)
    pdf.rect(x, 2.4, card_w, card_h, 'F')
    pdf.set_draw_color(*BRASS)
    pdf.set_line_width(0.03)
    pdf.line(x, 2.4, x + card_w, 2.4)
    pdf.set_text_color(*BRASS)
    pdf.set_font('Helvetica', 'B', 22)
    pdf.set_xy(x, 2.6)
    pdf.cell(w=card_w, h=0.4, txt='READ MODE', align='C')
    pdf.set_text_color(*INK)
    pdf.set_font('Helvetica', 'I', 13)
    pdf.set_xy(x, 3.1)
    pdf.cell(w=card_w, h=0.3, txt='Manga / storybook. Read-only.', align='C')
    pdf.set_text_color(*CREAM_W)
    pdf.set_font('Helvetica', '', 11)
    read_bullets = (
        "- One page per episode\n"
        "- Art panel + italic narration\n"
        "- 1-2 speech bubbles (speaker inferred)\n"
        "- Page-flip CSS animation\n"
        "- Keyboard nav: left/right arrows\n"
        "- Cream parchment background\n"
        "- No sign-up needed for the player"
    )
    pdf.draw_centered_multi(read_bullets, x + 0.2, 3.6, card_w - 0.4, CREAM_W, 'Helvetica', '', 11, line_h=0.3)
    pdf.draw_footer(5, TOTAL)

    # ============================================
    # SLIDE 6: WORLD MAP
    # ============================================
    pdf.add_slide()
    pdf.draw_decorative_bracket()
    pdf.draw_eyebrow('The world map', 0.7)
    pdf.draw_text_title('Scenes as nodes. Choices as edges.', 1.1)
    pdf.draw_gold_line(W/2 - 2, 1.9, W/2 + 2, 1.9, weight=0.01)
    # Center the brand mark on the right
    pdf.draw_brand_mark(W - 4.2, 2.6, 3.6)
    # Text on the left
    pdf.set_text_color(*BRASS_L)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_xy(0.6, 2.6)
    pdf.cell(w=W/2 - 0.4, h=0.3, txt='A Minecraft-style foundation')
    pdf.set_text_color(*CREAM_W)
    pdf.set_font('Helvetica', '', 12)
    pdf.set_xy(0.6, 3.0)
    pdf.multi_cell(w=W/2 - 0.4, h=0.3, txt=
        "- Each scene = one node on a 2D map\n"
        "- Visited scenes glow with amber light\n"
        "- Click a node to enter that scene\n"
        "- Linear graph synthesis when no author data\n"
        "- Custom placement in v24 (scene_nodes_json)\n"
        "- Foundation for full Minecraft-style navigation", align='L')
    pdf.draw_footer(6, TOTAL)

    # ============================================
    # SLIDE 7: ENGAGEMENT & COMMUNITY
    # ============================================
    pdf.add_slide()
    pdf.draw_decorative_bracket()
    pdf.draw_eyebrow('Engagement & community', 0.7)
    pdf.draw_text_title('Built for sharing, built for retention.', 1.1)
    pdf.draw_gold_line(W/2 - 2, 1.9, W/2 + 2, 1.9, weight=0.01)
    # Two columns
    col_w = (W - 1.6) / 2 - 0.2
    # Engagement
    pdf.set_text_color(*BRASS_L)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_xy(0.6, 2.4)
    pdf.cell(w=col_w, h=0.3, txt='Engagement loop')
    pdf.set_text_color(*INK)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_xy(0.6, 2.8)
    pdf.multi_cell(w=col_w, h=0.3, txt=
        "- Like a story (1-tap, persisted)\n"
        "- Per-world stats: views, plays, completions, likes, words\n"
        "- Continue-the-story prompt on every episode\n"
        "- Chapter progress bar\n"
        "- Milestone emails (1st story, 10 words, 100, 1k, 10k)\n"
        "- Weekly summary email for Pro + Creator", align='L')
    # Community
    pdf.set_text_color(*BRASS_L)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_xy(W/2 + 0.4, 2.4)
    pdf.cell(w=col_w, h=0.3, txt='Community')
    pdf.set_text_color(*INK)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_xy(W/2 + 0.4, 2.8)
    pdf.multi_cell(w=col_w, h=0.3, txt=
        "- Public profile at /u/<username>\n"
        "- 3 featured stories per profile\n"
        "- Follow graph (followers + following)\n"
        "- Notifications: new follower, story shared with you\n"
        "- Share token system (one world, many links)\n"
        "- QR code generation for every share link", align='L')
    pdf.draw_footer(7, TOTAL)

    # ============================================
    # SLIDE 8: EXPORTS
    # ============================================
    pdf.add_slide()
    pdf.draw_decorative_bracket()
    pdf.draw_eyebrow('Exports', 0.7)
    pdf.draw_text_title('Take it with you. In any format.', 1.1)
    pdf.draw_gold_line(W/2 - 2, 1.9, W/2 + 2, 1.9, weight=0.01)
    formats = [
        ('PDF', 'PDF', 'Cover page + all chapters in one document. Use the existing pdf_gen.py pipeline.'),
        ('Reader', 'EPUB', 'Standard e-reader format. Cover + TOC + per-chapter XHTML. Hand-rolled, no library dep.'),
        ('ZIP', 'Bulk ZIP', 'manifest.json + README + one .md per episode (chapters/00N-chapter-N.md).'),
        ('Link', 'Share link', 'A short URL + QR code. The recipient plays or reads in their browser -- no sign-up.'),
    ]
    for i, (icon, name, body) in enumerate(formats):
        x = 0.6 + (i % 4) * ((W - 1.2) / 4 + 0.05)
        # Icon
        pdf.set_text_color(*AMBER)
        pdf.set_font('Helvetica', 'B', 36)
        pdf.set_xy(x, 2.6)
        pdf.cell(w=(W - 1.2) / 4, h=0.7, txt=icon, align='C')
        # Name
        pdf.set_text_color(*BRASS_L)
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_xy(x, 3.4)
        pdf.cell(w=(W - 1.2) / 4, h=0.3, txt=name, align='C')
        # Body
        pdf.set_text_color(*INK)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_xy(x, 3.9)
        pdf.multi_cell(w=(W - 1.2) / 4, h=0.3, txt=body, align='C')
    pdf.draw_footer(8, TOTAL)

    # ============================================
    # SLIDE 9: ROADMAP
    # ============================================
    pdf.add_slide()
    pdf.draw_decorative_bracket()
    pdf.draw_eyebrow('Roadmap', 0.7)
    pdf.draw_text_title('The path to a Minecraft-style world.', 1.1)
    pdf.draw_gold_line(W/2 - 2, 1.9, W/2 + 2, 1.9, weight=0.01)
    # Timeline of versions
    versions = [
        ('v22 OK', 'Tech-Victorian visual identity + brand mark', CREAM),
        ('v23 OK', 'Engagement, community, exports, PWA, READ mode', BRASS_L),
        ('v24', 'Inventory, build mode, real node-graph editor,\nVAPID push delivery, custom world-map coordinates', AMBER),
        ('v25', 'Real-time multiplayer, native iOS/Android shells,\nAI-generated manga art (v.s. our SVG)', BRASS),
    ]
    y = 2.6
    for v, desc, color in versions:
        # Badge
        pdf.set_text_color(*color)
        pdf.set_font('Helvetica', 'B', 22)
        pdf.set_xy(0.8, y)
        pdf.cell(w=1.5, h=0.4, txt=v, align='L')
        # Description
        pdf.set_text_color(*INK)
        pdf.set_font('Helvetica', '', 12)
        pdf.set_xy(2.6, y + 0.05)
        pdf.multi_cell(w=W - 3.4, h=0.3, txt=desc, align='L')
        y += 1.3
    pdf.draw_footer(9, TOTAL)

    # ============================================
    # SLIDE 10: TECH STACK + CTA
    # ============================================
    pdf.add_slide()
    pdf.draw_decorative_bracket()
    pdf.draw_eyebrow('Tech stack + call to action', 0.7)
    pdf.draw_text_title('Single-file Flask. No vendor lock-in.', 1.1)
    pdf.draw_gold_line(W/2 - 2, 1.9, W/2 + 2, 1.9, weight=0.01)
    # Tech stack grid
    pdf.set_text_color(*BRASS_L)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_xy(0.6, 2.5)
    pdf.cell(w=W - 1.2, h=0.3, txt='TECH STACK', align='L')
    pdf.set_text_color(*INK)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_xy(0.6, 2.9)
    pdf.multi_cell(w=W - 1.2, h=0.3, txt=
        "Backend:  Python 3.13 + Flask (single app.py, ~9,000 lines) + APScheduler + sqlite3\n"
        "Frontend: server-rendered HTML + inline CSS + Jinja2 templates (no SPA, no build step)\n"
        "Storage:  SQLite (single file) + outbox-folder email + JSON column metadata\n"
        "AI:       procedural generator (default) + OpenAI-compatible BYOB (Creator tier)\n"
        "Mobile:   PWA (manifest + service worker) -> install on iOS/Android home screen", align='L')
    # CTA
    y = 5.4
    pdf.set_text_color(*BRASS_L)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_xy(0.6, y)
    pdf.cell(w=W - 1.2, h=0.3, txt='GET INVOLVED', align='C')
    pdf.set_text_color(*CREAM_W)
    pdf.set_font('Helvetica', '', 12)
    pdf.set_xy(0.6, y + 0.4)
    pdf.cell(w=W - 1.2, h=0.3, txt='pocketplot.app  -  Try the public /seed prompt generator  -  Read the open HANDOFF.md', align='C')
    pdf.set_text_color(*AMBER)
    pdf.set_font('Helvetica', 'I', 14)
    pdf.set_xy(0.6, y + 0.9)
    pdf.cell(w=W - 1.2, h=0.4, txt='"A world the user can actually play in -- not a button-click visual novel."', align='C')
    pdf.draw_footer(10, TOTAL)

    # Output
    out = '/tmp/pp_pitch_deck.pdf'
    pdf.output(out)
    return out


if __name__ == '__main__':
    out = build_deck()
    import os
    print(f'Written: {out} - {os.path.getsize(out)} bytes ({os.path.getsize(out)/1024:.0f} KB)')