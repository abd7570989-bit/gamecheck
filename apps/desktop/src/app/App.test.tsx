import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { createAppRouter } from "./router";
import { NAV_ITEMS } from "./nav";
import { initI18n } from "../lib/i18n";

function renderAt(path: string) {
  const router = createAppRouter(createMemoryHistory({ initialEntries: [path] }));
  render(
    <QueryClientProvider client={new QueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

describe("app shell", () => {
  beforeEach(() => {
    initI18n("en");
  });

  it("shows all seven sections in the sidebar", async () => {
    renderAt("/");
    const nav = await screen.findByRole("navigation", { name: "Main navigation" });
    const links = within(nav).getAllByRole("link");
    expect(links).toHaveLength(7);
    expect(links.map((l) => l.textContent)).toEqual([
      "Home",
      "Steam Store",
      "My Library",
      "My PC",
      "Compatibility Checker",
      "Performance",
      "Settings",
    ]);
  });

  it("navigates to every section", async () => {
    const user = userEvent.setup();
    const router = renderAt("/");
    const nav = await screen.findByRole("navigation", { name: "Main navigation" });
    for (const item of NAV_ITEMS) {
      const link = within(nav).getAllByRole("link")[NAV_ITEMS.indexOf(item)]!;
      await user.click(link);
      await waitFor(() => expect(router.state.location.pathname).toBe(item.path));
      expect(link).toHaveAttribute("data-status", "active");
    }
  });

  it("planned sections say they are in development and contain no buttons", async () => {
    renderAt("/store");
    const main = await screen.findByRole("main");
    expect(within(main).getByText(/Planned for phase 4/)).toBeInTheDocument();
    expect(within(main).queryAllByRole("button")).toHaveLength(0);
    expect(within(main).getAllByRole("listitem").length).toBeGreaterThan(0);
  });

  it("switches to Arabic and right-to-left from the top bar", async () => {
    const user = userEvent.setup();
    renderAt("/");
    await user.click(await screen.findByRole("button", { name: "Switch language" }));
    expect(document.documentElement.dir).toBe("rtl");
    expect(await screen.findByRole("navigation", { name: "التنقل الرئيسي" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("الرئيسية");
  });

  it("switches language from Settings", async () => {
    const user = userEvent.setup();
    renderAt("/settings");
    await user.click(await screen.findByRole("radio", { name: "العربية" }));
    expect(document.documentElement.dir).toBe("rtl");
    expect(screen.getByRole("radio", { name: "العربية" })).toBeChecked();
  });

  it("shows app details as unavailable outside the app instead of inventing them", async () => {
    renderAt("/settings");
    const notInApp = await screen.findAllByText("Not running inside the GameCheck app");
    expect(notInApp.length).toBe(4);
  });

  it("sends unknown paths to Home", async () => {
    const router = renderAt("/does-not-exist");
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(await screen.findByRole("heading", { name: "Welcome to GameCheck" })).toBeInTheDocument();
  });
});
