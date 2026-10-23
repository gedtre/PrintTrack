import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import lt from "./locales/lt.json";
import en from "./locales/en.json";
export type Language = "lt" | "en";
export const preferenceKey = "printtrack.language";
export function savedLanguage(): Language {
  try {
    return localStorage.getItem(preferenceKey) === "en" ? "en" : "lt";
  } catch {
    return "lt";
  }
}
export function persistLanguage(language: string) {
  document.documentElement.lang = language === "en" ? "en" : "lt";
  try {
    localStorage.setItem(preferenceKey, language);
  } catch {
    /* Private browsing can disable storage. */
  }
}
void i18n.use(initReactI18next).init({
  resources: { lt: { translation: lt }, en: { translation: en } },
  lng: savedLanguage(),
  fallbackLng: "lt",
  supportedLngs: ["lt", "en"],
  interpolation: { escapeValue: false },
});
document.documentElement.lang = i18n.language;
i18n.on("languageChanged", persistLanguage);
export default i18n;
