import { useTranslation } from "react-i18next";

import { Card } from "../components/Card";
import { useAppInfo } from "../app/useAppInfo";
import { currentLanguage, setLanguage, LANGUAGES, type Language } from "../lib/i18n";
import { inApp, type Probed } from "../lib/ipc";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-6 border-b border-line py-3 last:border-b-0">
      <dt className="shrink-0 text-sm text-muted">{label}</dt>
      <dd className="min-w-0 text-end text-sm break-all">{children}</dd>
    </div>
  );
}

function ProbedText({ value }: { value: Probed<string> | undefined }) {
  const { t } = useTranslation();
  if (value?.status === "known") {
    return (
      <bdi dir="ltr" className="font-mono text-xs">
        {value.value}
      </bdi>
    );
  }
  return <span className="text-faint" title={value?.reason}>{t("common.unavailable")}</span>;
}

export function SettingsPage() {
  const { t } = useTranslation();
  const language = currentLanguage();
  const appInfo = useAppInfo();
  const info = appInfo.data;
  const unavailable = (
    <span className="text-faint">{inApp() ? t("common.unavailable") : t("settings.notInApp")}</span>
  );
  const labels: Record<Language, string> = { ar: t("settings.arabic"), en: t("settings.english") };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold tracking-tight">{t("settings.title")}</h2>

      <Card>
        <fieldset>
          <legend className="mb-1 font-medium">{t("common.language")}</legend>
          <p className="mb-4 text-sm text-muted">{t("settings.languageHint")}</p>
          <div className="flex gap-3">
            {LANGUAGES.map((lng) => (
              <label
                key={lng}
                lang={lng}
                className="flex cursor-pointer items-center gap-2 rounded-lg border border-line px-4 py-2 text-sm transition-colors hover:border-line-strong has-[:checked]:border-accent has-[:checked]:bg-accent-soft"
              >
                <input
                  type="radio"
                  name="language"
                  value={lng}
                  checked={language === lng}
                  onChange={() => void setLanguage(lng)}
                  className="accent-[var(--color-accent)]"
                />
                {labels[lng]}
              </label>
            ))}
          </div>
        </fieldset>
      </Card>

      <Card>
        <h3 className="mb-2 font-medium">{t("settings.aboutTitle")}</h3>
        <dl>
          <Row label={t("settings.version")}>
            {info ? <bdi dir="ltr" className="font-mono">{info.version}</bdi> : appInfo.isLoading ? t("common.loading") : unavailable}
          </Row>
          <Row label={t("settings.build")}>{info ? <bdi dir="ltr">{info.buildProfile}</bdi> : unavailable}</Row>
          <Row label={t("settings.platform")}>
            {info ? <bdi dir="ltr">{`${info.targetOs} ${info.targetArch}`}</bdi> : unavailable}
          </Row>
          <Row label={t("settings.logFolder")}>{info ? <ProbedText value={info.logDir} /> : unavailable}</Row>
        </dl>
        <p className="mt-4 text-xs text-faint">{t("settings.disclaimer")}</p>
      </Card>
    </div>
  );
}
