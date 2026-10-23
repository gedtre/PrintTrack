import { Button } from "./components/ui/button";
import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
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
  Building,
  Layers,
} from "lucide-react";
import { api, ApiError, useWrite, type User } from "./api";
import { ErrorMessage, Loading } from "./components/Shared";
import { ResourcePage, CompatibilityPage } from "./components/Catalog";
import { InventoryPage } from "./components/Inventory";
import { ReportsPage } from "./components/Reports";
import { Dashboard } from "./components/Dashboard";
import { SettingsPage } from "./components/Settings";
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: true, staleTime: 10000 },
      mutations: { retry: false },
    },
  });
}
const sections = [
  "dashboard",
  "printers",
  "rooms",
  "departments",
  "buildings",
  "models",
  "cartridges",
  "inventory",
  "history",
  "reports",
  "settings",
];
const icons = [
  LayoutDashboard,
  Printer,
  DoorOpen,
  Building,
  Building,
  Layers,
  Package,
  Boxes,
  History,
  FileText,
  Settings,
];
function LanguageSwitcher({ user }: { user?: User }) {
  const { t, i18n } = useTranslation();
  const client = useQueryClient();
  const write = useWrite();
  return (
    <div>
      <div className="language" role="group" aria-label={t("common.language")}>
        {(["lt", "en"] as const).map((lang) => (
          <button
            key={lang}
            lang={lang}
            disabled={write.isPending}
            aria-pressed={i18n.resolvedLanguage === lang}
            onClick={() => {
              if (user) {
                write.mutate(
                  {
                    path: "/auth/language",
                    method: "PATCH",
                    body: { language: lang },
                  },
                  {
                    onSuccess: (updated) => {
                      client.setQueryData(["me"], updated);
                      void i18n.changeLanguage(lang);
                    },
                  },
                );
              } else void i18n.changeLanguage(lang);
            }}
          >
            {lang.toUpperCase()}
          </button>
        ))}
      </div>
      <ErrorMessage error={write.error} />
    </div>
  );
}
function LoginPage() {
  const { t } = useTranslation();
  const client = useQueryClient();
  const write = useWrite();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  return (
    <div className="login-layout">
      <section className="card login">
        <div className="page-heading">
          <h1>
            <Printer /> PrintTrack
          </h1>
          <LanguageSwitcher />
        </div>
        <h2>{t("app.login")}</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            write.mutate(
              { path: "/auth/login", body: { username, password } },
              {
                onSuccess: (user) => {
                  client.clear();
                  client.setQueryData(["me"], user);
                },
              },
            );
          }}
        >
          <label>
            {t("fields.username")}
            <input
              autoComplete="username"
              required
              maxLength={80}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label>
            {t("fields.password")}
            <input
              type="password"
              autoComplete="current-password"
              required
              maxLength={200}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <ErrorMessage error={write.error} />
          <Button type="submit" disabled={write.isPending}>
            {t("app.login")}
          </Button>
        </form>
        <p>{t("app.loginHelp")}</p>
      </section>
    </div>
  );
}
function Application() {
  const { t, i18n } = useTranslation();
  const client = useQueryClient();
  const write = useWrite();
  const [search, setSearch] = useState("");
  const profile = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/auth/me"),
    refetchInterval: 60000,
  });
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<{ demo: boolean }>("/health"),
  });
  const user = profile.data;
  useEffect(() => {
    if (user) void i18n.changeLanguage(user.language);
  }, [user?.id, user?.language, i18n, user]);
  if (profile.isLoading) return <Loading />;
  if (profile.error instanceof ApiError && profile.error.status === 401)
    return <LoginPage />;
  if (profile.error)
    return (
      <>
        <ErrorMessage error={profile.error} />
        <button onClick={() => void profile.refetch()}>{t("app.retry")}</button>
      </>
    );
  if (!user) return <LoginPage />;
  const canEdit = user.role !== "viewer";
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
          <div>
            <span className="badge">
              {health.data?.demo ? t("app.demo") : t("app.production")}
            </span>
            <input
              className="global-search"
              aria-label={t("app.globalSearch")}
              placeholder={t("app.globalSearch")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="row-actions">
            <span>{user.username}</span>
            <LanguageSwitcher user={user} />
            <button
              disabled={write.isPending}
              onClick={() =>
                write.mutate(
                  { path: "/auth/logout", method: "POST" },
                  {
                    onSuccess: () => {
                      client.clear();
                      client.setQueryData(["me"], null);
                    },
                  },
                )
              }
            >
              {t("app.logout")}
            </button>
          </div>
        </header>
        <main>
          <ErrorMessage error={write.error} />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            {["printers", "rooms", "departments", "buildings", "models"].map(
              (resource) => (
                <Route
                  key={resource}
                  path={`/${resource}`}
                  element={
                    <ResourcePage
                      key={resource}
                      resource={resource}
                      canEdit={canEdit}
                      search={search}
                    />
                  }
                />
              ),
            )}
            <Route
              path="/cartridges"
              element={
                <>
                  <ResourcePage
                    resource="cartridges"
                    canEdit={canEdit}
                    search={search}
                  />
                  <CompatibilityPage canEdit={canEdit} />
                </>
              }
            />
            <Route
              path="/inventory"
              element={<InventoryPage canEdit={canEdit} />}
            />
            <Route
              path="/history"
              element={<ReportsPage key="history" history canEdit={canEdit} />}
            />
            <Route
              path="/reports"
              element={<ReportsPage key="reports" canEdit={canEdit} />}
            />
            <Route path="/settings" element={<SettingsPage user={user} />} />
            <Route
              path="*"
              element={<p role="alert">{t("errors.NOT_FOUND")}</p>}
            />
          </Routes>
        </main>
      </div>
    </div>
  );
}
export default function App() {
  const [client] = useState(createQueryClient);
  const { t, i18n } = useTranslation();
  useEffect(() => {
    document
      .querySelectorAll<
        HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
      >("input, select, textarea")
      .forEach((element) => element.setCustomValidity(""));
  }, [i18n.resolvedLanguage]);
  return (
    <QueryClientProvider client={client}>
      <div
        onInvalid={(event) => {
          const element = event.target as HTMLInputElement;
          if (element.setCustomValidity)
            element.setCustomValidity(
              t(
                element.validity.valueMissing
                  ? "common.required"
                  : "errors.INVALID_INPUT",
              ),
            );
        }}
        onInput={(event) => {
          const element = event.target as HTMLInputElement;
          if (element.setCustomValidity) element.setCustomValidity("");
        }}
      >
        <Application />
      </div>
    </QueryClientProvider>
  );
}
