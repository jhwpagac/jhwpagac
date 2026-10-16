#!/usr/bin/env python3
"""
Animácia „Tento byt sme predali“ – 3 fotky v jednej karte, bez pozadia, so zvukom.
Používa rovnaký štýl a pomocné funkcie ako generuj_komentar.py.

Výstup: predany_byt.mov (QuickTime Animation s alfa + zvuk), predany_byt.png,
        predany_byt_nahlad.mp4, predany_byt_zvuk.wav
"""
import math, os, sys, subprocess, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import generuj_komentar as g
from generuj_komentar import (clamp, prog, ease_out_cubic, ease_in_cubic, ease_out_back,
                              shadow_of, place, whoosh, pop, write_wav, font, SS, SR, FPS)

FOTKY = ["fotky/1_kuchyna.jpg", "fotky/2_kupelna.jpg", "fotky/3_balkon.jpg"]
STITOK = "TENTO BYT SME PREDALI"
PECIATKA = "PREDANÉ"
NAZOV = "predany_byt"

RED, CARD, EDGE = g.ACCENT, g.CARD, g.CARD_EDGE
T_IN, D_IN = 0.0, 0.6
T_BADGE, D_BADGE = 0.30, 0.5
T_PH, PH_STAG, D_PH = 0.35, 0.16, 0.55
T_STAMP, D_STAMP = 1.45, 0.20
T_OUT, D_OUT = 5.6, 0.5
DLZKA = T_OUT + D_OUT + 0.15

S = SS
CW = 1000 * S
PAD = 22 * S
GAP = 14 * S
TW = (CW - 2 * PAD - 2 * GAP) // 3
TH = TW * 4 // 3
TOP = 40 * S
CH = TOP + TH + PAD

def rounded(im, r):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=r, fill=255)
    out = im.convert("RGBA"); out.putalpha(m); return out

def load_tile(p):
    im = Image.open(os.path.join(HERE, p)).convert("RGB")
    tr = TW / TH
    if im.width / im.height > tr:
        w = int(im.height * tr); x = (im.width - w) // 2; im = im.crop((x, 0, x + w, im.height))
    else:
        h = int(im.width / tr); y = (im.height - h) // 2; im = im.crop((0, y, im.width, y + h))
    return rounded(im.resize((TW, TH), Image.LANCZOS), 18 * S)

def make_badge():
    f = font("ExtraBold", 21); sp = 1.6 * S
    tw = sum(f.getlength(ch) for ch in STITOK) + sp * (len(STITOK) - 1)
    ic = 28 * S; h = 50 * S; w = int(18 * S + ic + 12 * S + tw + 22 * S)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=RED + (255,))
    cx, cy = 18 * S + ic / 2, h / 2
    d.ellipse([cx - ic / 2, cy - ic / 2, cx + ic / 2, cy + ic / 2], fill=(255, 255, 255, 255))
    # domček
    d.polygon([(cx - 8 * S, cy - 0.5 * S), (cx, cy - 8 * S), (cx + 8 * S, cy - 0.5 * S)], fill=RED + (255,))
    d.rectangle([cx - 5.5 * S, cy - 1 * S, cx + 5.5 * S, cy + 7 * S], fill=RED + (255,))
    d.rectangle([cx - 1.6 * S, cy + 2 * S, cx + 1.6 * S, cy + 7 * S], fill=(255, 255, 255, 255))
    x = 18 * S + ic + 12 * S
    for ch in STITOK:
        d.text((x, cy), ch, font=f, fill="white", anchor="lm"); x += f.getlength(ch) + sp
    return img

