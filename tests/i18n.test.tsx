import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import i18n, { savedLanguage, preferenceKey } from "../src/i18n";
import lt from "../src/locales/lt.json";
import en from "../src/locales/en.json";
import App from "../src/App";
import { useLocaleFormat } from "../src/format";
function leaves(object: object, prefix = ""): string[] {
  return Object.entries(object).flatMap(([key, value]) =>
    typeof value === "object"
      ? leaves(value, `${prefix}${key}.`)
      : [`${prefix}${key}`],
  );
}
let account: Record<string, unknown>;
let authenticated: boolean;
let posted: Record<string, unknown> | undefined;
const records = {
  departments: [{ id: 1, name: "Kardiologija" }],
  buildings: [{ id: 1, name: "A korpusas" }],
  rooms: [
    {
      id: 1,
      name: "Ąžuolas",
      number: "101",
      floor: "1",
      building_id: 1,
      department_id: 1,
    },
  ],
  models: [{ id: 1, name: "Fictional 1", manufacturer: "DEMO" }],
  printers: [
    {
      id: 1,
      model_id: 1,
      inventory_number: "P001",
      room_id: 1,
      status: "active",
      archived: false,
    },
  ],
  cartridges: [
    { id: 1, code: "Verified T1", balance: 5 },
    { id: 2, code: "Unverified T2", balance: 7 },
  ],
  compatibility: [
    { id: 1, model_id: 1, cartridge_id: 1, verified: true },
    { id: 2, model_id: 1, cartridge_id: 2, verified: false },
  ],
};
beforeEach(async () => {
  localStorage.clear();
  await i18n.changeLanguage("lt");
  account = {
    id: 1,
    username: "admin",
    role: "admin",
    language: "lt",
    active: true,
  };
  authenticated = true;
  posted = undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input).replace("/api", "").split("?")[0];
      const body = init?.body ? JSON.parse(String(init.body)) : undefined;
      let data: unknown = {};
      let status = 200;
      if (path === "/auth/me") {
        data = authenticated ? account : { detail: "UNAUTHORIZED" };
        status = authenticated ? 200 : 401;
      } else if (path === "/auth/language") {
        account = { ...account, ...body };
        data = account;
      } else if (path === "/auth/login") {
        authenticated = true;
        data = account;
      } else if (path === "/health") data = { demo: true };
      else if (path === "/users") data = [account];
      else if (path === "/transactions" && body) {
        posted = body;
        data = { id: 1, ...body };
      } else if (path === "/reports")
        data = {
          columns: ["code", "balance"],
          rows: [{ id: 1, code: "Verified T1", balance: 5 }],
        };
      else if (path.slice(1) in records)
        data = records[path.slice(1) as keyof typeof records];
      return new Response(JSON.stringify(data), {
        status,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
describe("internationalization", () => {
  it("has matching nonempty translation keys", () => {
    expect(leaves(lt).sort()).toEqual(leaves(en).sort());
    for (const lang of [lt, en])
      expect(JSON.stringify(lang)).not.toContain('""');
  });
  it("defaults to Lithuanian and restores supported browser preferences", () => {
    localStorage.clear();
    expect(savedLanguage()).toBe("lt");
    localStorage.setItem(preferenceKey, "en");
    expect(savedLanguage()).toBe("en");
    localStorage.setItem(preferenceKey, "fr");
    expect(savedLanguage()).toBe("lt");
  });
  it("changes interface language, persists it to the account and preserves room input", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/rooms"]}>
        <App />
      </MemoryRouter>,
    );
    await user.click(await screen.findByRole("button", { name: "Pridėti" }));
    await user.type(screen.getByLabelText("Pavadinimas"), "Širdies skyrius");
    await user.click(screen.getByRole("button", { name: "EN" }));
    await screen.findByRole("button", { name: "Save" });
    expect((screen.getByLabelText("Name") as HTMLInputElement).value).toBe(
      "Širdies skyrius",
    );
    expect(account.language).toBe("en");
    expect(localStorage.getItem(preferenceKey)).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(screen.getByRole("link", { name: "Printers" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "LT" }));
    await screen.findByRole("button", { name: "Išsaugoti" });
    expect(
      (screen.getByLabelText("Pavadinimas") as HTMLInputElement).value,
    ).toBe("Širdies skyrius");
  });
  it("restores the authenticated account preference", async () => {
    account.language = "en";
    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <App />
      </MemoryRouter>,
    );
    expect(
      await screen.findByRole("heading", { name: "Settings" }),
    ).toBeTruthy();
  });
  it("formats dates and numbers after switching languages", async () => {
    function Sample() {
      const f = useLocaleFormat();
      return (
        <div>
          <span>{f.number(12345.67)}</span>
          <span>{f.date(new Date(2026, 9, 23))}</span>
        </div>
      );
    }
    render(<Sample />);
    expect(
      screen.getByText(new Intl.NumberFormat("lt-LT").format(12345.67), {
        normalizer: (text) => text,
      }),
    ).toBeTruthy();
    const { act } = await import("@testing-library/react");
    await act(() => i18n.changeLanguage("en"));
    expect(screen.getByText("12,345.67")).toBeTruthy();
    expect(screen.getByText("23 Oct 2026")).toBeTruthy();
  });
  it("requires sign-in and localizes the login form", async () => {
    authenticated = false;
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    await screen.findByRole("button", { name: "Prisijungti" });
    await user.click(screen.getByRole("button", { name: "EN" }));
    expect(screen.getByLabelText("Username")).toBeTruthy();
    expect(screen.getByLabelText("Password")).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Printers" })).toBeNull();
  });
  it("only offers verified cartridges for issuing and submits the actual selection", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/inventory?printer=1&kind=issue"]}>
        <App />
      </MemoryRouter>,
    );
    const cartridges = await screen.findByLabelText("Kasetė");
    expect(cartridges.textContent).toContain("Verified T1");
    expect(cartridges.textContent).not.toContain("Unverified T2");
    await user.selectOptions(cartridges, "1");
    await user.click(screen.getByRole("button", { name: "Patvirtinti" }));
    await screen.findByRole("status");
    await waitFor(() => expect(posted?.kind).toBe("issue"));
    expect(posted?.quantity).toBe(1);
    expect(posted?.printer_id).toBe(1);
    expect(posted?.cartridge_id).toBe(1);
    expect(posted?.request_id).toMatch(/^[0-9a-f-]{36}$/);
  });
  it("does not expose mutation controls to read-only users", async () => {
    account.role = "viewer";
    render(
      <MemoryRouter initialEntries={["/rooms"]}>
        <App />
      </MemoryRouter>,
    );
    await screen.findByRole("heading", { name: "Kabinetai" });
    expect(screen.queryByRole("button", { name: "Pridėti" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Redaguoti" })).toBeNull();
  });
  it("translates server error codes rather than exposing raw errors", async () => {
    vi.mocked(fetch).mockImplementation(
      async () =>
        new Response(JSON.stringify({ detail: "DATABASE_ERROR" }), {
          status: 503,
        }),
    );
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    expect((await screen.findByRole("alert")).textContent).toBe(
      lt.errors.DATABASE_ERROR,
    );
  });
  it("resets report selection when navigating to transaction history", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/reports"]}>
        <App />
      </MemoryRouter>,
    );
    const type = await screen.findByLabelText("Ataskaitos tipas");
    await user.selectOptions(type, "stock");
    await user.click(screen.getByRole("link", { name: "Operacijų istorija" }));
    await waitFor(() =>
      expect(
        vi
          .mocked(fetch)
          .mock.calls.some(
            ([path]) => String(path) === "/api/reports?report=history",
          ),
      ).toBe(true),
    );
    expect(screen.queryByLabelText("Ataskaitos tipas")).toBeNull();
    expect(screen.getByLabelText("Nuo")).toBeTruthy();
  });
});
