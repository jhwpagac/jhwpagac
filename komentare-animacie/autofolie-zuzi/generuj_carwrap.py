#!/usr/bin/env python3
"""Autofólie ZUZI – textová animácia „CAR WRAP“ (5 s, 1080x1920, zelené pozadie + verzia bez pozadia).
Motív: nápis sa „obalí“ fóliou – zlatá hrana prejde cez písmená a za ňou ostane lesklý text."""
import os, sys, math, shutil, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "auto-vojto"))
from generuj_auto_vojto import (clamp, prog, ease_out_cubic, ease_in_cubic, ease_in_out, ease_out_back,
                                write_wav, mix, add, finish, whoosh, pop, sparkle, SR, FPS)
def pf(w, s): return ImageFont.truetype(os.path.join(ROOT, "auto-vojto", "fonty", f"Poppins-{w}.ttf"), s)

NAME = "carwrap_autofolie_zuzi"
W, H, S, DUR = 1080, 1920, 2, 5.0
GOLD, WHITE = (223, 186, 108), (246, 247, 249)
CY = H * 0.5
rng = np.random.default_rng(3)

def text_mask(txt, font, spacing=0):
    w = int(sum(font.getlength(c) for c in txt) + spacing * (len(txt) - 1)) + 20
    bb = font.getbbox("ÁgZ")
    h = int(bb[3] - bb[1] + 40)
    m = Image.new("L", (w, h), 0); d = ImageDraw.Draw(m); x = 10
    for c in txt:
        d.text((x, 20 - bb[1]), c, font=font, fill=255); x += font.getlength(c) + spacing
    return m

def gradient(w, h, top, bot):
    a = np.linspace(0, 1, h)[:, None, None]
    g = np.array(top)[None, None, :] * (1 - a) + np.array(bot)[None, None, :] * a
    return Image.fromarray(np.repeat(g, w, axis=1).astype(np.uint8))

# hlavný nápis
M_MAIN = text_mask("CAR WRAP", pf("ExtraBold", 150 * S), spacing=4 * S)
MW, MH = M_MAIN.size
FILL_MAIN = gradient(MW, MH, (255, 255, 255), (205, 208, 214))
M_SUB = text_mask("AUTOFÓLIE ZUZI", pf("SemiBold", 60 * S), spacing=14 * S)
M_CITY = text_mask("TRENČÍN", pf("Medium", 40 * S), spacing=18 * S)

# logo Autofólie ZUZI (biele, bez pozadia) – rovnaké vyrezanie ako v hooku
def nacitaj_logo(width):
    src = Image.open(os.path.join(HERE, "zdroj_logo.jpg")).convert("RGB").crop((205, 340, 850, 690))
    L = np.asarray(src.convert("L")).astype(float)
    a = np.clip((L - 70) / (225 - 70), 0, 1) * 255
    img = Image.new("RGBA", src.size, WHITE + (0,)); img.putalpha(Image.fromarray(a.astype(np.uint8)))
    img = img.crop(img.getbbox())
    img = img.resize((width, int(img.height * width / img.width)), Image.LANCZOS)
    # jemná tmavá žiara, aby sa logo oddelilo od textu, ktorý prekrýva
    P = 24 * S
    out = Image.new("RGBA", (img.width + 2 * P, img.height + 2 * P), (0, 0, 0, 0))
    la = Image.new("L", out.size, 0); la.paste(img.split()[3], (P, P))
    la = la.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(7 * S)).point(lambda v: min(255, int(v * 1.1)))
    dk = Image.new("RGBA", out.size, (16, 17, 20, 0)); dk.putalpha(la)
    out.alpha_composite(dk); out.alpha_composite(img, (P, P))
    return out
LOGO = nacitaj_logo(440 * S)

def layer_from(mask, fill):
    im = fill.convert("RGBA") if isinstance(fill, Image.Image) else Image.new("RGBA", mask.size, fill + (255,))
    im.putalpha(mask); return im

