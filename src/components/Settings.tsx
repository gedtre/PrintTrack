import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, useWrite, type Row, type User } from "../api";
import { ErrorMessage, Table } from "./Shared";
export function SettingsPage({ user }: { user: User }) {
  const { t } = useTranslation();
  const write = useWrite();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("viewer");
  const users = useQuery({
    queryKey: ["users"],
    queryFn: () => api<Row[]>("/users"),
    enabled: user.role === "admin",
  });
  return (
    <>
      <h1>{t("nav.settings")}</h1>
      <section className="card">
        <h2>{user.username}</h2>
        <p>{t(`values.${user.role}`)}</p>
        <p>{t("settings.preference")}</p>
      </section>
      {user.role === "admin" && (
        <section className="card">
          <h2>{t("app.users")}</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              write.mutate(
                { path: "/users", body: { username, password, role } },
                {
                  onSuccess: () => {
                    setUsername("");
                    setPassword("");
                  },
                },
              );
            }}
          >
            <div className="form-grid">
              <label>
                {t("fields.username")}
                <input
                  autoComplete="off"
                  maxLength={80}
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </label>
              <label>
                {t("fields.password")}
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={12}
                  maxLength={200}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <label>
                {t("fields.role")}
                <select value={role} onChange={(e) => setRole(e.target.value)}>
                  {["admin", "it", "viewer"].map((r) => (
                    <option key={r} value={r}>
                      {t(`values.${r}`)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <button className="primary" disabled={write.isPending}>
              {t("app.add")}
            </button>
          </form>
          <ErrorMessage error={write.error ?? users.error} />
          {write.isSuccess && <p role="status">{t("app.saved")}</p>}
          <Table
            rows={users.data ?? []}
            columns={["username", "role", "active"]}
            actions={(row) =>
              row.id !== user.id ? (
                <>
                  <select
                    aria-label={`${t("fields.role")} ${row.username}`}
                    value={String(row.role)}
                    disabled={write.isPending}
                    onChange={(e) =>
                      write.mutate({
                        path: `/users/${row.id}`,
                        method: "PUT",
                        body: { role: e.target.value, active: row.active },
                      })
                    }
                  >
                    {["admin", "it", "viewer"].map((r) => (
                      <option key={r} value={r}>
                        {t(`values.${r}`)}
                      </option>
                    ))}
                  </select>
                  <button
                    disabled={write.isPending}
                    onClick={() => {
                      if (window.confirm(t("app.confirmUserChange")))
                        write.mutate({
                          path: `/users/${row.id}`,
                          method: "PUT",
                          body: { role: row.role, active: !row.active },
                        });
                    }}
                  >
                    {t(row.active ? "app.disable" : "app.enable")}
                  </button>
                </>
              ) : null
            }
          />
        </section>
      )}
    </>
  );
}
