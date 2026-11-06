import {
  createHashHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Navigate,
  type RouterHistory,
} from "@tanstack/react-router";

import { RootLayout } from "./RootLayout";
import { HomePage } from "../pages/HomePage";
import { PlannedPage } from "../pages/PlannedPage";
import { SettingsPage } from "../pages/SettingsPage";

const rootRoute = createRootRoute({
  component: RootLayout,
  // Unknown paths go back to Home instead of showing a blank screen.
  notFoundComponent: () => <Navigate to="/" replace />,
});

const routes = [
  createRoute({ getParentRoute: () => rootRoute, path: "/", component: HomePage }),
  createRoute({
    getParentRoute: () => rootRoute,
    path: "/store",
    component: () => <PlannedPage pageKey="store" phase={4} />,
  }),
  createRoute({
    getParentRoute: () => rootRoute,
    path: "/library",
    component: () => <PlannedPage pageKey="library" phase={5} />,
  }),
  createRoute({
    getParentRoute: () => rootRoute,
    path: "/my-pc",
    component: () => <PlannedPage pageKey="myPc" phase={3} />,
  }),
  createRoute({
    getParentRoute: () => rootRoute,
    path: "/compatibility",
    component: () => <PlannedPage pageKey="compatibility" phase={6} />,
  }),
  createRoute({
    getParentRoute: () => rootRoute,
    path: "/performance",
    component: () => <PlannedPage pageKey="performance" phase={7} />,
  }),
  createRoute({ getParentRoute: () => rootRoute, path: "/settings", component: SettingsPage }),
];

const routeTree = rootRoute.addChildren(routes);

/** Hash history: the app is served from local files, so deep links must not hit the server. */
export function createAppRouter(history: RouterHistory = createHashHistory()) {
  return createRouter({ routeTree, history, defaultPreload: "intent" });
}

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}
