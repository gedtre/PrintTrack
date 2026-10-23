# PrintTrack

Veikianti vietinė spausdintuvų ir kasečių apskaitos sistema: React / TypeScript / Vite, FastAPI, SQLAlchemy 2, Alembic ir PostgreSQL 17. Lietuvių kalba numatytoji, anglų – pasirenkama. Pacientų duomenų sistema nerenka ir jų čia saugoti nereikia.

## Greitas paleidimas „Windows“ kompiuteryje

1. Įdiekite **Docker Desktop** su WSL 2 ir Linux konteineriais bei **Git**. Paleiskite Docker Desktop ir palaukite, kol jo variklis pradės veikti. Atskiro Node.js ar Python nereikia.
2. Atidarykite PowerShell:

```powershell
git clone --branch feature/printtrack-initial https://github.com/gedtre/PrintTrack.git
cd PrintTrack
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -Demo
docker compose up --build -d
```

`setup.ps1 -Demo` vieną kartą sukuria `.env` su atsitiktiniais duomenų bazės ir administratoriaus slaptažodžiais bei **aiškiai įjungia DEMO**. Esamo `.env` neperrašo. `ExecutionPolicy Bypass` galioja tik šiam PowerShell procesui, ne visam kompiuteriui. Jei nenorite vykdyti skripto, naudokite toliau aprašytą rankinį konfigūravimą.

3. Naršyklėje atidarykite **http://localhost:8080**.
4. Prisijungimo vardas – `admin`. Atidarykite `notepad .env` ir nukopijuokite tik reikšmę po `ADMIN_PASSWORD=` į slaptažodžio lauką. Slaptažodis atsitiktinis, nėra įrašytas programos kode. `.env` saugokite kaip slaptą failą, nekelkite į GitHub ir nesiųskite pokalbyje.

Pirmasis surinkimas gali užtrukti kelias minutes. Būseną patikrinsite:

```powershell
docker compose ps
docker compose logs --tail 50 backend
docker compose logs --tail 50 frontend
```

Visos trys paslaugos turi tapti `healthy`. Nginx pateikia sąsają ir persiunčia `/api` užklausas serveriui. Duomenų bazės ir serverio prievadai į kompiuterio tinklą neskelbiami. Migracijos ir pirmos paskyros sukūrimas vyksta automatiškai.

### Jei saugykla jau atsisiųsta

Naujo kopijavimo nereikia. Esamame projekto kataloge, išsaugoję savo vietinius pakeitimus:

```powershell
git switch feature/printtrack-initial
git pull --ff-only
```

Tada vieną kartą sukurkite `.env` ir vykdykite `docker compose up --build -d`.

### Rankinis konfigūravimas / Linux

Nukopijuokite `.env.example` į `.env` (`Copy-Item .env.example .env` arba `cp .env.example .env`). Nustatykite:

- `POSTGRES_PASSWORD` – atsitiktinė bent 32 šešioliktainių simbolių reikšmė (naudojama ir prisijungimo URL, todėl venkite specialių URL simbolių).
- `ADMIN_PASSWORD` – stiprus bent 12 simbolių slaptažodis. `.env` reikšmes su specialiais simboliais tinkamai apgaubkite pagal Docker Compose `.env` sintaksę.
- Tik demonstravimui: `DEMO_MODE=true`, `COMPOSE_PROJECT_NAME=printtrack-demo`.
- Tik vietiniam HTTP: `COOKIE_SECURE=false`. `.env.example` numatytoji `true` skirta HTTPS ir per paprastą HTTP prisijungimas neveiks.

Tada: `docker compose up --build -d`. Slaptažodis iš `ADMIN_PASSWORD` pritaikomas tik **pirmą kartą kuriant administratorių**; vėliau jo keitimas `.env` nekeičia jau egzistuojančios paskyros.

## Demonstravimas per 5–10 minučių

DEMO aplinka aiškiai pažymėta antraštėje. Ji turi 5 fiktyvius skyrius, 15 kabinetų, 20 spausdintuvų ir 12 kasečių tipų. **Pradiniai likučiai yra nuliniai. Visi suderinamumo ryšiai nepatvirtinti.** `DEMO` modeliai ir kasetės neegzistuoja tikrovėje.

