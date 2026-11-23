#!/usr/bin/env python3
"""Zostaví stránku „Animácie na stiahnutie“ (MP4 vložené do HTML + tlačidlo cez downloads capability).
Použitie: python3 build_page.py <výstup.html>   – najnovšie animácie patria na začiatok zoznamu ITEMS."""
import base64, html, os, sys
R = os.path.dirname(os.path.abspath(__file__)) + "/"
ITEMS = [
  ("Losovanie výhercu – story @lysak8", "9 s · 1080×1920 · hotová story s pozadím (nič nemusíš kľúčovať)", "araver-losovanie/losovanie_vyherca_story.mp4", "losovanie_vyherca_story.mp4"),
  ("Araver – 5 áut Škoda (Reels 9:16)", "7,2 s · 1080×1920 · zelené pozadie · Kamiq, Karoq, Scala, Octavia, Fabia", "araver-auta/araver_auta_reels_zelene_pozadie.mp4", "araver_auta_reels.mp4"),
  ("Autofólie ZUZI – hook „Ako vyzerá týždeň“", "5,3 s · zelené pozadie · text naraz, podčiarknutie, logo cez text", "autofolie-zuzi/hook_tyzden_v_autofolie_zuzi_zelene_pozadie.mp4", "autofolie_zuzi_hook_tyzden.mp4"),
  ("Auto Vojto – mapa Trnava s adresou", "5,6 s · zelené pozadie · obrys okresu + pin na Trstínskej 10", "auto-vojto/mapa_trnava_zelene_pozadie.mp4", "auto_vojto_mapa_trnava.mp4"),
  ("Auto Vojto – Google recenzie", "7,6 s · zelené pozadie · 4 recenzie vybehnú zdola", "auto-vojto/recenzie_zelene_pozadie.mp4", "auto_vojto_recenzie.mp4"),
  ("Auto Vojto – logo", "4,2 s · zelené pozadie · logo vyskočí so žiarou", "auto-vojto/logo_zelene_pozadie.mp4", "auto_vojto_logo.mp4"),
  ("Auto Vojto – dve tabuľky", "6,8 s · zelené pozadie · diagnostika + kontrola", "auto-vojto/dve_tabulky_zelene_pozadie.mp4", "auto_vojto_tabulky.mp4"),
  ("Mapa Slovenska – Bratislava, Trnava", "5,6 s · zelené pozadie · obrys + piny", "realitky/mapa_slovensko_zelene_pozadie.mp4", "mapa_slovensko.mp4"),
  ("Suma −10 000 € (červená)", "4 s · zelené pozadie · klesajúce cinky", "realitky/suma_minus_10000_zelene_pozadie.mp4", "suma_minus_10000.mp4"),
  ("Podpis – biely", "5 s · zelené pozadie · zvuk pera", "realitky/podpis_biely_zelene_pozadie.mp4", "podpis_biely.mp4"),
  ("Podpis – modrý", "5 s · zelené pozadie · zvuk pera", "realitky/podpis_modry_zelene_pozadie.mp4", "podpis_modry.mp4"),
  ("Suma 0 → 300 000 €", "4 s · fialové pozadie · cink cink", "realitky/suma_300000_fialove_pozadie.mp4", "suma_300000.mp4"),
  ("Suma 0 → 130 000 €", "4 s · fialové pozadie · cink + kasa", "realitky/suma_130000_fialove_pozadie.mp4", "suma_130000.mp4"),
  ("Tento byt sme predali", "6 s · zelené pozadie · 3 fotky + pečiatka", "byt/predany_byt_greenscreen.mp4", "predany_byt.mp4"),
]
cards = []
for i, (t, meta, p, fn) in enumerate(ITEMS):
    b = base64.b64encode(open(R + p, "rb").read()).decode()
    cards.append(f'''<article class="card">
<video id="v{i}" src="data:video/mp4;base64,{b}" controls playsinline preload="metadata"></video>
<div class="row"><div class="txt"><h2>{html.escape(t)}</h2><p>{html.escape(meta)}</p></div>
<button type="button" id="b{i}" data-i="{i}" data-fn="{fn}">Stiahnuť video</button></div>
<p class="msg" id="m{i}" aria-live="polite"></p></article>''')
page = f'''<title>Animácie na stiahnutie</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* layout: jeden stĺpec kariet, video hore, veľké tlačidlo pod ním */
:root{{--bg:#f3f3f5;--card:#ffffff;--fg:#141416;--muted:#6b6b75;--line:#e2e2e8;--accent:#e30613;--accent-fg:#ffffff;--ok:#1a8f4a;--vbg:#000000;
--sans:"Manrope",system-ui,-apple-system,"Segoe UI",sans-serif}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0e0e10;--card:#18181b;--fg:#f4f4f6;--muted:#9a9aa5;--line:#2a2a30;--accent:#ff2a36;--ok:#3ccf7a;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#0e0e10;--card:#18181b;--fg:#f4f4f6;--muted:#9a9aa5;--line:#2a2a30;--accent:#ff2a36;--ok:#3ccf7a;color-scheme:dark}}
body{{background:var(--bg);color:var(--fg);font-family:var(--sans);padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:24px 48px}}
main{{max-width:680px;margin:0 auto;display:flex;flex-direction:column;gap:20px}}
header h1{{font-size:1.6rem;font-weight:800;margin:0 0 6px;text-wrap:balance}}
header p{{margin:0;color:var(--muted);font-size:.95rem;line-height:1.5}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}}
video{{display:block;width:100%;max-width:100%;max-height:70vh;background:var(--vbg)}}
.row{{display:flex;flex-wrap:wrap;align-items:center;gap:12px;padding:14px 16px 6px}}
.txt{{flex:1 1 200px;min-width:0}}
h2{{font-size:1.05rem;margin:0 0 2px;font-weight:700}}
.txt p{{margin:0;color:var(--muted);font-size:.85rem}}
button{{font:inherit;font-weight:700;font-size:1rem;background:var(--accent);color:var(--accent-fg);border:0;border-radius:10px;padding:13px 20px;cursor:pointer;flex:0 0 auto}}
button:hover{{filter:brightness(1.08)}} button:focus-visible{{outline:3px solid var(--fg);outline-offset:2px}}
button:disabled{{opacity:.55;cursor:default}}
.msg{{margin:0;padding:0 16px 14px;font-size:.85rem;color:var(--muted);min-height:1em}}
.msg.ok{{color:var(--ok)}}
.tip{{font-size:.85rem;color:var(--muted);line-height:1.55;border-top:1px solid var(--line);padding-top:16px}}
</style>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;700;800&display=swap">
<main>
<header><h1>Animácie na stiahnutie</h1>
<p>Pozri si video a klikni na „Stiahnuť video“. Stiahne sa celé MP4 aj so zvukom.</p></header>
{''.join(cards)}
<p class="tip"><b>V Premiere:</b> daj video nad svoj záber → Effects → <b>Ultra Key</b> → kvapátkom klikni na zelenú alebo fialovú plochu. Pozadie zmizne.</p>
</main>
<script>
let dl=null;
(async()=>{{try{{dl=await window.claude?.use?.("downloads");}}catch(e){{dl=null}}
if(!dl)document.querySelectorAll(".msg").forEach(m=>m.textContent="Sťahovanie tu nie je dostupné – otvor stránku v claude.ai.");}})();
async function blobFrom(src){{const b64=src.split(",")[1];const bin=atob(b64);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return new Blob([u],{{type:"video/mp4"}});}}
document.querySelectorAll("button[data-i]").forEach(btn=>btn.addEventListener("click",async()=>{{
const i=btn.dataset.i,m=document.getElementById("m"+i);m.className="msg";
if(!dl){{m.textContent="Sťahovanie tu nie je dostupné – otvor stránku v claude.ai.";return}}
btn.disabled=true;m.textContent="Pripravujem…";
try{{const blob=await blobFrom(document.getElementById("v"+i).src);await dl.save({{filename:btn.dataset.fn,data:blob}});
m.textContent="Stiahnuté ✓";m.className="msg ok";}}
catch(e){{m.textContent=e&&e.code==="declined"?"Sťahovanie si zrušil.":e&&e.code==="rate_limited"?"Počkaj chvíľu a skús znova.":"Nepodarilo sa stiahnuť, skús znova.";}}
finally{{btn.disabled=false}}}}));
</script>'''
open(sys.argv[1], "w").write(page)
print(os.path.getsize(sys.argv[1]))
