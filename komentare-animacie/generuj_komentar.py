#!/usr/bin/env python3
"""
Generator animovaných komentárov (bez pozadia) na vloženie do videa.

Výstup pre každý komentár:
  - <nazov>.mov          ProRes 4444 s alfa kanálom + zvuk (priamo do Premiere)
  - <nazov>_zvuk.wav     samostatné zvukové efekty
  - <nazov>_nahlad.mp4   náhľad na tmavom pozadí (len na pozretie)
  - <nazov>_still.png    statický frame komentára (na predĺženie cez freeze)

Použitie:  python3 generuj_komentar.py
Komentáre sa upravujú v zozname KOMENTARE nižšie.
"""
import math, os, subprocess, shutil, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------------------------------------------------------- KONFIGURÁCIA
KOMENTARE = [
    {
        "nazov": "komentar_01_vibracie_pri_brzdeni",
        "meno": "Divák",
        "cas": "pred 2 dňami",
        "text": "A čo vibrácie pri brzdení? Výlučne pri brzdení a evidentne "
                "pri prudšom zabrzdení. Ďakujem za odpoveď.",
        # frázy, ktoré sa zvýraznia markerom (musia presne sedieť so slovami v texte)
        "zvyraznit": ["vibrácie pri brzdení?", "pri prudšom zabrzdení."],
        "lajky": 24,
        "stitok": "OTÁZKA OD DIVÁKA",
    },
]

FPS = 30
DLZKA = 7.0            # sekundy
SS = 2                 # supersampling (kreslí sa v 2x, potom zmenší)
CANVAS_W = 1080        # šírka výsledného videa
ACCENT = (255, 106, 0)         # oranžová – štítok
MARKER = (255, 214, 64)        # žltý zvýrazňovač
HEART = (255, 45, 85)
FONT_DIR = "/usr/share/fonts/opentype/inter/"
SR = 48000

def font(w, size):
    return ImageFont.truetype(FONT_DIR + f"Inter-{w}.otf", size * SS)

# ---------------------------------------------------------------- EASING
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, start, dur): return clamp((t - start) / dur)
def ease_out_cubic(x): return 1 - (1 - x) ** 3
def ease_in_cubic(x): return x ** 3
def ease_in_out(x): return 4 * x**3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def ease_out_back(x, s=1.7):
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2
def ease_out_elastic(x):
    if x in (0, 1): return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi) / 3) + 1

# ---------------------------------------------------------------- TIMELINE
T_IN, D_IN = 0.00, 0.60
T_BADGE, D_BADGE = 0.32, 0.50
T_WORDS, WORD_STAGGER, D_WORD = 0.55, 0.045, 0.22
D_HL = 0.38
T_OUT, D_OUT = 6.35, 0.50

# ---------------------------------------------------------------- LAYOUT
def layout(c):
    S = SS
    L = {}
    L["card_w"] = 1000 * S
    L["pad"] = 34 * S
    L["av"] = 64 * S
    L["gap"] = 20 * S
    L["tx"] = L["pad"] + L["av"] + L["gap"]
    L["tw"] = L["card_w"] - L["tx"] - L["pad"]
    L["f_name"] = font("Bold", 24)
    L["f_meta"] = font("Medium", 21)
    L["f_body"] = font("Medium", 34)
    L["f_act"] = font("SemiBold", 21)
    L["f_badge"] = font("ExtraBold", 21)
    L["lh"] = int(34 * 1.36 * S)
    top = 40 * S
    L["name_y"] = top
    L["body_y"] = top + 40 * S
    # zalamovanie slov
    words = c["text"].split()
    space = L["f_body"].getlength(" ")
    lines, cur, w = [], [], 0
    for wd in words:
        ww = L["f_body"].getlength(wd)
        if cur and w + space + ww > L["tw"]:
            lines.append(cur); cur, w = [], 0
        cur.append(wd); w += (space if len(cur) > 1 else 0) + ww
    if cur: lines.append(cur)
    boxes = []  # (word, x, y, w, line_idx)
    for li, ln in enumerate(lines):
        x = L["tx"]
        y = L["body_y"] + li * L["lh"]
        for wd in ln:
            ww = L["f_body"].getlength(wd)
            boxes.append([wd, x, y, ww, li])
            x += ww + space
    L["boxes"] = boxes
    L["space"] = space
    L["act_y"] = L["body_y"] + len(lines) * L["lh"] + 14 * S
    L["card_h"] = L["act_y"] + 30 * S + 32 * S
    # zvýraznené rozsahy slov
    hl = []
    wl = [b[0] for b in boxes]
    for ph in c["zvyraznit"]:
        pw = ph.split()
        for i in range(len(wl) - len(pw) + 1):
            if wl[i:i + len(pw)] == pw:
                hl.append((i, i + len(pw))); break
    L["hl"] = hl
    return L