1. **Apžvalga:** patikrinkite spausdintuvų skaičius ir nulinį sandėlio likutį.
2. **Sandėlis:** operacija „Gavimas“, kasetė `DEMO-T01`, kiekis `5`, pastaba „Demonstracinis gavimas“. Patvirtinkite. Likutis turi būti 5.
3. **Spausdintuvai:** prie `DEMO-P001` spauskite „Išduoti kasetę“. `DEMO-T01` dar nerodoma, nes suderinamumas nepatvirtintas.
4. **Kasečių katalogas → Kasečių suderinamumas:** pasirinkite modelį `PT-DEMO-1`, kasetę `DEMO-T01`, pažymėkite „Suderinamumas patvirtintas“, įrašykite „DEMO – tik fiktyvaus scenarijaus patvirtinimas“ ir išsaugokite. Tai nėra realaus gaminio suderinamumo įrodymas.
5. Vėl pasirinkite `DEMO-P001` → „Išduoti kasetę“, pasirinkite `DEMO-T01` ir kiekį `1`. Patvirtinkite. Sandėlio likutis turi tapti 4.
6. **Operacijų istorija:** matysite gavimą `+5` ir išdavimą `−1` su naudotoju, kabinetu ir skyriumi. Filtruokite pagal spausdintuvą ar kasetę.
7. **Ataskaitos:** išbandykite mėnesinį sunaudojimą, sunaudojimą pagal skyrių ir dabartinį likutį. „Eksportuoti CSV“ pateikia UTF-8 BOM failą su kabliataškiais, tinkamą atidaryti Excel. CSV antraštės ir operacijų tipai priklauso nuo LT / EN pasirinkimo.
8. **Operacijų istorija:** atšaukite išdavimą ir įrašykite priežastį. Sukuriamas kompensuojantis `+1` įrašas, senas įrašas lieka, likutis vėl 5. Atšaukti gavimo, kai jo atsargos jau sunaudotos ir susidarytų neigiamas likutis, negalima.
9. **Spausdintuvai → Redaguoti:** perkelkite spausdintuvą į kitą kabinetą. „Išsamiau“ rodys perkėlimo istoriją; senos sandėlio operacijos išlaikys buvusio kabineto ir skyriaus pavadinimus.
10. **Nustatymai:** sukurkite atskirą „Skaitytojo“ paskyrą ir patikrinkite, kad ji mato duomenis, tačiau negali jų keisti. LT / EN pasirinkimas saugomas paskyroje ir atkuriamas prisijungus.

Papildomai išbandykite grąžinimą, nurašymą ir koregavimą. Kiekį įveskite teigiamą; išdavimo ir nurašymo atveju serveris pats taiko minusą. Tik koregavimui galima įvesti neigiamą kiekį, nurodžius priežastį. Po operacijos likutis negali būti neigiamas.

## Sustabdymas, paleidimas ir atnaujinimas

```powershell
# Sustabdyti; duomenys lieka PostgreSQL tome:
docker compose down
# Vėl paleisti:
docker compose up -d
# Atnaujinti programą (prieš migracijas pasidarykite atsarginę kopiją):
git pull --ff-only
docker compose up --build -d
```

Nenaudokite `--volumes` įprastam sustabdymui. Atsitiktiniai pradiniai slaptažodžiai turi likti tame pačiame `.env`; pakeitus duomenų bazės slaptažodį tik `.env`, jau egzistuojanti PostgreSQL paskyra automatiškai nepasikeis.

### Pradėti demonstravimą iš naujo

**Toliau pateiktos komandos negrįžtamai ištrina šio Compose projekto duomenų bazę. Vykdykite tik atskiroje DEMO aplinkoje, patikrinę `.env`: `DEMO_MODE=true`, `COMPOSE_PROJECT_NAME=printtrack-demo`.**

```powershell
docker compose down --volumes
docker compose up -d
```

Liks tie patys `.env` prisijungimo duomenys, bus iš naujo įkelti fiktyvūs katalogai su nuliniais likučiais. Gamybinės aplinkos šitaip neatkurkite.

