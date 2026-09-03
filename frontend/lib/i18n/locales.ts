export const locales = ["en", "ru", "bg", "th", "it"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";

export const localeLabels: Record<Locale, string> = {
  en: "English",
  ru: "Русский",
  bg: "Български",
  th: "ไทย",
  it: "Italiano",
};

export function isLocale(value: string): value is Locale {
  return (locales as readonly string[]).includes(value);
}