# ---------------------------------------------------------------- KRESLENIE KARTY
def draw_heart(d, cx, cy, size, fill=None, outline=None, width=0):
    pts = []
    for i in range(80):
        a = i / 80 * 2 * math.pi
        x = 16 * math.sin(a) ** 3
        y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((cx + x * size / 34, cy + y * size / 34))
    if fill: d.polygon(pts, fill=fill)
    if outline: d.line(pts + [pts[0]], fill=outline, width=width, joint="curve")

def render_card(c, L, t):
    S = SS
    W, H = L["card_w"], L["card_h"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=30 * S, fill=(255, 255, 255, 255))

    # avatar s iniciálou
    p, av = L["pad"], L["av"]
    ay = L["name_y"] - 4 * S
    grad = Image.new("RGBA", (av, av))
    gd = ImageDraw.Draw(grad)
    for i in range(av):
        k = i / av
        col = (int(255 * (1 - k) + 255 * k), int(150 * (1 - k) + 70 * k), int(40 * (1 - k) + 0 * k), 255)
        gd.line([(0, i), (av, i)], fill=col)
    mask = Image.new("L", (av, av), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, av - 1, av - 1], fill=255)
    img.paste(grad, (p, ay), mask)
    fi = font("Bold", 30)
    ini = c["meno"][0].upper()
    d.text((p + av / 2, ay + av / 2), ini, font=fi, fill="white", anchor="mm")

    # meno + čas
    d.text((L["tx"], L["name_y"]), c["meno"], font=L["f_name"], fill=(20, 20, 24), anchor="lt")
    nw = L["f_name"].getlength(c["meno"])
    d.text((L["tx"] + nw + 12 * S, L["name_y"] + 2 * S), "· " + c["cas"], font=L["f_meta"],
           fill=(140, 140, 150), anchor="lt")

    # marker zvýraznenie (pod textom)
    base = L["f_body"].getmetrics()[0]
    for k, (i0, i1) in enumerate(L["hl"]):
        hp = ease_in_out(prog(t, hl_start(L, k), D_HL))
        if hp <= 0: continue
        # zoskupiť podľa riadkov
        segs = {}
        for b in L["boxes"][i0:i1]:
            segs.setdefault(b[4], []).append(b)
        total = sum(seg[-1][1] + seg[-1][3] - seg[0][1] for seg in segs.values())
        remaining = total * hp
        for li in sorted(segs):
            seg = segs[li]
            x0 = seg[0][1] - 6 * S
            full = seg[-1][1] + seg[-1][3] - seg[0][1]
            ln = min(full, remaining); remaining -= ln
            if ln <= 0: break
            y = seg[0][2]
            d.rounded_rectangle([x0, y + base - 20 * S, x0 + ln + 12 * S, y + base + 8 * S],
                                radius=8 * S, fill=MARKER + (255,))

    # slová – postupné objavenie
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt)
    for i, (wd, x, y, ww, li) in enumerate(L["boxes"]):
        wp = ease_out_cubic(prog(t, T_WORDS + i * WORD_STAGGER, D_WORD))
        if wp <= 0: continue
        dy = (1 - wp) * 14 * S
        td.text((x, y + base + dy), wd, font=L["f_body"], fill=(17, 17, 22, int(255 * wp)), anchor="ls")
    img = Image.alpha_composite(img, txt)
    d = ImageDraw.Draw(img)

    # akcie: srdce + počet, Odpovedať
    ay = L["act_y"] + 16 * S
    hx = L["tx"] + 14 * S
    hp = prog(t, heart_t(L), 0.55)
    liked = hp > 0
    sc = 1 + 0.45 * math.sin(math.pi * clamp(hp / 0.55)) if hp < 1 else 1.0
    hs = 26 * S * sc
    if liked:
        # rozstrek krúžku
        if hp < 0.7:
            rp = hp / 0.7
            r = 10 * S + rp * 30 * S
            d.ellipse([hx - r, ay - r, hx + r, ay + r], outline=HEART + (int(200 * (1 - rp)),),
                      width=max(1, int(4 * S * (1 - rp))))
            for j in range(8):
                a = j / 8 * 2 * math.pi
                rr = 18 * S + rp * 26 * S
                px, py = hx + math.cos(a) * rr, ay + math.sin(a) * rr
                s2 = 4 * S * (1 - rp)
                d.ellipse([px - s2, py - s2, px + s2, py + s2], fill=HEART + (int(255 * (1 - rp)),))
        draw_heart(d, hx, ay, hs, fill=HEART + (255,))
    else:
        draw_heart(d, hx, ay, hs, outline=(120, 120, 130, 255), width=int(2.6 * S))
    cnt = c["lajky"] + (1 if liked else 0)
    col = HEART if liked else (110, 110, 120)
    d.text((hx + 26 * S, ay), str(cnt), font=L["f_act"], fill=col + (255,), anchor="lm")
    d.text((hx + 26 * S + L["f_act"].getlength("999") + 36 * S, ay), "Odpovedať",
           font=L["f_act"], fill=(120, 120, 130, 255), anchor="lm")
    return img

