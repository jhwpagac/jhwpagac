#!/usr/bin/env python3
"""Story 9:16 – vyhlásenie výhercu: mená účastníkov sa točia ako na automate a zastavia na výhercovi."""
import math, os, sys, shutil, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "auto-vojto"))
from generuj_auto_vojto import (clamp, prog, ease_out_cubic, ease_in_cubic, ease_out_back,
                                write_wav, mix, add, finish, whoosh, pop, sparkle, thump, SR, FPS)
from generuj_realitky import coin
def pf(w, s): return ImageFont.truetype(os.path.join(ROOT, "auto-vojto", "fonty", f"Poppins-{w}.ttf"), s)

VYHERCA = "@lysak8"
NAME = "losovanie_vyherca_story"
W, H = 1080, 1920
RED, WHITE, BG, MUTED = (227, 6, 19), (255, 255, 255), (12, 12, 14), (150, 150, 160)
DUR = 9.0
T_SPIN, D_SPIN = 1.2, 3.6          # točenie 1,2 s – 4,8 s
T_WIN = T_SPIN + D_SPIN
rng = np.random.default_rng(8)
ROW = 150; N_ITEMS = 46            # koľko mien prebehne

# účastníci súťaže (autori komentárov pod príspevkom, súhlasili so zverejnením mena)
UCASTNICI = ["_viktortopoli_", "patrikvarga.69", "erik_hrnciarik", "sun.rus", "zuzanajanosik", "duso107",
             "marcipanik_mata", "sarlo_vavro", "zofcin_.45._", "mato_sotak_", "monciqund", "michal__9",
             "pa3ciia", "_alucard_zxc", "mar_ek.ley", "lukas_klima_s", "jarkasimona", "martin_chmelik",
             "simonachabadova", "aja.z", "_k_ia_", "stfn_mkl", "vikineckaaa_", "jana_lahka", "m_i_r_c_a",
             "tosko_lahky"]
ostatni = ["@" + u for u in UCASTNICI]
seq = []
while len(seq) < N_ITEMS + 2:
    blok = list(ostatni); rng.shuffle(blok); seq += blok
NAMES = seq[:N_ITEMS] + [VYHERCA] + seq[N_ITEMS:N_ITEMS + 2]
WIN_IDX = N_ITEMS

def background():
    im = Image.new("RGB", (W, H), BG)
    g = Image.new("L", (W, H), 0); d = ImageDraw.Draw(g)
    d.ellipse([-400, 500, W + 400, 1500], fill=110)
    g = g.filter(ImageFilter.GaussianBlur(220))
    im.paste(Image.new("RGB", (W, H), (70, 8, 14)), (0, 0), g)
    return im

BGIMG = background()
CONF = [(rng.uniform(0, W), rng.uniform(-300, -20), rng.uniform(-120, 120), rng.uniform(500, 900),
         rng.uniform(0, 6.28), rng.uniform(-8, 8), [RED, WHITE, (255, 200, 40), (255, 90, 100)][int(rng.integers(0, 4))],
         rng.uniform(10, 22)) for _ in range(220)]

def pos(t):
    """Pozícia valca v „riadkoch“ – rýchly štart, dlhé spomalenie a jemné dopruženie."""
    p = prog(t, T_SPIN, D_SPIN)
    e = 1 - (1 - p) ** 4
    over = 0.18 * math.sin(math.pi * clamp((t - T_WIN) / 0.35)) * (1 - clamp((t - T_WIN) / 0.35)) if t > T_WIN else 0
    return e * WIN_IDX + over

