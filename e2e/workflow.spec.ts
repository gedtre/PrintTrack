import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
test("demo: sign in, receive, verify, issue, report, reverse and persist language", async ({
  page,
}) => {
  const password = process.env.PRINTTRACK_E2E_PASSWORD;
  if (!password)
    throw new Error(
      "Set PRINTTRACK_E2E_PASSWORD for an isolated demo instance.",
    );
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page
    .getByLabel("Naudotojo vardas")
    .fill(process.env.PRINTTRACK_E2E_USERNAME ?? "admin");
  await page.getByLabel("Slaptažodis").fill(password);
  await page.getByRole("button", { name: "Prisijungti", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Spausdinimo ūkio apžvalga" }),
  ).toBeVisible();
  const health = await page.request.get("/api/health");
  expect((await health.json()).demo).toBe(true);
  const cartridges = await (await page.request.get("/api/cartridges")).json();
  const cartridge = cartridges.find(
    (c: { code: string }) => c.code === "DEMO-T01",
  );
  const printers = await (await page.request.get("/api/printers")).json();
  const printer = printers.find(
    (p: { inventory_number: string }) => p.inventory_number === "DEMO-P001",
  );
  const before = cartridge.balance;
  // Ensure the scenario is repeatable on a dedicated DEMO database.
  expect(
    (
      await page.request.post("/api/compatibility", {
        data: {
          model_id: printer.model_id,
          cartridge_id: cartridge.id,
          verified: false,
          evidence: "DEMO automated scenario reset",
        },
      })
    ).ok(),
  ).toBe(true);
  page.on("dialog", (dialog) =>
    dialog.accept(
      dialog.type() === "prompt" ? "DEMO reversal check" : undefined,
    ),
  );
  await page.getByRole("link", { name: "Sandėlis", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Kasetė", exact: true })
    .selectOption(String(cartridge.id));
  await page.getByLabel("Kiekis", { exact: true }).fill("5");
  await page.getByRole("button", { name: "Patvirtinti", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Operacija įrašyta. Likučiai atnaujinti.",
  );
  await page.goto(`/inventory?printer=${printer.id}&kind=issue`);
  await expect(
    page.getByRole("combobox", { name: "Kasetė", exact: true }),
  ).not.toContainText("DEMO-T01");
  await page.getByRole("link", { name: "Kasečių katalogas" }).click();
  await page
    .getByRole("combobox", { name: "Spausdintuvo modelis", exact: true })
    .selectOption(String(printer.model_id));
  await page
    .getByRole("combobox", { name: "Kasetė", exact: true })
    .selectOption(String(cartridge.id));
  await page.getByLabel("Suderinamumas patvirtintas", { exact: true }).check();
  await page
    .getByLabel("Patikrinimo pagrindas")
    .fill("DEMO · tik fiktyvaus scenarijaus patvirtinimas");
  await page.getByRole("button", { name: "Išsaugoti", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("Pakeitimai išsaugoti.");
  await page.goto(`/inventory?printer=${printer.id}&kind=issue`);
  await page
    .getByRole("combobox", { name: "Kasetė", exact: true })
    .selectOption(String(cartridge.id));
  await page.getByLabel("Kiekis", { exact: true }).fill("1");
  await page.getByLabel("Pastabos", { exact: true }).fill("DEMO E2E išdavimas");
  await page.getByRole("button", { name: "Patvirtinti", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Operacija įrašyta. Likučiai atnaujinti.",
  );
  const after = await (await page.request.get("/api/cartridges")).json();
  expect(after.find((c: { id: number }) => c.id === cartridge.id).balance).toBe(
    before + 4,
  );
  await page.getByRole("link", { name: "Operacijų istorija" }).click();
  await page
    .getByRole("combobox", { name: "Spausdintuvas", exact: true })
    .selectOption(String(printer.id));
  await expect(
    page.getByRole("cell", { name: "DEMO E2E išdavimas", exact: true }).first(),
  ).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Eksportuoti CSV" }).click();
  const download = await downloadPromise;
  const path = await download.path();
  expect(path).toBeTruthy();
  expect(await readFile(path!, "utf8")).toContain("DEMO E2E išdavimas");
  await page.getByRole("link", { name: "Ataskaitos", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Ataskaitos tipas", exact: true })
    .selectOption("stock");
  await expect(
    page.getByRole("cell", { name: "DEMO-T01", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Operacijų istorija" }).click();
  const issueRow = page
    .getByRole("row")
    .filter({
      has: page.getByRole("cell", { name: "DEMO E2E išdavimas", exact: true }),
    })
    .first();
  await issueRow
    .getByRole("button", { name: "Atšaukti operaciją", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText(
    "Operacija įrašyta. Likučiai atnaujinti.",
  );
  const reversed = await (await page.request.get("/api/cartridges")).json();
  expect(
    reversed.find((c: { id: number }) => c.id === cartridge.id).balance,
  ).toBe(before + 5);
  await page.getByRole("link", { name: "Ataskaitos", exact: true }).click();
  // Confirm HTTP-only authentication survives reload and account language persists.
  await page.getByRole("button", { name: "EN", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Reports", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Reports", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Rooms", exact: true }).click();
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill("DEMO Ąžuolas");
  await page.getByRole("button", { name: "LT", exact: true }).click();
  await expect(page.getByLabel("Pavadinimas", { exact: true })).toHaveValue(
    "DEMO Ąžuolas",
  );
  await page.getByRole("button", { name: "Atšaukti", exact: true }).click();
  await page.getByRole("button", { name: "Atsijungti", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Prisijungti", exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