def frame(t):
    big = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    pout = ease_in_cubic(prog(t, 4.35, 0.55))
    # ---- CAR WRAP: obalenie fóliou zľava doprava (šikmá hrana)
    pw = ease_in_out(prog(t, 0.1, 0.9))
    mx, my = int((W * S - MW) / 2), int(CY * S - 300 * S - MH / 2)
    if pw > 0:
        slant = MH * 0.35
        front = -slant + (MW + 2 * slant) * pw
        back = -slant + (MW + 2 * slant) * pout       # odchod: fólia sa „stiahne“ doprava
        reveal = Image.new("L", (MW, MH), 0); rd = ImageDraw.Draw(reveal)
        rd.polygon([(back, 0), (front + slant, 0), (front, MH), (back - slant, MH)], fill=255)
        m = ImageChops.multiply(M_MAIN, reveal)
        lay = layer_from(m, FILL_MAIN)
        # lesk prechádzajúci písmenami
        sp = prog(t, 1.15, 0.75)
        if 0 < sp < 1:
            gl = Image.new("L", (MW, MH), 0); gd = ImageDraw.Draw(gl)
            x = -MW * 0.2 + sp * MW * 1.4
            gd.polygon([(x, 0), (x + 70 * S, 0), (x + 70 * S - slant, MH), (x - slant, MH)], fill=200)
            gl = ImageChops.multiply(gl.filter(ImageFilter.GaussianBlur(10 * S)), m)
            g2 = Image.new("RGBA", (MW, MH), GOLD + (0,)); g2.putalpha(gl); lay.alpha_composite(g2)
        big.alpha_composite(lay, (mx, my))
        # zlatá hrana fólie (svieti iba na písmenách + jemný pruh)
        if 0 < pw < 1:
            edge = Image.new("L", (MW, MH), 0); ed = ImageDraw.Draw(edge)
            ed.line([(front + slant, 0), (front, MH)], fill=255, width=int(10 * S))
            eg = edge.filter(ImageFilter.GaussianBlur(6 * S))
            em = ImageChops.lighter(ImageChops.multiply(edge, M_MAIN), eg.point(lambda v: int(v * 0.35)))
            e2 = Image.new("RGBA", (MW, MH), GOLD + (0,)); e2.putalpha(em)
            big.alpha_composite(e2, (mx, my))
    # ---- zlatá linka
    pl = ease_out_cubic(prog(t, 0.85, 0.6)) * (1 - pout)
    if pl > 0:
        d = ImageDraw.Draw(big)
        lw = 520 * S * pl; ly = CY * S - 150 * S
        d.rounded_rectangle([W * S / 2 - lw / 2, ly - 3 * S, W * S / 2 + lw / 2, ly + 3 * S], radius=3 * S, fill=GOLD + (255,))
    # ---- AUTOFÓLIE ZUZI – vyjde zdola cez masku
    for mask, col, t0, y in ((M_SUB, GOLD, 1.15, CY * S - 60 * S), (M_CITY, WHITE, 1.55, CY * S + 40 * S)):
        p = prog(t, t0, 0.6)
        if p <= 0: continue
        e = ease_out_cubic(p)
        win = Image.new("L", mask.size, 0)
        off = int((1 - e) * mask.size[1]) + int(pout * mask.size[1])
        win.paste(mask, (0, off))
        win = win.point(lambda v: int(v * (1 - pout)))
        lay = layer_from(win, col)
        big.alpha_composite(lay, (int((W * S - mask.size[0]) / 2), int(y - mask.size[1] / 2)))
        if mask is M_CITY and p > 0.3:    # dve malé zlaté čiarky okolo TRENČÍN
            d = ImageDraw.Draw(big); a = int(255 * clamp((p - 0.3) / 0.7) * (1 - pout))
            cx = W * S / 2; hw = mask.size[0] / 2 + 30 * S
            for sgn in (-1, 1):
                d.line([(cx + sgn * hw, y), (cx + sgn * (hw + 60 * S * e), y)], fill=GOLD + (a,), width=int(3 * S))
    # ---- logo – vysunie sa zdola a trochu prekryje TRENČÍN
    pl2 = prog(t, 1.9, 0.6)
    if pl2 > 0:
        e = ease_out_cubic(pl2)
        lg = LOGO.copy(); al = lg.split()[3].point(lambda v: int(v * clamp(pl2 * 2) * (1 - pout)))
        lg.putalpha(al)
        top = CY * S + 40 * S + 6 * S                 # vrch loga trochu zasahuje do riadku TRENČÍN
        big.alpha_composite(lg, (int((W * S - lg.width) / 2), int(top - 24 * S + (1 - e) * 60 * S + pout * 40 * S)))
    return big.resize((W, H), Image.LANCZOS)

def foil(dur=0.95):
    """Šušťanie fólie – zrnité kliknutia + filtrovaný šum s rastúcou výškou."""
    n = int(dur * SR); t = np.linspace(0, 1, n)
    crinkle = (rng.random(n) < 0.02) * rng.standard_normal(n) * 1.2
    crinkle = np.convolve(crinkle, np.exp(-np.arange(40) / 6), mode="same")
    env = np.sin(np.pi * t) ** 0.7
    return (crinkle * 0.5 + whoosh(dur, 1200, 6000, 0.6)[:n]) * env * 0.6

def main():
    tmp = os.path.join(HERE, "_frames_cw"); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    for i in range(int(DUR * FPS)):
        frame(i / FPS).save(os.path.join(tmp, f"f_{i:04d}.png"))
    n = int(DUR * SR); buf = mix(n)
    add(buf, foil(0.95), 0.1, -0.4)
    add(buf, pop(600, 150, 0.15, 0.6), 0.95)
    add(buf, sparkle(), 1.2)
    add(buf, whoosh(0.5, 600, 3000, 0.3), 1.1, 0.2)
    add(buf, pop(1000, 300, 0.1, 0.4), 1.6, 0.3)
    add(buf, whoosh(0.45, 500, 2600, 0.3), 1.85, 0.0)
    add(buf, pop(800, 250, 0.11, 0.45), 2.15)
    add(buf, foil(0.55), 4.35, 0.4)
    wav = os.path.join(HERE, NAME + "_zvuk.wav"); write_wav(wav, finish(buf))
    seq = os.path.join(tmp, "f_%04d.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0x00FF00:s={W}x{H}:r={FPS}:d={DUR}",
                    "-framerate", str(FPS), "-i", seq, "-i", wav, "-filter_complex", "[0][1]overlay=format=auto,format=yuv420p[v]",
                    "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-c:a", "aac", "-b:a", "256k",
                    "-shortest", "-movflags", "+faststart", os.path.join(HERE, NAME + "_zelene_pozadie.mp4")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", seq, "-i", wav, "-c:v", "qtrle",
                    "-pix_fmt", "argb", "-c:a", "pcm_s16le", "-shortest", os.path.join(HERE, NAME + ".mov")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"gradients=s={W}x{H}:c0=0x3a3f48:c1=0x121418:x0=0:y0=0:x1={W}:y1={H}:d={DUR}:r={FPS}",
                    "-framerate", str(FPS), "-i", seq, "-i", wav, "-filter_complex", "[0][1]overlay=format=auto,format=yuv420p[v]",
                    "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", os.path.join(HERE, NAME + "_nahlad.mp4")], check=True)
    shutil.rmtree(tmp); print("hotovo", NAME)

if __name__ == "__main__":
    main()
