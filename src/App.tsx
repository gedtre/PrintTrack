import { useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Printer,
  LayoutDashboard,
  Boxes,
  Settings,
  FileText,
  DoorOpen,
  History,
  Package,
} from "lucide-react";
import { useLocaleFormat } from "./format";
const sections = [
  "dashboard",
  "printers",
  "rooms",
  "cartridges",
  "inventory",
  "history",
  "reports",
  "settings",
] as const;
const icons = [
  LayoutDashboard,
  Printer,
  DoorOpen,
  Package,
  Boxes,
  History,
  FileText,
  Settings,
];
function PreviewForm() {
  const { t } = useTranslation();
  const [room, setRoom] = useState("");
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [success, setSuccess] = useState(false);
  return (
    <section className="card">
      <h2>{t("form.title")}</h2>
      <p>{t("form.description")}</p>
      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          setSubmitted(true);
          setSuccess(!!room.trim());
        }}
      >
        <label htmlFor="room">{t("form.room")}</label>
        <input
          id="room"
          value={room}
          aria-required="true"
          aria-invalid={submitted && !room.trim()}
          aria-describedby={
            submitted && !room.trim() ? "room-error" : undefined
          }
          onChange={(e) => {
            setRoom(e.target.value);
            setSuccess(false);
          }}
        />
        {submitted && !room.trim() && (
          <p id="room-error" role="alert" className="error">
            {t("common.required")}
          </p>
        )}
        <label htmlFor="notes">{t("form.notes")}</label>
        <textarea
          id="notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        <button className="primary" type="submit">
          {t("common.save")}
        </button>
        {success && <p role="status">{t("form.success")}</p>}
      </form>
    </section>
  );
}
function Dashboard() {
  const { t } = useTranslation();
  return (
    <>
      <h1>{t("dashboard.title")}</h1>
      <p>{t("dashboard.subtitle")}</p>
      <div className="metrics">
        {["total", "active", "stock", "types", "low", "issued"].map((key) => (
          <section className="card" key={key}>
            <p>{t(`dashboard.${key}`)}</p>
            <strong aria-label={t("common.unavailable")}>—</strong>
          </section>
        ))}
      </div>
      <div className="columns">
        {["consumption", "recent"].map((key) => (
          <section className="card" key={key}>
            <h2>{t(`dashboard.${key}`)}</h2>
            <p className="empty">{t("common.unavailable")}</p>
          </section>
        ))}
      </div>
    </>
  );
}
function SettingsPage() {
  const { t } = useTranslation();
  const f = useLocaleFormat();
  return (
    <>
      <h1>{t("settings.title")}</h1>
      <section className="card">
        <p>{t("settings.preference")}</p>
        <dl>
          <dt>{t("settings.date")}</dt>
          <dd>{f.date(new Date(2026, 9, 23))}</dd>
          <dt>{t("settings.number")}</dt>
          <dd>{f.number(12345.67)}</dd>
        </dl>
      </section>
      <PreviewForm />
    </>
  );
}
function Reports() {
  const { t } = useTranslation();
  return (
    <>
      <h1>{t("reports.title")}</h1>
      <section className="card">
        <div className="columns">
          <label>
            {t("reports.from")}
            <input type="date" />
          </label>
          <label>
            {t("reports.to")}
            <input type="date" />
          </label>
        </div>
        <p>{t("reports.empty")}</p>
        <button disabled>{t("reports.export")}</button>
      </section>
    </>
  );
}
export default function App() {
  const { t, i18n } = useTranslation();
  return (
    <div className="app">
      <aside>
        <div className="brand">
          <Printer /> PrintTrack
        </div>
        <nav>
          {sections.map((key, index) => {
            const Icon = icons[index];
            return (
              <NavLink key={key} to={key === "dashboard" ? "/" : `/${key}`} end>
                <Icon size={19} />
                {t(`nav.${key}`)}
              </NavLink>
            );
          })}
        </nav>
      </aside>
      <div className="workspace">
        <header>
          <span className="badge">{t("common.prototype")}</span>
          <div
            className="language"
            role="group"
            aria-label={t("common.language")}
          >
            {(["lt", "en"] as const).map((lang) => (
              <button
                key={lang}
                lang={lang}
                aria-pressed={i18n.resolvedLanguage === lang}
                onClick={() => void i18n.changeLanguage(lang)}
              >
                {lang.toUpperCase()}
              </button>
            ))}
          </div>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/reports" element={<Reports />} />
            {sections
              .filter((s) => !["dashboard", "settings", "reports"].includes(s))
              .map((section) => (
                <Route
                  key={section}
                  path={`/${section}`}
                  element={
                    <>
                      <h1>{t(`nav.${section}`)}</h1>
                      <section className="card empty">
                        {t("common.unavailable")}
                      </section>
                    </>
                  }
                />
              ))}
            <Route
              path="*"
              element={<p role="alert">{t("errors.UNKNOWN")}</p>}
            />
          </Routes>
        </main>
      </div>
    </div>
  );
}
