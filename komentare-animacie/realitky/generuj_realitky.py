#!/usr/bin/env python3
"""
Animácie pre realitné video (bez pozadia, so zvukom):
  podpis_biely.mov / podpis_modry.mov  – ručne písaný podpis (5 s), zvuk pera
  suma_300000.mov                      – zelené číslo 0 → 300 000 € za 1 s, cink cink
  suma_130000.mov                      – 0 → 130 000 € za 1 s, cink cink + kasa na konci
"""
import math, os, sys, subprocess, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from generuj_komentar import (clamp, prog, ease_out_cubic, ease_in_cubic, ease_in_out, ease_out_back,
                              write_wav, font, SS, SR, FPS, whoosh)
rng = np.random.default_rng(3)
S = SS

# ----------------------------------------------------------------- spoločné
def export(name, frames_dir, wav, W, H, dur, bg="0x2b2f36"):
    seq = os.path.join(frames_dir, "f_%04d.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", seq, "-i", wav,
                    "-c:v", "qtrle", "-pix_fmt", "argb", "-c:a", "pcm_s16le", "-shortest",
                    os.path.join(HERE, name + ".mov")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"gradients=s={W}x{H}:c0={bg}:c1=0x0f1114:x0=0:y0=0:x1={W}:y1={H}:d={dur}:r={FPS}",
                    "-framerate", str(FPS), "-i", seq, "-i", wav,
                    "-filter_complex", "[0][1]overlay=format=auto,format=yuv420p[v]", "-map", "[v]", "-map", "2:a",
                    "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", os.path.join(HERE, name + "_nahlad.mp4")], check=True)

def mix(n):
    return np.zeros((n, 2))

def add(buf, sig, at, pan=0.0, gain=1.0):
    n = len(buf); i = int(at * SR); j = min(n, i + len(sig))
    if i >= n or j <= i: return
    l = math.cos((pan + 1) * math.pi / 4) * 1.414; r = math.sin((pan + 1) * math.pi / 4) * 1.414
    buf[i:j, 0] += sig[: j - i] * l * gain; buf[i:j, 1] += sig[: j - i] * r * gain

def finish(buf, peak=0.7):
    buf = buf / (np.max(np.abs(buf)) + 1e-9) * peak
    return (buf * 32767).astype(np.int16)

def opacity(img, op):
    if op >= 1: return img
    im = img.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * op))); return im

# ================================================================= PODPIS
SIG_DUR = 5.0
T_WRITE, D_WRITE = 0.25, 2.2
T_UNDER, D_UNDER = 2.5, 0.38
T_SIG_OUT, D_SIG_OUT = 4.45, 0.5

