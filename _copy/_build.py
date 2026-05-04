"""
Per-page copy export — generates one .txt file per live HTML page.

Each export contains:
  - Page meta (title + description) with word counts
  - All visible copy organized by section/role (H1..H3, body, eyebrows,
    buttons, list items, pull-quotes, meta-rows, counters, etc.) with
    word counts
  - Image inventory with src, alt, file size, pixel dimensions, and any
    DRAFT comments about the image
  - Loose-end notes (DRAFT / TODO / PLACEHOLDER comments harvested from
    the HTML source)

Run: python3 _copy/_build.py
"""
import re, html, pathlib, subprocess
from collections import OrderedDict

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT  = pathlib.Path(__file__).resolve().parent

LIVE_PAGES = [
    'index.html',
    'about.html',
    'services.html',
    'service-details.html',
    'portfolio.html',
    'client-stories-advia.html',
    'client-stories-nwfcu.html',
    'client-stories-harvard.html',
    'client-stories-capcom.html',
    'client-stories-jdcu.html',
    'blog.html',
    'blog-details.html',
    'team.html',
    'team-details.html',
    'team-details-matt.html',
    'team-details-jim.html',
    'team-details-john.html',
    'team-details-laurie.html',
    'contact.html',
    'faq.html',
    '404.html',
]

def strip_tags(s):
    return re.sub(r'<[^>]+>', '', s)

def clean(s):
    s = html.unescape(strip_tags(s))
    return re.sub(r'\s+', ' ', s).strip()

def wc(s):
    return len([w for w in re.split(r'\s+', s) if w])

# ────────────────────────────────────────────────────────
# Image dimension helper (macOS sips)
# ────────────────────────────────────────────────────────
def img_dims(path):
    full = ROOT / path
    if not full.exists():
        return None, None
    try:
        out = subprocess.run(
            ['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', str(full)],
            capture_output=True, text=True, timeout=4
        ).stdout
        w = re.search(r'pixelWidth:\s+(\d+)', out)
        h = re.search(r'pixelHeight:\s+(\d+)', out)
        return (int(w.group(1)), int(h.group(1))) if w and h else (None, None)
    except Exception:
        return None, None

def img_size_kb(path):
    full = ROOT / path
    return round(full.stat().st_size / 1024) if full.exists() else None

# ────────────────────────────────────────────────────────
# Strip header/footer/aside from content scope so we don't
# repeat the sitewide nav/footer copy on every page export.
# ────────────────────────────────────────────────────────
def isolate_main(src):
    """Return only the main content of the page (between <main>...</main>)
    if present, otherwise return everything inside <body>."""
    m = re.search(r'<main\b[^>]*>(.*?)</main>', src, re.S)
    if m:
        return m.group(1)
    m = re.search(r'<body\b[^>]*>(.*?)</body>', src, re.S)
    return m.group(1) if m else src