## Tuščia aplinka ir saugus diegimas

Be `-Demo` skriptas sukuria tuščią aplinką su `DEMO_MODE=false` ir atskiru `printtrack-local` projekto vardu. Skyrius, pastatus, kabinetus, modelius ir kasetes įveskite patys, tada registruokite tikrus gavimus. Gamybinėje bazėje nėra fiktyvių kiekių ar patvirtintų fiktyvių suderinamumų. `DEMO_MODE` keisti jau inicializuotai bazei draudžiama: serveris atsisakys startuoti. Kitam režimui naudokite atskirą projekto katalogą ir atskirą Compose projekto vardą / tomą.

Paleidimas pagal nutylėjimą pasiekiamas tik jūsų kompiuteryje (`HOST_BIND=127.0.0.1`). Įstaigos tinklui reikia administratoriaus sukonfigūruoto HTTPS atvirkštinio tarpinio serverio, sertifikato, ugniasienės ir atsarginių kopijų. Nustatykite `COOKIE_SECURE=true`; vien IP prievado atvėrimas nepakeičia HTTPS. Jei HTTPS tarpinis serveris keičia `Host`, jis turi išsaugoti išorinį `Host`, kad veiktų tos pačios kilmės patikra. Sesijos slapukai yra HttpOnly, SameSite=Strict; sesijos galioja 8 valandas. Duomenų bazės prievado neatverkite į LAN. Tai vietiniam demonstravimui patikrinta programa, ne atlikto įstaigos saugumo audito pakaitalas.

### Atsarginė kopija

Šios komandos nesugadina dvejetainio failo ir senesniame Windows PowerShell:

```powershell
docker compose exec -T db pg_dump -U printtrack -d printtrack -Fc -f /tmp/printtrack.dump
docker compose cp db:/tmp/printtrack.dump .\printtrack.dump
```

Saugokite kopiją saugioje vietoje. Atkūrimas (perrašo esamos bazės objektus, todėl pirmiausia išsaugokite dabartinę kopiją):

```powershell
docker compose stop frontend backend
docker compose cp .\printtrack.dump db:/tmp/printtrack.dump
docker compose exec -T db pg_restore --clean --if-exists --no-owner -U printtrack -d printtrack /tmp/printtrack.dump
docker compose up -d
```

## Architektūra ir apskaitos taisyklės

- Normalizuotos lentelės: naudotojai, sesijos, skyriai, pastatai, kabinetai, modeliai, spausdintuvai, kasetės, daugelio su daugeliu suderinamumas, operacijos, perkėlimai, auditas. Alembic migracijos saugomos `backend/migrations`.
- Kiekviena likutį keičianti operacija PostgreSQL užrakina kasetės eilutę prieš skaičiuodama `SUM(quantity)`; neigiamas likutis atmetamas. Operacijos, suderinamumo pakeitimai ir kompensavimai naudoja tą patį užrakto mechanizmą.
- Operacijų, perkėlimų ir audito UPDATE/DELETE uždrausti duomenų bazės trigeriais. Taisymas – priešingas įrašas su priežastimi. Kiekvienos operacijos užklausos UUID saugo nuo dubliavimo pakartotinai siunčiant tą pačią užklausą.
- Istorijoje saugomi pavadinimų momentiniai vaizdai; katalogo pervadinimas ar spausdintuvo perkėlimas istorijos neperrašo. Spausdintuvai archyvuojami, o istoriją turintys katalogo įrašai netrinami.
- Išdavimui būtinas aktyvus nearchyvuotas spausdintuvas ir aiškiai IT specialisto arba administratoriaus patvirtintas suderinamumas su pagrindu. Sistemoje esančių gamintojų duomenys nėra suderinamumo įrodymas.
- Administratorius valdo paskyras ir duomenis; IT specialistas valdo katalogus ir operacijas; skaitytojas tik skaito ir eksportuoja. Serveris tikrina teises nepriklausomai nuo sąsajos.
- Slaptažodžiai maišomi Argon2; sesijų žetonai bazėje saugomi tik kaip SHA-256 maišos. Prisijungimas ribojamas po 10 nesėkmingų bandymų per 15 minučių vienam vardui.
- Sunaudojimo ataskaitos rodo išdavimus, atėmus jų kompensavimus iki pasirinktos pabaigos datos. Grąžinimai yra atskiri sandėlio įvykiai ir savaime neatšaukia ankstesnio išdavimo. Datos filtruojamos Lietuvos laiku. Dabartinio bendro sandėlio likučiui datos / skyriaus / spausdintuvo filtrai netaikomi.
- CSV tekstai apsaugomi nuo formulės interpretavimo. Katalogų ir istorijos duomenys pateikiami originalo kalba, naudotojo tekstai neverčiami.

