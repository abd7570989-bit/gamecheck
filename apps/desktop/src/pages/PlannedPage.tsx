import { Construction } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Card } from "../components/Card";
import type { NavKey } from "../app/nav";

type PlannedKey = Exclude<NavKey, "home" | "settings">;

/**
 * Placeholder for a section whose phase has not been built yet. It describes what the
 * section will do and deliberately contains no buttons or fake data.
 */
export function PlannedPage({ pageKey, phase }: { pageKey: PlannedKey; phase: number }) {
  const { t } = useTranslation();
  const features = t(`pages.${pageKey}.features`, { returnObjects: true }) as string[];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-2xl font-semibold tracking-tight">{t(`nav.${pageKey}`)}</h2>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-warning/30 bg-warning/10 px-2.5 py-0.5 text-xs font-medium text-warning">
          <Construction className="size-3.5" aria-hidden />
          {t("common.inDevelopment")} · {t("common.plannedPhase", { phase })}
        </span>
      </div>
      <p className="max-w-3xl text-muted">{t(`pages.${pageKey}.description`)}</p>

      <Card>
        <h3 className="mb-4 text-sm font-medium tracking-wide text-faint uppercase">{t("common.plannedFeatures")}</h3>
        <ul className="space-y-3">
          {features.map((feature) => (
            <li key={feature} className="flex gap-3 text-sm">
              <span className="mt-2 size-1.5 shrink-0 rounded-full bg-accent" aria-hidden />
              <span>{feature}</span>
            </li>
          ))}
        </ul>
      </Card>

      <p className="text-sm text-faint">{t("common.notBuiltYet")}</p>
    </div>
  );
}