def signature_path():
    """Kurzívny podpis: veľké začiatočné písmeno, oblúčiky, slučky, dolný ťah + podčiarknutie."""
    # (typ, výška, posun, sila slučky, smer)  smer -1 = hore, +1 = pod riadok
    glyphs = [("cap", 190, 95, 0.80, -1), ("e", 34, 30, 0.55, -1), ("hump", 44, 36, 0.10, -1),
              ("hump", 44, 36, 0.10, -1), ("l", 135, 40, 0.42, -1), ("e", 32, 28, 0.55, -1),
              ("g", 95, 40, 0.38, 1), ("hump", 42, 36, 0.12, -1), ("e", 30, 30, 0.55, -1),
              ("k", 120, 38, 0.40, -1), ("hump", 38, 40, 0.08, -1)]
    pts = []; x = 0.0
    drift = lambda xx: 8 * math.sin(xx / 160) - xx * 0.04      # mierne stúpajúci riadok
    for i, (typ, h, adv, lf, dr) in enumerate(glyphs):
        n = int(60 + h * 1.4); r = h / 2
        jit = 1 + 0.08 * math.sin(i * 2.3)
        for k in range(n):
            u = k / n * 2 * math.pi
            px = x + adv * (k / n) - r * lf * jit * math.sin(u)
            py = dr * r * jit * (1 - math.cos(u)) * (-1 if dr < 0 else 1)
            py = -abs(py) if dr < 0 else abs(py)
            pts.append((px, py + drift(px)))
        x += adv
    # koncový chvost
    xe, ye = pts[-1]
    for k in range(1, 70):
        u = k / 70
        pts.append((xe + 70 * u, ye + 10 * math.sin(u * math.pi) - 25 * u))
    main_n = len(pts)
    # podčiarknutie – dlhý švih späť doľava popod meno
    p0 = pts[-1]; p2 = (-60, 70); p1 = (p0[0] * 0.55, 120)
    for k in range(1, 180):
        u = k / 180
        bx = (1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0]
        by = (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]
        pts.append((bx, by))
    pts = [(px - py * 0.30, py) for px, py in pts]           # sklon doprava
    arr = np.array(pts)
    seg = np.linalg.norm(np.diff(arr, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    main_len = cum[main_n - 1]
    step = 0.5
    L = np.arange(0, cum[-1], step)
    xs = np.interp(L, cum, arr[:, 0]); ys = np.interp(L, cum, arr[:, 1])
    return np.stack([xs, ys], 1), int(main_len / step)

def render_signature(color, glow, name):
    path, split = signature_path()
    mn = path.min(0); mx = path.max(0)
    W, H = 1080, 440
    sc = min(860 / (mx[0] - mn[0]), 330 / (mx[1] - mn[1])) * S
    off = np.array([(W * S - (mx[0] - mn[0]) * sc) / 2, (H * S - (mx[1] - mn[1]) * sc) / 2]) - mn * sc
    P = path * sc + off
    d = np.diff(P, axis=0, prepend=P[:1])
    dirn = d / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-9)
    # ťahy nadol hrubšie (ako pero)
    base = 4.6 * S
    widths = base * (0.62 + 0.55 * np.clip(dirn[:, 1], 0, 1))
    widths[split:] = base * np.linspace(1.0, 0.35, len(widths) - split)  # podčiarknutie sa zužuje
    widths = np.convolve(widths, np.ones(25) / 25, mode="same")
    widths[:30] *= np.linspace(0.4, 1, 30)

    ink = Image.new("L", (W * S, H * S), 0)
    dr = ImageDraw.Draw(ink)
    drawn = 0
    frames = os.path.join(HERE, "_frames_" + name); shutil.rmtree(frames, ignore_errors=True); os.makedirs(frames)
    nfr = int(SIG_DUR * FPS)
    tip_idx = []
    for fi in range(nfr):
        t = fi / FPS
        pw = prog(t, T_WRITE, D_WRITE); pu = prog(t, T_UNDER, D_UNDER)
        # písanie: mierne nerovnomerná rýchlosť
        pw2 = clamp(pw + 0.015 * math.sin(pw * 40)) if 0 < pw < 1 else pw
        target = int(split * ease_in_out(pw2) if pw < 1 else split)
        if pu > 0: target = split + int((len(P) - split) * ease_out_cubic(pu))
        target = min(target, len(P))
        for i in range(drawn, target):
            x, y = P[i]; w = widths[i] / 2
            dr.ellipse([x - w, y - w, x + w, y + w], fill=255)
        drawn = max(drawn, target)
        tip_idx.append(drawn)
        pout = ease_in_cubic(prog(t, T_SIG_OUT, D_SIG_OUT))
        mask = ink.resize((W, H), Image.LANCZOS)
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh = mask.filter(ImageFilter.GaussianBlur(6)).point(lambda v: min(255, int(v * (0.85 if glow == (0, 0, 0) else 2.2))))
        g = Image.new("RGBA", (W, H), glow + (0,)); g.putalpha(sh)
        canvas.alpha_composite(g, (0, 3))
        layer = Image.new("RGBA", (W, H), color + (0,)); layer.putalpha(mask)
        canvas.alpha_composite(layer)
        canvas = opacity(canvas, 1 - pout)
        canvas.save(os.path.join(frames, f"f_{fi:04d}.png"))
        if fi == int(4.0 * FPS): canvas.save(os.path.join(HERE, name + ".png"))

    # zvuk pera – škrabanie podľa rýchlosti a smeru hrotu
    n = int(SIG_DUR * SR); buf = mix(n)
    tt = np.arange(n) / SR
    idx = np.interp(tt, np.arange(nfr) / FPS, np.array(tip_idx, float))
    vel = np.gradient(idx) * SR
    ii = np.clip(idx.astype(int), 0, len(P) - 1)
    down = np.clip(dirn[ii, 1], 0, 1)
    amp = np.clip(vel / (np.percentile(vel[vel > 0], 90) + 1e-9), 0, 1.2) * (0.45 + 0.55 * down)
    amp = np.convolve(amp, np.ones(240) / 240, mode="same")
    noise = rng.standard_normal(n)
    hp = np.diff(noise, prepend=0)                          # vysoké frekvencie
    grain = np.convolve(hp, np.array([1, 0.6, 0.2]), mode="same")
    crackle = (rng.random(n) < 0.004) * rng.standard_normal(n) * 3  # zrnitosť papiera
    pen = (grain * 0.6 + crackle) * amp
    buf[:, 0] += pen * 0.9; buf[:, 1] += pen * 0.8
    # ťuk hrotu na začiatku
    k = int(0.03 * SR); tk = np.arange(k) / SR
    add(buf, (np.sin(2 * np.pi * 900 * tk) * 0.6 + rng.standard_normal(k) * 0.4) * np.exp(-tk * 160) * 0.6, T_WRITE - 0.01)
    # švih podčiarknutia
    add(buf, whoosh(0.45, 2500, 900, 0.35), T_UNDER - 0.04)
    wav = os.path.join(HERE, name + "_zvuk.wav"); write_wav(wav, finish(buf, 0.6))
    export(name, frames, wav, W, H, SIG_DUR); shutil.rmtree(frames)
    print("hotovo", name)

# ================================================================= SUMA
NUM_DUR = 4.0
T_POP, D_POP = 0.0, 0.32
T_CNT, D_CNT = 0.3, 1.0
T_NUM_OUT, D_NUM_OUT = 3.5, 0.4
GREEN_TOP, GREEN_BOT = (120, 255, 160), (18, 200, 80)
OUTLINE = (4, 48, 22)

def fmt(v):
    return f"{int(v):,}".replace(",", " ") + " €"

def coin(pitch=1.0, vol=0.35, dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 2637 * pitch
    s = (np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 25)
         + 0.4 * np.sin(2 * np.pi * f * 1.5 * t)) * np.exp(-t * 14)
    s[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return s / 2 * vol

def cash_register():
    n = int(1.6 * SR); t = np.arange(n) / SR; s = np.zeros(n)
    # mechanické cvaknutie / klapnutie
    k = int(0.06 * SR); tk = np.arange(k) / SR
    s[:k] += rng.standard_normal(k) * np.exp(-tk * 90) * 0.9
    s[:k] += np.sin(2 * np.pi * 140 * tk) * np.exp(-tk * 50) * 0.8
    # druhé cvak (zásuvka)
    o = int(0.09 * SR); s[o:o + k] += rng.standard_normal(k) * np.exp(-tk * 120) * 0.6
    # zvonček „ching“
    o = int(0.11 * SR); tb = t[: n - o]
    bell = sum(a * np.sin(2 * np.pi * f * tb) * np.exp(-tb * dcy)
               for f, a, dcy in [(2093, 1.0, 3.2), (2637, 0.5, 4.0), (3520, 0.45, 5.0),
                                 (4186, 0.35, 6.5), (5274, 0.2, 8.0)])
    bell *= (1 + 0.15 * np.sin(2 * np.pi * 6 * tb))
    s[o:] += bell * 0.55
    # prešmyknutie zásuvky
    o = int(0.25 * SR); m = int(0.35 * SR); tm = np.linspace(0, 1, m)
    s[o:o + m] += np.convolve(rng.standard_normal(m), np.ones(6) / 6, mode="same") * np.sin(np.pi * tm) * 0.25
    return s / np.max(np.abs(s)) * 0.9

def render_number_layers(text, size):
    f = font("Black", size)
    # pevná šírka číslic, aby číslo neposkakovalo
    dw = max(f.getlength(c) for c in "0123456789")
    widths = [dw if c.isdigit() else (dw * 0.42 if c == " " else f.getlength(c)) for c in text]
    total = sum(widths)
    pad = 40 * S
    W, H = int(total + pad * 2), int(size * S * 1.5 + pad)
    fill = Image.new("L", (W, H), 0); strk = Image.new("L", (W, H), 0)
    df, ds = ImageDraw.Draw(fill), ImageDraw.Draw(strk)
    x = pad; cy = H / 2
    for c, w in zip(text, widths):
        cx = x + w / 2
        ds.text((cx, cy), c, font=f, fill=255, anchor="mm", stroke_width=int(7 * S), stroke_fill=255)
        df.text((cx, cy), c, font=f, fill=255, anchor="mm")
        x += w
    grad = Image.new("RGBA", (W, H))
    gd = ImageDraw.Draw(grad)
    bb = fill.getbbox() or (0, 0, W, H)
    for y in range(H):
        k = clamp((y - bb[1]) / max(1, bb[3] - bb[1]))
        gd.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(GREEN_TOP, GREEN_BOT)) + (255,))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = strk.filter(ImageFilter.GaussianBlur(10 * S)).point(lambda v: int(v * 0.6))
    shl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); shl.putalpha(sh)
    img.alpha_composite(shl, (0, int(6 * S)))
    glow = strk.filter(ImageFilter.GaussianBlur(18 * S)).point(lambda v: int(v * 0.55))
    gl = Image.new("RGBA", (W, H), (40, 255, 110, 0)); gl.putalpha(glow)
    img.alpha_composite(gl)
    ol = Image.new("RGBA", (W, H), OUTLINE + (0,)); ol.putalpha(strk)
    img.alpha_composite(ol)
    grad.putalpha(fill); img.alpha_composite(grad)
    # lesk – svetlý pruh v hornej tretine
    hl = Image.new("L", (W, H), 0); ImageDraw.Draw(hl).rectangle([0, bb[1], W, bb[1] + (bb[3] - bb[1]) * 0.33], fill=60)
    hl = ImageChops.multiply(hl, fill)
    wl = Image.new("RGBA", (W, H), (255, 255, 255, 0)); wl.putalpha(hl); img.alpha_composite(wl)
    return img

