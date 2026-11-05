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

# ---------------- escenas de Reel (1080x1920) ----------------
RW, RH = 1080, 1920
# zona segura de Reels: contenido entre y=260 y y=1550

def sc_gancho(t, p, img, d):
    lines = p["lineas"]
    f = F(PB, p.get("tam", 112))
    y0 = 760 - len(lines) * 75
    for i, ln in enumerate(lines):
        e = ease_back(prog(t, 0.15 + i * 0.3, 0.5))
        text_block(d, RW, y0 + i * f.size * 1.2 + (1 - e) * 120, ln, f, WHITE, alpha=255 * clamp(e))
    yb = y0 + len(lines) * f.size * 1.2 + 15
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
    # indicador de página
    for i in range(total):
        x = CW / 2 - (total - 1) * 18 + i * 36
        d.ellipse([x - 7, CH - 70, x + 7, CH - 56], fill=(ORANGE if i == n else (255, 255, 255)) + (255 if i == n else 70,))
    return img, d

def sl_portada(s, img, d):
    y = 330
    if s.get("etiqueta"):
        pill(d, CW / 2, y, s["etiqueta"], F(PB, 44)); y += 110
    y = text_block(d, CW, y, s["titulo"], F(PB, s.get("tam", 96)), WHITE, maxw=CW - 140)
    if s.get("sub"):
        text_block(d, CW, y + 30, s["sub"], F(PM, 50), SOFT, maxw=CW - 200)
    text_block(d, CW, CH - 170, "Desliza para ver más", F(PB, 40), ORANGE)

def sl_lista(s, img, d):
    y = text_block(d, CW, 230, s["titulo"], F(PB, 70), WHITE, maxw=CW - 160)
    y += 40
    items = s["items"]
    step = min(170, (CH - 200 - y) / max(len(items), 1))
    for a in items:
        tit, sub = (a if isinstance(a, list) else [a, ""])
        check_icon(d, 110, y + 10, 0.85, 255)
        fy = text_block(d, CW, y, tit, F(PB, 50), WHITE, align="left", x0=210, maxw=CW - 290)
        if sub:
            text_block(d, CW, fy, sub, F(PM, 36), SOFT, align="left", x0=210, maxw=CW - 290)
        y += step

def sl_mito(s, img, d):
    pill(d, CW / 2, 250, s.get("etiqueta", "MITO"), F(PB, 42), color=(120, 130, 155))
    x_icon(d, 110, 360, 0.9, 255)
    text_block(d, CW, 360, s["mito"], F(PB, 58), SOFT, align="left", x0=220, maxw=CW - 300)
    pill(d, CW / 2, 720, "REALIDAD", F(PB, 42))
    check_icon(d, 110, 830, 0.9, 255)
    text_block(d, CW, 830, s["realidad"], F(PB, 58), WHITE, align="left", x0=220, maxw=CW - 300)

def sl_precio(s, img, d):
    text_block(d, CW, 230, s["programa"], F(PB, 72), WHITE, maxw=CW - 160)
    text_block(d, CW, 470, "Costo normal", F(PM, 46), SOFT)
    text_block(d, CW, 530, s["normal"], F(PB, 60), SOFT)
    text_block(d, CW, 700, "Con Beca UDEP", F(PB, 58), ORANGE)
    pill(d, CW / 2, 860, s["beca"], F(PB, 88))
    text_block(d, CW, 990, s.get("extra", "Inscripción GRATIS"), F(PB, 60), WHITE)

def sl_cierre(s, img, d):
    paste_logo(img, CW / 2, 170, 460)
    d = ImageDraw.Draw(img, "RGBA")
    y = text_block(d, CW, 700, s.get("titulo", "Estudia 100% en línea con validez oficial"), F(PB, 56), WHITE,
                   maxw=CW - 180)
    pill(d, CW / 2, y + 110, s.get("boton", "Pide informes"), F(PB, 60))
    text_block(d, CW, y + 220, "WhatsApp 444 519 3359", F(PB, 56), WHITE)

SLIDES = {"portada": sl_portada, "lista": sl_lista, "mito": sl_mito, "precio": sl_precio, "cierre": sl_cierre}

def render_carrusel(spec, preview=False):
    outs = []
    total = len(spec["slides"])
    for n, s in enumerate(spec["slides"]):
        img, d = slide_base(n, total, logo=s["tipo"] != "cierre")
        SLIDES[s["tipo"]](s, img, d)
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
