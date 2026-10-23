import { useTranslation } from "react-i18next";
export function useLocaleFormat() {
  const { i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "en" ? "en-GB" : "lt-LT";
  return {
    number: (value: number) => new Intl.NumberFormat(locale).format(value),
    date: (value: Date) =>
      new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(value),
  };
}
