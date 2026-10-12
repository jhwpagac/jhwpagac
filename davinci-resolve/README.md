# OdstranPauzy – automatické hardcuty bez páuz pre DaVinci Resolve

Lua skript `OdstranPauzy.lua` zoberie aktuálny timeline, cez ffmpeg nájde ticho
a vytvorí **nový timeline „… - bez pauz“**, kde sú časti s rečou poskladané
hardcutmi tesne za sebou. Pôvodný timeline zostane nedotknutý.

## Čo potrebuješ
1. **ffmpeg** – Mac: `brew install ffmpeg` (skript ho nájde v `/opt/homebrew/bin` aj `/usr/local/bin`).
2. **Media online** – súbory musia byť na ceste, ktorú vidí Resolve
   (v projekte `araver video 1` sú to `~/Downloads/DJI_20260922114548_0523_D.MP4`
   a `~/Downloads/DJI_20260922114927_0524_D.MP4`).
3. Klipy na stope **V1** (audio môže byť linknuté, pridá sa automaticky).

## Inštalácia (Mac)
Skopíruj `OdstranPauzy.lua` do:
```
~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Edit/
```
Reštartuj Resolve → otvor timeline → **Workspace → Scripts → OdstranPauzy**.
Log uvidíš vo **Workspace → Console** (záložka Lua).

## Ladenie (hore v skripte, `CONFIG`)
| Nastavenie | Default | Čo robí |
|---|---|---|
| `NOISE_DB` | -35 | prah ticha; šum v pozadí → -30, tichá miestnosť → -40 |
| `MIN_SILENCE` | 0.4 s | kratšie pauzy ostanú; pre rýchle Reels skús 0.3 |
| `PAD_BEFORE` / `PAD_AFTER` | 0.08 / 0.12 s | rezerva, aby slová neboli odseknuté |
| `MIN_KEEP` | 0.25 s | zahodí krátke zvuky (kliky, nádychy) |
| `DRY_RUN` | false | `true` = len vypíše strihy, nič nevytvorí |
