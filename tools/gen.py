"""Generador de contenido UDEP Connect (Reels 1080x1920 y carruseles 1080x1350).

Uso:
    python3 tools/gen.py contenido/2026-11-06-carrusel-licenciaturas.json
    python3 tools/gen.py contenido/archivo.json --preview   # solo fotogramas de prueba

El JSON define "tipo": "reel" | "carrusel", "salida" (ruta sin extension) y "escenas"/"slides".
Ver contenido/*.json como ejemplos.
"""
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
NAVY = (20, 30, 51)
NAVY2 = (31, 45, 76)
ORANGE = (255, 43, 0)      # naranja del logo UDEP Connect
WHITE = (255, 255, 255)
SOFT = (200, 208, 224)

FONT_DIRS = ["/usr/share/fonts/truetype/google-fonts", os.path.join(ROOT, "tools", "fonts")]
def _font_path(name):
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    raise SystemExit(f"No encuentro la fuente {name}")
PB = _font_path("Poppins-Bold.ttf")
PM = _font_path("Poppins-Medium.ttf")
_fc = {}
def F(path, size):
    k = (path, int(size))
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, int(size))
    return _fc[k]

LOGO_W = Image.open(os.path.join(ROOT, "marca", "logo_udep_connect_blanco.png")).convert("RGBA")

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_back(t):
    t = clamp(t); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
def prog(t, s, d): return clamp((t - s) / d)

