import { useRouterState } from "@tanstack/react-router";
import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";

import { navItemForPath } from "./nav";
import { currentLanguage, setLanguage } from "../lib/i18n";

export function Topbar() {
  const { t } = useTranslation();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const item = navItemForPath(pathname);
  const next = currentLanguage() === "ar" ? "en" : "ar";

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-line px-8">
      <h1 className="text-base font-medium text-text">{t(`nav.${item.key}`)}</h1>
      <button
        type="button"
        onClick={() => void setLanguage(next)}
        className="flex items-center gap-2 rounded-lg border border-line px-3 py-1.5 text-sm text-muted transition-colors hover:border-line-strong hover:text-text"
        aria-label={t("common.switchLanguage")}
      >
        <Languages className="size-4" aria-hidden />
        <span lang={next}>{next === "ar" ? t("settings.arabic") : t("settings.english")}</span>
      </button>
    </header>
  );
}
