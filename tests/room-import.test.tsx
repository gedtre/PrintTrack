import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "../src/i18n";
import i18n from "../src/i18n";
import { RoomImport } from "../src/components/RoomImport";
let invalid = false;
beforeEach(async () => {
  invalid = false;
  await i18n.changeLanguage("lt");
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: RequestInfo | URL) => {
      let data: unknown = [{ id: 1, name: "Patikrintas pastatas" }];
      if (String(path).endsWith("/preview"))
        data = {
          valid: !invalid,
          counts: {
            ready: invalid ? 0 : 1,
            existing: 0,
            skipped: 0,
            error: invalid ? 1 : 0,
          },
          new_departments: ["Naujas skyrius"],
          rows: [
            {
              line: 2,
              number: "001.",
              name: "Kabinetas 001.",
              department: "Naujas skyrius",
              building: invalid ? "" : "Patikrintas pastatas",
              floor: "2",
              status: invalid ? "error" : "ready",
              issues: invalid ? ["BUILDING"] : [],
            },
          ],
        };
      if (String(path).endsWith("/commit"))
        data = { created: 1, existing: 0, skipped: 0 };
      return new Response(JSON.stringify(data), {
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  vi.spyOn(window, "confirm").mockReturnValue(true);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <RoomImport />
    </QueryClientProvider>,
  );
}
async function upload() {
  const user = userEvent.setup();
  await user.click(screen.getByText("Importuoti kabinetus iš CSV"));
  const file = new File(
    ["numeris;padalinys\n001.;Naujas skyrius"],
    "rooms.csv",
    { type: "text/csv" },
  );
  Object.defineProperty(file, "text", {
    value: async () => "numeris;padalinys\n001.;Naujas skyrius",
  });
  await user.upload(screen.getByLabelText("CSV failas"), file);
  await waitFor(() =>
    expect(
      (
        screen.getByRole("button", {
          name: "Peržiūrėti importą",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false),
  );
  return user;
}
it("requires a preview, clears it after changes, and commits only after confirmation", async () => {
  mount();
  const user = await upload();
  expect(
    screen.queryByRole("button", { name: "Importuoti patikrintas eilutes" }),
  ).toBeNull();
  await user.selectOptions(
    screen.getByLabelText("Pastatas (tuštiems CSV laukams)"),
    "1",
  );
  await user.type(screen.getByLabelText("Aukštas (tuštiems CSV laukams)"), "2");
  await user.click(screen.getByRole("button", { name: "Peržiūrėti importą" }));
  await screen.findByRole("cell", { name: "001." });
  expect(
    vi
      .mocked(fetch)
      .mock.calls.some(([path]) => String(path).endsWith("/commit")),
  ).toBe(false);
  await user.type(screen.getByLabelText("Aukštas (tuštiems CSV laukams)"), "A");
  expect(
    screen.queryByRole("button", { name: "Importuoti patikrintas eilutes" }),
  ).toBeNull();
  await user.click(screen.getByRole("button", { name: "Peržiūrėti importą" }));
  await user.click(
    await screen.findByRole("button", {
      name: "Importuoti patikrintas eilutes",
    }),
  );
  await screen.findByText("Sukurta kabinetų: 1. Esamų: 0. Praleista: 0.");
  expect(window.confirm).toHaveBeenCalled();
  const call = vi
    .mocked(fetch)
    .mock.calls.find(([path]) => String(path).endsWith("/commit"))!;
  expect(JSON.parse(String(call[1]?.body))).toMatchObject({
    default_building_id: 1,
    default_floor: "2A",
    csv_text: expect.stringContaining("001."),
  });
});
it("blocks import when the preview reports missing metadata", async () => {
  invalid = true;
  mount();
  const user = await upload();
  await user.click(screen.getByRole("button", { name: "Peržiūrėti importą" }));
  await screen.findByRole("cell", { name: "Trūksta pastato." });
  expect(
    (
      screen.getByRole("button", {
        name: "Importuoti patikrintas eilutes",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
});
it("localizes the import interface in English", async () => {
  await i18n.changeLanguage("en");
  mount();
  expect(screen.getByText("Import rooms from CSV")).toBeTruthy();
});
