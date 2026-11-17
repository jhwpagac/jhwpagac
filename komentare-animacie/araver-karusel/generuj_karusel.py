#!/usr/bin/env python3
"""Araver – Instagram karusel 4:5 (1080x1350): úvod, 5 áut Škoda, záver. Výstup: slide_01.jpg … slide_07.jpg"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
FOTKY = os.path.join(os.path.dirname(HERE), "araver-auta", "fotky")
FONTY = os.path.join(os.path.dirname(HERE), "auto-vojto", "fonty")
W, H = 1080, 1350
RED, WHITE, BG, BG2, MUTED, CARD = (227, 6, 19), (255, 255, 255), (14, 14, 16), (28, 28, 32), (165, 165, 175), (24, 24, 28)
def pf(w, s): return ImageFont.truetype(os.path.join(FONTY, f"Poppins-{w}.ttf"), s)

AUTA = [
    ("Kamiq", "1_kamiq.png", "Mestské SUV",
     "Vyššie sedenie a kompaktné rozmery – ideálne do mesta aj na výlety.",
     ["Ľahké parkovanie v meste", "Vyššia pozícia za volantom", "Praktický kufor na každý deň"]),
    ("Karoq", "2_karoq.png", "Rodinné SUV",
     "Priestranné SUV pre celú rodinu, ktoré zvládne dovolenku aj dlhé cesty.",
     ["Veľký variabilný kufor", "Pohodlie na dlhé trasy", "Robustný SUV vzhľad"]),
    ("Scala", "3_scala.png", "Kompaktný hatchback",
     "Moderný hatchback s priestorom, aký by ste v tejto triede nečakali.",
     ["Priestranný interiér", "Úsporná prevádzka", "Moderný dizajn"]),
    ("Octavia", "4_octavia.png", "Bestseller Škody",
     "Najobľúbenejšia Škoda – univerzálne auto do práce, pre rodinu aj na cesty.",
     ["Obrovský kufor", "Komfort vyššej triedy", "Overená spoľahlivosť"]),
    ("Fabia", "5_fabia.png", "Šikovné malé auto",
     "Kompaktná, úsporná a prekvapivo priestranná – skvelá voľba do mesta.",
     ["Nízka spotreba", "Ľahko sa s ňou parkuje", "Ideálne prvé auto"]),
]

def bg():
    im = Image.new("RGB", (W, H), BG)
    g = Image.new("L", (W, H), 0); d = ImageDraw.Draw(g)
    d.ellipse([-300, -400, W + 300, 700], fill=90)
    g = g.filter(ImageFilter.GaussianBlur(160))
    im.paste(Image.new("RGB", (W, H), BG2), (0, 0), g)
    # jemný červený pruh hore
    ImageDraw.Draw(im).rectangle([0, 0, W, 10], fill=RED)
    return im

def rounded(im, r):
    m = Image.new("L", (im.width * 3, im.height * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, m.width - 1, m.height - 1], radius=r * 3, fill=255)
    out = im.convert("RGBA"); out.putalpha(m.resize(im.size, Image.LANCZOS)); return out

def photo(name, w, h):
    src = Image.open(os.path.join(FOTKY, name)).convert("RGB")
    r = max(w / src.width, h / src.height)
    im = src.resize((int(src.width * r + 1), int(src.height * r + 1)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h)).filter(ImageFilter.UnsharpMask(2, 70, 2))

def framed(canvas, ph, x, y, r=28, border=8):
    fw, fh = ph.width + 2 * border, ph.height + 2 * border
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).rounded_rectangle([x, y + 18, x + fw, y + fh + 18], radius=r + border, fill=200)
    canvas.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(26)))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([x - 5, y - 5, x + fw + 5, y + fh + 5], radius=r + border + 5, fill=RED)
    d.rounded_rectangle([x, y, x + fw, y + fh], radius=r + border, fill=WHITE)
    canvas.paste(rounded(ph, r), (x + border, y + border), rounded(ph, r))

def header(d, idx=None):
    d.text((70, 86), "ARAVER", font=pf("ExtraBold", 34), fill=WHITE, anchor="lm")
    d.text((70 + pf("ExtraBold", 34).getlength("ARAVER") + 14, 88), "× ŠKODA", font=pf("Medium", 26), fill=MUTED, anchor="lm")
    if idx:
        t = f"{idx:02d} / 05"; f = pf("SemiBold", 26)
        tw = f.getlength(t)
        d.rounded_rectangle([W - 70 - tw - 36, 62, W - 70, 112], radius=25, outline=(80, 80, 88), width=2)
        d.text((W - 70 - tw / 2 - 18, 88), t, font=f, fill=WHITE, anchor="mm")

def footer(d, text="Posuň ďalej"):
    f = pf("SemiBold", 26)
    tw = f.getlength(text)
    x = W - 70 - 56 - 18 - tw
    d.text((x, H - 92), text, font=f, fill=WHITE, anchor="lm")
    cx, cy = W - 70 - 28, H - 92
    d.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=RED)
    d.line([(cx - 11, cy), (cx + 10, cy)], fill=WHITE, width=4)
    d.line([(cx + 2, cy - 9), (cx + 11, cy), (cx + 2, cy + 9)], fill=WHITE, width=4, joint="curve")

def wrap(text, font, width):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if font.getlength(t) <= width or not cur: cur = t
        else: out.append(cur); cur = w
    return out + [cur]

def check(d, x, y):
    d.ellipse([x - 20, y - 20, x + 20, y + 20], fill=RED)
    d.line([(x - 9, y + 1), (x - 2, y + 8), (x + 10, y - 7)], fill=WHITE, width=5, joint="curve")

def slide_cover():
    im = bg(); d = ImageDraw.Draw(im); header(d)
    d.text((70, 230), "5 ŠKODOVIEK", font=pf("ExtraBold", 92), fill=WHITE, anchor="ls")
    d.text((70, 336), "ktoré u nás", font=pf("Bold", 76), fill=WHITE, anchor="ls")
    d.text((70, 432), "nájdeš", font=pf("Bold", 76), fill=RED, anchor="ls")
    d.text((70, 500), "Pre mesto, rodinu aj dlhé cesty – ktorá je tvoja?", font=pf("Regular", 30), fill=MUTED, anchor="ls")
    # koláž 5 áut
    tiles = [(70, 580, 460, 290), (550, 580, 460, 290), (70, 890, 300, 200), (390, 890, 300, 200), (710, 890, 300, 200)]
    for (nm, f, *_), (x, y, w, h) in zip(AUTA, tiles):
        ph = rounded(photo(f, w, h), 20)
        im.paste(ph, (x, y), ph)
        lf = pf("Bold", 24 if w < 400 else 28); tw = lf.getlength(nm)
        d.rounded_rectangle([x + 14, y + h - 54, x + 14 + tw + 32, y + h - 14], radius=20, fill=RED)
        d.text((x + 30, y + h - 34), nm, font=lf, fill=WHITE, anchor="lm")
    footer(d)
    return im

def slide_car(i, nm, f, kat, popis, body):
    im = bg(); d = ImageDraw.Draw(im); header(d, i + 1)
    d.text((70, 168), kat.upper(), font=pf("SemiBold", 28), fill=RED, anchor="lm")
    d.text((66, 268), "Škoda " + nm, font=pf("ExtraBold", 88), fill=WHITE, anchor="ls")
    framed(im, photo(f, 924, 520), 70, 318)
    d = ImageDraw.Draw(im)
    y = 912
    for ln in wrap(popis, pf("Regular", 32), W - 140):
        d.text((70, y), ln, font=pf("Regular", 32), fill=(225, 225, 230), anchor="lm"); y += 46
    y += 26
    for b in body:
        check(d, 92, y); d.text((132, y), b, font=pf("SemiBold", 32), fill=WHITE, anchor="lm"); y += 62
    footer(d) if i < 4 else footer(d, "Ešte jeden slide")
    return im

def slide_cta():
    im = bg(); d = ImageDraw.Draw(im); header(d)
    d.text((70, 420), "Ktorá je", font=pf("ExtraBold", 110), fill=WHITE, anchor="ls")
    d.text((70, 545), "tvoja?", font=pf("ExtraBold", 110), fill=RED, anchor="ls")
    y = 640
    for ln in wrap("Napíš nám do komentára, ktorý model sa ti páči najviac – alebo sa zastav a vyskúšaj ho naživo.", pf("Regular", 36), W - 140):
        d.text((70, y), ln, font=pf("Regular", 36), fill=(225, 225, 230), anchor="lm"); y += 54
    # pásik s miniatúrami
    x = 70; tw = (W - 140 - 4 * 16) // 5
    for nm, f, *_ in AUTA:
        ph = rounded(photo(f, tw, int(tw * 0.75)), 14); im.paste(ph, (x, 900), ph); x += tw + 16
    d.rounded_rectangle([70, 1110, 70 + 500, 1196], radius=43, fill=RED)
    d.text((70 + 250, 1153), "Testovacia jazda", font=pf("Bold", 36), fill=WHITE, anchor="mm")
    d.text((610, 1153), "araver.sk", font=pf("SemiBold", 34), fill=WHITE, anchor="lm")
    return im

if __name__ == "__main__":
    slides = [slide_cover()] + [slide_car(i, *a) for i, a in enumerate(AUTA)] + [slide_cta()]
    for k, s in enumerate(slides, 1):
        s.save(os.path.join(HERE, f"slide_{k:02d}.jpg"), quality=94, subsampling=0)
    print(len(slides), "slidov")