def make_stamp():
    f = font("Black", 64); sp = 4 * S
    tw = sum(f.getlength(ch) for ch in PECIATKA) + sp * (len(PECIATKA) - 1)
    w, h = int(tw + 70 * S), int(110 * S)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=18 * S, fill=RED + (255,),
                        outline=(255, 255, 255, 255), width=6 * S)
    x = 35 * S
    for ch in PECIATKA:
        d.text((x, h / 2 + 2 * S), ch, font=f, fill="white", anchor="lm"); x += f.getlength(ch) + sp
    big = Image.new("RGBA", (int(w * 1.3), int(h * 2.2)), (0, 0, 0, 0))
    big.paste(img, ((big.width - w) // 2, (big.height - h) // 2))
    return big.rotate(9, resample=Image.BICUBIC, expand=False)

def thud():
    n = int(0.5 * SR); t = np.arange(n) / SR
    f = 55 + 90 * np.exp(-t * 30)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    s += g.rng.standard_normal(n) * np.exp(-t * 60) * 0.5
    return s * 0.95

def build_audio():
    n = int(DLZKA * SR); out = np.zeros((n, 2))
    def add(sig, at, pan=0.0):
        i = int(at * SR); j = min(n, i + len(sig))
        l = math.cos((pan + 1) * math.pi / 4) * 1.414; r = math.sin((pan + 1) * math.pi / 4) * 1.414
        out[i:j, 0] += sig[: j - i] * l; out[i:j, 1] += sig[: j - i] * r
    add(whoosh(0.5, 400, 3200, 0.45), T_IN)
    add(pop(700, 160, 0.14, 0.7), T_IN + 0.28)
    add(pop(1400, 500, 0.09, 0.4), T_BADGE + 0.12, -0.3)
    for k in range(3):
        add(pop(900 + k * 200, 300, 0.1, 0.5), T_PH + k * PH_STAG + 0.1, (k - 1) * 0.6)
    add(whoosh(0.22, 1500, 5000, 0.25), T_STAMP - 0.15)
    add(thud(), T_STAMP + D_STAMP - 0.03)
    add(whoosh(0.5, 3200, 450, 0.4), T_OUT - 0.05)
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.7
    return (out * 32767).astype(np.int16)

def render_card(t, tiles, stamp):
    img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, CW - 1, CH - 1], radius=30 * S, fill=CARD + (255,),
                        outline=EDGE + (255,), width=2 * S)
    for k, tile in enumerate(tiles):
        p = prog(t, T_PH + k * PH_STAG, D_PH)
        if p <= 0: continue
        s = 0.6 + 0.4 * ease_out_back(p, 2.0) if p < 1 else 1.0
        op = ease_out_cubic(clamp(p * 2.5))
        w, h = int(TW * s), int(TH * s)
        im = tile.resize((w, h), Image.BICUBIC) if s != 1 else tile.copy()
        if op < 1: im.putalpha(im.split()[3].point(lambda v: int(v * op)))
        cx = PAD + k * (TW + GAP) + TW / 2; cy = TOP + TH / 2 + (1 - ease_out_cubic(p)) * 30 * S
        img.alpha_composite(im, (int(cx - w / 2), int(cy - h / 2)))
    sp = prog(t, T_STAMP, D_STAMP)
    if sp > 0:
        s = 2.4 - 1.4 * ease_in_cubic(sp) if sp < 1 else 1.0
        if sp >= 1:  # malé dopruženie po dopade
            q = prog(t, T_STAMP + D_STAMP, 0.25)
            s = 1 + 0.06 * math.sin(q * math.pi) * (1 - q)
        op = clamp(sp * 3)
        w, h = int(stamp.width * s), int(stamp.height * s)
        im = stamp.resize((w, h), Image.BICUBIC)
        if op < 1: im.putalpha(im.split()[3].point(lambda v: int(v * op)))
        layer = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        layer.paste(im, (int(CW / 2 - w / 2), int(TOP + TH / 2 - h / 2)), im)
        img.alpha_composite(layer)
    return img

def main():
    tiles = [load_tile(p) for p in FOTKY]
    stamp = make_stamp(); badge = make_badge()
    bsh, _ = shadow_of(badge, 10 * S, 0.30)
    W = 1080; mt, mb = 70, 70
    H = int(math.ceil((CH / S + mt + mb) / 2) * 2)
    ccx, ccy = W / 2, mt + CH / S / 2
    bx = (W - CW / S) / 2 + PAD / S + badge.width / S / 2 - 4; by = mt - 4
    frames = os.path.join(HERE, "_frames"); shutil.rmtree(frames, ignore_errors=True); os.makedirs(frames)
    for fi in range(int(DLZKA * FPS)):
        t = fi / FPS
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pin = prog(t, T_IN, D_IN); pout = ease_in_cubic(prog(t, T_OUT, D_OUT))
        s = (0.72 + 0.28 * ease_out_back(pin, 1.9) if pin < 1 else 1.0) * (1 - 0.12 * pout)
        op = ease_out_cubic(clamp(pin * 2.2)) * (1 - pout)
        dy = (1 - ease_out_cubic(pin)) * 60 - pout * 40
        # otras karty pri dopade pečiatky
        q = prog(t, T_STAMP + D_STAMP, 0.3)
        shake = math.sin(q * 40) * 5 * (1 - q) if 0 < q < 1 else 0
        card = render_card(t, tiles, stamp)
        sh, _ = shadow_of(card, 22 * S, 0.45)
        place(canvas, sh, ccx + shake, ccy + dy + 14 * s, s, op)
        place(canvas, card, ccx + shake, ccy + dy, s, op)
        pb = prog(t, T_BADGE, D_BADGE)
        bs = (0.3 + 0.7 * ease_out_back(pb, 2.6) if pb < 1 else 1.0) * (1 - 0.3 * pout)
        bop = clamp(pb * 3) * (1 - clamp(pout * 1.4))
        byy = by + dy + (ccy - by) * (1 - s); bxx = ccx + shake + (bx - ccx) * s
        place(canvas, bsh, bxx, byy + 6, bs, bop); place(canvas, badge, bxx, byy, bs, bop)
        canvas.save(os.path.join(frames, f"f_{fi:04d}.png"))
        if abs(t - (T_OUT - 0.5)) < 0.5 / FPS: canvas.save(os.path.join(HERE, NAZOV + ".png"))
    wav = os.path.join(HERE, NAZOV + "_zvuk.wav"); write_wav(wav, build_audio())
    seq = os.path.join(frames, "f_%04d.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", seq, "-i", wav,
                    "-c:v", "qtrle", "-pix_fmt", "argb", "-c:a", "pcm_s16le", "-shortest",
                    os.path.join(HERE, NAZOV + ".mov")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"gradients=s={W}x{H}:c0=0x2b2f36:c1=0x0f1114:x0=0:y0=0:x1={W}:y1={H}:d={DLZKA}:r={FPS}",
                    "-framerate", str(FPS), "-i", seq, "-i", wav,
                    "-filter_complex", "[0][1]overlay=format=auto,format=yuv420p[v]", "-map", "[v]", "-map", "2:a",
                    "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", os.path.join(HERE, NAZOV + "_nahlad.mp4")], check=True)
    shutil.rmtree(frames)
    print("hotovo", W, H, DLZKA)

if __name__ == "__main__":
    main()
