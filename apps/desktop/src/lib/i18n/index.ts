import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import ar from "../../locales/ar.json";
import en from "../../locales/en.json";

export const LANGUAGES = ["ar", "en"] as const;
export type Language = (typeof LANGUAGES)[number];

const STORAGE_KEY = "gamecheck.language";

export function isLanguage(value: unknown): value is Language {
  return typeof value === "string" && (LANGUAGES as readonly string[]).includes(value);
}

export function directionOf(language: Language): "rtl" | "ltr" {
  return language === "ar" ? "rtl" : "ltr";
}

/** Saved choice first, then the system language, then English. */
export function detectLanguage(): Language {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (isLanguage(saved)) return saved;
  } catch {
    // Storage blocked or unavailable: fall through to the system language.
  }
  const system = (navigator.languages?.[0] ?? navigator.language ?? "").toLowerCase();
  return system.startsWith("ar") ? "ar" : "en";
}

function applyToDocument(language: Language) {
  const root = document.documentElement;
  root.lang = language;
  root.dir = directionOf(language);
}

export async function setLanguage(language: Language) {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // The choice still applies for this session.
  }
  await i18n.changeLanguage(language);
}

export function currentLanguage(): Language {
  return isLanguage(i18n.resolvedLanguage) ? i18n.resolvedLanguage : "en";
}

export function initI18n(language: Language = detectLanguage()) {
  if (!i18n.isInitialized) {
    i18n.on("languageChanged", (lng) => {
      if (isLanguage(lng)) applyToDocument(lng);
    });
    void i18n.use(initReactI18next).init({
      resources: { ar: { translation: ar }, en: { translation: en } },
      lng: language,
      fallbackLng: "en",
      supportedLngs: [...LANGUAGES],
      interpolation: { escapeValue: false },
      returnNull: false,
      initAsync: false,
    });
  } else {
    void i18n.changeLanguage(language);
  }
  applyToDocument(language);
  return i18n;
}

export default i18n;
