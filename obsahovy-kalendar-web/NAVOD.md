# Obsahový kalendár – návod na spustenie

Výsledok:
- **Ty** máš appku nainštalovanú na PC aj na mobile, s ikonou a vo vlastnom okne.
- **Klient** dostane odkaz, rozklikne ho a otvorí sa mu obyčajná webová stránka. Uvidí iba svoj plán.

Ako to funguje: **dáta** sú v tvojej Google Tabuľke (Google Apps Script) a **appka** beží na GitHub Pages. Obe služby sú zadarmo.

---

## Časť 1 – Server s dátami (Google, cca 5 min)

1. Otvor **sheets.google.com** a vytvor novú prázdnu tabuľku. Pomenuj ju napr. „Obsahový kalendár“.
2. V tabuľke klikni na **Rozšírenia → Apps Script**.
3. V súbore `Kód.gs` (alebo `Code.gs`) **vymaž všetko** a vlož celý obsah súboru `Code.gs`.
4. V riadku `const HESLO = 'zmen-ma-123';` zmeň heslo na svoje vlastné.
5. Vľavo pri „Súbory“ klikni na **+ → HTML**, pomenuj súbor **`Index`** a vlož doň obsah `Index.html`. Tento krok nie je povinný, ale bez neho nebude fungovať záložná verzia priamo na Google adrese.
6. Ulož (Ctrl+S).
7. Klikni **Nasadiť → Nové nasadenie → (ozubené koliesko) Webová aplikácia**:
   - **Spustiť ako:** Ja,
   - **Kto má prístup:** Ktokoľvek,
   - potom **Nasadiť**.
8. Klikni **Autorizovať prístup**, vyber účet a potom **Rozšírené → Prejsť na … → Povoliť**.
9. Skopíruj **URL webovej aplikácie**, teda adresu, ktorá končí na `/exec`. Budeš ju potrebovať v časti 3.

## Časť 2 – Zapnutie appky (GitHub Pages, cca 2 min)

1. Otvor repozitár **github.com/jhwpagac/jhwpagac** → **Settings**.
2. Na bezplatnom GitHub účte musí byť repozitár **verejný**. Ak nie je, zmeníš to v **Settings → General → úplne dole Danger Zone → Change visibility → Public**.
   - Tvoje dáta ani heslo tým nikto neuvidí. Sú iba v tvojom Google účte, verejný je len kód appky.
3. Choď do **Settings → Pages** a nastav:
   - **Source:** Deploy from a branch,
   - **Branch:** `claude/intelligent-carson-dp0dii` (alebo `main`, ak zmeny zlúčiš), priečinok **`/docs`**,
   - potom **Save**.
4. Po 1 až 2 minútach bude appka na adrese **https://jhwpagac.github.io/jhwpagac/**.

## Časť 3 – Prvé spustenie

1. Otvor **https://jhwpagac.github.io/jhwpagac/**.
2. Vlož adresu `/exec` z časti 1 a prihlás sa svojím heslom.
3. Aby klientske odkazy boli krátke, môžeš adresu `/exec` vložiť aj do súboru `docs/config.js` na GitHube (ceruzka → upraviť → Commit). Nie je to povinné, funguje to aj bez toho. Alebo mi adresu pošli a vložím ju tam ja.

## Inštalácia appky

- **PC (Chrome alebo Edge):** otvor adresu appky a v adresnom riadku vpravo klikni na ikonku **Inštalovať** (monitor so šípkou). Appka sa objaví v ponuke Štart a môžeš si ju pripnúť na lištu.
- **iPhone:** otvor adresu v **Safari** → tlačidlo **Zdieľať** → **Pridať na plochu**.
- **Android:** otvor adresu v **Chrome** → menu ⋮ → **Inštalovať aplikáciu** (alebo „Pridať na plochu“).

## Zdieľanie s klientom

V appke klikni na **Klienti a zdieľanie** → pri klientovi **Kopírovať odkaz** a pošli mu ho napríklad cez WhatsApp alebo e-mail.
- Klient nemusí nič inštalovať, odkaz sa mu otvorí ako webová stránka.
- Vidí **iba svoj plán**, nič nemôže meniť a tvoje interné poznámky nevidí.
- Keď chceš klientovi prístup zrušiť, klikni **Nový odkaz**. Starý odkaz prestane fungovať.

## Keď budeš aktualizovať kód na Google

V Apps Script choď na **Nasadiť → Spravovať nasadenia → ceruzka → Verzia: Nová verzia → Nasadiť**.
Takto zostane rovnaká adresa `/exec`. „Nové nasadenie“ by vytvorilo novú adresu.
