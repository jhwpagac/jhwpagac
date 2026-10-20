#!/usr/bin/env python3
"""
Animácie pre Auto Vojto (bez pozadia, so zvukom) – farby a písmo podľa ich grafiky.
  mapa_trnava       – obrys okresu Trnava + pin na adrese Trstínska cesta 10
  recenzie          – Google recenzie vybiehajú zdola hore
  logo              – logo vyskočí so žiarou
  dve_tabulky       – 2 tabuľky s textom, 2 s po sebe
Spustenie: python3 generuj_auto_vojto.py [mapa] [recenzie] [logo] [tabulky]
"""
import math, os, sys, json, shutil, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "realitky"))
from generuj_komentar import (clamp, prog, ease_out_cubic, ease_in_cubic, ease_in_out, ease_out_back,
                              write_wav, SR, FPS, whoosh, pop)
from generuj_realitky import mix, add, finish, opacity, coin

S = 2
NAVY = (1, 20, 52)
CARD = (24, 44, 74)
GOLD = (248, 198, 18)
WHITE = (255, 255, 255)
MUTED = (170, 182, 200)
rng = np.random.default_rng(11)

def pf(w, size):
    return ImageFont.truetype(os.path.join(HERE, "fonty", f"Poppins-{w}.ttf"), int(size * S))

def export(name, frames, wav, W, H, dur):
    seq = os.path.join(frames, "f_%04d.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", seq, "-i", wav,
                    "-c:v", "qtrle", "-pix_fmt", "argb", "-c:a", "pcm_s16le", "-shortest",
                    os.path.join(HERE, name + ".mov")], check=True)
    # MP4 na zelenom pozadí (Ultra Key) – na stiahnutie
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"color=c=0x00FF00:s={W}x{H}:r={FPS}:d={dur}", "-framerate", str(FPS), "-i", seq, "-i", wav,
                    "-filter_complex", "[0][1]overlay=format=auto,format=yuv420p[v]", "-map", "[v]", "-map", "2:a",
                    "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-c:a", "aac", "-b:a", "256k", "-shortest",
                    "-movflags", "+faststart", os.path.join(HERE, name + "_zelene_pozadie.mp4")], check=True)
    # náhľad na tmavom pozadí
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"gradients=s={W}x{H}:c0=0x3a4252:c1=0x14171c:x0=0:y0=0:x1={W}:y1={H}:d={dur}:r={FPS}",
                    "-framerate", str(FPS), "-i", seq, "-i", wav,
                    "-filter_complex", "[0][1]overlay=format=auto,format=yuv420p[v]", "-map", "[v]", "-map", "2:a",
                    "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", os.path.join(HERE, name + "_nahlad.mp4")], check=True)
    shutil.rmtree(frames)
    print("hotovo", name, W, H, dur)

def new_frames(name):
    f = os.path.join(HERE, "_frames_" + name); shutil.rmtree(f, ignore_errors=True); os.makedirs(f); return f

def soft_shadow(img, blur, alpha, dy, pad=True):
    """Pridá mäkký tieň; pri pad=True zväčší plátno rovnomerne (stred ostáva), aby sa tieň neorezal."""
    m = int(blur * 2.5 + dy) if pad else 0
    base = Image.new("RGBA", (img.width + 2 * m, img.height + 2 * m), (0, 0, 0, 0)); base.paste(img, (m, m))
    a = base.split()[3].filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * alpha))
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0)); sh.putalpha(a)
    out = Image.new("RGBA", base.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, dy)); out.alpha_composite(base)
    return out

def paste_scaled(canvas, img, cx, cy, s, op, rot=0):
    """img v 2x rozlíšení, vloží so stredom (cx, cy) v 1x."""
    if s <= 0.01 or op <= 0.003: return
    im = img
    if rot: im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    w, h = max(1, int(im.width * s / S)), max(1, int(im.height * s / S))
    im = opacity(im.resize((w, h), Image.LANCZOS), op)
    canvas.alpha_composite(im, (int(round(cx - w / 2)), int(round(cy - h / 2))))

