import { useTranslation } from "react-i18next";
import { useLocaleFormat } from "../format";
import { errorCode, type Row } from "../api";
export function ErrorMessage({ error }: { error: unknown }) {
  const { t } = useTranslation();
  if (!error) return null;
  return (
    <p role="alert" className="error">
      {t(`errors.${errorCode(error)}`, { defaultValue: t("errors.UNKNOWN") })}
    </p>
  );
}
export function Loading() {
  const { t } = useTranslation();
  return <p role="status">{t("common.loading")}</p>;
}
export function Table({
  rows,
  columns,
  actions,
}: {
  rows: Row[];
  columns: string[];
  actions?: (row: Row) => React.ReactNode;
}) {
  const { t } = useTranslation();
  const format = useLocaleFormat();
  function cell(row: Row, key: string) {
    const value = row[key];
    if (value === null || value === undefined || value === "") return "—";
    if (key === "occurred_at" || key === "verified_at")
      return format.dateTime(new Date(String(value)));
    if (key === "installation_date")
      return format.date(new Date(`${value}T12:00:00`));
    if (
      ["kind", "color", "status", "role"].includes(key) &&
      typeof value === "string"
    )
      return t(`values.${value}`, { defaultValue: value });
    if (typeof value === "boolean") return t(value ? "app.yes" : "app.no");
    if (typeof value === "number") return format.number(value);
    return String(value);
  }
  return rows.length ? (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((key) => (
              <th key={key}>{t(`fields.${key}`)}</th>
            ))}
            {actions && <th>{t("app.actions")}</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {columns.map((key) => (
                <td key={key}>{cell(row, key)}</td>
              ))}
              {actions && (
                <td>
                  <div className="row-actions">{actions(row)}</div>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <p className="empty">{t("common.empty")}</p>
  );
}