def hl_start(L, k):
    t_end_words = T_WORDS + len(L["boxes"]) * WORD_STAGGER + D_WORD
    return t_end_words + 0.25 + k * (D_HL + 0.12)

def heart_t(L):
    return hl_start(L, len(L["hl"])) + 0.1

def render_badge(c):
    S = SS
    f = font("ExtraBold", 21)
    txt = c["stitok"]
    # rozostupy písmen
    sp = 1.6 * S
    tw = sum(f.getlength(ch) for ch in txt) + sp * (len(txt) - 1)
    ic = 28 * S
    w = int(18 * S + ic + 12 * S + tw + 22 * S)
    h = 50 * S
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=ACCENT + (255,))
    cx, cy = 18 * S + ic / 2, h / 2
    d.ellipse([cx - ic / 2, cy - ic / 2, cx + ic / 2, cy + ic / 2], fill=(255, 255, 255, 255))
    d.text((cx, cy + 1 * S), "?", font=font("Black", 19), fill=ACCENT + (255,), anchor="mm")
    x = 18 * S + ic + 12 * S
    for ch in txt:
        d.text((x, cy), ch, font=f, fill="white", anchor="lm")
        x += f.getlength(ch) + sp
    return img

def shadow_of(img, blur, alpha, spread=0):
    a = img.split()[3].point(lambda v: 255 if v > 0 else 0)
    pad = blur * 3
    m = Image.new("L", (img.width + pad * 2, img.height + pad * 2), 0)
    m.paste(a, (pad, pad))
    m = m.filter(ImageFilter.GaussianBlur(blur))
    sh = Image.new("RGBA", m.size, (0, 0, 0, 0))
    sh.putalpha(m.point(lambda v: int(v * alpha)))
    return sh, pad