# ---------------- dibujo base ----------------
def background(W, H, t=0.0):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img, "RGBA")
    off = (t * 40) % 400
    for i in range(-3, 8):
        x = i * 400 + off
        d.polygon([(x, 0), (x + 120, 0), (x + 120 - 700, H), (x - 700, H)], fill=(255, 255, 255, 8))
    k = 8
    mask = Image.new("L", (W // k, H // k), 0)
    gd = ImageDraw.Draw(mask)
    r = (420 + 20 * math.sin(t * 1.5)) / k
    gd.ellipse([W / k - r * 0.9, -r * 0.6, W / k + r * 1.1, r * 1.4], fill=95)
    mask = mask.filter(ImageFilter.GaussianBlur(18)).resize((W, H), Image.BILINEAR)
    img.paste(Image.new("RGB", (W, H), ORANGE), (0, 0), mask)
    return img

def wrap(d, txt, font, maxw):
    out = []
    for para in txt.split("\n"):
        words, line = para.split(), ""
        for w in words:
            test = (line + " " + w).strip()
            if d.textlength(test, font=font) <= maxw or not line:
                line = test
            else:
                out.append(line); line = w
        out.append(line)
    return out

def fit(d, txt, path, size, maxw, minsize=30):
    while size > minsize and d.textlength(txt, font=F(path, size)) > maxw:
        size -= 2
    return F(path, size)

def text_block(d, W, y, txt, font, fill, alpha=255, maxw=None, gap=1.18, align="center", x0=None):
    maxw = maxw or W - 160
    lines = wrap(d, txt, font, maxw)
    for ln in lines:
        w = d.textlength(ln, font=font)
        x = (W - w) / 2 if align == "center" else x0
        d.text((x, y), ln, font=font, fill=fill + (int(alpha),))
        y += font.size * gap
    return y

def pill(d, cx, cy, txt, font, scale=1.0, alpha=255, color=ORANGE):
    if scale <= 0.05: return
    f2 = F(font.path, max(8, font.size * scale))
    tw = d.textlength(txt, font=f2)
    pw, ph = tw + 110 * scale, f2.size * 1.55
    d.rounded_rectangle([cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2], radius=ph / 2,
                        fill=color + (int(alpha),))
    d.text((cx - tw / 2, cy - f2.size * 0.68), txt, font=f2, fill=WHITE + (int(alpha),))

def check_icon(d, x, y, s, alpha):
    d.ellipse([x, y, x + 84 * s, y + 84 * s], fill=ORANGE + (int(alpha),))
    d.line([(x + 22 * s, y + 44 * s), (x + 38 * s, y + 60 * s), (x + 64 * s, y + 28 * s)],
           fill=WHITE + (int(alpha),), width=int(10 * s), joint="curve")

def x_icon(d, x, y, s, alpha):
    d.ellipse([x, y, x + 84 * s, y + 84 * s], fill=(120, 130, 155, int(alpha)))
    d.line([(x + 28 * s, y + 28 * s), (x + 56 * s, y + 56 * s)], fill=WHITE + (int(alpha),), width=int(10 * s))
    d.line([(x + 56 * s, y + 28 * s), (x + 28 * s, y + 56 * s)], fill=WHITE + (int(alpha),), width=int(10 * s))

def paste_logo(img, cx, y, size, alpha=1.0):
    lg = LOGO_W.resize((int(size), int(size)), Image.LANCZOS)
    if alpha < 1:
        lg.putalpha(lg.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(lg, (int(cx - size / 2), int(y)), lg)

def phone(d, cx, cy, s, t, labels, alpha=255):
    pw, ph = 470 * s, 900 * s
    x0, y0 = cx - pw / 2, cy - ph / 2
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=70 * s, fill=(10, 14, 26, alpha),
                        outline=(255, 255, 255, int(alpha * 0.35)), width=int(6 * s))
    sx0, sy0 = x0 + 24 * s, y0 + 60 * s
    sw, sh = pw - 48 * s, ph - 120 * s
    d.rounded_rectangle([sx0, sy0, sx0 + sw, sy0 + sh], radius=40 * s, fill=(245, 246, 250, alpha))
    d.rounded_rectangle([sx0, sy0, sx0 + sw, sy0 + 90 * s], radius=40 * s, fill=NAVY + (alpha,))
    d.rectangle([sx0, sy0 + 50 * s, sx0 + sw, sy0 + 90 * s], fill=NAVY + (alpha,))
    d.text((sx0 + 28 * s, sy0 + 26 * s), "Mi clase", font=F(PB, 30 * s), fill=WHITE + (alpha,))
    vx0, vy0 = sx0 + 24 * s, sy0 + 120 * s
    vw, vh = sw - 48 * s, 300 * s
    d.rounded_rectangle([vx0, vy0, vx0 + vw, vy0 + vh], radius=24 * s, fill=NAVY2 + (alpha,))
    pc = (vx0 + vw / 2, vy0 + vh / 2); r = 50 * s
    d.ellipse([pc[0] - r, pc[1] - r, pc[0] + r, pc[1] + r], fill=ORANGE + (alpha,))
    d.polygon([(pc[0] - 15 * s, pc[1] - 25 * s), (pc[0] - 15 * s, pc[1] + 25 * s), (pc[0] + 28 * s, pc[1])],
              fill=WHITE + (alpha,))
    vals = [0.85, 0.6, 0.72]
    for i, lb in enumerate(labels[:3]):
        yy = vy0 + vh + 50 * s + i * 105 * s
        d.text((vx0, yy), lb, font=F(PM, 26 * s), fill=NAVY + (alpha,))
        d.rounded_rectangle([vx0, yy + 42 * s, vx0 + vw, yy + 60 * s], radius=9 * s, fill=(220, 224, 234, alpha))
        fp = ease_out(prog(t, 0.6 + i * 0.25, 1.2)) * vals[i]
        d.rounded_rectangle([vx0, yy + 42 * s, vx0 + vw * max(fp, 0.04), yy + 60 * s], radius=9 * s,
                            fill=ORANGE + (alpha,))


# ---------------- ilustraciones: dispositivos (estudiar en línea) ----------------
from functools import lru_cache
ILL_SS = 3
INK = (10, 14, 26)
SCREEN = (245, 246, 250)
LINE = (220, 224, 234)
METAL = (200, 208, 224)
METAL2 = (150, 160, 182)
BLUE = (120, 150, 220)
PEACH = (255, 170, 120)
GREEN = (80, 200, 120)
YELLOW = (255, 190, 60)

class _Pen:
    def __init__(s, w, h, ss=ILL_SS):
        s.k, s.w, s.h = ss, w, h
        s.im = Image.new("RGBA", (int(w * ss), int(h * ss)), (0, 0, 0, 0))
        s.sh = Image.new("RGBA", s.im.size, (0, 0, 0, 0))
        s.d, s.sd = ImageDraw.Draw(s.im), ImageDraw.Draw(s.sh)
    def b(s, b): return [v * s.k for v in b]
    def rr(s, b, r, fill, outline=None, width=0):
        s.d.rounded_rectangle(s.b(b), radius=r * s.k, fill=fill, outline=outline, width=int(width * s.k))
    def rect(s, b, fill): s.d.rectangle(s.b(b), fill=fill)
    def el(s, b, fill, outline=None, width=0): s.d.ellipse(s.b(b), fill=fill, outline=outline, width=int(width * s.k))
    def poly(s, pts, fill): s.d.polygon([(x * s.k, y * s.k) for x, y in pts], fill=fill)
    def line(s, pts, fill, width): s.d.line([(x * s.k, y * s.k) for x, y in pts], fill=fill, width=int(width * s.k), joint="curve")
    def arc(s, b, a0, a1, fill, width): s.d.arc(s.b(b), a0, a1, fill=fill, width=int(width * s.k))
    def text_c(s, cx, cy, txt, size, fill):
        f = F(PB, size * s.k); w = s.d.textlength(txt, font=f)
        s.d.text((cx * s.k - w / 2, cy * s.k - size * s.k * 0.68), txt, font=f, fill=fill)
    def shadow(s, b, a=110): s.sd.ellipse(s.b(b), fill=(0, 0, 0, a))
    def done(s):
        sh = s.sh.filter(ImageFilter.GaussianBlur(10 * s.k))
        return Image.alpha_composite(sh, s.im)

def _avatar(p, tile, head, body):
    x0, y0, x1, y1 = tile; H = y1 - y0; cx = (x0 + x1) / 2
    r = H * 0.16; cy = y0 + H * 0.38
    p.el([cx - 1.7 * r, cy + 1.25 * r, cx + 1.7 * r, cy + 3.85 * r], body)
    p.el([cx - r, cy - r, cx + r, cy + r], head)

@lru_cache(None)
def ill_laptop():
    p = _Pen(640, 430)
    p.shadow([40, 380, 600, 425])
    p.rr([70, 0, 570, 350], 22, INK)
    p.rr([86, 16, 554, 332], 10, SCREEN)
    p.rr([86, 16, 554, 54], 10, NAVY); p.rect([86, 40, 554, 54], NAVY)
    for i, c in enumerate([ORANGE, YELLOW, GREEN]):
        p.el([102 + i * 20, 29, 114 + i * 20, 41], c)
    p.rr([100, 66, 400, 252], 10, NAVY2); _avatar(p, [100, 66, 400, 252], PEACH, ORANGE)
    p.rr([112, 78, 166, 98], 10, ORANGE); p.el([120, 84, 128, 92], WHITE)
    cols = [(BLUE, (80, 110, 190)), (PEACH, (230, 120, 80)), ((180, 200, 230), NAVY2)]
    for i in range(3):
        y = 66 + i * 63; tile = [412, y, 540, y + 56]
        p.rr(tile, 8, (225, 229, 238)); _avatar(p, tile, *cols[i])
    p.rr([100, 264, 540, 318], 10, (232, 235, 242))
    for i, c in enumerate([NAVY2, NAVY2, ORANGE]):
        cx = 270 + i * 50; p.el([cx - 16, 275, cx + 16, 307], c)
    p.rr([116, 284, 220, 298], 7, LINE); p.rr([116, 284, 180, 298], 7, ORANGE)
    p.poly([(50, 348), (590, 348), (640, 384), (0, 384)], METAL)
    p.rr([0, 380, 640, 396], 8, METAL2)
    p.rr([270, 348, 370, 358], 5, (175, 183, 203))
    return p.done()

@lru_cache(None)
def ill_monitor():
    p = _Pen(560, 500)
    p.shadow([90, 455, 470, 495])
    p.poly([(245, 355), (315, 355), (332, 458), (228, 458)], (170, 178, 198))
    p.rr([170, 452, 390, 472], 10, METAL2)
    p.rr([0, 0, 560, 362], 22, INK)
    p.rr([14, 14, 546, 332], 10, SCREEN)
    p.rr([14, 14, 110, 332], 10, NAVY); p.rect([60, 14, 110, 332], NAVY)
    for i in range(5):
        p.rr([40, 40 + i * 52, 84, 66 + i * 52], 8, ORANGE if i == 1 else NAVY2)
    p.rr([130, 32, 330, 50], 9, (205, 210, 222)); p.el([500, 28, 526, 54], ORANGE)
    p.rr([130, 70, 300, 232], 14, WHITE)
    p.arc([162, 92, 268, 198], 0, 360, LINE, 16); p.arc([162, 92, 268, 198], -90, 180, ORANGE, 16)
    p.line([(196, 146), (210, 160), (236, 132)], NAVY, 9)
    p.rr([316, 70, 528, 232], 14, WHITE)
    for i, hh in enumerate([60, 95, 75, 120, 100]):
        x = 340 + i * 37; p.rr([x, 214 - hh, x + 22, 214], 6, ORANGE if i == 3 else NAVY2)
    for i in range(2):
        y = 248 + i * 40
        p.rr([130, y, 528, y + 30], 8, WHITE); p.rr([144, y + 10, 300, y + 20], 5, LINE)
        p.rr([400, y + 10, 512, y + 20], 5, LINE); p.rr([400, y + 10, 450 + i * 40, y + 20], 5, ORANGE)
    p.el([273, 340, 287, 354], (40, 48, 70))
    return p.done()

@lru_cache(None)
def ill_phone():
    p = _Pen(280, 570)
    p.shadow([30, 525, 250, 565])
    p.rr([0, 0, 280, 545], 44, INK)
    p.rr([12, 12, 268, 533], 34, SCREEN)
    p.rr([12, 12, 268, 100], 34, NAVY); p.rect([12, 64, 268, 100], NAVY)
    p.rr([110, 22, 170, 34], 6, INK)
    p.el([30, 46, 68, 84], ORANGE); p.rr([82, 52, 180, 64], 6, WHITE); p.rr([82, 72, 140, 80], 4, (150, 160, 190))
    G = (225, 229, 238); T = (180, 186, 200)
    p.rr([26, 118, 196, 166], 18, G); p.rr([42, 132, 170, 142], 5, T); p.rr([42, 148, 130, 156], 4, T)
    p.rr([100, 180, 254, 216], 18, ORANGE); p.rr([116, 193, 236, 203], 5, (255, 200, 185))
    p.rr([26, 230, 214, 290], 18, G); p.rr([42, 244, 196, 254], 5, T); p.rr([42, 266, 150, 276], 5, T)
    p.rr([124, 304, 254, 340], 18, ORANGE); p.rr([140, 317, 234, 327], 5, (255, 200, 185))
    p.rr([26, 356, 104, 392], 18, G)
    for i in range(3): p.el([42 + i * 18, 368, 54 + i * 18, 380], T)
    p.rr([24, 478, 206, 514], 18, WHITE, outline=LINE, width=2)
    p.el([216, 476, 256, 516], ORANGE)
    p.poly([(228, 486), (248, 496), (228, 506), (232, 496)], WHITE)
    return p.done()

@lru_cache(None)
def ill_tablet():
    p = _Pen(460, 350)
    p.shadow([40, 305, 420, 345])
    p.rr([0, 0, 460, 320], 30, INK)
    p.rr([16, 16, 444, 304], 14, SCREEN)
    p.rr([32, 28, 200, 44], 8, LINE); p.el([404, 24, 428, 48], ORANGE)
    thumbs = [NAVY2, ORANGE, BLUE, PEACH, NAVY2, GREEN]
    for r in range(2):
        for c in range(3):
            x = 32 + c * 138; y = 60 + r * 120
            p.rr([x, y, x + 124, y + 108], 12, WHITE)
            p.rr([x + 8, y + 8, x + 116, y + 60], 9, thumbs[r * 3 + c])
            if r * 3 + c in (0, 4):
                cx, cy = x + 62, y + 34
                p.poly([(cx - 9, cy - 13), (cx - 9, cy + 13), (cx + 14, cy)], WHITE)
            p.rr([x + 10, y + 70, x + 104, y + 80], 5, LINE); p.rr([x + 10, y + 88, x + 70, y + 96], 4, LINE)
    return p.done()

@lru_cache(None)
def ill_badge(kind):
    p = _Pen(140, 140)
    p.shadow([20, 30, 120, 135], 90)
    p.el([10, 10, 130, 130], WHITE)
    if kind == "play":
        p.el([34, 34, 106, 106], ORANGE); p.poly([(60, 50), (60, 90), (92, 70)], WHITE)
    elif kind == "cap":
        p.poly([(70, 40), (114, 60), (70, 80), (26, 60)], NAVY)
        p.poly([(44, 70), (96, 70), (96, 92), (70, 102), (44, 92)], NAVY2)
        p.line([(110, 62), (110, 90)], ORANGE, 5); p.el([104, 86, 116, 98], ORANGE)
    elif kind == "wifi":
        for r, w in [(46, 9), (31, 9), (16, 9)]:
            p.arc([70 - r, 88 - r, 70 + r, 88 + r], 220, 320, ORANGE, w)
        p.el([63, 81, 77, 95], ORANGE)
    elif kind == "check":
        p.el([34, 34, 106, 106], ORANGE); p.line([(52, 72), (65, 85), (90, 56)], WHITE, 10)
    elif kind == "247":
        p.text_c(70, 72, "24/7", 34, NAVY)
    elif kind == "chat":
        p.rr([32, 38, 108, 92], 18, ORANGE); p.poly([(46, 88), (46, 106), (66, 90)], ORANGE)
        for i in range(3): p.el([48 + i * 17, 59, 60 + i * 17, 71], WHITE)
    elif kind == "book":
        p.poly([(70, 52), (70, 100), (34, 92), (34, 44)], NAVY2)
        p.poly([(70, 52), (70, 100), (106, 92), (106, 44)], NAVY)
        p.line([(70, 50), (70, 102)], ORANGE, 5)
    return p.done()

ILL = {"laptop": ill_laptop, "monitor": ill_monitor, "phone": ill_phone, "tablet": ill_tablet}
# composiciones (lienzo base 1000x520): (tipo, x, y, ancho)
COMPS = {
    "clase": [("laptop", 150, 60, 640), ("phone", 708, 120, 200), ("b:cap", 40, 40, 120), ("b:play", 850, 10, 110),
              ("b:wifi", 50, 330, 100)],
    "panel": [("monitor", 330, 10, 560), ("tablet", 80, 245, 340), ("b:247", 880, 50, 115), ("b:check", 70, 60, 110)],
    "movil": [("tablet", 90, 140, 440), ("phone", 545, 30, 240), ("b:chat", 820, 80, 120), ("b:book", 40, 40, 110),
              ("b:wifi", 835, 360, 100)],
}

@lru_cache(None)
def _comp_hi(name, q=2):
    C = Image.new("RGBA", (1000 * q, 520 * q), (0, 0, 0, 0))
    for kind, x, y, w in COMPS[name]:
        src = ill_badge(kind[2:]) if kind.startswith("b:") else ILL[kind]()
        h = src.height * w / src.width
        im = src.resize((int(w * q), int(h * q)), Image.LANCZOS)
        C.alpha_composite(im, (int(x * q), int(y * q)))
    return C

@lru_cache(None)
def comp_img(name, w):
    w = int(w); return _comp_hi(name).resize((w, int(w * 0.52)), Image.LANCZOS)

@lru_cache(None)
def badge_img(kind, w):
    return ill_badge(kind).resize((int(w), int(w)), Image.LANCZOS)

def put(img, im, x, y, alpha=1.0):
    if alpha <= 0.01: return
    if alpha < 1:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(im, (int(x), int(y)), im)

@lru_cache(None)
def device_img(kind, h):
    src = ILL[kind](); h = int(h)
    return src.resize((int(src.width * h / src.height), h), Image.LANCZOS)

def device_fit(img, kind, box, dy=0.0, alpha=1.0):
    x0, y0, x1, y1 = box
    src = ILL[kind]()
    h = min(y1 - y0, (x1 - x0) * src.height / src.width)
    im = device_img(kind, h)
    put(img, im, (x0 + x1 - im.width) / 2, (y0 + y1 - im.height) / 2 + dy, alpha)

def badge_row(img, t, kinds, y, t0, size=130, W=1080):
    n = len(kinds); gap = 70
    x = (W - (n * size + (n - 1) * gap)) / 2
    for i, k in enumerate(kinds):
        eb = ease_back(prog(t, t0 + i * 0.15, 0.5))
        put(img, badge_img(k, size), x + i * (size + gap), y + bob(t, i * 1.3) + (1 - eb) * 50, clamp(eb * 1.5))

def comp_fit(img, name, box, dy=0.0, alpha=1.0, minh=150):
    """Dibuja la composición centrada dentro de box=(x0,y0,x1,y1). Si no cabe (alto < minh) no dibuja."""
    x0, y0, x1, y1 = box
    if y1 - y0 < minh: return
    w = min(x1 - x0, (y1 - y0) / 0.52)
    im = comp_img(name, w)
    put(img, im, (x0 + x1 - im.width) / 2, (y0 + y1 - im.height) / 2 + dy, alpha)

# ---------------- escenas de Reel (1080x1920) ----------------
RW, RH = 1080, 1920
# zona segura de Reels: contenido entre y=260 y y=1550

def bob(t, ph, a=10): return a * math.sin(t * 2.2 + ph)

def sc_gancho(t, p, img, d):
    lines = p["lineas"]
    size = p.get("tam", 112)
    # cada linea en un solo renglon: reducir tamaño hasta que todas quepan
    for ln in lines:
        size = min(size, fit(d, ln, PB, size, RW - 140).size)
    f = F(PB, size)
    lh = f.size * 1.2
    y0 = 760 - len(lines) * lh / 2
    ysub = y0 + len(lines) * lh + 65
    if p.get("sub"):
        ysub += len(wrap(d, p["sub"], F(PM, 56), RW - 160)) * 56 * 1.18
    ec = ease_back(prog(t, 0.5, 0.7))
    comp_fit(img, p.get("ilustracion", "clase"), (110, ysub + 30, RW - 110, 1545), dy=(1 - ec) * 250,
             alpha=clamp(ec * 1.5))
    for i, (k, x, y) in enumerate([("play", 120, 300), ("wifi", RW - 250, 330)]):
        eb = ease_back(prog(t, 1.0 + i * 0.25, 0.5))
        put(img, badge_img(k, 130), x, y + bob(t, i * 2) + (1 - eb) * 60, clamp(eb * 1.5))
    d = ImageDraw.Draw(img, "RGBA")
    for i, ln in enumerate(lines):
        e = ease_back(prog(t, 0.15 + i * 0.3, 0.5))
        w = d.textlength(ln, font=f)
        d.text(((RW - w) / 2, y0 + i * lh + (1 - e) * 120), ln, font=f, fill=WHITE + (int(255 * clamp(e)),))
    yb = y0 + len(lines) * lh + 15
    e2 = ease_out(prog(t, 0.9, 0.6))
    d.rounded_rectangle([RW / 2 - 300 * e2, yb, RW / 2 + 300 * e2, yb + 16], radius=8, fill=ORANGE + (255,))
    if p.get("sub"):
        e3 = ease_out(prog(t, 1.3, 0.5))
        text_block(d, RW, yb + 50 + (1 - e3) * 40, p["sub"], F(PM, 56), SOFT, alpha=255 * e3)

def sc_pastilla(t, p, img, d):
    e = ease_out(prog(t, 0.0, 0.45))
    text_block(d, RW, 300 + (1 - e) * 60, p["titulo"], F(PB, 96), WHITE, alpha=255 * e)
    e2 = ease_back(prog(t, 0.3, 0.5))
    pill(d, RW / 2, 520, p["pastilla"], F(PB, 80), scale=max(e2, 0.01), alpha=255 * clamp(e2 * 1.5))
    for i, (k, x, y) in enumerate([("cap", 110, 760), ("play", RW - 250, 860), ("247", 120, 1230),
                                   ("book", RW - 250, 1330)]):
        eb = ease_back(prog(t, 0.9 + i * 0.2, 0.5))
        put(img, badge_img(k, 130), x, y + bob(t, i * 1.7), clamp(eb * 1.5))
    d = ImageDraw.Draw(img, "RGBA")
    es = ease_back(prog(t, 0.5, 0.7))
    phone(d, RW / 2, 1110 + (1 - es) * 300, 0.82, t, p.get("materias", ["Materia 1", "Materia 2", "Materia 3"]),
          alpha=int(255 * clamp(es * 1.4)))

def sc_checks(t, p, img, d):
    e = ease_out(prog(t, 0.0, 0.4))
    text_block(d, RW, 360 + (1 - e) * 40, p["titulo"], fit(d, p["titulo"], PB, 74, RW - 180), WHITE, alpha=255 * e)
    for i, (a, b) in enumerate(p["items"]):
        pi = ease_out(prog(t, 0.45 + i * 0.55, 0.5))
        x = 150 + (1 - pi) * -260; y = 620 + i * 260; al = 255 * pi
        d.rounded_rectangle([x - 40, y - 40, x + 820, y + 170], radius=40, fill=(255, 255, 255, int(18 * pi)))
        check_icon(d, x, y + 20, 1.0, al)
        d.text((x + 125, y - 5), a, font=fit(d, a, PB, 58, 670), fill=WHITE + (int(al),))
        d.text((x + 125, y + 80), b, font=F(PM, 40), fill=SOFT + (int(al),))
    yb = 620 + len(p["items"]) * 260 - 50
    ec = ease_out(prog(t, 0.45 + len(p["items"]) * 0.55, 0.6))
    if yb + 170 < 1545:
        badge_row(img, t, ["wifi", "play", "cap", "247"], yb + 25, 0.45 + len(p["items"]) * 0.55)

def sc_precio(t, p, img, d):
    e = ease_out(prog(t, 0.0, 0.4))
    text_block(d, RW, 330 + (1 - e) * 40, p.get("titulo", "¿Cuánto cuesta?"), F(PB, 80), WHITE, alpha=255 * e)
    e1 = ease_out(prog(t, 0.4, 0.5))
    text_block(d, RW, 560, "Costo normal", F(PM, 50), SOFT, alpha=255 * e1)
    text_block(d, RW, 625, p["normal"], F(PB, 66), SOFT, alpha=255 * e1)
    e2 = ease_back(prog(t, 1.0, 0.6))
    a2 = clamp(e2 * 1.4)
    text_block(d, RW, 830, "Con Beca UDEP", F(PB, 60), ORANGE, alpha=255 * a2)
    pill(d, RW / 2, 1010, p["beca"], F(PB, 92), scale=max(e2, 0.01), alpha=255 * a2)
    e3 = ease_out(prog(t, 1.6, 0.5))
    text_block(d, RW, 1180 + (1 - e3) * 30, p.get("extra", "Inscripción GRATIS"), F(PB, 64), WHITE, alpha=255 * e3)
    ec = ease_back(prog(t, 2.0, 0.6))
    device_fit(img, p.get("ilustracion", "laptop"), (180, 1290, RW - 180, 1545), dy=(1 - ec) * 120, alpha=clamp(ec * 1.5))

def sc_cierre(t, p, img, d):
    e = ease_back(prog(t, 0.0, 0.6))
    paste_logo(img, RW / 2, 250 + (1 - e) * 60, 480, alpha=clamp(e))
    d = ImageDraw.Draw(img, "RGBA")
    e2 = ease_out(prog(t, 0.5, 0.5))
    text_block(d, RW, 800 + (1 - e2) * 40, p.get("programas", "Bachillerato · Licenciaturas\nMaestrías"),
               F(PB, 54), WHITE, alpha=255 * e2)
    e3 = ease_back(prog(t, 1.0, 0.5))
    pulse = 1 + 0.04 * math.sin(max(t - 1.5, 0) * 6)
    pill(d, RW / 2, 1130, p.get("boton", "Pide informes"), F(PB, 66), scale=max(e3, 0.01) * pulse,
         alpha=255 * clamp(e3 * 1.5))
    for i, (k, x, y) in enumerate([("cap", 90, 360), ("chat", RW - 230, 380)]):
        eb = ease_back(prog(t, 0.4 + i * 0.2, 0.5))
        put(img, badge_img(k, 140), x, y + bob(t, i * 2), clamp(eb * 1.5))
    d = ImageDraw.Draw(img, "RGBA")
    e4 = ease_out(prog(t, 1.4, 0.5))
    text_block(d, RW, 1250 + (1 - e4) * 30, "WhatsApp 444 519 3359", F(PB, 58), WHITE, alpha=255 * e4)

ESCENAS = {"gancho": sc_gancho, "pastilla": sc_pastilla, "checks": sc_checks, "precio": sc_precio,
           "cierre": sc_cierre}

def frame_reel(sc, t, t0):
    img = background(RW, RH, t + t0)
    d = ImageDraw.Draw(img, "RGBA")
    ESCENAS[sc["tipo"]](t, sc, img, d)
    return img

def render_reel(spec, preview=False):
    out = os.path.join(ROOT, spec["salida"] + ".mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmpdir = os.path.join("/tmp", "udep_gen", os.path.basename(spec["salida"]))
    os.makedirs(tmpdir, exist_ok=True)
    t0, files = 0.0, []
    for k, sc in enumerate(spec["escenas"]):
        dur = sc["dur"]
        if preview:
            frame_reel(sc, dur * 0.8, t0).save(os.path.join(tmpdir, f"prev_{k}.jpg"), quality=85)
            t0 += dur; continue
        tmp = os.path.join(tmpdir, f"s{k}.tmp.mp4"); fin = os.path.join(tmpdir, f"s{k}.mp4")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}",
               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
               "-pix_fmt", "yuv420p", tmp]
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n = int(round(dur * FPS))
        for i in range(n):
            t = i / FPS
            img = frame_reel(sc, t, t0)
            fade = min(1.0, (dur - t) / 0.25) if k == 0 else min(1.0, t / 0.25, (dur - t) / 0.25)
            if fade < 1:
                img = Image.blend(Image.new("RGB", (RW, RH), NAVY), img, max(fade, 0))
            pr.stdin.write(img.tobytes())
        pr.stdin.close()
        if pr.wait() != 0: raise SystemExit("ffmpeg falló")
        os.replace(tmp, fin); files.append(fin); t0 += dur
    if preview:
        return tmpdir
    lst = os.path.join(tmpdir, "list.txt")
    with open(lst, "w") as fh:
        for f in files: fh.write(f"file '{f}'\n")
    tmp = out[:-4] + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)
    return out