def render_sum(target, name, kasa):
    W, H = 1080, 330
    nfr = int(NUM_DUR * FPS)
    steps = 12
    frames = os.path.join(HERE, "_frames_" + name); shutil.rmtree(frames, ignore_errors=True); os.makedirs(frames)
    cache = {}
    cink_times = []
    last_bucket = 0
    for fi in range(nfr):
        t = fi / FPS
        pc = prog(t, T_CNT, D_CNT)
        val = target * ease_out_cubic(pc)
        if pc < 1 and pc > 0:
            val = round(val / 10) * 10 + (fi * 7) % 10  # „živé“ posledné cifry
        val = min(val, target) if pc < 1 else target
        txt = fmt(val)
        if txt not in cache:
            cache.clear(); cache[txt] = render_number_layers(txt, 112)
        img = cache[txt]
        # pulz pri každom cinku a väčší na konci
        bucket = int(val / (target / steps))
        pulse = 0.0
        pend = prog(t, T_CNT + D_CNT, 0.35)
        if 0 < pend < 1: pulse = 0.16 * math.sin(math.pi * pend) * (1 - pend * 0.5)
        pp = prog(t, T_POP, D_POP)
        s = (0.5 + 0.5 * ease_out_back(pp, 2.2) if pp < 1 else 1.0) + pulse
        pout = ease_in_cubic(prog(t, T_NUM_OUT, D_NUM_OUT))
        s *= 1 - 0.15 * pout
        op = clamp(pp * 3) * (1 - pout)
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # záblesk / krúžok na konci
        if 0 < pend < 1:
            d = ImageDraw.Draw(canvas)
            for j in range(14):
                a = j / 14 * 2 * math.pi + 0.2
                r0 = 120 + pend * 330; r1 = r0 + 40 * (1 - pend)
                cx, cy = W / 2, H / 2
                d.line([(cx + math.cos(a) * r0, cy + math.sin(a) * r0 * 0.42),
                        (cx + math.cos(a) * r1, cy + math.sin(a) * r1 * 0.42)],
                       fill=(120, 255, 160, int(230 * (1 - pend))), width=5)
        w, h = int(img.width * s / S), int(img.height * s / S)
        im = opacity(img.resize((w, h), Image.LANCZOS), op)
        canvas.alpha_composite(im, (int(W / 2 - w / 2), int(H / 2 - h / 2)))
        canvas.save(os.path.join(frames, f"f_{fi:04d}.png"))
        if fi == int(2.6 * FPS): canvas.save(os.path.join(HERE, name + ".png"))
    # cinky v okamihoch, keď číslo prejde ďalšiu dvanástinu
    n = int(NUM_DUR * SR); buf = mix(n)
    for k in range(1, steps + 1):
        u = k / steps
        tc = T_CNT + D_CNT * (1 - (1 - u) ** (1 / 3))   # inverzia ease_out_cubic
        add(buf, coin(1.0 + 0.02 * k + rng.uniform(-0.02, 0.02), 0.30), tc - 0.01, rng.uniform(-0.5, 0.5))
    add(buf, whoosh(0.3, 600, 3000, 0.25), T_POP)
    if kasa:
        add(buf, cash_register(), T_CNT + D_CNT - 0.02, 0, 1.3)
    else:
        add(buf, coin(1.0, 0.5, 0.8), T_CNT + D_CNT, -0.2); add(buf, coin(1.26, 0.4, 0.8), T_CNT + D_CNT + 0.06, 0.2)
    add(buf, whoosh(0.4, 3000, 500, 0.25), T_NUM_OUT - 0.05)
    wav = os.path.join(HERE, name + "_zvuk.wav"); write_wav(wav, finish(buf))
    export(name, frames, wav, W, H, NUM_DUR); shutil.rmtree(frames)
    print("hotovo", name)

if __name__ == "__main__":
    which = sys.argv[1:] or ["podpis", "300", "130"]
    if "podpis" in which:
        render_signature((255, 255, 255), (0, 0, 0), "podpis_biely")
        render_signature((20, 50, 160), (255, 255, 255), "podpis_modry")
    if "300" in which: render_sum(300000, "suma_300000", kasa=False)
    if "130" in which: render_sum(130000, "suma_130000", kasa=True)
