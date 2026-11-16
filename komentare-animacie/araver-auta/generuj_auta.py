#!/usr/bin/env python3
"""
Araver – 5 áut Škoda vyskakuje do rámu podľa toho, ako ich moderátorka menuje.
Formát Reels 9:16 (1080x1920), bez pozadia, so zvukom. Rám je v hornej polovici,
aby neprekrýval titulky.
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "auto-vojto"))
import generuj_auto_vojto as av
from generuj_auto_vojto import (clamp, prog, ease_out_cubic, ease_in_cubic, ease_out_back,
                                write_wav, mix, add, finish, opacity, whoosh, pop, new_frames, SR, FPS)
from PIL import ImageFont
def pf(w, size):
    return ImageFont.truetype(os.path.join(os.path.dirname(HERE), "auto-vojto", "fonty", f"Poppins-{w}.ttf"), int(size))

# poradie a čas, kedy moderátorka auto vysloví (sekundy od začiatku klipu)
AUTA = [("Kamiq", "fotky/1_kamiq.png", 1.5), ("Karoq", "fotky/2_karoq.png", 2.5),
        ("Scala", "fotky/3_scala.png", 3.5), ("Octavia", "fotky/4_octavia.png", 4.5),
        ("Fabia", "fotky/5_fabia.png", 5.5)]
RED, WHITE, DARK = (227, 6, 19), (255, 255, 255), (16, 16, 18)
NAME = "araver_auta_reels"
W, H = 1080, 1920
PW, PH = 940, 529          # plocha fotky 16:9
BORDER = 12
CY = 700                   # stred rámu (horná polovica, mimo titulkov)
T_FRAME, T_OUT, DUR = 1.15, 6.6, 7.2

def rounded_mask(w, h, r):
    m = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius=r * 4, fill=255)
    return m.resize((w, h), Image.LANCZOS)

def cover(img, w, h):
    r = max(w / img.width, h / img.height)
    im = img.resize((int(img.width * r + 1), int(img.height * r + 1)), Image.LANCZOS)
    x = (im.width - w) // 2; y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))

def main():
    photos = []
    for nm, p, t in AUTA:
        src = Image.open(os.path.join(HERE, p)).convert("RGB")
        im = cover(src, int(PW * 1.25), int(PH * 1.25)).filter(ImageFilter.UnsharpMask(2, 60, 2))
        photos.append(im)
    FW, FH = PW + 2 * BORDER, PH + 2 * BORDER
    inner_mask = rounded_mask(PW, PH, 22)
    frame_mask = rounded_mask(FW, FH, 32)
    # rám: biely okraj + červený vonkajší obrys + tieň
    frame = Image.new("RGBA", (FW + 120, FH + 120), (0, 0, 0, 0))
    fr = Image.new("RGBA", (FW, FH), WHITE + (255,)); fr.putalpha(frame_mask)
    sh = Image.new("L", frame.size, 0); sh.paste(frame_mask, (60, 72))
    sh = sh.filter(ImageFilter.GaussianBlur(24)).point(lambda v: int(v * 0.55))
    shl = Image.new("RGBA", frame.size, (0, 0, 0, 0)); shl.putalpha(sh); frame.alpha_composite(shl)
    red = Image.new("L", frame.size, 0)
    ImageDraw.Draw(red).rounded_rectangle([60 - 7, 60 - 7, 60 + FW + 6, 60 + FH + 6], radius=38, fill=255)
    rl = Image.new("RGBA", frame.size, RED + (0,)); rl.putalpha(red); frame.alpha_composite(rl)
    frame.alpha_composite(fr, (60, 60))
    dark = Image.new("RGBA", (PW, PH), DARK + (255,)); dark.putalpha(inner_mask)
    frame.alpha_composite(dark, (60 + BORDER, 60 + BORDER))
    f_brand, f_model = pf("SemiBold", 34), pf("ExtraBold", 58)

    frames = new_frames(NAME)
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pin = prog(t, T_FRAME, 0.4); pout = ease_in_cubic(prog(t, T_OUT, 0.5))
        if pin <= 0:
            canvas.save(os.path.join(frames, f"f_{fi:04d}.png")); continue
        # ktoré auto je práve aktívne
        cur = -1
        for i, (_, _, ts) in enumerate(AUTA):
            if t >= ts: cur = i
        bump = 0
        if cur >= 0:
            pb = prog(t, AUTA[cur][2], 0.3)
            bump = 0.035 * math.sin(math.pi * pb) if pb < 1 else 0
        comp = frame.copy()
        # fotky – nová vyskočí cez predošlú
        inner = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
        for i in range(max(0, cur - 1), cur + 1):
            if i < 0: continue
            p = prog(t, AUTA[i][2], 0.42)
            if i < cur and prog(t, AUTA[cur][2], 0.42) >= 1: continue
            e = ease_out_back(p, 1.6) if p < 1 else 1
            sc = 1.25 - 0.25 * e          # priblíženie 125 % -> 100 %
            ph = photos[i]
            w, h = int(PW * sc), int(PH * sc)
            im = ph.resize((w, h), Image.BILINEAR).convert("RGBA")
            dx = int((1 - ease_out_cubic(p)) * PW * 0.35) if i == cur and cur > 0 else 0
            layer = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
            layer.paste(im, ((PW - w) // 2 + dx, (PH - h) // 2))
            inner.alpha_composite(opacity(layer, clamp(p * 3)))
        # biely záblesk pri výmene
        if cur >= 0:
            fl = prog(t, AUTA[cur][2], 0.25)
            if 0 < fl < 1:
                inner.alpha_composite(Image.new("RGBA", (PW, PH), (255, 255, 255, int(150 * (1 - fl)))))
        inner.putalpha(Image.fromarray(np.minimum(np.asarray(inner.split()[3]), np.asarray(inner_mask))))
        comp.alpha_composite(inner, (60 + BORDER, 60 + BORDER))
        s = (0.6 + 0.4 * ease_out_back(pin, 2.0) if pin < 1 else 1) * (1 + bump) * (1 - 0.1 * pout)
        op = clamp(pin * 3) * (1 - pout)
        w, h = int(comp.width * s), int(comp.height * s)
        im = opacity(comp.resize((w, h), Image.BILINEAR), op)
        canvas.alpha_composite(im, (W // 2 - w // 2, CY - h // 2 - int(pout * 40)))
        # štítok s názvom modelu
        if cur >= 0:
            nm = AUTA[cur][0]
            pl = prog(t, AUTA[cur][2] + 0.05, 0.35)
            tw = f_brand.getlength("ŠKODA ") + f_model.getlength(nm)
            lw, lh = int(tw + 70), 96
            lab = Image.new("RGBA", (lw, lh), (0, 0, 0, 0)); ld = ImageDraw.Draw(lab)
            ld.rounded_rectangle([0, 0, lw - 1, lh - 1], radius=lh // 2, fill=RED + (255,))
            ld.text((35, lh / 2 + 3), "ŠKODA ", font=f_brand, fill=(255, 220, 220, 255), anchor="lm")
            ld.text((35 + f_brand.getlength("ŠKODA "), lh / 2 + 2), nm, font=f_model, fill=WHITE + (255,), anchor="lm")
            e = ease_out_back(pl, 2.2) if pl < 1 else 1
            ww, hh = max(1, int(lw * e)), max(1, int(lh * e))
            lab = opacity(lab.resize((ww, hh), Image.BICUBIC), clamp(pl * 3) * (1 - pout))
            ly = CY + FH // 2 + 70 - int(pout * 40)
            canvas.alpha_composite(lab, (W // 2 - ww // 2, ly - hh // 2))
            # bodky – poradie 1 až 5
            d = ImageDraw.Draw(canvas)
            for k in range(len(AUTA)):
                x = W // 2 + (k - 2) * 34; y = ly + 80 - int(pout * 40)
                r = 9 if k == cur else 6
                col = RED + (int(255 * (1 - pout)),) if k <= cur else (255, 255, 255, int(150 * (1 - pout)))
                d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline=(0, 0, 0, int(90 * (1 - pout))), width=1)
        canvas.save(os.path.join(frames, f"f_{fi:04d}.png"))
    n = int(DUR * SR); buf = mix(n)
    add(buf, whoosh(0.4, 400, 3000, 0.4), T_FRAME - 0.08)
    add(buf, pop(650, 160, 0.13, 0.55), T_FRAME + 0.2)
    rng = np.random.default_rng(5)
    for i, (_, _, ts) in enumerate(AUTA):
        # spúšť fotoaparátu + švih
        k = int(0.09 * SR); tk = np.arange(k) / SR
        click = rng.standard_normal(k) * (np.exp(-tk * 140) + 0.6 * np.exp(-np.maximum(0, tk - 0.045) * 160) * (tk > 0.045))
        add(buf, click * 0.7, ts - 0.01, (i - 2) * 0.2)
        add(buf, whoosh(0.3, 700, 3500, 0.3), ts - 0.08, (i - 2) * 0.2)
        add(buf, pop(900 + 80 * i, 300, 0.09, 0.4), ts + 0.06, (i - 2) * 0.2)
    add(buf, whoosh(0.5, 3000, 450, 0.35), T_OUT - 0.05)
    wav = os.path.join(HERE, NAME + "_zvuk.wav"); write_wav(wav, finish(buf))
    av.HERE_SAVE = av.HERE; av.HERE = HERE
    av.export(NAME, frames, wav, W, H, DUR)
    av.HERE = av.HERE_SAVE

if __name__ == "__main__":
    main()
