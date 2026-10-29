import { test, expect } from "@playwright/test";
test("room CSV preview validates metadata, imports atomically and skips existing entries", async ({
  page,
}) => {
  const password = process.env.PRINTTRACK_E2E_PASSWORD;
  if (!password) throw new Error("Set isolated DEMO administrator password");
  await page.goto("/");
  await page
    .getByLabel("Naudotojo vardas")
    .fill(process.env.PRINTTRACK_E2E_USERNAME ?? "admin");
  await page.getByLabel("Slaptažodis").fill(password);
  await page.getByRole("button", { name: "Prisijungti", exact: true }).click();
  await expect(
    page.getByRole("link", { name: /^(Kabinetai|Rooms)$/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: "LT", exact: true }).click();
  expect((await (await page.request.get("/api/health")).json()).demo).toBe(
    true,
  );
  const buildingName = `DEMO import test ${Date.now()}`;
  const response = await page.request.post("/api/buildings", {
    data: { name: buildingName },
  });
  expect(response.status()).toBe(201);
  const building = await response.json();
  const before = (await (await page.request.get("/api/rooms")).json()).length;
  await page.getByRole("link", { name: "Kabinetai", exact: true }).click();
  await page.getByText("Importuoti kabinetus iš CSV", { exact: true }).click();
  const csv =
    "importuoti;numeris;pavadinimas;padalinys;pastatas;aukstas\ntaip;001.;Tyrimų Ąžuolas;DEMO CSV;;\ntaip;202(II lygis);;DEMO CSV;;\nne;1;Registratūra;DEMO CSV;;\n";
  await page.getByLabel("CSV failas").setInputFiles({
    name: "rooms.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv, "utf8"),
  });
  await page
    .getByRole("button", { name: "Peržiūrėti importą", exact: true })
    .click();
  await expect(
    page.getByRole("button", {
      name: "Importuoti patikrintas eilutes",
      exact: true,
    }),
  ).toBeDisabled();
  await expect(
    page
      .getByRole("cell", {
        name: "Trūksta pastato. Trūksta aukšto.",
        exact: true,
      })
      .first(),
  ).toBeVisible();
  expect((await (await page.request.get("/api/rooms")).json()).length).toBe(
    before,
  );
  await page
    .getByRole("combobox", {
      name: "Pastatas (tuštiems CSV laukams)",
      exact: true,
    })
    .selectOption(String(building.id));
  await page
    .getByLabel("Aukštas (tuštiems CSV laukams)", { exact: true })
    .fill("2");
  await page
    .getByRole("button", { name: "Peržiūrėti importą", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText(
    "Paruošta: 2. Esamų: 0. Praleista: 1. Su klaidomis: 0.",
  );
  page.on("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", {
      name: "Importuoti patikrintas eilutes",
      exact: true,
    })
    .click();
  await expect(page.getByRole("status")).toHaveText(
    "Sukurta kabinetų: 2. Esamų: 0. Praleista: 1.",
  );
  const rooms = await (await page.request.get("/api/rooms")).json();
  expect(rooms.length).toBe(before + 2);
  expect(
    rooms.find(
      (r: { building_id: number; number: string }) =>
        r.building_id === building.id && r.number === "001.",
    ).name,
  ).toBe("Tyrimų Ąžuolas");
  expect(
    rooms.some(
      (r: { building_id: number; number: string }) =>
        r.building_id === building.id && r.number === "202(II lygis)",
    ),
  ).toBe(true);
  await page
    .getByRole("button", { name: "Peržiūrėti importą", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText(
    "Paruošta: 0. Esamų: 2. Praleista: 1. Su klaidomis: 0.",
  );
  await expect(
    page.getByRole("button", {
      name: "Importuoti patikrintas eilutes",
      exact: true,
    }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "EN", exact: true }).click();
  await expect(
    page.getByText("Import rooms from CSV", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "LT", exact: true }).click();
});
