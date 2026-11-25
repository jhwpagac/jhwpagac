#!/usr/bin/env python3
"""Araver – 3 červené boxy „čo je v ponuke“ vybiehajú pod sebou, každý o 1 s neskôr. Bez pozadia, so zvukom."""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "auto-vojto"))
import generuj_auto_vojto as av
from generuj_auto_vojto import (clamp, prog, ease_out_cubic, ease_in_cubic, ease_out_back,
                                write_wav, mix, add, finish, opacity, whoosh, pop, new_frames, SR, FPS)
from generuj_realitky import coin
def pf(w, s): return ImageFont.truetype(os.path.join(ROOT, "auto-vojto", "fonty", f"Poppins-{w}.ttf"), s)

NAME = "araver_ponuka_3_boxy"
BOXY = ["Poistenie", "Servis", "Cestná daň na Vaše auto"]
CASY = [0.2, 1.2, 2.2]                 # každý box o 1 sekundu neskôr
RED, WHITE = (227, 6, 19), (255, 255, 255)
W, BW, BH, GAP = 1080, 860, 120, 22
H = int(40 + 3 * BH + 2 * GAP + 40); H += H % 2
T_OUT, DUR = 5.6, 6.3
S = 2

def box(text):
    w, h = BW * S, BH * S
    img = Image.new("RGBA", (w + 80 * S, h + 80 * S), (0, 0, 0, 0))
    m = 40 * S
    sh = Image.new("L", img.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle([m, m + 10 * S, m + w, m + h + 10 * S], radius=26 * S, fill=170)
    shl = Image.new("RGBA", img.size, (0, 0, 0, 0)); shl.putalpha(sh.filter(ImageFilter.GaussianBlur(16 * S)))
    img.alpha_composite(shl)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([m, m, m + w, m + h], radius=26 * S, fill=RED + (255,))
    # jemný lesk v hornej polovici
    gl = Image.new("L", img.size, 0)
    ImageDraw.Draw(gl).rounded_rectangle([m, m, m + w, m + h // 2], radius=26 * S, fill=28)
    wl = Image.new("RGBA", img.size, WHITE + (0,)); wl.putalpha(gl); img.alpha_composite(wl)
    d = ImageDraw.Draw(img)
    # ikona – biely krúžok s fajkou
    cx, cy, r = m + 64 * S, m + h / 2, 34 * S
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE + (255,))
    d.line([(cx - 15 * S, cy + 1 * S), (cx - 4 * S, cy + 12 * S), (cx + 16 * S, cy - 11 * S)], fill=RED + (255,), width=int(7 * S), joint="curve")
    f = pf("Bold", 50 * S)
    if f.getlength(text) > w - 150 * S: f = pf("Bold", 44 * S)
    d.text((m + 124 * S, cy + 2 * S), text, font=f, fill=WHITE + (255,), anchor="lm")
    return img

def main():
    boxes = [box(t) for t in BOXY]
    frames = new_frames(NAME)
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for i, b in enumerate(boxes):
            p = prog(t, CASY[i], 0.55)
            if p <= 0: continue
            po = ease_in_cubic(prog(t, T_OUT + i * 0.08, 0.4))
            e = ease_out_back(p, 1.6) if p < 1 else 1
            dx = (1 - e) * -260 + po * 300
            sc = (0.85 + 0.15 * e) * (1 - 0.05 * po)
            op = clamp(p * 3) * (1 - po)
            w, h = int(b.width * sc / S), int(b.height * sc / S)
            im = opacity(b.resize((w, h), Image.LANCZOS), op)
            cy = 40 + BH / 2 + i * (BH + GAP)
            canvas.alpha_composite(im, (int(W / 2 - w / 2 + dx), int(cy - h / 2)))
        canvas.save(os.path.join(frames, f"f_{fi:04d}.png"))
    n = int(DUR * SR); buf = mix(n)
    for i, tt in enumerate(CASY):
        add(buf, whoosh(0.4, 450, 3200, 0.4), tt - 0.06, -0.3)
        add(buf, pop(700 + 120 * i, 220, 0.12, 0.55), tt + 0.3)
        add(buf, coin(0.9 + 0.1 * i, 0.18, 0.4), tt + 0.33)
    add(buf, whoosh(0.5, 3000, 450, 0.35), T_OUT - 0.05)
    wav = os.path.join(HERE, NAME + "_zvuk.wav"); write_wav(wav, finish(buf))
    av.HERE_SAVE = av.HERE; av.HERE = HERE
    av.export(NAME, frames, wav, W, H, DUR)
    av.HERE = av.HERE_SAVE

if __name__ == "__main__":
    main()