def place(canvas, img, cx, cy, scale, opacity):
    """vloží img (v SS rozlíšení) so stredom v (cx,cy) v 1x súradniciach"""
    if scale <= 0.01 or opacity <= 0.003: return
    w = max(1, int(img.width * scale / SS)); h = max(1, int(img.height * scale / SS))
    im = img.resize((w, h), Image.LANCZOS)
    if opacity < 1:
        a = im.split()[3].point(lambda v: int(v * opacity))
        im.putalpha(a)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(im, (int(round(cx - w / 2)), int(round(cy - h / 2))))
    canvas.alpha_composite(layer)

# ---------------------------------------------------------------- ZVUKY
rng = np.random.default_rng(7)
def env_ad(n, a, d_):
    e = np.ones(n)
    ai = int(a * SR); di = n - ai
    e[:ai] = np.linspace(0, 1, ai) ** 2 if ai else 1
    e[ai:] = np.exp(-np.linspace(0, d_, di))
    return e

def bandsweep(noise, f0, f1):
    # jednoduchý rezonančný filter s posúvajúcou sa frekvenciou
    out = np.zeros_like(noise); y1 = y2 = 0.0
    n = len(noise)
    for i in range(n):
        f = f0 * (f1 / f0) ** (i / n)
        w = 2 * math.pi * f / SR; r = 0.985
        a1, a2 = -2 * r * math.cos(w), r * r
        y = noise[i] * (1 - r) - a1 * y1 - a2 * y2
        out[i] = y; y2, y1 = y1, y
    return out / (np.max(np.abs(out)) + 1e-9)

def whoosh(dur=0.45, f0=500, f1=3500, vol=0.5):
    n = int(dur * SR)
    x = bandsweep(rng.standard_normal(n), f0, f1)
    t = np.linspace(0, 1, n)
    e = np.sin(np.pi * t ** 0.7) ** 2
    return x * e * vol

def pop(f0=900, f1=180, dur=0.12, vol=0.7):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 45)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 38)
    click = rng.standard_normal(n) * np.exp(-t * 900) * 0.3
    return (s + click) * vol

def tick(vol=0.08):
    n = int(0.025 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2400 * t) * 0.5 + rng.standard_normal(n) * 0.5) * np.exp(-t * 260) * vol

def ding(vol=0.35):
    n = int(0.9 * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * 1318.5 * t) + 0.5 * np.sin(2 * np.pi * 1975.5 * t) +
         0.25 * np.sin(2 * np.pi * 2637 * t)) * np.exp(-t * 6)
    s[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    return s / 1.75 * vol

def marker(dur=0.36, vol=0.18):
    n = int(dur * SR); t = np.linspace(0, 1, n)
    x = bandsweep(rng.standard_normal(n), 2500, 5000)
    return x * np.sin(np.pi * t) ** 1.5 * vol

def build_audio(L):
    n = int(DLZKA * SR)
    L_ch = np.zeros(n); R_ch = np.zeros(n)
    def add(sig, at, pan=0.0):
        i = int(at * SR); j = min(n, i + len(sig))
        if i >= n: return
        l = math.cos((pan + 1) * math.pi / 4); r = math.sin((pan + 1) * math.pi / 4)
        L_ch[i:j] += sig[: j - i] * l * 1.414; R_ch[i:j] += sig[: j - i] * r * 1.414
    add(whoosh(0.5, 400, 3200, 0.45), T_IN - 0.0)
    add(pop(700, 160, 0.14, 0.75), T_IN + 0.28)
    add(pop(1400, 500, 0.09, 0.45), T_BADGE + 0.12, -0.3)
    for i, b in enumerate(L["boxes"]):
        add(tick(0.07 + 0.02 * rng.random()), T_WORDS + i * WORD_STAGGER, (b[1] / L["card_w"] - 0.5) * 0.8)
    for k in range(len(L["hl"])):
        add(marker(), hl_start(L, k), -0.2 + 0.4 * k)
    add(pop(1100, 300, 0.1, 0.55), heart_t(L))
    add(ding(0.3), heart_t(L) + 0.03)
    add(whoosh(0.5, 3200, 450, 0.4), T_OUT - 0.05)
    st = np.stack([L_ch, R_ch], 1)
    st = st / (np.max(np.abs(st)) + 1e-9) * 0.7  # cca -3 dB
    return (st * 32767).astype(np.int16)

def write_wav(path, data):
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())