# ────────────────────────────────────────────────────────
# Extractors
# ────────────────────────────────────────────────────────
def extract_blocks(scope):
    """Extract structured copy blocks in document order."""
    blocks = []  # list of (role, text)

    # Patterns we walk in source order
    PATTERNS = [
        # Page title banner H2
        (r'<h2 class="page-title[^"]*"[^>]*>(.*?)</h2>',  'PAGE TITLE H2'),
        # Section subtitle eyebrows
        (r'<span class="section-subtitle"[^>]*>(.*?)</span>',  'EYEBROW'),
        # Case-study eyebrows + client tags
        (r'<span class="case-eyebrow"[^>]*>(.*?)</span>',  'CASE EYEBROW'),
        (r'<span class="case-client-tag"[^>]*>(.*?)</span>', 'CASE CLIENT TAG'),
        (r'<span class="case-chapter-label"[^>]*>(.*?)</span>', 'CASE CHAPTER LABEL'),
        # Section titles
        (r'<h1 class="section-title[^"]*"[^>]*>(.*?)</h1>',  'H1 (HERO)'),
        (r'<h1[^>]*>(.*?)</h1>',  'H1'),
        (r'<h2 class="section-title[^"]*"[^>]*>(.*?)</h2>',  'H2'),
        (r'<h2 class="title"[^>]*>(.*?)</h2>',  'H2 (block)'),
        (r'<h3 class="title"[^>]*>(.*?)</h3>',  'H3'),
        (r'<h3 class="name"[^>]*>(.*?)</h3>',   'NAME'),
        (r'<span class="post"[^>]*>(.*?)</span>', 'POST/ROLE'),
        # Body paragraphs
        (r'<p class="case-dek"[^>]*>(.*?)</p>', 'DEK'),
        (r'<p class="info-text"[^>]*>(.*?)</p>', 'INTRO'),
        (r'<p class="text(?: text-invert)?"[^>]*>(.*?)</p>',  'BODY'),
        # Button text
        (r'<span class="text-one"[^>]*>(.*?)</span>', 'BUTTON'),
        # Underline link with arrow icon
        (r'<a class="rr-btn-underline"[^>]*>(.*?)<span', 'LINK'),
        (r'<a href="[^"]*" class="rr-btn-underline"[^>]*>(.*?)<span', 'LINK'),
        # Accordion (FAQ) buttons
        (r'<button class="accordion-button[^"]*"[^>]*>(.*?)</button>', 'FAQ Q'),
        # Accordion bodies
        (r'<div class="accordion-body"[^>]*>(.*?)</div>', 'FAQ A'),
        # Pull quotes
        (r'<blockquote[^>]*>(.*?)</blockquote>', 'PULL QUOTE'),
        # Meta items (case study metadata row)
        (r'<div class="meta-item">\s*<p class="title">([^<]*)</p>\s*<p class="text">([^<]*)</p>\s*</div>', 'META ITEM'),
        # Counter / funfact items (about + case-study metrics)
        (r'<div class="funfact-item">\s*<p class="text">([^<]*)</p>\s*<h3 class="number[^"]*"[^>]*>([^<]*)</h3>\s*</div>', 'COUNTER'),
        # Approach pillar bullets
        (r'<div class="approach-list">\s*<ul>(.*?)</ul>\s*</div>', 'PILLAR BULLETS'),
        # Service sub-disciplines
        (r'<ul class="service-list">(.*?)</ul>', 'SERVICE BULLETS'),
        # Award-list style entries
        (r'<ul class="award-list">(.*?)</ul>', 'OUTLET LIST'),
        # Channels strip
        (r'<span class="case-channels-list"[^>]*>(.*?)</span>', 'CHANNELS'),
        # Tags strip
        (r'<div class="tags">(.*?)</div>', 'TAGS'),
        # Info-list (footer meta)
        (r'<div class="info-list">\s*<ul>(.*?)</ul>\s*</div>', 'INFO LIST'),
    ]

    # Build a list of (start_index, role, raw_match) so we can sort by appearance
    found = []
    for pat, role in PATTERNS:
        for m in re.finditer(pat, scope, re.S):
            found.append((m.start(), role, m))

    # Sort by document order, deduplicate overlapping matches by keeping earliest
    found.sort(key=lambda t: t[0])
    seen_spans = []
    for start, role, m in found:
        end = m.end()
        if any(s <= start and end <= e for s, e in seen_spans):
            continue
        seen_spans.append((start, end))

        if role == 'META ITEM':
            label, value = clean(m.group(1)), clean(m.group(2))
            if label or value:
                blocks.append((role, f'{label}: {value}'))
        elif role == 'COUNTER':
            label, value = clean(m.group(1)), clean(m.group(2))
            blocks.append((role, f'{value} — {label}'))
        elif role in ('PILLAR BULLETS', 'SERVICE BULLETS', 'OUTLET LIST', 'INFO LIST'):
            items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), re.S)
            for it in items:
                t = clean(it)
                if t:
                    blocks.append((role, '• ' + t))
        elif role == 'TAGS':
            tags = re.findall(r'<span class="tag"[^>]*>(.*?)</span>', m.group(1), re.S)
            joined = ' · '.join(clean(t) for t in tags if clean(t))
            if joined:
                blocks.append((role, joined))
        else:
            t = clean(m.group(1))
            if t:
                blocks.append((role, t))
    return blocks