def frame(t):
    im = BGIMG.copy(); d = ImageDraw.Draw(im)
    # hlavička
    ph = prog(t, 0.1, 0.5); e = ease_out_back(ph, 1.8) if ph < 1 else 1
    if ph > 0:
        d.text((W / 2, 330 - (1 - e) * 60), "LOSOVANIE", font=pf("ExtraBold", 110), fill=WHITE, anchor="mm")
        d.text((W / 2, 445 - (1 - e) * 60), "VÝHERCU", font=pf("ExtraBold", 110), fill=RED, anchor="mm")
    sub = "Výherca je…" if t < T_WIN else "Gratulujeme!"
    if t > 0.5:
        d.text((W / 2, 560), sub, font=pf("SemiBold", 44), fill=MUTED if t < T_WIN else WHITE, anchor="mm")
    # valec s menami
    cx, cy = W / 2, 900
    wb = prog(t, T_WIN, 0.5)
    box_w, box_h = 860, ROW * 3
    if t > 0.6:
        d.rounded_rectangle([cx - box_w / 2, cy - box_h / 2, cx + box_w / 2, cy + box_h / 2], radius=40, fill=(22, 22, 26), outline=(55, 55, 62), width=3)
        p = pos(t)
        f_norm, f_win = pf("Bold", 64), pf("ExtraBold", 78)
        layer = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
        base = int(p)
        for k in range(base - 2, base + 4):
            if k < 0 or k >= len(NAMES): continue
            y = box_h / 2 + (k - p) * ROW
            dist = abs(k - p)
            a = int(255 * clamp(1 - dist / 1.8))
            is_win = (k == WIN_IDX and t >= T_WIN)
            col = (WHITE if not is_win else WHITE) + (a,)
            ld.text((box_w / 2, y), NAMES[k], font=f_win if is_win else f_norm, fill=col, anchor="mm")
        # rozmazanie pri rýchlom točení
        speed = (pos(t + 0.02) - pos(t)) / 0.02
        if speed > 4: layer = layer.filter(ImageFilter.BoxBlur(min(6, speed / 6)))
        im.paste(layer, (int(cx - box_w / 2), int(cy - box_h / 2)), layer)
        d = ImageDraw.Draw(im)
        # stredový výber
        glow = 6 + int(10 * math.sin(math.pi * wb)) if 0 < wb < 1 else 6
        d.rounded_rectangle([cx - box_w / 2 + 20, cy - ROW / 2 + 8, cx + box_w / 2 - 20, cy + ROW / 2 - 8], radius=30,
                            outline=RED, width=glow)
        for sx in (-1, 1):
            x = cx + sx * (box_w / 2 + 34)
            d.polygon([(x, cy), (x + sx * 30, cy - 24), (x + sx * 30, cy + 24)], fill=RED)
    # výhra
    if t >= T_WIN:
        # konfety
        d = ImageDraw.Draw(im)
        tc = t - T_WIN
        for x0, y0, vx, vy, a0, va, col, s in CONF:
            x = x0 + vx * tc + 40 * math.sin(tc * 2 + a0); y = y0 + vy * tc + 120 * tc * tc
            if y > H + 40: continue
            ang = a0 + va * tc
            dx, dy = math.cos(ang) * s, math.sin(ang) * s * 0.45
            d.polygon([(x - dx, y - dy), (x + dy, y - dx * 0.3), (x + dx, y + dy), (x - dy, y + dx * 0.3)], fill=col)
        pw = prog(t, T_WIN + 0.15, 0.5); e = ease_out_back(pw, 2.0) if pw < 1 else 1
        if pw > 0:
            f = pf("ExtraBold", 64)
            lab = "VÝHERCA"
            tw = f.getlength(lab) + 90
            y = 1240
            sc = e
            w2, h2 = tw * sc, 110 * sc
            d.rounded_rectangle([W / 2 - w2 / 2, y - h2 / 2, W / 2 + w2 / 2, y + h2 / 2], radius=55 * sc, fill=RED)
            if sc > 0.3: d.text((W / 2, y + 2), lab, font=pf("ExtraBold", int(64 * sc)), fill=WHITE, anchor="mm")
        pt = prog(t, T_WIN + 0.6, 0.5)
        if pt > 0:
            a = int(255 * pt)
            txt = Image.new("RGBA", (W, 300), (0, 0, 0, 0)); td = ImageDraw.Draw(txt)
            td.rounded_rectangle([110, 10, W - 110, 260], radius=36, fill=(14, 14, 16, int(225 * pt)), outline=(60, 60, 66, a), width=2)
            td.text((W / 2, 60), "Vyhráva 2 VIP vstupenky na", font=pf("Medium", 40), fill=(230, 230, 235, a), anchor="mm")
            td.text((W / 2, 115), "PML 22 | ARAVER FIGHT NIGHT", font=pf("Bold", 42), fill=(230, 230, 235, a), anchor="mm")
            td.text((W / 2, 210), "Ozveme sa Vám do komentárov!", font=pf("Bold", 46), fill=(255, 255, 255, a), anchor="mm")
            im.paste(txt, (0, int(1330 + (1 - pt) * 30)), txt)
    # záverečné stmavnutie
    po = prog(t, DUR - 0.4, 0.4)
    if po > 0:
        im = Image.blend(im, Image.new("RGB", (W, H), (0, 0, 0)), po)
    return im

