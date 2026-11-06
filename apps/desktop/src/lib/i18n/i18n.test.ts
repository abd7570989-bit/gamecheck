import { afterEach, describe, expect, it, vi } from "vitest";

import ar from "../../locales/ar.json";
import en from "../../locales/en.json";
import { detectLanguage, directionOf, initI18n, setLanguage } from ".";

type Tree = { [key: string]: unknown };

/** Every leaf path, with arrays reported by their length so both languages must match. */
function shape(tree: unknown, prefix = ""): string[] {
  if (Array.isArray(tree)) return [`${prefix}[${tree.length}]`];
  if (tree && typeof tree === "object") {
    return Object.entries(tree as Tree).flatMap(([key, value]) => shape(value, prefix ? `${prefix}.${key}` : key));
  }
  return [prefix];
}

function leaves(tree: unknown): unknown[] {
  if (Array.isArray(tree)) return tree;
  if (tree && typeof tree === "object") return Object.values(tree as Tree).flatMap(leaves);
  return [tree];
}

describe("translations", () => {
  it("Arabic and English have exactly the same keys", () => {
    expect(shape(ar).sort()).toEqual(shape(en).sort());
  });

  it("no translation is empty", () => {
    for (const value of [...leaves(ar), ...leaves(en)]) {
      expect(typeof value).toBe("string");
      expect((value as string).trim()).not.toBe("");
    }
  });

  it("interpolation placeholders match between languages", () => {
    const placeholders = (s: string) => (s.match(/\{\{\w+\}\}/g) ?? []).sort();
    const arPaths = shape(ar);
    const get = (tree: unknown, path: string) =>
      path.split(".").reduce<unknown>((node, key) => (node as Tree | undefined)?.[key], tree);
    for (const path of arPaths.filter((p) => !p.endsWith("]"))) {
      expect(placeholders(get(ar, path) as string), path).toEqual(placeholders(get(en, path) as string));
    }
  });
});

describe("language detection", () => {
  afterEach(() => vi.restoreAllMocks());

  it("uses the saved choice first", () => {
    window.localStorage.setItem("gamecheck.language", "ar");
    vi.spyOn(navigator, "language", "get").mockReturnValue("en-US");
    expect(detectLanguage()).toBe("ar");
  });

  it("ignores an invalid saved value", () => {
    window.localStorage.setItem("gamecheck.language", "fr");
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["en-GB"]);
    expect(detectLanguage()).toBe("en");
  });

  it("falls back to an Arabic system language", () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["ar-SA", "en"]);
    expect(detectLanguage()).toBe("ar");
  });

  it("defaults to English for other system languages", () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["de-DE"]);
    expect(detectLanguage()).toBe("en");
  });

  it("still works when storage throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["ar-EG"]);
    expect(detectLanguage()).toBe("ar");
  });
});

describe("direction", () => {
  it("maps languages to text direction", () => {
    expect(directionOf("ar")).toBe("rtl");
    expect(directionOf("en")).toBe("ltr");
  });

  it("updates the document and saves the choice", async () => {
    initI18n("en");
    expect(document.documentElement.dir).toBe("ltr");
    await setLanguage("ar");
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ar");
    expect(window.localStorage.getItem("gamecheck.language")).toBe("ar");
  });

  it("applies the language even if saving fails", async () => {
    initI18n("en");
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    await setLanguage("ar");
    expect(document.documentElement.dir).toBe("rtl");
    vi.restoreAllMocks();
  });
});
