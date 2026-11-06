import { Link } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { NAV_ITEMS } from "../app/nav";

export function HomePage() {
  const { t } = useTranslation();
  const sections = NAV_ITEMS.filter((item) => item.key !== "home");

  return (
    <div className="space-y-8">
      <div className="relative overflow-hidden rounded-2xl border border-line bg-gradient-to-br from-surface-2 to-surface p-8">
        <div className="pointer-events-none absolute -top-24 size-72 rounded-full bg-accent/15 blur-3xl ltr:-right-16 rtl:-left-16" />
        <div className="relative flex items-start gap-5">
          <Logo className="size-14 shrink-0" />
          <div className="space-y-2">
            <h2 className="text-3xl font-semibold tracking-tight">{t("home.title")}</h2>
            <p className="max-w-2xl leading-relaxed text-muted">{t("home.intro")}</p>
          </div>
        </div>
      </div>

      <div>
        <h3 className="mb-4 text-sm font-medium tracking-wide text-faint uppercase">{t("home.sectionsTitle")}</h3>
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-3">
          {sections.map(({ key, path, icon: Icon }) => (
            <Link
              key={key}
              to={path}
              aria-label={t("home.open", { section: t(`nav.${key}`) })}
              className="group flex items-center gap-4 rounded-xl border border-line bg-surface/70 p-5 transition-all duration-150 hover:border-accent/50 hover:shadow-glow"
            >
              <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-accent-soft text-accent">
                <Icon className="size-5" aria-hidden />
              </span>
              <span className="flex-1 font-medium">{t(`nav.${key}`)}</span>
              <ChevronRight
                className="size-4 text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-accent rtl:rotate-180 rtl:group-hover:-translate-x-0.5"
                aria-hidden
              />
            </Link>
          ))}
        </div>
      </div>

      <Card>
        <h3 className="mb-2 font-medium">{t("home.statusTitle")}</h3>
        <p className="text-sm leading-relaxed text-muted">{t("home.statusBody")}</p>
      </Card>
    </div>
  );
}