def wrap(text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.getlength(t) <= width or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def star(d, cx, cy, r, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    d.polygon(pts, fill=fill)

def sparkle():
    n = int(0.9 * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for k in range(7):
        o = int(k * 0.07 * SR); f = 2600 * (1.12 ** k)
        tt = t[: n - o]
        s[o:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 9) * (0.5 + 0.5 * rng.random())
    return s / np.max(np.abs(s)) * 0.25

def thump(vol=0.8):
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 50 + 110 * np.exp(-t * 35)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12) + rng.standard_normal(n) * np.exp(-t * 80) * 0.3
    return s * vol

# ================================================================== 1) MAPA TRNAVA
ADRESA = ("AUTO VOJTO", "Trstínska cesta 10, Trnava")
# približná poloha adresy Trstínska cesta 681/10 (SZ časť Trnavy)
ADRESA_GPS = (48.3905, 17.5675)

def mapa():
    name = "mapa_trnava"; dur = 5.6
    ring = json.load(open(os.path.join(HERE, "okres_trnava.geojson")))["geometry"]["coordinates"][0]
    lat0 = math.radians(48.45)
    proj = lambda lon, lat: (lon * math.cos(lat0), -lat)
    P = np.array([proj(*c) for c in ring])
    W, H = 1080, 1080
    mn, mx = P.min(0), P.max(0)
    sc = min(760 / (mx[0] - mn[0]), 880 / (mx[1] - mn[1])) * S
    off = np.array([(W * S - (mx[0] - mn[0]) * sc) / 2 - 120 * S, (H * S - (mx[1] - mn[1]) * sc) / 2]) - mn * sc
    pts = P * sc + off
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); total = cum[-1]
    ax, ay = np.array(proj(ADRESA_GPS[1], ADRESA_GPS[0])) * sc + off
    T_DRAW, D_DRAW, T_FILL, D_FILL, T_PIN, T_OUT = 0.1, 1.5, 1.1, 0.6, 1.9, 5.1
    f1, f2, fcity = pf("ExtraBold", 30), pf("Medium", 22), pf("Bold", 26)
    frames = new_frames(name)
    for fi in range(int(dur * FPS)):
        t = fi / FPS
        big = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        p_fill = ease_out_cubic(prog(t, T_FILL, D_FILL))
        if p_fill > 0:
            fl = Image.new("RGBA", big.size, (0, 0, 0, 0))
            ImageDraw.Draw(fl).polygon([tuple(p) for p in pts], fill=NAVY + (int(235 * p_fill),))
            big.alpha_composite(soft_shadow(fl, 16 * S, 0.5, 10 * S, pad=False))
            # názov okresu
            dd = ImageDraw.Draw(big)
            dd.text((pts[:, 0].mean() - 20 * S, pts[:, 1].min() + (pts[:, 1].max() - pts[:, 1].min()) * 0.33), "OKRES TRNAVA", font=fcity, anchor="mm",
                    fill=GOLD + (int(150 * p_fill),))
        pd = ease_in_out(prog(t, T_DRAW, D_DRAW))
        if pd > 0:
            L = total * pd; k = int(np.searchsorted(cum, L))
            line = [tuple(p) for p in pts[:k]]
            if 0 < k < len(pts):
                u = (L - cum[k - 1]) / max(1e-9, seg[k - 1]); line.append(tuple(pts[k - 1] + (pts[k] - pts[k - 1]) * u))
            if len(line) > 1:
                gl = Image.new("L", big.size, 0)
                ImageDraw.Draw(gl).line(line, fill=255, width=int(16 * S), joint="curve")
                gl = gl.filter(ImageFilter.GaussianBlur(12 * S)).point(lambda v: int(v * 0.45))
                gll = Image.new("RGBA", big.size, GOLD + (0,)); gll.putalpha(gl); big.alpha_composite(gll)
                d = ImageDraw.Draw(big)
                d.line(line, fill=GOLD + (255,), width=int(5 * S), joint="curve")
                if pd < 1:
                    hx, hy = line[-1]; r = 8 * S; d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=WHITE + (255,))
        d = ImageDraw.Draw(big)
        pp = prog(t, T_PIN, 0.45)
        if pp > 0:
            q = (t - T_PIN - 0.3) % 1.4 / 1.4 if t > T_PIN + 0.3 else -1   # opakujúca sa vlna
            if q >= 0:
                for k2 in (0, 0.5):
                    qq = (q + k2) % 1
                    rr = (10 + 70 * qq) * S
                    d.ellipse([ax - rr, ay - rr * 0.45, ax + rr, ay + rr * 0.45], outline=GOLD + (int(220 * (1 - qq)),), width=int(3 * S))
            drop = (1 - ease_out_back(pp, 2.2)) * 90 * S
            d.ellipse([ax - 12 * S, ay - 4 * S, ax + 12 * S, ay + 4 * S], fill=(0, 0, 0, int(130 * pp)))
            r = 26 * S; y = ay - drop
            d.polygon([(ax - r * 0.72, y - r * 1.25), (ax + r * 0.72, y - r * 1.25), (ax, y)], fill=GOLD + (255,))
            d.ellipse([ax - r, y - r * 2.6, ax + r, y - r * 0.6], fill=GOLD + (255,), outline=NAVY + (255,), width=int(3 * S))
            d.ellipse([ax - r * 0.42, y - r * 2.02, ax + r * 0.42, y - r * 1.18], fill=NAVY + (255,))
            pl = prog(t, T_PIN + 0.3, 0.45)
            if pl > 0:
                tw = max(f1.getlength(ADRESA[0]), f2.getlength(ADRESA[1])); pw, ph = tw + 56 * S, 108 * S
                lab = Image.new("RGBA", (int(pw), int(ph)), (0, 0, 0, 0)); ld = ImageDraw.Draw(lab)
                ld.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=22 * S, fill=CARD + (245,), outline=GOLD + (255,), width=int(3 * S))
                ld.text((28 * S, 30 * S), ADRESA[0], font=f1, fill=GOLD + (255,), anchor="lm")
                ld.text((28 * S, 74 * S), ADRESA[1], font=f2, fill=WHITE + (255,), anchor="lm")
                s2 = ease_out_back(pl, 1.8); lx = ax + 50 * S + pw / 2 - (1 - s2) * 30 * S
                ww, hh = max(1, int(pw * s2)), max(1, int(ph * s2))
                im = opacity(lab.resize((ww, hh), Image.BICUBIC), clamp(pl * 2))
                big.alpha_composite(im, (int(lx - ww / 2), int(ay - 52 * S - hh / 2)))
        canvas = big.resize((W, H), Image.LANCZOS)
        pout = ease_in_cubic(prog(t, T_OUT, 0.45))
        if pout > 0:
            s2 = 1 - 0.1 * pout; cw, ch = int(W * s2), int(H * s2)
            small = opacity(canvas.resize((cw, ch), Image.LANCZOS), 1 - pout)
            canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0)); canvas.alpha_composite(small, ((W - cw) // 2, (H - ch) // 2))
        canvas.save(os.path.join(frames, f"f_{fi:04d}.png"))
    n = int(dur * SR); buf = mix(n)
    add(buf, whoosh(D_DRAW + 0.2, 300, 2200, 0.35), T_DRAW)
    add(buf, pop(900, 200, 0.14, 0.8), T_PIN + 0.3)
    add(buf, coin(0.8, 0.25, 0.5), T_PIN + 0.42)
    add(buf, whoosh(0.3, 900, 3500, 0.2), T_PIN + 0.3)
    add(buf, whoosh(0.45, 3000, 500, 0.3), T_OUT - 0.05)
    wav = os.path.join(HERE, name + "_zvuk.wav"); write_wav(wav, finish(buf))
    export(name, frames, wav, W, H, dur)

# ================================================================== 2) RECENZIE
RECENZIE = [  # skrátené verzie skutočných Google recenzií
    ("Lucia Lipčáková", "pred 5 mesiacmi", "Už roky využívame služby tohto servisu. Milý prístup personálu. Krátka a príjemná doba čakania v peknom novom prostredí. Odporúčam."),
    ("Patrícia Dominová", "pred 3 mesiacmi", "Chcem sa veľmi pekne poďakovať mladému chalanovi, ktorý mi dnes pomohol s defektom na aute. Bol veľmi ochotný a profesionálny."),
    ("Matej Kadlec", "pred 6 mesiacmi", "Som dlhoročný zákazník a so službami v servise som vždy nadmieru spokojný."),
    ("Peter Burda", "pred 4 mesiacmi", "Dnes som konečne šoféroval moju BMW 6tku bez toho, aby ma ťahala do protismeru."),
]
AVATAR_COL = [(16, 150, 160), (20, 140, 110), (235, 90, 40), (90, 110, 200)]

def review_card(i, name, when, text, w):
    fN, fW, fT = pf("Bold", 25), pf("Regular", 19), pf("Regular", 23)
    pad = 30 * S; av = 62 * S
    lines = wrap(text, fT, w - 2 * pad)
    lh = int(23 * 1.5 * S)
    h = int(pad + av + 18 * S + len(lines) * lh + pad - 6 * S)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=26 * S, fill=CARD + (242,), outline=GOLD + (110,), width=int(2 * S))
    d.ellipse([pad, pad, pad + av, pad + av], fill=AVATAR_COL[i % 4] + (255,))
    d.text((pad + av / 2, pad + av / 2), name[0], font=pf("SemiBold", 28), fill=WHITE + (255,), anchor="mm")
    x = pad + av + 18 * S
    d.text((x, pad + 4 * S), name, font=fN, fill=WHITE + (255,), anchor="lt")
    for k in range(5): star(d, x + 11 * S + k * 25 * S, pad + 50 * S, 10 * S, GOLD + (255,))
    d.text((x + 5 * 25 * S + 10 * S, pad + 50 * S), "Google · " + when, font=fW, fill=MUTED + (255,), anchor="lm")
    y = pad + av + 18 * S
    for ln in lines:
        d.text((pad, y), ln, font=fT, fill=WHITE + (255,), anchor="lt"); y += lh
    return soft_shadow(img, 14 * S, 0.45, 8 * S)

def header_pill():
    f1, f2 = pf("ExtraBold", 36), pf("Medium", 22)
    w, h = 560 * S, 96 * S
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=NAVY + (250,), outline=GOLD + (255,), width=int(3 * S))
    d.text((44 * S, h / 2), "4,6", font=f1, fill=GOLD + (255,), anchor="lm")
    x = 44 * S + f1.getlength("4,6") + 20 * S
    for k in range(5): star(d, x + 14 * S + k * 31 * S, h / 2 - 14 * S, 13 * S, GOLD + (255,))
    d.text((x, h / 2 + 18 * S), "205 recenzií na Google", font=f2, fill=WHITE + (255,), anchor="lm")
    return soft_shadow(img, 12 * S, 0.45, 6 * S)

