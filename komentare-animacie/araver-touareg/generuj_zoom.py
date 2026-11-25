#!/usr/bin/env python3
"""
Zoom z vesmíru: Zem -> Slovensko -> ARAVER Piešťany -> záblesk -> video (9:16).
Použitie: python3 generuj_zoom.py <video.MOV> <výstup.mp4>
"""
import os, sys, math, json, shutil, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "auto-vojto"))
from generuj_auto_vojto import clamp, prog, ease_in_out, ease_out_cubic, ease_out_back, ease_in_cubic, write_wav, mix, add, finish, whoosh, pop, thump, SR
def pf(w, s): return ImageFont.truetype(os.path.join(ROOT, "auto-vojto", "fonty", f"Poppins-{w}.ttf"), s)

VIDEO, OUT = sys.argv[1], sys.argv[2]
W, H, S, FPS = 1080, 1920, 2, 30
INTRO = 4.0
CIEL = (17.8272, 48.5948)           # Piešťany
SK_STRED = (19.45, 48.72)
RED, WHITE = (227, 6, 19), (255, 255, 255)
OCEAN, LAND, BORDER = (8, 22, 44), (26, 40, 60), (70, 96, 130)
rng = np.random.default_rng(4)

data = json.load(open(os.path.join(HERE, "staty.json")))
ISO = [d[0] for d in data]
RINGS = [np.radians(np.array(d[1], float)) for d in data]
STARS = [(rng.uniform(0, W * S), rng.uniform(0, H * S), rng.uniform(0.6, 2.4) * S, rng.uniform(80, 255)) for _ in range(700)]

def kamera(t):
    R0, R1 = 440.0, 70000.0
    if t < 0.9:
        u = t / 0.9
        return -25 + 22 * u, 22 + 8 * u, R0
    if t < 3.6:
        u = (t - 0.9) / 2.7
        e = ease_in_out(u); ep = 1 - (1 - min(1, u * 1.25)) ** 3
        lon = -3 + (CIEL[0] - -3) * ep; lat = 30 + (CIEL[1] - 30) * ep
        return lon, lat, math.exp(math.log(R0) + (math.log(R1) - math.log(R0)) * e)
    u = (t - 3.6) / 0.4
    return CIEL[0], CIEL[1], R1 * math.exp(3.2 * u * u)

def proj(lonlat_rad, lon0, lat0, R):
    lam, phi = lonlat_rad[:, 0], lonlat_rad[:, 1]
    l0, p0 = math.radians(lon0), math.radians(lat0)
    cosc = math.sin(p0) * np.sin(phi) + math.cos(p0) * np.cos(phi) * np.cos(lam - l0)
    x = np.cos(phi) * np.sin(lam - l0)
    y = math.cos(p0) * np.sin(phi) - math.sin(p0) * np.cos(phi) * np.cos(lam - l0)
    vis = cosc > 0
    n = np.sqrt(x * x + y * y) + 1e-12
    x = np.where(vis, x, x / n); y = np.where(vis, y, y / n)     # skryté body na horizont
    X = W * S / 2 + x * R * S; Y = H * S * 0.46 - y * R * S
    return np.clip(X, -2e5, 2e5), np.clip(Y, -2e5, 2e5), vis

GLOW = None
def glow_sprite():
    g = Image.new("L", (1000, 1000), 0); d = ImageDraw.Draw(g)
    d.ellipse([60, 60, 940, 940], fill=255)
    g = g.filter(ImageFilter.GaussianBlur(40))
    inner = Image.new("L", (1000, 1000), 0); ImageDraw.Draw(inner).ellipse([100, 100, 900, 900], fill=255)
    g = ImageChops.subtract(g, inner.filter(ImageFilter.GaussianBlur(4)))
    yy, xx = np.mgrid[0:1000, 0:1000]; rr = np.hypot(xx - 500, yy - 500) / 500
    fall = np.clip((1 - rr) / 0.08, 0, 1)                      # na okraji sprite presne nula
    g = Image.fromarray((np.asarray(g).astype(np.float32) * fall).astype(np.uint8))
    col = Image.new("RGBA", (1000, 1000), (90, 160, 255, 0)); col.putalpha(g)
    return col

