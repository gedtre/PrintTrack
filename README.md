# PrintTrack

Pradinis React / TypeScript / Vite sąsajos ir internacionalizavimo etapas.

## Paleidimas

Reikia Node.js 22+ ir npm.

```sh
npm ci --cache /tmp/printtrack-npm
npm run dev
```

```sh
npm test
npm run typecheck
npm run build
```

## Kalbos

Lietuvių kalba yra numatytoji, nepriklausomai nuo naršyklės kalbos. Viršuje dešinėje esantis LT / EN jungiklis keičia visą įgyvendintą sąsają. Pasirinkimas saugomas `localStorage` raktu `printtrack.language` ir atkuriamas kitą kartą šioje naršyklėje. Jei saugykla nepasiekiama, kalbą vis tiek galima keisti dabartinėje sesijoje. Skirtingų įrenginių ir paskyrų sinchronizavimas dar neįgyvendintas, nes nėra autentifikavimo ar serverio.

Vertimai: `src/locales/lt.json` ir `src/locales/en.json`. Naują funkciją kurkite su abiejų kalbų raktais, naudokite `useTranslation`, venkite tiesioginio sąsajos teksto. Datoms ir skaičiams naudokite `useLocaleFormat`. Duomenų bazės tekstų, kabinetų pavadinimų, pastabų ir kitų naudotojo įvestų duomenų neversti. Validacijos būsenose saugokite kodus, ne išverstą tekstą; pranešimą išverskite atvaizdavimo metu. API klaidas susiekite su `errors` raktais ir nežinomoms klaidoms naudokite `errors.UNKNOWN`. Neatvaizduokite neapdorotų serverio klaidų.

Testai tikrina vertimų raktų atitikimą, kalbos numatytąją reikšmę ir išsaugojimą, validaciją, pranešimus, įvestų duomenų išlikimą bei lokalizuotus formatus.

## Įgyvendinta ir likę darbai

Įgyvendinta adaptyvi navigacija, kalbų jungiklis, lokalizavimo peržiūros forma, nustatymų puslapis ir ataskaitų filtrų sąsajos pagrindas. Apžvalga nerodo išgalvotų statistinių duomenų. Forma duomenų į serverį nesiunčia.

Dar neįgyvendinta: FastAPI, PostgreSQL, migracijos, autentifikavimas, rolės, inventoriaus operacijos, suderinamumo tvirtinimas, duomenimis pagrįstos diagramos, CSV eksportas, Docker diegimas ir likę projekto aprašo reikalavimai. Tai nėra parengta gamybai inventoriaus sistema.
