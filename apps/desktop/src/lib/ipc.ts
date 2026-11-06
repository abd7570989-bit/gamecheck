/**
 * Typed wrappers around the Rust commands. The frontend never talks to the network
 * or the database directly; everything goes through these calls.
 */
import { invoke, isTauri } from "@tauri-apps/api/core";

export type Probed<T> = { status: "known"; value: T } | { status: "unavailable"; reason: string };

export interface AppInfo {
  name: string;
  version: string;
  buildProfile: string;
  targetOs: string;
  targetArch: string;
  logDir: Probed<string>;
}

export interface FrontendReadyReport {
  language: string;
  direction: string;
  route: string;
  navItems: number;
}

/** True inside the GameCheck window, false in a plain browser (e.g. `vite dev`). */
export function inApp(): boolean {
  return isTauri();
}

export class NotInAppError extends Error {
  constructor() {
    super("Not running inside the GameCheck app");
    this.name = "NotInAppError";
  }
}

export async function getAppInfo(): Promise<AppInfo> {
  if (!inApp()) throw new NotInAppError();
  return invoke<AppInfo>("get_app_info");
}

export async function reportFrontendReady(report: FrontendReadyReport): Promise<void> {
  if (!inApp()) return;
  await invoke("frontend_ready", { report });
}
