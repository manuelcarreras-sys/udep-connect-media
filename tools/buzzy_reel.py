"""Arma un Reel 1080x1920 con clips de video de Buzzy + textos y tarjetas de marca UDEP Connect + voz y música.

Uso: python3 tools/buzzy_reel.py contenido/<archivo>-buzzy.json

JSON:
{
  "salida": "reels/2026-11-21-administracion-buzzy",
  "voz": "/ruta/voz.mp3", "voz_inicio": 0.3, "musica": "/ruta/musica.mp3", "musica_db": -17,
  "segmentos": [
     {"tipo": "clip", "archivo": "/ruta/clip1.mp4", "desde": 0, "dur": 6,
      "textos": [{"t0": 0.2, "t1": 3.0, "texto": "¿Sueñas con tu propio negocio?", "estilo": "grande"},
                 {"t0": 3.2, "t1": 6.0, "texto": "Licenciatura en Administración", "pastilla": "100% EN LÍNEA"}]},
     {"tipo": "tarjeta", "escena": {...escena de gen.py: precio/cierre/checks...}, "dur": 5.4}
  ]
}
Los tiempos de "textos" son relativos al inicio del segmento.
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen  # noqa: E402
from gen import F, PB, PM, WHITE, NAVY, ORANGE, SOFT, RW, RH, FPS, ease_out, ease_back, prog, clamp, fit, wrap

LOGO_SMALL = gen.LOGO_W.resize((170, 170), Image.LANCZOS)


def clip_frames(path, start, dur):
    """Devuelve frames RGB 1080x1920 del clip (escala y recorta al centro)."""
    cmd = ["ffmpeg", "-loglevel", "error", "-ss", str(start), "-t", str(dur), "-i", path,
           "-vf", f"scale={RW}:{RH}:force_original_aspect_ratio=increase,crop={RW}:{RH},fps={FPS}",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = RW * RH * 3
    n = int(round(dur * FPS))
    last = None
    for _ in range(n):
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        last = Image.frombytes("RGB", (RW, RH), buf)
        yield last
    p.stdout.close(); p.wait()
    # si el clip es más corto, congelar el último cuadro
    produced = 0 if last is None else None


def draw_caption(img, t, tx, en_banda=False):
    """Texto de marca sobre el video. En banda: centrado dentro de la franja inferior."""
    e = ease_out(prog(t, tx["t0"], 0.35))
    out = 1 - ease_out(prog(t, tx["t1"] - 0.25, 0.25))
    a = clamp(min(e, out))
    if a <= 0:
        return
    ov = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    grande = tx.get("estilo") == "grande"
    base = 78 if grande else 66
    font = fit(d, tx["texto"], PB, base, RW - 160, minsize=54)
    lines = wrap(d, tx["texto"], font, RW - 160)
    lh = font.size * 1.18
    pill_h = F(PB, 50).size * 1.55 + 26 if tx.get("pastilla") else 0
    block_h = len(lines) * lh + pill_h
    if en_banda:
        cy = (BANDA[0] + BANDA[1]) / 2 + 5
        y = cy - block_h / 2 + (1 - e) * 25
    else:
        cy = tx.get("y", 1330)
        box_h = block_h + 70
        y0 = cy - box_h / 2 + (1 - e) * 40
        d.rounded_rectangle([70, y0, RW - 70, y0 + box_h], radius=36, fill=NAVY + (int(215 * a),))
        d.rounded_rectangle([70, y0, 84, y0 + box_h], radius=7, fill=ORANGE + (int(255 * a),))
        y = y0 + 35
    for ln in lines:
        w = d.textlength(ln, font=font)
        d.text(((RW - w) / 2, y), ln, font=font, fill=WHITE + (int(255 * a),))
        y += lh
    if tx.get("pastilla"):
        gen.pill(d, RW / 2, y + pill_h / 2 - 2, tx["pastilla"], F(PB, 50), alpha=255 * a)
    img.paste(ov, (0, 0), ov)


def watermark(img):
    ov = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([RW - 222, 132, RW - 18, 336], radius=34, fill=NAVY + (205,))
    img.paste(ov, (0, 0), ov)
    img.paste(LOGO_SMALL, (RW - 205, 149), LOGO_SMALL)


BANDA = (1290, 1630)   # franja inferior fija: tapa logos de terceros que dibuje la IA


def banda(img, a=1.0):
    ov = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    y0, y1 = BANDA
    d.rectangle([0, y0, RW, y1], fill=NAVY + (int(242 * a),))
    d.rectangle([0, y0, RW, y0 + 10], fill=ORANGE + (int(255 * a),))
    img.paste(ov, (0, 0), ov)


def render(spec):
    root = gen.ROOT
    out = os.path.join(root, spec["salida"] + ".mp4")
    tmpdir = os.path.join("/tmp", "buzzy_reel", os.path.basename(spec["salida"]))
    os.makedirs(tmpdir, exist_ok=True)
    silent = os.path.join(tmpdir, "video_sin_audio.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{RW}x{RH}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset",
                            "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    total = 0.0
    prev_last = None
    for k, seg in enumerate(spec["segmentos"]):
        dur = seg["dur"]; n = int(round(dur * FPS))
        if seg["tipo"] == "clip":
            frames = list(clip_frames(seg["archivo"], seg.get("desde", 0), dur))
            while len(frames) < n:
                frames.append(frames[-1])
            for i in range(n):
                t = i / FPS
                img = frames[i].copy()
                watermark(img)
                if spec.get("banda"):
                    banda(img, clamp(t / 0.3) if k == 0 else 1.0)
                for tx in seg.get("textos", []):
                    draw_caption(img, t, tx, en_banda=spec.get("banda", False))
                if k == 0 and t < 0.2:
                    img = Image.blend(Image.new("RGB", (RW, RH), (0, 0, 0)), img, t / 0.2)
                enc.stdin.write(img.tobytes())
                prev_last = img
        else:
            sc = seg["escena"]
            for i in range(n):
                t = i / FPS
                img = gen.frame_reel(sc, t, total)
                if prev_last is not None and t < 0.35:   # transición suave desde el video
                    img = Image.blend(prev_last, img, t / 0.35)
                enc.stdin.write(img.tobytes())
            prev_last = img
        total += dur
    enc.stdin.close()
    if enc.wait() != 0:
        raise SystemExit("ffmpeg falló al codificar el video")
    # audio: voz con retraso + música bajita con fade-out, normalizado
    vi = spec.get("voz_inicio", 0.3)
    mdb = spec.get("musica_db", -17)
    fc = (f"[1:a]adelay={int(vi*1000)}|{int(vi*1000)},apad[v];"
          f"[2:a]volume={mdb}dB,afade=t=in:d=0.5,afade=t=out:st={total-1.5}:d=1.5[m];"
          f"[v][m]amix=inputs=2:duration=longest:normalize=0,atrim=0:{total},loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    tmp = out[:-4] + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", spec["voz"], "-i", spec["musica"],
                    "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-ar", "48000", "-t", str(total), "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)
    return out


def preview(spec, times):
    """Dibuja cuadros sueltos en tiempos globales para revisar."""
    tmpdir = os.path.join("/tmp", "buzzy_reel", os.path.basename(spec["salida"]))
    os.makedirs(tmpdir, exist_ok=True)
    outs = []
    for T in times:
        acc = 0.0
        for seg in spec["segmentos"]:
            if acc <= T < acc + seg["dur"]:
                t = T - acc
                if seg["tipo"] == "clip":
                    img = next(clip_frames(seg["archivo"], seg.get("desde", 0) + t, 0.1))
                    watermark(img)
                    if spec.get("banda"):
                        banda(img)
                    for tx in seg.get("textos", []):
                        draw_caption(img, t, tx, en_banda=spec.get("banda", False))
                else:
                    img = gen.frame_reel(seg["escena"], t, acc)
                p = os.path.join(tmpdir, f"prev_{T:05.1f}.jpg"); img.save(p, quality=85); outs.append(p)
                break
            acc += seg["dur"]
    return outs


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    if "--preview" in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]
        print(preview(spec, ts))
    else:
        print(render(spec))