# ---------------- carrusel (1080x1350) ----------------
CW, CH = 1080, 1350

def slide_base(n, total, logo=True):
    img = background(CW, CH, n * 0.7)
    d = ImageDraw.Draw(img, "RGBA")
    if logo:
        paste_logo(img, CW - 120, 40, 150)
    d = ImageDraw.Draw(img, "RGBA")
    return img, d

def page_dots(d, n, total):
    for i in range(total):
        x = CW / 2 - (total - 1) * 18 + i * 36
        d.ellipse([x - 7, CH - 70, x + 7, CH - 56], fill=(ORANGE if i == n else (255, 255, 255)) + (255 if i == n else 70,))

def sl_portada(s, img, d):
    y = 330
    if s.get("etiqueta"):
        pill(d, CW / 2, y, s["etiqueta"], F(PB, 44)); y += 110
    y = text_block(d, CW, y, s["titulo"], F(PB, s.get("tam", 96)), WHITE, maxw=CW - 140)
    if s.get("sub"):
        y = text_block(d, CW, y + 30, s["sub"], F(PM, 50), SOFT, maxw=CW - 200)
    text_block(d, CW, CH - 170, "Desliza para ver más", F(PB, 40), ORANGE)
    return y

def sl_lista(s, img, d):
    y = text_block(d, CW, 230, s["titulo"], F(PB, 70), WHITE, maxw=CW - 160)
    y += 40
    items = s["items"]
    step = min(170, (CH - 200 - y) / max(len(items), 1))
    last = y
    for a in items:
        tit, sub = (a if isinstance(a, list) else [a, ""])
        check_icon(d, 110, y + 10, 0.85, 255)
        fy = text_block(d, CW, y, tit, F(PB, 50), WHITE, align="left", x0=210, maxw=CW - 290)
        if sub:
            fy = text_block(d, CW, fy, sub, F(PM, 36), SOFT, align="left", x0=210, maxw=CW - 290)
        last = fy
        y = max(y + step, fy + 40)
    return last

