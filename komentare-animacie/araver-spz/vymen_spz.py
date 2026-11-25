#!/usr/bin/env python3
"""
Výmena ŠPZ za čiernu tabuľku ARAVER vo videu (sledovanie pohybu + perspektíva).
Použitie: python3 vymen_spz.py <vstup.mov> <priečinok_so_snímkami> <výstup.mp4>
Snímky: ffmpeg -i vstup.mov <priečinok>/f_%04d.png  (číslovanie od 1)
"""
import sys, os, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter

VSTUP, FR, VYSTUP = sys.argv[1], sys.argv[2], sys.argv[3]
HERE = os.path.dirname(os.path.abspath(__file__))
# záber: (názov, prvá snímka, posledná snímka, kotviaca snímka, rohy ŠPZ TL, TR, BR, BL, biela ŠPZ = dohľadať v každej snímke)
ZABERY = [
    ("VW",    76, 155, 80,  [(571, 630), (649, 629), (649, 657), (571, 658)], True),
    ("cervene", 156, 255, 160, [(410, 630), (579, 631), (579, 672), (410, 670)], True),
    ("Cupra", 368, 413, 400, [(642, 641), (848, 641), (848, 689), (642, 689)], False),
]

def nacitaj(i): return cv2.imread(os.path.join(FR, f"f_{i:04d}.png"))