## Kūrimas ir testai

Frontend: Node.js 22+, `npm ci`, `npm run dev`. Vite persiunčia `/api` į `127.0.0.1:8000`. Backend: Python 3.12+, virtualioji aplinka, `pip install -r backend/requirements.txt`; vykdykite iš `backend` katalogo: `alembic upgrade head`, `python -m app.bootstrap`, `uvicorn app.main:app`. Nustatykite `DATABASE_URL`, `ADMIN_PASSWORD`, `COOKIE_SECURE=false` tik vietiniam HTTP ir pasirinktinai `DEMO_MODE=true`.

```sh
npm run lint
npm run typecheck
npm test
npm run build
# Iš backend katalogo, su ATSKIRA PostgreSQL baze, kurios vardas baigiasi _test:
# DATABASE_URL turi rodyti tik į tą atskirą testavimo bazę.
ADMIN_PASSWORD=local-test-only-password DEMO_MODE=true COOKIE_SECURE=false python -m pytest -q tests
ruff check .
```

Serverio testai išvalo testų bazę prieš kiekvieną testą ir niekada neturi būti nukreipti į naudojamą duomenų bazę. Tikrinami gavimai, išdavimai, grąžinimai, koregavimai, kompensavimai, neigiamo likučio draudimas, tikri vienalaikiai PostgreSQL įrašai, idempotentiškumas, suderinamumas, rolės, sesijos, CSRF, istorijos nekintamumas, perkėlimai ir ataskaitos.

Naršyklės testas skirtas tik **atskirai DEMO aplinkai**: jis sukuria tikras operacijas, keičia fiktyvų suderinamumą ir kalbą. `npm ci`, `npx playwright install chromium`, nustatykite `PRINTTRACK_E2E_PASSWORD` (jūsų DEMO administratoriaus slaptažodį), pasirinktinai `PRINTTRACK_E2E_URL`, tada `npm run test:e2e`. Slaptažodžio į kodą nerašykite. Galima naudoti jau įdiegtą Chromium, nurodant `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`.

LT / EN vertimai: `src/locales/lt.json`, `src/locales/en.json`. Naują funkciją papildykite abiem kalbomis; datos / skaičiai per `useLocaleFormat`, klaidos – kodais per `errors`. Nenaudokite serverio išimčių teksto kaip sąsajos pranešimo.

## Ribos

Ši versija skirta vietiniam demonstravimui ir pagrindiniams apskaitos procesams. Nėra SSO, el. pašto slaptažodžio atkūrimo, automatinių atsarginių kopijų, centralizuoto stebėjimo ar realių gamintojų suderinamumo duomenų importo. Prieš naudojant įstaigoje reikia jos IT saugumo ir diegimo peržiūros. Didelio duomenų kiekio ataskaitos šioje versijoje surenkamos serverio atmintyje; dideliam diegimui reikėtų puslapiavimo ir srautinių eksportų.

Patikrų rezultatai ir jų ribos: [docs/VALIDATION.md](docs/VALIDATION.md).

### Tik Codex debesijos aplinkai

Kai įprastą Docker surinkimą blokuoja debesijos DNS, `deploy/cloud-build.py --project <Compose-projekto-vardas>` gali panaudoti jau suteiktą HTTPS tarpinį serverį ir patikimą sertifikatą. TLS tikrinimas išlieka įjungtas; įprastam Windows paleidimui šio pagalbininko nereikia. `python deploy/init_demo_env.py --demo` yra alternatyva DEMO `.env` sukurti, jei turite Python; esamo failo ji neperrašo.
