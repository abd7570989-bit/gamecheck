import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { NAV_ITEMS } from "./nav";
import { useAppInfo } from "./useAppInfo";
import { Logo } from "../components/Logo";

export function Sidebar() {
  const { t } = useTranslation();
  const appInfo = useAppInfo();

  return (
    <aside className="flex w-64 shrink-0 flex-col border-e border-line bg-surface/80 backdrop-blur">
      <div className="flex items-center gap-3 px-5 pt-6 pb-8">
        <Logo className="size-9" />
        <div className="min-w-0">
          <div className="text-lg font-semibold tracking-tight" dir="ltr">
            {t("app.name")}
          </div>
          <div className="truncate text-xs text-muted">{t("app.tagline")}</div>
        </div>
      </div>

      <nav aria-label={t("nav.main")} className="flex-1 px-3">
        <ul className="space-y-1">
          {NAV_ITEMS.map(({ key, path, icon: Icon }) => (
            <li key={key}>
              <Link
                to={path}
                activeOptions={{ exact: true }}
                className="group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-text data-[status=active]:bg-accent-soft data-[status=active]:text-text data-[status=active]:shadow-[inset_3px_0_0_var(--color-accent)] rtl:data-[status=active]:shadow-[inset_-3px_0_0_var(--color-accent)]"
              >
                <Icon className="size-[18px] shrink-0 transition-colors group-data-[status=active]:text-accent" aria-hidden />
                <span className="truncate">{t(`nav.${key}`)}</span>
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-line px-5 py-4 text-xs text-faint">
        <span>{t("app.devBuild")}</span>{" "}
        <bdi dir="ltr" className="font-mono">
          {appInfo.data ? `v${appInfo.data.version}` : ""}
        </bdi>
      </div>
    </aside>
  );
}