def recenzie():
    name = "recenzie"; dur = 7.6
    W = 1080; cw = 960 * S
    cards = [review_card(i, *r, cw) for i, r in enumerate(RECENZIE)]
    head = header_pill()
    gap = 22
    heights = [c.height / S - 2 * (14 * 2.5 + 8) for c in cards]
    H = int((head.height / S - 2 * (12 * 2.5 + 6)) + gap + sum(heights) + gap * (len(cards) - 1) + 60); H += H % 2
    hh = head.height / S - 2 * (12 * 2.5 + 6)
    slots = []; y = 30 + hh + gap
    for h in heights: slots.append(y + h / 2); y += h + gap
    T_HEAD, T0, STAG, D_IN, T_OUT = 0.0, 0.45, 0.55, 0.6, 7.0
    frames = new_frames(name)
    for fi in range(int(dur * FPS)):
        t = fi / FPS
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pout = ease_in_cubic(prog(t, T_OUT, 0.5))
        ph = prog(t, T_HEAD, 0.5)
        if ph > 0:
            s = ease_out_back(ph, 2.0) if ph < 1 else 1
            paste_scaled(canvas, head, W / 2, 30 + hh / 2 - pout * 30, s * (1 - 0.1 * pout), clamp(ph * 3) * (1 - pout))
        for i, c in enumerate(cards):
            p = prog(t, T0 + i * STAG, D_IN)
            if p <= 0: continue
            e = ease_out_back(p, 1.3)
            yy = slots[i] + (1 - e) * (H - slots[i] + c.height / S) - pout * 40
            paste_scaled(canvas, c, W / 2, yy, 1 - 0.06 * pout, clamp(p * 2.5) * (1 - pout))
        canvas.save(os.path.join(frames, f"f_{fi:04d}.png"))
    n = int(dur * SR); buf = mix(n)
    add(buf, pop(1200, 400, 0.1, 0.5), T_HEAD + 0.12)
    add(buf, sparkle(), T_HEAD + 0.15)
    for i in range(len(cards)):
        add(buf, whoosh(0.35, 500, 2800, 0.3), T0 + i * STAG - 0.05, (i % 2 - 0.5) * 0.6)
        add(buf, pop(800 + 120 * i, 250, 0.11, 0.55), T0 + i * STAG + 0.3, (i % 2 - 0.5) * 0.6)
    add(buf, whoosh(0.5, 3000, 450, 0.35), T_OUT - 0.05)
    wav = os.path.join(HERE, name + "_zvuk.wav"); write_wav(wav, finish(buf))
    export(name, frames, wav, W, H, dur)

