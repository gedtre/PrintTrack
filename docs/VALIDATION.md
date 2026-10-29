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

## 2026-10-29: kabinetų CSV importas

- Bendra PostgreSQL serverio testų programa: **24 testai sėkmingi** (ankstesni 16 ir 8 importo testai). Tikrinamas peržiūros nekeičiantis režimas, privalomi pastatas / aukštas, tipų ir numerių išsaugojimas, vientisas įrašymas, pakartotinis bei vienalaikis importas, auditas, konfliktai, formatas ir teisės.
- Frontend: **13 testų sėkmingi** (ankstesni 10 ir 3 importo sąsajos testai). Lint, TypeScript ir produkcinis surinkimas sėkmingi.
- Naujas Chromium importo scenarijus sėkmingas prieš tikrą FastAPI / PostgreSQL testų aplinką per Vite: įkėlimas → trūkstamų laukų blokavimas → pastatas ir aukštas → peržiūra → patvirtinimas → 2 kabinetai bazėje → pakartotinė peržiūra be dublių → LT / EN.
- Pateiktų nuotraukų vietinis CSV patikrintas serverio peržiūros funkcija neįrašant duomenų. Pastatai ir aukštai joje nebuvo spėjami. Asmens pateikti duomenys laikomi ignoruojamame vietiniame kataloge ir nekeliami į GitHub.
- Importo pakeitimams nereikia migracijos ar naujų priklausomybių. Šiame etape veikiančios naudotojo Docker bazės nekeičiau; patikroms naudota atskira testų bazė ir atskiri procesai.
