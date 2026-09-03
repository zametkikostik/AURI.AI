import type { Locale } from "./locales";
import type { Dictionary } from "./dictionaries/en";
import en from "./dictionaries/en";
import ru from "./dictionaries/ru";
import bg from "./dictionaries/bg";
import th from "./dictionaries/th";
import it from "./dictionaries/it";

const map: Record<Locale, Dictionary> = { en, ru, bg, th, it };

export function getDictionary(locale: Locale): Dictionary {
  return map[locale] ?? en;
}