# ================================================================== 3) LOGO
def load_logo(size):
    src = Image.open(os.path.join(HERE, "zdroj_grafika_logo.jpg")).convert("RGB")
    cx, cy, r = 540, 425, 96.4
    box = (int(cx - r - 4), int(cy - r - 4), int(cx + r + 4), int(cy + r + 4))
    k = size / (2 * r)
    im = src.crop(box).resize((int((box[2] - box[0]) * k), int((box[3] - box[1]) * k)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))
    m = Image.new("L", (im.width * 4, im.height * 4), 0)
    c4 = (cx - box[0]) * k * 4; rr = r * k * 4
    ImageDraw.Draw(m).ellipse([c4 - rr, c4 - rr, c4 + rr, c4 + rr], fill=255)
    m = m.resize(im.size, Image.LANCZOS)
    out = im.convert("RGBA"); out.putalpha(m)
    return out.crop(out.getbbox())

def logo():
    name = "logo"; dur = 4.2
    W = H = 1080
    lg = load_logo(600 * S)
    lsh = soft_shadow(lg, 20 * S, 0.5, 12 * S)
    mask = lg.split()[3]
    T_IN, T_OUT = 0.15, 3.65
    frames = new_frames(name)
    for fi in range(int(dur * FPS)):
        t = fi / FPS
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        p = prog(t, T_IN, 0.7)
        pout = ease_in_cubic(prog(t, T_OUT, 0.5))
        # zlaté kruhy – rázová vlna
        q = prog(t, T_IN + 0.35, 0.8)
        if 0 < q < 1:
            d = ImageDraw.Draw(canvas)
            for k2, dl in ((0, 0), (1, 0.12)):
                qq = clamp((q - dl) / (1 - dl))
                if qq <= 0: continue
                rr = 300 + 210 * ease_out_cubic(qq)
                d.ellipse([W / 2 - rr, H / 2 - rr, W / 2 + rr, H / 2 + rr], outline=GOLD + (int(230 * (1 - qq)),), width=max(1, int(8 * (1 - qq))))
            for j in range(16):
                a = j / 16 * 2 * math.pi + 0.1
                r0 = 320 + 190 * ease_out_cubic(q); r1 = r0 + 40 * (1 - q)
                d.line([(W / 2 + math.cos(a) * r0, H / 2 + math.sin(a) * r0), (W / 2 + math.cos(a) * r1, H / 2 + math.sin(a) * r1)],
                       fill=GOLD + (int(255 * (1 - q)),), width=6)
        if p > 0:
            s = ease_out_back(p, 2.4) if p < 1 else 1.0
            s *= 1 - 0.25 * pout
            rot = (1 - ease_out_cubic(p)) * -25
            img = lsh.copy()
            # lesk prechádzajúci logom
            sp = prog(t, 1.25, 0.7)
            if 0 < sp < 1:
                g = Image.new("L", lg.size, 0); gd = ImageDraw.Draw(g)
                x = -lg.width * 0.4 + sp * lg.width * 1.8; wdt = lg.width * 0.16
                gd.polygon([(x, 0), (x + wdt, 0), (x + wdt - lg.width * 0.4, lg.height), (x - lg.width * 0.4, lg.height)], fill=120)
                g = ImageChops.multiply(g.filter(ImageFilter.GaussianBlur(8 * S)), mask)
                wl = Image.new("RGBA", lg.size, (255, 255, 255, 0)); wl.putalpha(g)
                tmp = Image.new("RGBA", img.size, (0, 0, 0, 0)); tmp.alpha_composite(wl); img.alpha_composite(tmp)
            paste_scaled(canvas, img, W / 2, H / 2 + 6, s, clamp(p * 3) * (1 - pout), rot)
        canvas.save(os.path.join(frames, f"f_{fi:04d}.png"))
    n = int(dur * SR); buf = mix(n)
    add(buf, whoosh(0.5, 400, 3000, 0.45), T_IN - 0.1)
    add(buf, thump(0.9), T_IN + 0.33)
    add(buf, pop(700, 160, 0.14, 0.6), T_IN + 0.33)
    add(buf, sparkle(), 1.25)
    add(buf, whoosh(0.5, 3000, 450, 0.35), T_OUT - 0.05)
    wav = os.path.join(HERE, name + "_zvuk.wav"); write_wav(wav, finish(buf))
    export(name, frames, wav, W, H, dur)

