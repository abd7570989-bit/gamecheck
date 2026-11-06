import { Outlet, useRouterState } from "@tanstack/react-router";
import { useEffect, useRef } from "react";

import { NAV_ITEMS } from "./nav";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { currentLanguage, directionOf } from "../lib/i18n";
import { reportFrontendReady } from "../lib/ipc";

export function RootLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const reported = useRef(false);

  // Tell the Rust side once that the interface rendered (logged, and used by the CI smoke test).
  useEffect(() => {
    if (reported.current) return;
    reported.current = true;
    const language = currentLanguage();
    reportFrontendReady({
      language,
      direction: directionOf(language),
      route: pathname,
      navItems: document.querySelectorAll("nav a[href]").length || NAV_ITEMS.length,
    }).catch((err: unknown) => console.error("frontend_ready failed", err));
  }, [pathname]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-y-auto">
          <div key={pathname} className="animate-page-in mx-auto max-w-6xl px-8 py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