def extract_images(scope):
    imgs = []
    for m in re.finditer(r'<img\s+([^>]+?)>', scope):
        attrs = m.group(1)
        src = re.search(r'src="([^"]+)"', attrs)
        alt = re.search(r'alt="([^"]*)"', attrs)
        if not src:
            continue
        s = src.group(1)
        a = alt.group(1) if alt else ''
        if s.startswith('data:'):
            continue
        # Look back ~200 chars for any preceding DRAFT comment
        prelude = scope[max(0, m.start()-300):m.start()]
        draft = re.search(r'<!--\s*DRAFT[^>]*?-->', prelude, re.S)
        flag = clean(draft.group(0).replace('<!--', '').replace('-->', '')).strip() if draft else ''
        imgs.append({
            'src': s,
            'alt': a,
            'flag': flag,
        })
    return imgs

def extract_loose_ends(src):
    """Find DRAFT / TODO / PLACEHOLDER HTML comments anywhere in the source."""
    notes = []
    for m in re.finditer(r'<!--\s*(DRAFT|TODO|PLACEHOLDER|Hero still)[^>]*?-->', src, re.S):
        text = clean(m.group(0).replace('<!--', '').replace('-->', '')).strip()
        if text and text not in notes:
            notes.append(text)
    return notes

def extract_meta(src):
    title = re.search(r'<title[^>]*>(.*?)</title>', src, re.S)
    desc  = re.search(r'<meta name="description" content="([^"]*)"', src)
    return (
        clean(title.group(1)) if title else '',
        desc.group(1).strip() if desc else '',
    )

# ────────────────────────────────────────────────────────
# Per-page exporter
# ────────────────────────────────────────────────────────
def export_page(fname):
    src = (ROOT / fname).read_text()
    title, desc = extract_meta(src)
    main = isolate_main(src)
    blocks = extract_blocks(main)
    imgs   = extract_images(main)
    notes  = extract_loose_ends(src)

    lines = []
    bar = '═' * 70
    lines.append(bar)
    lines.append(f'JXM SITE — COPY EXPORT — {fname}')
    lines.append('Generated 2026-04-28')
    lines.append(bar)
    lines.append('')

    # PAGE META ─────────────────────────────────────────────
    lines.append('PAGE META')
    lines.append('─' * 70)
    lines.append(f'TITLE  [{wc(title)}w]')
    lines.append(f'  {title}')
    lines.append('')
    lines.append(f'META DESCRIPTION  [{wc(desc)}w]')
    lines.append(f'  {desc}')
    lines.append('')

    # COPY BLOCKS ────────────────────────────────────────────
    lines.append('COPY (in document order)')
    lines.append('─' * 70)
    if not blocks:
        lines.append('  (no copy extracted)')
    else:
        for role, text in blocks:
            n = wc(text)
            lines.append(f'[{role}]  [{n}w]')
            # wrap long lines softly for readability
            wrapped = re.sub(r'(.{1,98})(\s|$)', r'  \1\n', text).rstrip()
            lines.append(wrapped)
            lines.append('')

    # IMAGES ─────────────────────────────────────────────────
    lines.append('')
    lines.append('IMAGES')
    lines.append('─' * 70)
    seen_src = set()
    for im in imgs:
        if im['src'] in seen_src:
            continue
        seen_src.add(im['src'])
        w, h = img_dims(im['src'])
        kb = img_size_kb(im['src'])
        size = f'{w}×{h}px' if w and h else 'dimensions unknown'
        weight = f'{kb} KB' if kb is not None else 'file missing'
        lines.append(f'• {im["src"]}')
        lines.append(f'    size:  {size}, {weight}')
        if im['alt']:
            lines.append(f'    alt:   "{im["alt"]}"')
        if im['flag']:
            lines.append(f'    note:  {im["flag"]}')
        lines.append('')
    if not imgs:
        lines.append('  (no images on this page)')
        lines.append('')

    # LOOSE ENDS ─────────────────────────────────────────────
    lines.append('')
    lines.append('LOOSE ENDS / DRAFT NOTES')
    lines.append('─' * 70)
    if not notes:
        lines.append('  (none flagged)')
    else:
        for n in notes:
            lines.append(f'• {n}')
    lines.append('')

    return '\n'.join(lines)