def sl_mito(s, img, d):
    pill(d, CW / 2, 250, s.get("etiqueta", "MITO"), F(PB, 42), color=(120, 130, 155))
    x_icon(d, 110, 360, 0.9, 255)
    text_block(d, CW, 360, s["mito"], F(PB, 58), SOFT, align="left", x0=220, maxw=CW - 300)
    pill(d, CW / 2, 720, "REALIDAD", F(PB, 42))
    check_icon(d, 110, 830, 0.9, 255)
    return text_block(d, CW, 830, s["realidad"], F(PB, 58), WHITE, align="left", x0=220, maxw=CW - 300)

def sl_precio(s, img, d):
    text_block(d, CW, 230, s["programa"], F(PB, 72), WHITE, maxw=CW - 160)
    text_block(d, CW, 470, "Costo normal", F(PM, 46), SOFT)
    text_block(d, CW, 530, s["normal"], F(PB, 60), SOFT)
    text_block(d, CW, 700, "Con Beca UDEP", F(PB, 58), ORANGE)
    pill(d, CW / 2, 860, s["beca"], F(PB, 88))
    return text_block(d, CW, 990, s.get("extra", "Inscripción GRATIS"), F(PB, 60), WHITE)

def sl_cierre(s, img, d):
    paste_logo(img, CW / 2, 170, 460)
    d = ImageDraw.Draw(img, "RGBA")
    y = text_block(d, CW, 700, s.get("titulo", "Estudia 100% en línea con validez oficial"), F(PB, 56), WHITE,
                   maxw=CW - 180)
    pill(d, CW / 2, y + 110, s.get("boton", "Pide informes"), F(PB, 60))
    put(img, badge_img("cap", 130), 70, 300)
    put(img, badge_img("chat", 130), CW - 200, 300)
    return text_block(d, CW, y + 220, "WhatsApp 444 519 3359", F(PB, 56), WHITE)