def frame(t):
    lon0, lat0, R = kamera(t)
    big = Image.new("RGB", (W * S, H * S), (2, 3, 8))
    d = ImageDraw.Draw(big)
    zoom01 = clamp((math.log(R) - math.log(440)) / (math.log(6000) - math.log(440)))
    # hviezdy
    for x, y, r, a in STARS:
        a = int(a * (1 - zoom01))
        if a > 5: d.ellipse([x - r, y - r, x + r, y + r], fill=(a, a, a))
    cx, cy = W * S / 2, H * S * 0.46
    # atmosféra
    global GLOW
    if R < 3000:
        if GLOW is None: GLOW = glow_sprite()
        sz = int(R * S * 2 * 1000 / 800)
        gimg = GLOW.resize((sz, sz), Image.BILINEAR)
        a = np.asarray(gimg.split()[3]).astype(np.float32)[..., None] / 255
        rgb = (np.asarray(gimg.convert("RGB")).astype(np.float32) * a).astype(np.uint8)
        layer = Image.new("RGB", big.size, (0, 0, 0)); layer.paste(Image.fromarray(rgb), (int(cx - sz / 2), int(cy - sz / 2)))
        big = ImageChops.add(big, layer); d = ImageDraw.Draw(big)   # aditívna žiara – hviezdy ostanú
    d.ellipse([cx - R * S, cy - R * S, cx + R * S, cy + R * S], fill=OCEAN)
    # sieť poludníkov/rovnobežiek
    ga = int(70 * (1 - zoom01))
    if ga > 4:
        for lo in range(-180, 180, 15):
            pts = np.radians(np.array([[lo, la] for la in range(-90, 91, 3)], float))
            X, Y, v = proj(pts, lon0, lat0, R)
            seg = [(X[i], Y[i]) for i in range(len(X)) if v[i]]
            if len(seg) > 1: d.line(seg, fill=(30 + ga // 3, 60 + ga // 2, 100 + ga // 2), width=S)
        for la in range(-75, 90, 15):
            pts = np.radians(np.array([[lo, la] for lo in range(-180, 181, 3)], float))
            X, Y, v = proj(pts, lon0, lat0, R)
            seg = [(X[i], Y[i]) for i in range(len(X)) if v[i]]
            if len(seg) > 1: d.line(seg, fill=(30 + ga // 3, 60 + ga // 2, 100 + ga // 2), width=S)
    # pevnina
    sk_polys = []
    bw = max(1, int((1.2 + 1.5 * zoom01) * S))
    for iso, ring in zip(ISO, RINGS):
        X, Y, v = proj(ring, lon0, lat0, R)
        if not v.any(): continue
        if X.max() < 0 or X.min() > W * S or Y.max() < 0 or Y.min() > H * S: continue
        pts = list(zip(X, Y))
        if iso == "SVK": sk_polys.append(pts); continue
        d.polygon(pts, fill=LAND, outline=BORDER)
        if bw > 1: d.line(pts + [pts[0]], fill=BORDER, width=bw)
    # Slovensko – zvýraznenie
    hl = clamp((math.log(R) - math.log(1500)) / (math.log(9000) - math.log(1500)))
    for pts in sk_polys:
        col = tuple(int(LAND[k] + (RED[k] * 0.55 - LAND[k]) * hl) for k in range(3))
        d.polygon(pts, fill=col)
        if hl > 0:
            gl = Image.new("L", big.size, 0); ImageDraw.Draw(gl).line(pts + [pts[0]], fill=255, width=int((6 + 10 * hl) * S))
            gl = gl.filter(ImageFilter.GaussianBlur(10 * S)).point(lambda v: int(v * 0.8 * hl))
            big.paste(Image.new("RGB", big.size, RED), (0, 0), gl)
            d = ImageDraw.Draw(big)
        d.line(pts + [pts[0]], fill=tuple(int(BORDER[k] + (255 - BORDER[k]) * hl) for k in range(3)), width=int((1.5 + 3 * hl) * S))
    # nápis SLOVENSKO
    la = clamp((R - 4000) / 4000) * (1 - clamp((R - 30000) / 15000))
    if la > 0.02:
        X, Y, _ = proj(np.radians(np.array([SK_STRED], float)), lon0, lat0, R)
        f = pf("ExtraBold", int(64 * S))
        tl = Image.new("RGBA", big.size, (0, 0, 0, 0))
        ImageDraw.Draw(tl).text((X[0], Y[0]), "SLOVENSKO", font=f, fill=(255, 255, 255, int(255 * la)), anchor="mm")
        big.paste(tl, (0, 0), tl); d = ImageDraw.Draw(big)
    # pin Piešťany
    pp = prog(t, 2.75, 0.45)
    if pp > 0:
        X, Y, _ = proj(np.radians(np.array([CIEL], float)), lon0, lat0, R)
        x, y = X[0], Y[0]
        q = (t - 3.05) % 1.0 if t > 3.05 else -1
        if q >= 0:
            rr = (20 + 120 * q) * S
            d.ellipse([x - rr, y - rr * 0.5, x + rr, y + rr * 0.5], outline=RED, width=int(4 * S))
        drop = (1 - ease_out_back(pp, 2.2)) * 160 * S; r = 34 * S; yy = y - drop
        d.polygon([(x - r * 0.72, yy - r * 1.25), (x + r * 0.72, yy - r * 1.25), (x, yy)], fill=RED)
        d.ellipse([x - r, yy - r * 2.6, x + r, yy - r * 0.6], fill=RED, outline=WHITE, width=int(5 * S))
        d.ellipse([x - r * 0.4, yy - r * 2.0, x + r * 0.4, yy - r * 1.2], fill=WHITE)
        pl = prog(t, 3.0, 0.35)
        if pl > 0:
            f1, f2 = pf("ExtraBold", int(46 * S)), pf("Medium", int(32 * S))
            tw = max(f1.getlength("ARAVER"), f2.getlength("Piešťany")) + 64 * S
            th = 130 * S; e = ease_out_back(pl, 2.0)
            lab = Image.new("RGBA", (int(tw), int(th)), (0, 0, 0, 0)); ld = ImageDraw.Draw(lab)
            ld.rounded_rectangle([0, 0, tw - 1, th - 1], radius=28 * S, fill=RED + (255,), outline=WHITE + (255,), width=int(4 * S))
            ld.text((32 * S, 44 * S), "ARAVER", font=f1, fill=WHITE, anchor="lm")
            ld.text((32 * S, 94 * S), "Piešťany", font=f2, fill=(255, 225, 225), anchor="lm")
            lw, lh = max(1, int(tw * e)), max(1, int(th * e))
            lab = lab.resize((lw, lh), Image.BICUBIC)
            big.paste(lab, (int(x - lw / 2), int(y - 2.6 * r - 40 * S - lh)), lab)
    img = big.resize((W, H), Image.LANCZOS)
    # radiálne rozmazanie pri záverečnom zoome
    zb = prog(t, 3.6, 0.4)
    if zb > 0:
        acc = np.asarray(img).astype(np.float32); n = 1
        for k in range(1, 6):
            s = 1 + 0.04 * k * zb
            w2, h2 = int(W * s), int(H * s)
            z = img.resize((w2, h2), Image.BILINEAR).crop(((w2 - W) // 2, int(h2 * 0.46 - H * 0.46), (w2 - W) // 2 + W, int(h2 * 0.46 - H * 0.46) + H))
            acc += np.asarray(z).astype(np.float32); n += 1
        img = Image.fromarray((acc / n).astype(np.uint8))
        img = Image.blend(img, Image.new("RGB", (W, H), WHITE), ease_in_cubic(zb) * 0.95)
    return img

def main():
    tmp = os.path.join(HERE, "_frames"); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    vid = os.path.join(tmp, "v"); os.makedirs(vid)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", VIDEO, "-vf", "scale=1080:1920", os.path.join(vid, "v_%04d.png")], check=True)
    nv = len(os.listdir(vid))
    ni = int(INTRO * FPS)
    for i in range(ni):
        frame(i / FPS).save(os.path.join(tmp, f"f_{i:04d}.png"))
    # video – úvodné snímky: biely záblesk mizne a obraz sa jemne „dotiahne“ z priblíženia
    for j in range(nv):
        im = Image.open(os.path.join(vid, f"v_{j + 1:04d}.png")).convert("RGB")
        u = clamp(j / 18)
        if u < 1:
            s = 1.25 - 0.25 * ease_out_cubic(u)
            w2, h2 = int(W * s), int(H * s)
            im = im.resize((w2, h2), Image.BILINEAR).crop(((w2 - W) // 2, (h2 - H) // 2, (w2 - W) // 2 + W, (h2 - H) // 2 + H))
            im = Image.blend(im, Image.new("RGB", (W, H), WHITE), 0.95 * (1 - ease_out_cubic(u)))
        im.save(os.path.join(tmp, f"f_{ni + j:04d}.png"))
    # zvuk úvodu
    n = int(INTRO * SR) + SR; buf = mix(n)
    m = int(3.6 * SR); tt = np.arange(m) / SR
    rumble = np.convolve(rng.standard_normal(m), np.ones(60) / 60, mode="same") * (tt / 3.6) ** 1.5
    add(buf, rumble * 3.0, 0.0)
    add(buf, whoosh(1.4, 200, 1800, 0.35), 0.9)
    add(buf, whoosh(1.2, 400, 3000, 0.4), 2.2)
    add(buf, pop(800, 200, 0.14, 0.7), 3.08)
    add(buf, whoosh(0.6, 500, 6000, 0.7), 3.5)
    add(buf, thump(1.0), INTRO - 0.02)
    wav = os.path.join(tmp, "intro.wav"); write_wav(wav, finish(buf, 0.8))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "f_%04d.png"),
                    "-i", wav, "-i", VIDEO, "-filter_complex",
                    f"[2:a]adelay={int(INTRO*1000)}|{int(INTRO*1000)}[va];[1:a][va]amix=inputs=2:duration=longest:normalize=0[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-crf", "20", "-preset", "slow", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT], check=True)
    shutil.rmtree(tmp); print("hotovo", OUT)

if __name__ == "__main__":
    main()