# ================================================================== 4) DVE TABUĽKY
TABULKY = [
    ("diag", "Preto si dávame záležať", "na presnej diagnostike"),
    ("check", "a na poctivej kontrole", "každého vozidla"),
]

def icon(d, kind, cx, cy, s):
    w = int(4 * S)
    if kind == "diag":
        pts = [(-30, 0), (-14, 0), (-6, -22), (6, 24), (14, 0), (30, 0)]
        d.line([(cx + x * s, cy + y * s) for x, y in pts], fill=GOLD + (255,), width=w, joint="curve")
    else:
        r = 26 * s
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD + (255,), width=w)
        d.line([(cx - 11 * s, cy + 1 * s), (cx - 2 * s, cy + 10 * s), (cx + 13 * s, cy - 9 * s)], fill=GOLD + (255,), width=w, joint="curve")

def table_card(kind, l1, l2, w):
    h = 190 * S
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=28 * S, fill=CARD + (238,), outline=GOLD + (130,), width=int(2 * S))
    icon(d, kind, 84 * S, h / 2, S)
    d.text((150 * S, h / 2 - 30 * S), l1, font=pf("SemiBold", 34), fill=WHITE + (255,), anchor="lm")
    d.text((150 * S, h / 2 + 26 * S), l2, font=pf("Bold", 40), fill=GOLD + (255,), anchor="lm")
    return soft_shadow(img, 16 * S, 0.5, 10 * S)

