# Kabinetų importas iš CSV

Administratorius arba IT specialistas: **Kabinetai → Importuoti kabinetus iš CSV**. Skaitytojas importuoti negali.

1. Skiltyje **Pastatai** sukurkite tikrus pastatus. Pastato ir aukšto pagal numerį sistema nenustato.
2. Paruoškite CSV UTF-8 su kabliataškiais arba kableliais. Excel patogiausia redaguoti XLSX tekstinius laukus ir lapą su duomenimis išsaugoti kaip CSV UTF-8.
3. Pasirinkite failą. Jei dalis CSV pastato ir aukšto laukų tušti, galite nurodyti bendras reikšmes **tik jei jos tikrai tinka toms eilutėms**. Užpildyti CSV laukai visada turi pirmenybę prieš bendras reikšmes.
4. Spauskite **Peržiūrėti importą**. Peržiūra nekeičia bazės. Parodomos visos eilutės, praleidimai, klaidos ir nauji padaliniai, kurie bus sukurti.
5. Ištaisykite visas pasirinktų eilučių klaidas faile ir vėl pasirinkite failą / atlikite peržiūrą. Tik tada spauskite **Importuoti patikrintas eilutes** ir patvirtinkite.

## Stulpeliai

```csv
importuoti;numeris;pavadinimas;padalinys;pastatas;aukstas;tipas_saltinyje;vieta_nuo;saltinis;pastaba
```

- `numeris`, `padalinys` – privalomi. Numeris yra tekstas, ne skaičius.
- `importuoti` – `taip` arba `ne` (taip pat priimami `yes/no`, `1/0`). Nesant šio stulpelio eilutės atrenkamos importui, bet vis tiek būtina peržiūra ir patvirtinimas. Tuščia reikšmė šiame stulpelyje laikoma klaida.
- `pavadinimas` – neprivalomas. Jei tuščias, peržiūroje siūlomas „Kabinetas <numeris>“. Tai sugeneruotas pavadinimas, ne nuskaitymas iš šaltinio.
- `pastatas` – tikslus jau esančio pastato pavadinimas; jei tuščias, naudoti galima bendrą pasirinkimą sąsajoje. Pastatai automatiškai nekuriami.
- `aukstas` – tikra aukšto žyma; jei tuščia, galima bendra reikšmė sąsajoje. „II lygis“ nėra automatiškai interpretuojamas kaip antras aukštas.
- `tipas_saltinyje`, `vieta_nuo`, `pastaba` – peržiūrai skirtų dokumentų laukai, neperkeliami į kabinetų duomenų modelį. `saltinis` saugomas importo audito įraše. Šie stulpeliai neprivalomi.

Numerių `101`, `101.`, `119 kab.`, `119_1`, `202(II lygis)` programa nesuvienodina: tai gali būti atskiri šaltinio įrašai arba to paties kabineto variantai. Prieš importą patikrinkite tikras fizines vietas, kad nesukurtumėte dublių.

Viename pastate tas pats tikslus numeris gali būti tik kartą, nepriklausomai nuo padalinio ir aukšto. Jei faile numeris tam pačiam pastatui kartojasi, abi eilutės pažymimos klaidomis. Nekeiskite tikro pastato į išgalvotą vien tam, kad praeitų tikrinimas.

Importas vientisas: klaida bent vienoje pasirinktoje eilutėje neleidžia įrašyti nieko. Identiški esami kabinetai (pastatas, numeris, pavadinimas, padalinys, aukštas) praleidžiami; jei duomenys skiriasi, esamas kabinetas neperrašomas, rodomas konfliktas. Nauji padaliniai ir kabinetai sukuriami vienoje duomenų bazės operacijoje su audito įrašais. Pakartotinis to paties patvirtinto failo importas nekurs tokių pačių įrašų dar kartą.

Ribos: iki 1 MB, iki 500 duomenų eilučių. Tik CSV UTF-8 (BOM leidžiamas), ne XLSX ar Windows-1257. Viešas šablonas: [examples/rooms_import_template.csv](../examples/rooms_import_template.csv). Jame esanti pavyzdinė eilutė numatytai neįtraukiama.

Naudotojo pateiktų nuotraukų išrašai laikomi vietiniame ignoruojamame `local-imports/` kataloge ir neįkeliami į viešą kodo saugyklą.
