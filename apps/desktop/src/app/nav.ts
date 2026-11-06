import { Cpu, Gauge, House, Library, ListChecks, Settings, Store, type LucideIcon } from "lucide-react";

export type NavKey = "home" | "store" | "library" | "myPc" | "compatibility" | "performance" | "settings";

export interface NavItem {
  key: NavKey;
  path: string;
  icon: LucideIcon;
}

/** The seven main sections, in sidebar order. */
export const NAV_ITEMS: readonly NavItem[] = [
  { key: "home", path: "/", icon: House },
  { key: "store", path: "/store", icon: Store },
  { key: "library", path: "/library", icon: Library },
  { key: "myPc", path: "/my-pc", icon: Cpu },
  { key: "compatibility", path: "/compatibility", icon: ListChecks },
  { key: "performance", path: "/performance", icon: Gauge },
  { key: "settings", path: "/settings", icon: Settings },
];

export function navItemForPath(pathname: string): NavItem {
  return NAV_ITEMS.find((item) => item.path === pathname) ?? NAV_ITEMS[0]!;
}