def tabulky():
    name = "dve_tabulky"; dur = 6.8
    W = 1080
    cards = [table_card(k, a, b, 960 * S) for k, a, b in TABULKY]
    ch = cards[0].height / S - 2 * (16 * 2.5 + 10); gap = 30
    H = int(ch * 2 + gap + 80); H += H % 2
    slots = [40 + ch / 2, 40 + ch * 1.5 + gap]
    times = [0.1, 2.1]; T_OUT = 6.2
    frames = new_frames(name)
    for fi in range(int(dur * FPS)):
        t = fi / FPS
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pout = ease_in_cubic(prog(t, T_OUT, 0.5))
        for i, c in enumerate(cards):
            p = prog(t, times[i], 0.65)
            if p <= 0: continue
            e = ease_out_back(p, 1.4)
            yy = slots[i] + (1 - e) * 140 - pout * 40
            paste_scaled(canvas, c, W / 2, yy, (0.9 + 0.1 * e) * (1 - 0.06 * pout), clamp(p * 2.5) * (1 - pout))
        canvas.save(os.path.join(frames, f"f_{fi:04d}.png"))
    n = int(dur * SR); buf = mix(n)
    for i, tt in enumerate(times):
        add(buf, whoosh(0.45, 450, 3000, 0.4), tt - 0.05)
        add(buf, pop(750, 200, 0.13, 0.6), tt + 0.35)
    add(buf, whoosh(0.5, 3000, 450, 0.35), T_OUT - 0.05)
    wav = os.path.join(HERE, name + "_zvuk.wav"); write_wav(wav, finish(buf))
    export(name, frames, wav, W, H, dur)

if __name__ == "__main__":
    which = sys.argv[1:] or ["mapa", "recenzie", "logo", "tabulky"]
    if "mapa" in which: mapa()
    if "recenzie" in which: recenzie()
    if "logo" in which: logo()
    if "tabulky" in which: tabulky()