# ---------- čierna tabuľka ARAVER (logo vyrezané z koncovej karty videa) ----------
def tabulka():
    PW, PH = 1040, 220
    logo = Image.open(os.path.join(HERE, "araver_logo_cervene.png")).convert("RGB")
    a = np.asarray(logo).astype(float)
    m = np.clip((a[..., 1] - 90) / (225 - 90), 0, 1)          # biela časť loga
    m = Image.fromarray((m * 255).astype(np.uint8))
    bb = m.getbbox(); m = m.crop(bb)
    w = int(PW * 0.78); h = int(m.height * w / m.width)
    if h > PH * 0.62: h = int(PH * 0.62); w = int(m.width * h / m.height)
    m = m.resize((w, h), Image.LANCZOS)
    plate = Image.new("RGB", (PW, PH), (18, 18, 20))
    d = ImageDraw.Draw(plate)
    # jemný lesk
    for y in range(PH):
        k = 1 - y / PH
        d.line([(0, y), (PW, y)], fill=(int(18 + 16 * k), int(18 + 16 * k), int(21 + 16 * k)))
    d.rounded_rectangle([14, 14, PW - 15, PH - 15], radius=22, outline=(200, 200, 205), width=6)
    plate.paste(Image.new("RGB", m.size, (235, 235, 238)), ((PW - w) // 2, (PH - h) // 2 + 4), m)
    alpha = Image.new("L", (PW, PH), 0)
    ImageDraw.Draw(alpha).rounded_rectangle([0, 0, PW - 1, PH - 1], radius=26, fill=255)
    return np.asarray(plate)[..., ::-1].copy(), np.asarray(alpha).copy()

PLATE, PALPHA = tabulka()
cv2.imwrite(os.path.join(HERE, "araver_tabulka.png"), np.dstack([PLATE, PALPHA]))

# ---------- sledovanie rohov ----------
def region_mask(shape, quad):
    q = np.array(quad, np.float32)
    w = np.linalg.norm(q[1] - q[0]); h = np.linalg.norm(q[3] - q[0])
    c = q.mean(0)
    x0, x1 = c[0] - w * 1.6, c[0] + w * 1.6
    y0, y1 = c[1] - h * 3.5, c[1] + h * 1.8
    m = np.zeros(shape[:2], np.uint8)
    m[int(max(0, y0)):int(min(shape[0], y1)), int(max(0, x0)):int(min(shape[1], x1))] = 255
    return m

def krok(g0, g1, quad):
    m = region_mask(g0.shape, quad)
    p0 = cv2.goodFeaturesToTrack(g0, 300, 0.005, 4, mask=m)
    if p0 is None or len(p0) < 8: return quad
    p1, st, _ = cv2.calcOpticalFlowPyrLK(g0, g1, p0, None, winSize=(25, 25), maxLevel=4)
    pb, st2, _ = cv2.calcOpticalFlowPyrLK(g1, g0, p1, None, winSize=(25, 25), maxLevel=4)
    ok = (st.ravel() == 1) & (st2.ravel() == 1) & (np.linalg.norm(p0 - pb, axis=2).ravel() < 1.0)
    a, b = p0[ok], p1[ok]
    if len(a) < 8: return quad
    Hm, inl = cv2.findHomography(a, b, cv2.RANSAC, 2.0)
    if Hm is None or inl.sum() < 8:
        A, _ = cv2.estimateAffinePartial2D(a, b)
        if A is None: return quad
        Hm = np.vstack([A, [0, 0, 1]])
    q = cv2.perspectiveTransform(np.array([quad], np.float32), Hm)[0]
    return [tuple(map(float, p)) for p in q]

def order(pts):
    pts = np.array(pts, np.float32); s = pts.sum(1); d = np.diff(pts, axis=1).ravel()
    return [tuple(pts[np.argmin(s)]), tuple(pts[np.argmin(d)]), tuple(pts[np.argmax(s)]), tuple(pts[np.argmax(d)])]

def dohladaj(g, quad):
    """Nájde biely obdĺžnik pôvodnej ŠPZ v okolí predpovedanej polohy."""
    q = np.array(quad, np.float32); c = q.mean(0)
    w = np.linalg.norm(q[1] - q[0]); h = np.linalg.norm(q[3] - q[0])
    x0, x1 = int(max(0, c[0] - w)), int(min(g.shape[1], c[0] + w))
    y0, y1 = int(max(0, c[1] - h * 1.4)), int(min(g.shape[0], c[1] + h * 1.4))
    win = g[y0:y1, x0:x1]
    if win.size < 50: return quad
    t, bw = cv2.threshold(cv2.GaussianBlur(win, (3, 3), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area0 = cv2.contourArea(q); best = None; bd = 1e9
    for cn in cnts:
        a = cv2.contourArea(cn)
        if a < area0 * 0.45 or a > area0 * 1.8: continue
        M = cv2.moments(cn); cc = np.array([M["m10"] / M["m00"] + x0, M["m01"] / M["m00"] + y0])
        dd = np.linalg.norm(cc - c)
        if dd < bd and dd < w * 0.5: bd, best = dd, cn
    if best is None: return quad
    box = cv2.boxPoints(cv2.minAreaRect(best)) + np.array([x0, y0], np.float32)
    return order(box)

def sleduj(prvy, posledny, kotva, rohy, biela):
    quads = {kotva: rohy}
    gray = {i: cv2.cvtColor(nacitaj(i), cv2.COLOR_BGR2GRAY) for i in range(prvy, posledny + 1)}
    ref = (lambda i, q: dohladaj(gray[i], q)) if biela else (lambda i, q: q)
    for i in range(kotva, posledny):
        quads[i + 1] = ref(i + 1, krok(gray[i], gray[i + 1], quads[i]))
    for i in range(kotva, prvy, -1):
        quads[i - 1] = ref(i - 1, krok(gray[i], gray[i - 1], quads[i]))
    # vyhladenie chvenia (kĺzavý priemer po 5 snímkach)
    ks = sorted(quads); arr = np.array([quads[k] for k in ks])
    sm = arr.copy()
    for j in range(len(ks)):
        lo, hi = max(0, j - 2), min(len(ks), j + 3)
        sm[j] = arr[lo:hi].mean(0)
    return {k: sm[j] for j, k in enumerate(ks)}

# ---------- vloženie tabuľky ----------
def vloz(img, quad):
    q = np.array(quad, np.float32)
    # trochu zväčšiť, aby úplne prekryla pôvodnú ŠPZ
    left = (q[0] - q[1]) * 0.07
    q[0] += left; q[3] += left                     # prekryť aj modrý EU pásik vľavo
    c = q.mean(0); q = c + (q - c) * np.array([1.10, 1.22], np.float32)
    ph, pw = PLATE.shape[:2]
    src = np.array([[0, 0], [pw, 0], [pw, ph], [0, ph]], np.float32)
    Hm = cv2.getPerspectiveTransform(src, q)
    W, H = img.shape[1], img.shape[0]
    warped = cv2.warpPerspective(PLATE, Hm, (W, H), flags=cv2.INTER_AREA)
    alpha = cv2.warpPerspective(PALPHA, Hm, (W, H), flags=cv2.INTER_LINEAR).astype(np.float32) / 255
    # osvetlenie podľa pôvodnej (bielej/oranžovej) ŠPZ
    mask = np.zeros((H, W), np.uint8); cv2.fillConvexPoly(mask, np.array(quad, np.int32), 255)
    lum = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[mask > 0]
    gain = np.clip(np.percentile(lum, 90) / 215.0, 0.02, 1.05) if lum.size > 20 else 0.8
    warped = warped.astype(np.float32) * gain
    # zmäkčenie podľa veľkosti, aby sedela s ostrosťou videa
    wpx = np.linalg.norm(q[1] - q[0])
    s = 0.9 if wpx < 140 else 0.6
    warped = cv2.GaussianBlur(warped, (0, 0), s); alpha = cv2.GaussianBlur(alpha, (0, 0), 0.8)
    out = img.astype(np.float32) * (1 - alpha[..., None]) + warped * alpha[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    vsetky = {}
    for nm, a, b, k, rohy, biela in ZABERY:
        vsetky.update(sleduj(a, b, k, rohy, biela)); print("sledovanie hotové:", nm)
    n = len([f for f in os.listdir(FR) if f.startswith("f_")])
    out_dir = FR.rstrip("/") + "_out"; os.makedirs(out_dir, exist_ok=True)
    for i in range(1, n + 1):
        img = nacitaj(i)
        if i in vsetky: img = vloz(img, vsetky[i])
        cv2.imwrite(os.path.join(out_dir, f"f_{i:04d}.png"), img)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-i", os.path.join(out_dir, "f_%04d.png"),
                    "-i", VSTUP, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "17", "-preset", "slow",
                    "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "-movflags", "+faststart", VYSTUP], check=True)
    print("hotovo", VYSTUP)
