#!/usr/bin/env python3
"""
Autofólie ZUZI – textový hook „Ako vyzerá týždeň v Autofólie ZUZI?“ + logo v rohu.
Bez pozadia, so zvukom. Farby a písmo podľa ich grafiky (tmavá, biela, zlatá, Poppins).
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "auto-vojto"))
import generuj_auto_vojto as av
from generuj_auto_vojto import (S, clamp, prog, ease_out_cubic, ease_in_cubic, ease_in_out, ease_out_back,
                                write_wav, mix, add, finish, opacity, whoosh, pop, sparkle, new_frames, SR, FPS)
av.HERE_FONTS = os.path.join(os.path.dirname(HERE), "auto-vojto", "fonty")
def pf(w, size):
    from PIL import ImageFont
    return ImageFont.truetype(os.path.join(av.HERE_FONTS, f"Poppins-{w}.ttf"), int(size * S))

GOLD = (223, 186, 108)
WHITE = (246, 247, 249)
NAME = "hook_tyzden_v_autofolie_zuzi"
# riadky hooku: (text, farba, veľkosť)
RIADKY = [("Ako vyzerá", WHITE, 74), ("týždeň v", GOLD, 96), ("Autofólie ZUZI?", WHITE, 74)]

def load_logo(width):
    src = Image.open(os.path.join(HERE, "zdroj_logo.jpg")).convert("RGB").crop((205, 340, 850, 690))
    L = np.asarray(src.convert("L")).astype(float)
    a = np.clip((L - 70) / (225 - 70), 0, 1) * 255
    img = Image.new("RGBA", src.size, WHITE + (0,)); img.putalpha(Image.fromarray(a.astype(np.uint8)))
    img = img.crop(img.getbbox())
    h = int(img.height * width / img.width)
    return img.resize((width, h), Image.LANCZOS)

def text_layer(txt, col, size):
    f = pf("Bold", size)
    bb = f.getbbox(txt)
    w, h = bb[2] + 20 * S, int(size * S * 1.32)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10 * S, h / 2), txt, font=f, fill=col + (255,), anchor="lm")
    return img

def main():
    W = 1080
    lines = [text_layer(*r) for r in RIADKY]
    logo = load_logo(300 * S)
    # tmavá žiara okolo loga, aby sa oddelilo od bieleho textu pod ním
    LP = 30 * S
    logo_sh = Image.new("RGBA", (logo.width + 2 * LP, logo.height + 2 * LP), (0, 0, 0, 0))
    la = Image.new("L", logo_sh.size, 0); la.paste(logo.split()[3], (LP, LP))
    la = la.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(9 * S)).point(lambda v: min(255, int(v * 1.6)))
    dk = Image.new("RGBA", logo_sh.size, (14, 16, 20, 0)); dk.putalpha(la)
    logo_sh.alpha_composite(dk); logo_sh.alpha_composite(logo, (LP, LP))
    gap = -8 * S
    block_h = sum(l.height for l in lines) + gap * (len(lines) - 1)
    H2 = int(70 * S + block_h + logo.height * 0.6 + 60 * S)
    H = int(math.ceil(H2 / S / 2) * 2)
    x0 = 80 * S
    ys = []; y = 70 * S
    for l in lines: ys.append(y); y += l.height + gap
    under_y = ys[1] + lines[1].height * 0.97
    # logo čiastočne prekrýva koniec posledného riadku
    logo_y = ys[2] + lines[2].height * 0.42; logo_x = x0 + lines[2].width - logo.width * 0.42
    T = [0.1, 0.1, 0.1]; D_LINE = 0.6   # celý text naraz
    T_UNDER, T_LOGO, T_OUT, DUR = 0.8, 1.15, 4.7, 5.3
    frames = new_frames(NAME)
    tw_gold = lines[1].width - 20 * S
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        big = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        pout = ease_in_cubic(prog(t, T_OUT, 0.5))
        # riadky vybiehajú zdola cez masku (každý riadok má vlastné „okno“)
        for i, l in enumerate(lines):
            p = prog(t, T[i], D_LINE)
            if p <= 0: continue
            e = ease_out_back(p, 1.2) if p < 1 else 1
            off = (1 - e) * l.height * 0.9 + pout * 30 * S
            win = Image.new("RGBA", l.size, (0, 0, 0, 0))
            win.alpha_composite(opacity(l, clamp(p * 2) * (1 - pout)), (0, int(off)) if off < l.height else (0, l.height - 1))
            # orez spodku okna – text sa „vynorí“
            big.alpha_composite(win, (int(x0 - (pout * 0)), int(ys[i])))
        # zlatá vlnovka pod „týždeň“ – ako krivka auta v logu
        pu = ease_in_out(prog(t, T_UNDER, 0.5))
        if pu > 0:
            d = ImageDraw.Draw(big)
            pts = []
            n = 80
            for k in range(int(n * pu) + 1):
                u = k / n
                xx = x0 + 14 * S + u * tw_gold
                yy = under_y + math.sin(u * math.pi) * -14 * S + u * 6 * S
                pts.append((xx, yy))
            wcol = GOLD + (int(255 * (1 - pout)),)
            if len(pts) > 1:
                for k in range(len(pts) - 1):
                    wdt = int((3 + 5 * math.sin(math.pi * k / n)) * S)
                    d.line([pts[k], pts[k + 1]], fill=wcol, width=wdt)
        # logo
        pl = prog(t, T_LOGO, 0.6)
        if pl > 0:
            e = ease_out_cubic(pl)
            im = opacity(logo_sh, e * (1 - pout))
            big.alpha_composite(im, (int(logo_x - LP + (1 - e) * 40 * S), int(logo_y - LP)))
        # jemný tieň pod všetkým kvôli čitateľnosti na videu
        a = big.split()[3].filter(ImageFilter.GaussianBlur(10 * S)).point(lambda v: int(v * 0.55))
        sh = Image.new("RGBA", big.size, (0, 0, 0, 0)); sh.putalpha(a)
        out = Image.new("RGBA", big.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 5 * S)); out.alpha_composite(big)
        canvas = out.resize((W, H), Image.LANCZOS)
        canvas.save(os.path.join(frames, f"f_{fi:04d}.png"))
    n = int(DUR * SR); buf = mix(n)
    add(buf, whoosh(0.45, 450, 3200, 0.45), T[0] - 0.05)
    add(buf, pop(750, 200, 0.13, 0.6), T[0] + 0.3)
    add(buf, whoosh(0.5, 1800, 4500, 0.2), T_UNDER)
    add(buf, sparkle(), T_UNDER + 0.15)
    add(buf, pop(1100, 350, 0.1, 0.4), T_LOGO + 0.1)
    add(buf, whoosh(0.5, 3000, 450, 0.35), T_OUT - 0.05)
    wav = os.path.join(HERE, NAME + "_zvuk.wav"); write_wav(wav, finish(buf))
    av.HERE_SAVE = av.HERE
    av.HERE = HERE
    av.export(NAME, frames, wav, W, H, DUR)
    av.HERE = av.HERE_SAVE

if __name__ == "__main__":
    main()