def audio():
    n = int(DUR * SR); buf = mix(n)
    add(buf, whoosh(0.5, 400, 3000, 0.4), 0.05)
    add(buf, pop(700, 160, 0.14, 0.6), 0.35)
    # tikanie pri prechode každého mena
    last = 0
    for i in range(1, int(DUR * SR / 240)):
        t = i * 240 / SR
        if T_SPIN <= t <= T_WIN + 0.05:
            k = int(pos(t))
            if k != last:
                last = k
                m = int(0.018 * SR); tk = np.arange(m) / SR
                tick = (np.sin(2 * np.pi * 1800 * tk) * 0.6 + rng.standard_normal(m) * 0.4) * np.exp(-tk * 300)
                add(buf, tick * 0.35, t, rng.uniform(-0.3, 0.3))
    # vírenie bubna počas točenia
    m = int(D_SPIN * SR); tt = np.arange(m) / SR
    roll = rng.standard_normal(m) * (0.5 + 0.5 * np.sin(2 * np.pi * 28 * tt) ** 2)
    roll = np.convolve(roll, np.ones(8) / 8, mode="same") * np.linspace(0.05, 0.3, m)
    add(buf, roll, T_SPIN)
    # fanfára pri výhre
    add(buf, thump(1.0), T_WIN)
    for k, f0 in enumerate([523.25, 659.25, 783.99, 1046.5]):
        m = int(1.6 * SR); tt = np.arange(m) / SR
        tone = sum(np.sin(2 * np.pi * f0 * h * tt) / h for h in (1, 2, 3)) * np.exp(-tt * 2.2) * np.minimum(1, tt / 0.01)
        add(buf, tone * 0.22, T_WIN + 0.02 + k * 0.07, (k - 1.5) * 0.3)
    add(buf, sparkle(), T_WIN + 0.1)
    for k in range(6): add(buf, pop(1200 + 200 * k, 400, 0.07, 0.35), T_WIN + 0.05 + k * 0.05, rng.uniform(-0.7, 0.7))
    add(buf, coin(1.0, 0.3, 0.6), T_WIN + 0.7)
    return finish(buf)

if __name__ == "__main__":
    fr = os.path.join(HERE, "_frames"); shutil.rmtree(fr, ignore_errors=True); os.makedirs(fr)
    for i in range(int(DUR * FPS)):
        frame(i / FPS).save(os.path.join(fr, f"f_{i:04d}.png"))
    wav = os.path.join(HERE, NAME + "_zvuk.wav"); write_wav(wav, audio())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(fr, "f_%04d.png"), "-i", wav,
                    "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", os.path.join(HERE, NAME + ".mp4")], check=True)
    frame(T_WIN + 1.6).save(os.path.join(HERE, NAME + "_nahlad.jpg"), quality=92)
    shutil.rmtree(fr); print("hotovo", NAME)
