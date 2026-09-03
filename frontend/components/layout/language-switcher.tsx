"use client";

import { useI18n } from "@/lib/i18n/context";
import { localeLabels, locales, type Locale } from "@/lib/i18n/locales";

export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale, t } = useI18n();

  return (
    <label className="flex items-center gap-2 text-xs text-muted-foreground">
      {!compact && <span className="hidden sm:inline">{t.common.language}</span>}
      <select
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
        className="rounded-md border bg-background px-2 py-1.5 text-xs font-medium text-foreground"
        aria-label={t.common.language}
      >
        {locales.map((code) => (
          <option key={code} value={code}>
            {localeLabels[code]}
          </option>
        ))}
      </select>
    </label>
  );
}