# ────────────────────────────────────────────────────────
# Sitewide / shared elements (extracted once from index.html)
# ────────────────────────────────────────────────────────
def export_sitewide():
    src = (ROOT / 'index.html').read_text()

    # Side drawer (between side toggle start / side toggle end)
    drawer = re.search(r'<!-- side toggle start -->(.*?)<!-- side toggle end -->', src, re.S)
    drawer_blocks = extract_blocks(drawer.group(1)) if drawer else []
    drawer_imgs   = extract_images(drawer.group(1)) if drawer else []

    # Header (between header start/end)
    header = re.search(r'<!-- Header area start -->(.*?)<!-- Header area end -->', src, re.S)
    header_blocks = extract_blocks(header.group(1)) if header else []
    header_imgs   = extract_images(header.group(1)) if header else []

    # Footer (between footer start/end)
    footer = re.search(r'<!-- footer area start[^>]*-->(.*?)<!-- footer area end[^>]*-->', src, re.S)
    footer_blocks = extract_blocks(footer.group(1)) if footer else []
    footer_imgs   = extract_images(footer.group(1)) if footer else []

    # Pull header nav links manually (the extractor doesn't pick up <li><a>)
    header_links = re.findall(r'<li><a href="[^"]*">([^<]+)</a></li>', header.group(1)) if header else []
    footer_links = re.findall(r'<li><a href="[^"]*">([^<]+)</a></li>', footer.group(1)) if footer else []

    lines = []
    bar = '═' * 70
    lines.append(bar)
    lines.append('JXM SITE — COPY EXPORT — 00 SITEWIDE')
    lines.append('Shared elements — appear on every page')
    lines.append('Generated 2026-04-28')
    lines.append(bar)
    lines.append('')

    lines.append('TOP NAV (header)')
    lines.append('─' * 70)
    for link in header_links:
        lines.append(f'• {link}  [{wc(link)}w]')
    lines.append('')

    lines.append('SIDE DRAWER (mobile menu / Let\'s Talk slide-out)')
    lines.append('─' * 70)
    for role, text in drawer_blocks:
        lines.append(f'[{role}]  [{wc(text)}w]')
        lines.append(f'  {text}')
        lines.append('')

    lines.append('FOOTER NAV')
    lines.append('─' * 70)
    for link in footer_links:
        lines.append(f'• {link}  [{wc(link)}w]')
    lines.append('')

    lines.append('FOOTER COPYRIGHT')
    lines.append('─' * 70)
    for role, text in footer_blocks:
        if 'Rights' in text or 'rights' in text or '©' in text:
            lines.append(f'[{role}]  [{wc(text)}w]')
            lines.append(f'  {text}')
            lines.append('')

    lines.append('SHARED IMAGES (logo, favicon, mobile nav icon)')
    lines.append('─' * 70)
    seen = set()
    for im in header_imgs + drawer_imgs + footer_imgs:
        if im['src'] in seen:
            continue
        seen.add(im['src'])
        w, h = img_dims(im['src'])
        kb = img_size_kb(im['src'])
        size = f'{w}×{h}px' if w and h else 'dimensions unknown'
        weight = f'{kb} KB' if kb is not None else 'file missing'
        lines.append(f'• {im["src"]}')
        lines.append(f'    size:  {size}, {weight}')
        if im['alt']:
            lines.append(f'    alt:   "{im["alt"]}"')
        lines.append('')

    return '\n'.join(lines)

# ────────────────────────────────────────────────────────
# Run
# ────────────────────────────────────────────────────────
def main():
    # Sitewide first
    (OUT / '00-sitewide.txt').write_text(export_sitewide())
    print(f'  wrote 00-sitewide.txt')

    # Per-page
    for fname in LIVE_PAGES:
        if not (ROOT / fname).exists():
            print(f'  skip   {fname} (missing)')
            continue
        out_name = fname.replace('.html', '.txt')
        (OUT / out_name).write_text(export_page(fname))
        print(f'  wrote {out_name}')

if __name__ == '__main__':
    main()
