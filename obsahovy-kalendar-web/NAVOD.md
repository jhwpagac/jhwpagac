# Obsahový kalendár – spustenie ako samostatná web appka

Appka beží na tvojom Google účte (Google Apps Script) a je zadarmo. Dáta sa ukladajú do Google Tabuľky.
Dostaneš normálny odkaz `https://script.google.com/macros/s/.../exec`, ktorý otvoríš v hocijakom prehliadači aj na mobile.

## Inštalácia (cca 5 minút, robí sa iba raz)

1. Otvor **sheets.google.com** a vytvor novú prázdnu tabuľku. Pomenuj ju napr. „Obsahový kalendár“.
2. V tabuľke klikni v hornom menu na **Rozšírenia → Apps Script**.
3. Otvorí sa editor so súborom `Kód.gs` (alebo `Code.gs`). **Vymaž jeho obsah** a vlož celý obsah súboru `Code.gs`.
4. Hneď na začiatku súboru zmeň heslo v riadku `const HESLO = 'zmen-ma-123';` na svoje vlastné heslo.
5. Vľavo pri „Súbory“ klikni na **+ → HTML** a pomenuj súbor presne **`Index`** (bez .html). Vymaž jeho obsah a vlož celý obsah súboru `Index.html`.
6. Ulož (ikona diskety alebo Ctrl+S).
7. Vpravo hore klikni na **Nasadiť → Nové nasadenie**.
   - pri „Vyberte typ“ (ozubené koliesko) zvoľ **Webová aplikácia**,
   - **Spustiť ako:** *Ja (tvoj e-mail)*,
   - **Kto má prístup:** *Ktokoľvek*,
   - klikni **Nasadiť**.
8. Google ťa požiada o povolenie. Klikni **Autorizovať prístup**, vyber svoj účet a potom **Rozšírené → Prejsť na … (nebezpečné)** → **Povoliť**. Toto je normálne pri vlastných skriptoch, appka pristupuje iba k tejto tabuľke.
9. Skopíruj **URL webovej aplikácie**. To je tvoj odkaz na kalendár. Ulož si ho do záložiek alebo na plochu mobilu (v prehliadači: Zdieľať → Pridať na plochu).

## Používanie

- Otvor odkaz a prihlás sa heslom z kroku 4.
- Pri prvom otvorení sa v tabuľke vytvoria hárky **Klienti** a **Prispevky** s ukážkovými dátami označenými „(príklad)“.
- **Klienti a zdieľanie:** tu pridáš klientov a ku každému skopíruješ jeho odkaz, ktorý pošleš majiteľovi firmy.
  - Majiteľ vidí **iba svoj plán**, nič nemôže meniť a nevidí tvoje interné poznámky.
  - Ostatných klientov nevidí, lebo server mu pošle len jeho dáta.
  - Keď chceš klientovi prístup zrušiť, klikni „Nový odkaz“. Starý odkaz prestane fungovať.
- Pri každom príspevku je tlačidlo **Pripomienka do Google Kalendára**, takže ti príde notifikácia, keď treba postnúť.

## Keď budeš appku aktualizovať

Keď zmeníš kód, choď na **Nasadiť → Spravovať nasadenia → ceruzka (Upraviť) → Verzia: Nová verzia → Nasadiť**.
Takto zostane rovnaký odkaz pre teba aj pre klientov. Pozor, „Nové nasadenie“ by vytvorilo nový odkaz.
