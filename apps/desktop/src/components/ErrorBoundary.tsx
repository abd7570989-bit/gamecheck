import { Component, type ErrorInfo, type ReactNode } from "react";
import { error as logError } from "@tauri-apps/plugin-log";

import i18n from "../lib/i18n";
import { inApp } from "../lib/ipc";

interface State {
  failed: boolean;
}

/** Last line of defence: log the error and offer a reload instead of a blank window. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(err: Error, info: ErrorInfo) {
    const message = `UI error: ${err.message}\n${info.componentStack ?? ""}`;
    console.error(message);
    if (inApp()) void logError(message).catch(() => undefined);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div role="alert" className="flex h-screen flex-col items-center justify-center gap-4 p-8 text-center">
        <h1 className="text-xl font-semibold">{i18n.t("error.title")}</h1>
        <p className="max-w-md text-muted">{i18n.t("error.body")}</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="rounded-lg bg-accent-strong px-4 py-2 text-sm font-medium text-white hover:bg-accent"
        >
          {i18n.t("error.reload")}
        </button>
      </div>
    );
  }
}