def deco_slide(img, s, n, yend):
    """Ilustraciones de dispositivos en el espacio libre de cada lámina."""
    t = s["tipo"]
    name = s.get("ilustracion") if isinstance(s.get("ilustracion"), str) else None
    if t == "portada":
        comp_fit(img, name or "clase", (80, yend + 50, CW - 80, CH - 205))
    elif t == "lista":
        comp_fit(img, name or ["panel", "movil", "clase"][n % 3], (110, yend + 40, CW - 110, CH - 100))
    elif t == "mito":
        comp_fit(img, name or "movil", (150, yend + 40, CW - 150, CH - 100))
    elif t == "precio":
        comp_fit(img, name or "panel", (200, yend + 30, CW - 200, CH - 95), minh=120)

SLIDES = {"portada": sl_portada, "lista": sl_lista, "mito": sl_mito, "precio": sl_precio, "cierre": sl_cierre}

def render_carrusel(spec, preview=False):
    outs = []
    total = len(spec["slides"])
    for n, s in enumerate(spec["slides"]):
        img, d = slide_base(n, total, logo=s["tipo"] != "cierre")
        yend = SLIDES[s["tipo"]](s, img, d) or 0
        if s.get("ilustracion", True) is not False:
            deco_slide(img, s, n, yend)
        d = ImageDraw.Draw(img, "RGBA")
        page_dots(d, n, total)
        out = os.path.join(ROOT, f"{spec['salida']}-{n + 1}.jpg")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        img.save(out, quality=90)
        outs.append(out)
    return outs

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    prev = "--preview" in sys.argv
    r = render_reel(spec, prev) if spec["tipo"] == "reel" else render_carrusel(spec, prev)
    print(r)
