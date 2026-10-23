import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import i18n, { savedLanguage, preferenceKey } from "../src/i18n";
import lt from "../src/locales/lt.json";
import en from "../src/locales/en.json";
import App from "../src/App";
function leaves(object: object, prefix = ""): string[] {
  return Object.entries(object).flatMap(([key, value]) =>
    typeof value === "object"
      ? leaves(value, `${prefix}${key}.`)
      : [`${prefix}${key}`],
  );
}
beforeEach(async () => {
  localStorage.clear();
  await i18n.changeLanguage("lt");
});
afterEach(cleanup);
describe("internationalization", () => {
  it("has matching nonempty translation keys", () => {
    expect(leaves(lt).sort()).toEqual(leaves(en).sort());
    for (const lang of [lt, en])
      expect(JSON.stringify(lang)).not.toContain('""');
  });
  it("defaults to Lithuanian, restores English and rejects unsupported preferences", () => {
    localStorage.clear();
    expect(savedLanguage()).toBe("lt");
    localStorage.setItem(preferenceKey, "en");
    expect(savedLanguage()).toBe("en");
    localStorage.setItem(preferenceKey, "fr");
    expect(savedLanguage()).toBe("lt");
  });
  it("switches navigation, validation and notifications without changing user data", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <App />
      </MemoryRouter>,
    );
    await user.type(screen.getByLabelText("Pastabos"), "Kambarys Ąžuolas");
    await user.click(screen.getByRole("button", { name: "Išsaugoti" }));
    expect(screen.getByRole("alert").textContent).toBe("Šis laukas privalomas");
    await user.click(screen.getByRole("button", { name: "EN" }));
    expect(screen.getByRole("alert").textContent).toBe(
      "This field is required",
    );
    expect((screen.getByLabelText("Notes") as HTMLTextAreaElement).value).toBe(
      "Kambarys Ąžuolas",
    );
    expect(localStorage.getItem(preferenceKey)).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(screen.getByRole("link", { name: "Printers" })).toBeTruthy();
    await user.type(screen.getByLabelText("Room name"), "Širdies skyrius");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByRole("status").textContent).toContain("Form validated");
    await user.click(screen.getByRole("button", { name: "LT" }));
    expect(screen.getByRole("status").textContent).toContain(
      "Forma patikrinta",
    );
    expect(
      (screen.getByLabelText("Kabineto pavadinimas") as HTMLInputElement).value,
    ).toBe("Širdies skyrius");
  });
  it("formats numbers and dates using the selected locale", async () => {
    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <App />
      </MemoryRouter>,
    );
    expect(
      screen.getByText(new Intl.NumberFormat("lt-LT").format(12345.67), {
        normalizer: (text) => text,
      }),
    ).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "EN" }));
    expect(
      screen.getByText(new Intl.NumberFormat("en-GB").format(12345.67)),
    ).toBeTruthy();
    expect(
      screen.getByText(
        new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(
          new Date(2026, 9, 23),
        ),
      ),
    ).toBeTruthy();
  });
});
