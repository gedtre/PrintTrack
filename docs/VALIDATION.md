# Patikros (2026-10-23)

Šioje Linux debesijos aplinkoje atliktos patikros:

- `npm run lint` – sėkminga.
- `npm run typecheck` – sėkminga.
- `npm test` – 10 testų sėkmingi (LT / EN raktai, numatytoji kalba, paskyros pasirinkimas, įvestų duomenų išlikimas, formatavimas, autentifikavimas, teisės, išdavimas ir ataskaitų navigacijos regresija).
- `npm run build` – sėkmingas produkcinis surinkimas.
- `ruff check backend deploy` – sėkminga.
- `python -m pytest -q tests` iš `backend` katalogo su atskira PostgreSQL 17 testų baze – 16 testų sėkmingi, įskaitant tikrus vienalaikius išdavimus ir idempotentiškus gavimus. Vienas priklausomybės `anyio` nebenaudotino API perspėjimas, testai nepraleisti.
- Alembic `upgrade head → downgrade base → upgrade head` atskiroje naujoje bazėje – sėkminga.
- Docker vaizdai surinkti; visos trys Compose paslaugos tapo `healthy`; Nginx ir FastAPI API pasiekiami.
- `npm run test:e2e` su vietiniu Chromium – 1 išsamus naršyklės testas sėkmingas: prisijungimas, gavimas, nepatvirtinto suderinamumo blokavimas, patvirtinimas, išdavimas, likučio pasikeitimas, istorija, CSV failas, ataskaitos, kompensavimas, LT / EN, kalbos atkūrimas, įvesto teksto išlikimas ir atsijungimas.
- Visiškai sustabdžius ir pašalinus Compose konteinerius (`down`, be `--volumes`) ir paleidus juos iš naujo, išliko tie patys katalogai, likučiai, operacijos, kalbos pasirinkimas ir duomenų bazėje saugoma sesija.
- Chromium darbalaukio sąsaja vizualiai peržiūrėta; 390 px pločio sandėlio puslapis neturi viso puslapio horizontalaus perpildymo.
- `npm audit --omit=dev` – neaptikta pažeidžiamumų; tai nėra nepriklausomas saugumo auditas.

## Aplinkos skirtumai

Šiame Codex konteineryje įprastas Docker surinkimas negalėjo išspręsti paketų serverių DNS vardų. Patikrai naudotas `deploy/cloud-build.py`: esamas tarpinis serveris ir patikimas CA perduodami per standartinius Docker parametrus / BuildKit secret. TLS tikrinimas neišjungtas. Projekto įprasti Dockerfile dėl šio apribojimo nekeisti į priklausančius nuo debesijos; Windows paleidimui šio pagalbininko nereikia.

Naršyklės atsisiuntimo domenas čia buvo neprieinamas, todėl naudotas jau įdiegtas Chromium per `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`.

Windows / Docker Desktop ir PowerShell scenarijus šioje Linux aplinkoje **natūraliai nepaleisti**. Pateiktos jų instrukcijos ir Docker Compose konfigūracija. GitHub Actions konfigūracija pridėta, tačiau jos nuotolinio vykdymo rezultatas šiame pokalbyje nepatvirtintas. HTTPS diegimas įstaigos tinkle ir įstaigos saugumo peržiūra neatlikti.