# ---------------------------------------------------------------- RENDER
def render(c, outdir):
    L = layout(c)
    badge = render_badge(c)
    bsh, bpad = shadow_of(badge, 10 * SS, 0.30)
    # rozmery plátna
    card_h1 = L["card_h"] / SS
    margin_top, margin_bot = 70, 70
    H = int(math.ceil((card_h1 + margin_top + margin_bot) / 2) * 2)
    W = CANVAS_W
    ccx = W / 2
    ccy = margin_top + card_h1 / 2
    bx = (W - L["card_w"] / SS) / 2 + L["pad"] / SS + badge.width / SS / 2 - 4
    by = margin_top - 4

    frames = os.path.join(outdir, "_frames_" + c["nazov"])
    shutil.rmtree(frames, ignore_errors=True); os.makedirs(frames)
    nfr = int(DLZKA * FPS)
    still_t = heart_t(L) + 1.0
    still_saved = False
    for fi in range(nfr):
        t = fi / FPS
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # karta
        pin = prog(t, T_IN, D_IN)
        pout = ease_in_cubic(prog(t, T_OUT, D_OUT))
        s = 0.72 + 0.28 * ease_out_back(pin, 1.9) if pin < 1 else 1.0
        s *= 1 - 0.12 * pout
        op = ease_out_cubic(clamp(pin * 2.2)) * (1 - pout)
        float_y = math.sin(max(0, t - 1.2) * 1.6) * 2.0 if pin >= 1 else 0
        dy = (1 - ease_out_cubic(pin)) * 60 - pout * 40 + float_y
        card = render_card(c, L, t)
        sh, spad = shadow_of(card, 22 * SS, 0.28)
        place(canvas, sh, ccx, ccy + dy + 14 * s, s, op)
        place(canvas, card, ccx, ccy + dy, s, op)
        # štítok
        pb = prog(t, T_BADGE, D_BADGE)
        bs = (0.3 + 0.7 * ease_out_back(pb, 2.6)) if pb < 1 else 1.0
        bs *= 1 - 0.3 * pout
        bop = clamp(pb * 3) * (1 - clamp(pout * 1.4))
        brot_y = by + dy + (ccy - by) * (1 - s)  # drží sa karty pri zmenšovaní
        bxx = ccx + (bx - ccx) * s
        place(canvas, bsh, bxx, brot_y + 6, bs, bop)
        place(canvas, badge, bxx, brot_y, bs, bop)
        canvas.save(os.path.join(frames, f"f_{fi:04d}.png"))
        if not still_saved and t >= still_t:
            canvas.save(os.path.join(outdir, c["nazov"] + "_still.png")); still_saved = True

    wav = os.path.join(outdir, c["nazov"] + "_zvuk.wav")
    write_wav(wav, build_audio(L))
    mov = os.path.join(outdir, c["nazov"] + ".mov")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                    "-i", os.path.join(frames, "f_%04d.png"), "-i", wav,
                    "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
                    "-alpha_bits", "16", "-vendor", "apl0", "-qscale:v", "9",
                    "-c:a", "pcm_s16le", "-shortest", mov], check=True)
    prev = os.path.join(outdir, c["nazov"] + "_nahlad.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"gradients=s={W}x{H}:c0=0x2b2f36:c1=0x0f1114:x0=0:y0=0:x1={W}:y1={H}:d={DLZKA}:r={FPS}",
                    "-framerate", str(FPS), "-i", os.path.join(frames, "f_%04d.png"), "-i", wav,
                    "-filter_complex", "[0][1]overlay=format=auto,format=yuv420p[v]",
                    "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", prev], check=True)
    shutil.rmtree(frames)
    print("hotovo:", mov, f"({W}x{H}, {DLZKA}s)")

if __name__ == "__main__":
    out = os.path.dirname(os.path.abspath(__file__))
    for c in KOMENTARE:
        render(c, out)
